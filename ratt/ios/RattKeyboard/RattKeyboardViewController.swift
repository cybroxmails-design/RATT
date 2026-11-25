// iOS RattKeyboardViewController.swift - Slot Palette & Deletion Handling
// (`mobile_implimentation.pdf` Section 6: Phase 3 iPhone Slot Palette Extension)
//
// Because iOS strictly prohibits floating pop-ups over third-party apps, RATT for iPhone
// utilizes Apple's official UIInputViewController. The user stays on their standard Apple
// keyboard for typing; tapping the Globe ([GLOBE]) icon expands the RATT Slot Palette
// showing 10 cards synced from the desktop.

import UIKit

class RattKeyboardViewController: UIInputViewController {
    private let dataManager = AppGroupDataManager.shared
    private let slotStore = KeychainSlotStore.shared
    private var slotCards: [Int: UIButton] = [:]
    private var statusBanner: UILabel?

    override func viewDidLoad() {
        super.viewDidLoad()
        _ = SecurityHardening.enforceRuntimeDefense()
        view.backgroundColor = UIColor(red: 0.05, green: 0.08, blue: 0.13, alpha: 1.0)
        setupSlotPaletteGrid()
        observeDarwinDeletionNotification()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleSlotClearedNotification),
            name: .slotCleared,
            object: nil
        )
    }

    @objc private func clearAllPaletteSlots() {
        dataManager.clearAllSlots()
        slotStore.clearAllSlots()
        refreshPaletteCards()
        statusBanner?.text = "Cleared all 10 slots"
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        _ = dataManager.importSlotsFromPasteboardCarrier()
        refreshPaletteCards()
        pullSlotsFromLocalhostIfAvailable()
    }

    /// Fallback for Sideloadly Free Apple ID installs where App Group entitlement is stripped:
    /// Fetches all 10 slots from the local RATT container app listener on 127.0.0.1:49211.
    private func pullSlotsFromLocalhostIfAvailable() {
        guard let url = URL(string: "http://127.0.0.1:49211/get_all_slots") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.timeoutInterval = 0.8
        req.setValue(dataManager.getOrCreateSyncToken(), forHTTPHeaderField: "X-RATT-Token")
        URLSession.shared.dataTask(with: req) { [weak self] data, _, _ in
            guard let self = self,
                  let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let slots = json["slots"] as? [String: String] else {
                return
            }
            var updated = false
            for (k, v) in slots {
                if let sId = Int(k), (1...10).contains(sId), !v.isEmpty {
                    _ = self.slotStore.encryptAndStore(slot: sId, text: v)
                    _ = self.dataManager.saveSlot(id: sId, content: v)
                    updated = true
                }
            }
            if updated {
                DispatchQueue.main.async {
                    self.refreshPaletteCards()
                }
            }
        }.resume()
    }

    private let pcSlotHexColors = [
        "#00BFFF", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899",
        "#3B82F6", "#14B8A6", "#EF4444", "#EAB308", "#06B6D4"
    ]

    private func colorFromHex(_ hex: String) -> UIColor {
        var int: UInt64 = 0
        let cleanHex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        Scanner(string: cleanHex).scanHexInt64(&int)
        let r = CGFloat((int >> 16) & 0xFF) / 255.0
        let g = CGFloat((int >> 8) & 0xFF) / 255.0
        let b = CGFloat(int & 0xFF) / 255.0
        return UIColor(red: r, green: g, blue: b, alpha: 1.0)
    }

    func didSelectSlot(_ slot: RattSlot) {
        guard slotStore.canAccessSlot(slot.id) else {
            statusBanner?.text = "Slot #\(slot.id) is not available on your plan."
            return
        }
        // IOS-03: Use localOnly + 60s expiration so sensitive items never leak via Universal Clipboard
        let pasteOpts: [UIPasteboard.OptionsKey: Any] = [
            .localOnly: true,
            .expirationDate: Date().addingTimeInterval(60)
        ]
        // Phase 1: Native Images
        if slot.kind == "image" || slot.kind == "diagram" {
            if let dataB64 = slot.dataBase64, let imgData = Data(base64Encoded: dataB64), UIImage(data: imgData) != nil {
                UIPasteboard.general.setItems([["public.png": imgData]], options: pasteOpts)
                let generator = UINotificationFeedbackGenerator()
                generator.notificationOccurred(.success)
                statusBanner?.text = "Image Slot #\(slot.id) copied locally (60s TTL)."
                return
            }
        }
        // Phase 3: Documents and Media
        if slot.kind == "files" {
            let docName = slot.fileName ?? "Document"
            guard RattSecurityGuard.isSafeFileName(docName) else {
                statusBanner?.text = "Blocked unsafe file type: \(docName)"
                return
            }
            if let dataB64 = slot.dataBase64, let fileData = Data(base64Encoded: dataB64) {
                let mime = slot.mimeType ?? "public.data"
                UIPasteboard.general.setItems([[mime: fileData, "public.data": fileData]], options: pasteOpts)
            }
            let generator = UINotificationFeedbackGenerator()
            generator.notificationOccurred(.success)
            statusBanner?.text = "\(docName) copied locally (60s TTL)."
            return
        }
        // IOS-03: Prevent accidental clipboard injection into secure password fields
        if self.textDocumentProxy.isSecureTextEntry == true {
            statusBanner?.text = "Injection blocked on secure password field."
            return
        }
        let (isSafe, clean) = RattSecurityGuard.sanitizeText(slot.content)
        if isSafe {
            self.textDocumentProxy.insertText(clean)
            statusBanner?.text = "Injected Slot #\(slot.id) • Hold to clear"
        }
    }

    @objc private func handleCardLongPress(_ gesture: UILongPressGestureRecognizer) {
        if gesture.state == .began, let btn = gesture.view as? UIButton {
            let slotId = btn.tag
            dataManager.clearSlot(id: slotId)
            slotStore.clearSlot(slotId)
            refreshPaletteCards()
            statusBanner?.text = "Cleared Slot #\(slotId)"
        }
    }

    func observeDarwinDeletionNotification() {
        CFNotificationCenterAddObserver(CFNotificationCenterGetDarwinNotifyCenter(),
            nil, { _, _, _, _, _ in NotificationCenter.default.post(name: .slotCleared, object: nil) },
            "com.cybrox.ratt.slotCleared" as CFString, nil, .deliverImmediately)
    }

    @objc private func handleSlotClearedNotification() {
        DispatchQueue.main.async { [weak self] in
            self?.refreshPaletteCards()
            self?.statusBanner?.text = "Slot cleared from PC (<100ms)"
        }
    }

    func setupSlotPaletteGrid() {
        let header = UIView(frame: CGRect(x: 0, y: 0, width: view.bounds.width, height: 30))
        header.autoresizingMask = [.flexibleWidth]
        header.backgroundColor = UIColor(red: 0.04, green: 0.07, blue: 0.11, alpha: 1.0)

        let title = UILabel(frame: CGRect(x: 12, y: 5, width: 170, height: 20))
        title.text = "RATT v2 Slot Palette"
        title.font = UIFont.boldSystemFont(ofSize: 12)
        title.textColor = UIColor(red: 0.01, green: 0.65, blue: 0.98, alpha: 1.0)
        header.addSubview(title)

        let banner = UILabel(frame: CGRect(x: 185, y: 5, width: max(120, view.bounds.width - 230), height: 20))
        banner.autoresizingMask = [.flexibleWidth]
        banner.font = UIFont.systemFont(ofSize: 11)
        banner.textColor = UIColor(white: 0.75, alpha: 1.0)
        banner.text = "Tap a slot card to inject • Tap 🌐 for Apple Keyboard"
        header.addSubview(banner)
        self.statusBanner = banner

        let clearAllBtn = UIButton(type: .system)
        clearAllBtn.frame = CGRect(x: view.bounds.width - 96, y: 3, width: 54, height: 24)
        clearAllBtn.autoresizingMask = [.flexibleLeftMargin]
        clearAllBtn.setTitle("Clear All", for: .normal)
        clearAllBtn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 10.5)
        clearAllBtn.setTitleColor(UIColor(red: 0.94, green: 0.27, blue: 0.27, alpha: 1.0), for: .normal)
        clearAllBtn.addTarget(self, action: #selector(clearAllPaletteSlots), for: .touchUpInside)
        header.addSubview(clearAllBtn)

        let globeBtn = UIButton(type: .system)
        globeBtn.frame = CGRect(x: view.bounds.width - 38, y: 3, width: 32, height: 24)
        globeBtn.autoresizingMask = [.flexibleLeftMargin]
        globeBtn.setTitle("🌐", for: .normal)
        globeBtn.addTarget(self, action: #selector(handleInputModeList(from:with:)), for: .allTouchEvents)
        header.addSubview(globeBtn)

        view.addSubview(header)

        let gridContainer = UIStackView(frame: CGRect(x: 8, y: 34, width: view.bounds.width - 16, height: 156))
        gridContainer.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        gridContainer.axis = .vertical
        gridContainer.distribution = .fillEqually
        gridContainer.spacing = 6

        for rowIdx in 0..<2 {
            let rowStack = UIStackView()
            rowStack.axis = .horizontal
            rowStack.distribution = .fillEqually
            rowStack.spacing = 6

            for colIdx in 1...5 {
                let slotId = rowIdx * 5 + colIdx
                let card = UIButton(type: .system)
                card.tag = slotId
                card.titleLabel?.font = UIFont.boldSystemFont(ofSize: 11)
                card.titleLabel?.numberOfLines = 2
                card.titleLabel?.textAlignment = .center
                card.setTitle("Slot \(slotId)\n[Empty]", for: .normal)
                card.setTitleColor(UIColor(white: 0.70, alpha: 1.0), for: .normal)
                card.backgroundColor = UIColor(red: 0.09, green: 0.13, blue: 0.20, alpha: 1.0)
                card.layer.cornerRadius = 6
                card.layer.borderWidth = 1
                card.layer.borderColor = UIColor(white: 0.25, alpha: 1.0).cgColor

                let longPress = UILongPressGestureRecognizer(target: self, action: #selector(handleCardLongPress(_:)))
                card.addGestureRecognizer(longPress)

                card.addAction(UIAction { [weak self] _ in
                    guard let self = self else { return }
                    if let slot = self.dataManager.loadSlot(id: slotId) {
                        self.didSelectSlot(slot)
                    } else {
                        self.statusBanner?.text = "Slot #\(slotId) is [Empty]"
                    }
                }, for: .touchUpInside)

                slotCards[slotId] = card
                rowStack.addArrangedSubview(card)
            }
            gridContainer.addArrangedSubview(rowStack)
        }

        view.addSubview(gridContainer)
        refreshPaletteCards()
    }

    func refreshPaletteCards() {
        for (slotId, card) in slotCards {
            let isUnlocked = slotStore.canAccessSlot(slotId)
            let color = colorFromHex(pcSlotHexColors[slotId - 1])

            if !isUnlocked {
                card.setTitle("🔒 Slot \(slotId)\n[Locked]", for: .normal)
                card.setTitleColor(UIColor(white: 0.40, alpha: 1.0), for: .normal)
                card.layer.borderColor = UIColor(white: 0.18, alpha: 1.0).cgColor
            } else if let slot = dataManager.loadSlot(id: slotId), !slot.content.isEmpty {
                let badge = slot.kind == "image" ? "🖼️ " : (slot.kind == "files" ? "📄 " : "")
                let preview = slot.content.count > 14 ? String(slot.content.prefix(12)) + ".." : slot.content
                card.setTitle("Slot \(slotId)\n\(badge)\(preview)", for: .normal)
                card.setTitleColor(UIColor.white, for: .normal)
                card.layer.borderColor = color.cgColor
                card.layer.borderWidth = 1.5
            } else {
                card.setTitle("Slot \(slotId)\n[Empty]", for: .normal)
                card.setTitleColor(UIColor(white: 0.65, alpha: 1.0), for: .normal)
                card.layer.borderColor = UIColor(white: 0.25, alpha: 1.0).cgColor
                card.layer.borderWidth = 1.0
            }
        }
    }
}
