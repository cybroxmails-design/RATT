// iOS RattKeyboardViewController.swift - "Paste from RATT" In-Place Filled Slot Chooser
// When the user clicks "📋 Paste from RATT" on the RATT iOS Keyboard, the slots that contain
// data appear at the exact same place so the user can choose which slot to paste from.

import UIKit

class RattKeyboardViewController: UIInputViewController {
    private let dataManager = AppGroupDataManager.shared
    private let slotStore = KeychainSlotStore.shared
    private var statusBanner: UILabel?
    private var pasteFromRattBtn: UIButton?
    private var filledSlotsScroll: UIScrollView?
    private var filledSlotsStack: UIStackView?
    private var showingSlotChoices: Bool = false

    private let pcSlotHexColors = [
        "#00BFFF", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899",
        "#3B82F6", "#14B8A6", "#EF4444", "#EAB308", "#06B6D4"
    ]

    override func viewDidLoad() {
        super.viewDidLoad()
        _ = SecurityHardening.enforceRuntimeDefense()
        view.backgroundColor = UIColor(red: 0.05, green: 0.08, blue: 0.13, alpha: 1.0)
        setupKeyboardLayout()
        observeDarwinDeletionNotification()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleSlotClearedNotification),
            name: .slotCleared,
            object: nil
        )
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        _ = dataManager.importSlotsFromPasteboardCarrier()
        rebuildFilledSlotChoices()
        pullSlotsFromLocalhostIfAvailable()
    }

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
                if let sId = Int(k), (1...10).contains(sId) {
                    if !v.isEmpty {
                        _ = self.slotStore.encryptAndStore(slot: sId, text: v)
                        _ = self.dataManager.saveSlot(id: sId, content: v)
                        updated = true
                    }
                }
            }
            if updated {
                DispatchQueue.main.async {
                    self.rebuildFilledSlotChoices()
                }
            }
        }.resume()
    }

    private func colorFromHex(_ hex: String) -> UIColor {
        var int: UInt64 = 0
        let cleanHex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        Scanner(string: cleanHex).scanHexInt64(&int)
        let r = CGFloat((int >> 16) & 0xFF) / 255.0
        let g = CGFloat((int >> 8) & 0xFF) / 255.0
        let b = CGFloat(int & 0xFF) / 255.0
        return UIColor(red: r, green: g, blue: b, alpha: 1.0)
    }

    private func setupKeyboardLayout() {
        // 1. Header Bar
        let header = UIView(frame: CGRect(x: 0, y: 0, width: view.bounds.width, height: 30))
        header.autoresizingMask = [.flexibleWidth]
        header.backgroundColor = UIColor(red: 0.04, green: 0.07, blue: 0.11, alpha: 1.0)

        let title = UILabel(frame: CGRect(x: 10, y: 5, width: 120, height: 20))
        title.text = "RATT v2 Keyboard"
        title.font = UIFont.boldSystemFont(ofSize: 12)
        title.textColor = UIColor(red: 0.01, green: 0.75, blue: 1.0, alpha: 1.0)
        header.addSubview(title)

        let banner = UILabel(frame: CGRect(x: 132, y: 5, width: max(120, view.bounds.width - 178), height: 20))
        banner.autoresizingMask = [.flexibleWidth]
        banner.font = UIFont.systemFont(ofSize: 11)
        banner.textColor = UIColor(white: 0.80, alpha: 1.0)
        banner.text = "Tap 'Paste from RATT' to choose a slot"
        header.addSubview(banner)
        self.statusBanner = banner

        let globeBtn = UIButton(type: .system)
        globeBtn.frame = CGRect(x: view.bounds.width - 38, y: 3, width: 32, height: 24)
        globeBtn.autoresizingMask = [.flexibleLeftMargin]
        globeBtn.setTitle("🌐", for: .normal)
        globeBtn.addTarget(self, action: #selector(handleInputModeList(from:with:)), for: .allTouchEvents)
        header.addSubview(globeBtn)

        view.addSubview(header)

        // 2. Main Interactive Area (y: 36, height: 110)
        // Here resides the "📋 Paste from RATT" button AND at the exact same place the filled slot choices!
        let mainAreaFrame = CGRect(x: 10, y: 36, width: view.bounds.width - 20, height: 110)

        let pasteBtn = UIButton(type: .system)
        pasteBtn.frame = mainAreaFrame
        pasteBtn.autoresizingMask = [.flexibleWidth]
        pasteBtn.setTitle("📋 Paste from RATT (Tap to Choose Slot)", for: .normal)
        pasteBtn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 15)
        pasteBtn.setTitleColor(.black, for: .normal)
        pasteBtn.backgroundColor = UIColor(red: 0.22, green: 1.0, blue: 0.08, alpha: 1.0)
        pasteBtn.layer.cornerRadius = 10
        pasteBtn.layer.borderWidth = 2
        pasteBtn.layer.borderColor = UIColor.white.cgColor
        pasteBtn.addTarget(self, action: #selector(onPasteFromRattTapped), for: .touchUpInside)
        view.addSubview(pasteBtn)
        self.pasteFromRattBtn = pasteBtn

        // Scrollable container AT THE EXACT SAME PLACE (`mainAreaFrame`) showing all slots that contain data!
        let scroll = UIScrollView(frame: mainAreaFrame)
        scroll.autoresizingMask = [.flexibleWidth]
        scroll.showsVerticalScrollIndicator = true
        scroll.backgroundColor = UIColor(red: 0.07, green: 0.10, blue: 0.15, alpha: 1.0)
        scroll.layer.cornerRadius = 10
        scroll.layer.borderWidth = 1.5
        scroll.layer.borderColor = UIColor(red: 0.22, green: 1.0, blue: 0.08, alpha: 1.0).cgColor
        scroll.isHidden = true

        let stack = UIStackView()
        stack.axis = .vertical
        stack.spacing = 6
        stack.distribution = .fillEqually
        scroll.addSubview(stack)
        view.addSubview(scroll)
        self.filledSlotsScroll = scroll
        self.filledSlotsStack = stack

        // 3. Bottom Utility Row (Space, Backspace, Return, Back to Paste from RATT)
        let bottomRow = UIStackView(frame: CGRect(x: 10, y: 152, width: view.bounds.width - 20, height: 34))
        bottomRow.autoresizingMask = [.flexibleWidth]
        bottomRow.axis = .horizontal
        bottomRow.spacing = 6
        bottomRow.distribution = .fillEqually

        let chooseBtn = UIButton(type: .system)
        chooseBtn.setTitle("📋 Choose Slot", for: .normal)
        chooseBtn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 11.5)
        chooseBtn.setTitleColor(UIColor(red: 0.22, green: 1.0, blue: 0.08, alpha: 1.0), for: .normal)
        chooseBtn.backgroundColor = UIColor(red: 0.09, green: 0.14, blue: 0.22, alpha: 1.0)
        chooseBtn.layer.cornerRadius = 6
        chooseBtn.addTarget(self, action: #selector(onPasteFromRattTapped), for: .touchUpInside)
        bottomRow.addArrangedSubview(chooseBtn)

        let spaceBtn = UIButton(type: .system)
        spaceBtn.setTitle("Space", for: .normal)
        spaceBtn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 12)
        spaceBtn.setTitleColor(.white, for: .normal)
        spaceBtn.backgroundColor = UIColor(red: 0.13, green: 0.17, blue: 0.23, alpha: 1.0)
        spaceBtn.layer.cornerRadius = 6
        spaceBtn.addAction(UIAction { [weak self] _ in
            self?.textDocumentProxy.insertText(" ")
        }, for: .touchUpInside)
        bottomRow.addArrangedSubview(spaceBtn)

        let bkspBtn = UIButton(type: .system)
        bkspBtn.setTitle("⌫ Delete", for: .normal)
        bkspBtn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 12)
        bkspBtn.setTitleColor(.white, for: .normal)
        bkspBtn.backgroundColor = UIColor(red: 0.13, green: 0.17, blue: 0.23, alpha: 1.0)
        bkspBtn.layer.cornerRadius = 6
        bkspBtn.addAction(UIAction { [weak self] _ in
            self?.textDocumentProxy.deleteBackward()
        }, for: .touchUpInside)
        bottomRow.addArrangedSubview(bkspBtn)

        let retBtn = UIButton(type: .system)
        retBtn.setTitle("↵ Return", for: .normal)
        retBtn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 12)
        retBtn.setTitleColor(.white, for: .normal)
        retBtn.backgroundColor = UIColor(red: 0.01, green: 0.52, blue: 0.78, alpha: 1.0)
        retBtn.layer.cornerRadius = 6
        retBtn.addAction(UIAction { [weak self] _ in
            self?.textDocumentProxy.insertText("\n")
        }, for: .touchUpInside)
        bottomRow.addArrangedSubview(retBtn)

        view.addSubview(bottomRow)
    }

    @objc private func onPasteFromRattTapped() {
        _ = dataManager.importSlotsFromPasteboardCarrier()
        showingSlotChoices = true
        rebuildFilledSlotChoices()
    }

    private func getFilledSlots() -> [(Int, RattSlot)] {
        var result: [(Int, RattSlot)] = []
        for sId in 1...10 {
            if let slot = dataManager.loadSlot(id: sId), !slot.content.isEmpty {
                result.append((sId, slot))
            } else if let txt = slotStore.decryptSlot(sId), !txt.isEmpty {
                result.append((sId, RattSlot(id: sId, content: txt)))
            }
        }
        return result
    }

    func rebuildFilledSlotChoices() {
        guard let scroll = filledSlotsScroll,
              let stack = filledSlotsStack,
              let pasteBtn = pasteFromRattBtn else { return }

        for sub in stack.arrangedSubviews {
            stack.removeArrangedSubview(sub)
            sub.removeFromSuperview()
        }

        let filled = getFilledSlots()
        pasteBtn.setTitle(
            filled.isEmpty
                ? "📋 Paste from RATT (No Slots Saved Yet)"
                : "📋 Paste from RATT (\(filled.count) Slot\(filled.count == 1 ? "" : "s") Ready — Tap to Choose)",
            for: .normal
        )

        if !showingSlotChoices {
            pasteBtn.isHidden = false
            scroll.isHidden = true
            return
        }

        // Show filled slots AT THE EXACT SAME PLACE as the "Paste from RATT" button!
        pasteBtn.isHidden = true
        scroll.isHidden = false

        if filled.isEmpty {
            let emptyBtn = UIButton(type: .system)
            emptyBtn.setTitle("No slots contain data yet. Save text in RATT first (Tap to close)", for: .normal)
            emptyBtn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 12)
            emptyBtn.setTitleColor(UIColor(white: 0.75, alpha: 1.0), for: .normal)
            emptyBtn.addAction(UIAction { [weak self] _ in
                self?.showingSlotChoices = false
                self?.rebuildFilledSlotChoices()
            }, for: .touchUpInside)
            stack.addArrangedSubview(emptyBtn)
            stack.frame = CGRect(x: 6, y: 6, width: scroll.bounds.width - 12, height: 40)
            scroll.contentSize = CGSize(width: scroll.bounds.width, height: 52)
            return
        }

        let rowHeight: CGFloat = 34
        for (slotId, slot) in filled {
            let btn = UIButton(type: .system)
            let color = colorFromHex(pcSlotHexColors[slotId - 1])
            let preview = slot.content.replacingOccurrences(of: "\n", with: " ")
            let trimmedPreview = preview.count > 38 ? String(preview.prefix(36)) + "..." : preview
            btn.setTitle("  Slot #\(slotId):  \(trimmedPreview)", for: .normal)
            btn.contentHorizontalAlignment = .left
            btn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 12.5)
            btn.setTitleColor(.white, for: .normal)
            btn.backgroundColor = UIColor(red: 0.08, green: 0.18, blue: 0.14, alpha: 1.0)
            btn.layer.cornerRadius = 6
            btn.layer.borderWidth = 1.5
            btn.layer.borderColor = color.cgColor

            btn.addAction(UIAction { [weak self] _ in
                self?.didSelectSlot(slot)
            }, for: .touchUpInside)

            stack.addArrangedSubview(btn)
        }

        let totalHeight = CGFloat(filled.count) * (rowHeight + 6)
        stack.frame = CGRect(x: 6, y: 6, width: scroll.bounds.width - 12, height: max(rowHeight, totalHeight - 6))
        scroll.contentSize = CGSize(width: scroll.bounds.width, height: totalHeight + 12)
        statusBanner?.text = "Tap any slot below to paste it:"
    }

    func didSelectSlot(_ slot: RattSlot) {
        if self.textDocumentProxy.isSecureTextEntry == true {
            statusBanner?.text = "Injection blocked on secure password field."
            return
        }
        let (isSafe, clean) = RattSecurityGuard.sanitizeText(slot.content)
        if isSafe {
            self.textDocumentProxy.insertText(clean)
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            statusBanner?.text = "✅ Pasted Slot #\(slot.id)!"
        }
    }

    func observeDarwinDeletionNotification() {
        CFNotificationCenterAddObserver(
            CFNotificationCenterGetDarwinNotifyCenter(),
            nil,
            { _, _, _, _, _ in NotificationCenter.default.post(name: .slotCleared, object: nil) },
            "com.cybrox.ratt.slotCleared" as CFString,
            nil,
            .deliverImmediately
        )
    }

    @objc private func handleSlotClearedNotification() {
        DispatchQueue.main.async { [weak self] in
            _ = self?.dataManager.importSlotsFromPasteboardCarrier()
            self?.rebuildFilledSlotChoices()
            self?.statusBanner?.text = "Slots updated"
        }
    }
}
