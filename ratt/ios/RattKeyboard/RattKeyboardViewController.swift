// iOS RattKeyboardViewController.swift
// Full iOS Dark-Mode QWERTY Keyboard with "Paste from RATT v2" Top Bar.
// Matches the native iPhone dark keyboard layout:
// - Top prediction bar displays:
//       <Active Slot Text>
//       Paste from RATT v2
// - When the user taps "Paste from RATT v2", all slots that contain data appear in a list
//   right there so the user can choose which slot to paste from.

import UIKit

class RattKeyboardViewController: UIInputViewController {
    private let dataManager = AppGroupDataManager.shared
    private let slotStore = KeychainSlotStore.shared

    private var topBarButton: UIControl!
    private var topPrimaryLabel: UILabel!
    private var topSecondaryLabel: UILabel!
    private var keysContainer: UIView!
    private var slotListScroll: UIScrollView!
    private var slotListStack: UIStackView!

    private var isShowingSlotList: Bool = false
    private var isUppercase: Bool = true
    private var isNumbersMode: Bool = false
    private var letterButtons: [UIButton] = []
    private var shiftButton: UIButton?
    private var mode123Button: UIButton?
    private var lastSelectedText: String = ""
    private var heightConstraint: NSLayoutConstraint?

    private let pcSlotHexColors = [
        "#00BFFF", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899",
        "#3B82F6", "#14B8A6", "#EF4444", "#EAB308", "#06B6D4"
    ]

    override func viewDidLoad() {
        super.viewDidLoad()
        _ = SecurityHardening.enforceRuntimeDefense()
        // Native iOS Dark Keyboard Background (#1C1C1E)
        view.backgroundColor = UIColor(red: 0.11, green: 0.11, blue: 0.12, alpha: 1.0)

        let hc = view.heightAnchor.constraint(equalToConstant: 266)
        hc.priority = UILayoutPriority(999)
        hc.isActive = true
        self.heightConstraint = hc

        setupTopPasteFromRattBar()
        setupQwertyKeys()
        setupSlotListOverlay()
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
        refreshTopBarAndSlotList()
        pullSlotsFromLocalhostIfAvailable()
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        layoutSlotListStack()
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

    // MARK: - 1. Top "Paste from RATT v2" Bar (Matches iPhone Screenshot)

    private func setupTopPasteFromRattBar() {
        let topBar = UIControl()
        topBar.translatesAutoresizingMaskIntoConstraints = false
        topBar.backgroundColor = UIColor(red: 0.14, green: 0.14, blue: 0.15, alpha: 1.0)
        topBar.addTarget(self, action: #selector(onPasteFromRattBarTapped), for: .touchUpInside)
        view.addSubview(topBar)
        self.topBarButton = topBar

        // Left subtle divider (matching iOS QuickType bar)
        let leftDiv = UIView()
        leftDiv.translatesAutoresizingMaskIntoConstraints = false
        leftDiv.backgroundColor = UIColor(white: 0.28, alpha: 0.6)
        topBar.addSubview(leftDiv)

        // Right subtle divider
        let rightDiv = UIView()
        rightDiv.translatesAutoresizingMaskIntoConstraints = false
        rightDiv.backgroundColor = UIColor(white: 0.28, alpha: 0.6)
        topBar.addSubview(rightDiv)

        let pLabel = UILabel()
        pLabel.translatesAutoresizingMaskIntoConstraints = false
        pLabel.text = "Tap to Choose Slot"
        pLabel.font = UIFont.systemFont(ofSize: 15, weight: .regular)
        pLabel.textColor = .white
        pLabel.textAlignment = .center
        pLabel.isUserInteractionEnabled = false
        topBar.addSubview(pLabel)
        self.topPrimaryLabel = pLabel

        let sLabel = UILabel()
        sLabel.translatesAutoresizingMaskIntoConstraints = false
        sLabel.text = "Paste from RATT v2"
        sLabel.font = UIFont.systemFont(ofSize: 11.5, weight: .regular)
        sLabel.textColor = UIColor(white: 0.62, alpha: 1.0)
        sLabel.textAlignment = .center
        sLabel.isUserInteractionEnabled = false
        topBar.addSubview(sLabel)
        self.topSecondaryLabel = sLabel

        NSLayoutConstraint.activate([
            topBar.topAnchor.constraint(equalTo: view.topAnchor),
            topBar.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            topBar.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            topBar.heightAnchor.constraint(equalToConstant: 48),

            leftDiv.leadingAnchor.constraint(equalTo: topBar.leadingAnchor, constant: 24),
            leftDiv.centerYAnchor.constraint(equalTo: topBar.centerYAnchor),
            leftDiv.widthAnchor.constraint(equalToConstant: 1),
            leftDiv.heightAnchor.constraint(equalToConstant: 26),

            rightDiv.trailingAnchor.constraint(equalTo: topBar.trailingAnchor, constant: -24),
            rightDiv.centerYAnchor.constraint(equalTo: topBar.centerYAnchor),
            rightDiv.widthAnchor.constraint(equalToConstant: 1),
            rightDiv.heightAnchor.constraint(equalToConstant: 26),

            pLabel.topAnchor.constraint(equalTo: topBar.topAnchor, constant: 6),
            pLabel.leadingAnchor.constraint(equalTo: leftDiv.trailingAnchor, constant: 8),
            pLabel.trailingAnchor.constraint(equalTo: rightDiv.leadingAnchor, constant: -8),

            sLabel.topAnchor.constraint(equalTo: pLabel.bottomAnchor, constant: 1),
            sLabel.leadingAnchor.constraint(equalTo: leftDiv.trailingAnchor, constant: 8),
            sLabel.trailingAnchor.constraint(equalTo: rightDiv.leadingAnchor, constant: -8)
        ])
    }

    // MARK: - 2. Full Dark-Mode QWERTY Keyboard Layout

    private func setupQwertyKeys() {
        let container = UIView()
        container.translatesAutoresizingMaskIntoConstraints = false
        container.backgroundColor = .clear
        view.addSubview(container)
        self.keysContainer = container

        NSLayoutConstraint.activate([
            container.topAnchor.constraint(equalTo: topBarButton.bottomAnchor, constant: 4),
            container.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 3),
            container.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -3),
            container.bottomAnchor.constraint(equalTo: view.bottomAnchor, constant: -4)
        ])

        buildKeyboardRows()
    }

    private func buildKeyboardRows() {
        for sub in keysContainer.subviews {
            sub.removeFromSuperview()
        }
        letterButtons.removeAll()

        let mainStack = UIStackView()
        mainStack.translatesAutoresizingMaskIntoConstraints = false
        mainStack.axis = .vertical
        mainStack.distribution = .fillEqually
        mainStack.spacing = 10
        keysContainer.addSubview(mainStack)

        NSLayoutConstraint.activate([
            mainStack.topAnchor.constraint(equalTo: keysContainer.topAnchor, constant: 2),
            mainStack.leadingAnchor.constraint(equalTo: keysContainer.leadingAnchor),
            mainStack.trailingAnchor.constraint(equalTo: keysContainer.trailingAnchor),
            mainStack.bottomAnchor.constraint(equalTo: keysContainer.bottomAnchor, constant: -2)
        ])

        let row1Keys = isNumbersMode
            ? ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]
            : ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"]
        let row2Keys = isNumbersMode
            ? ["-", "/", ":", ";", "(", ")", "$", "&", "@", "\""]
            : ["A", "S", "D", "F", "G", "H", "J", "K", "L"]
        let row3Keys = isNumbersMode
            ? [".", ",", "?", "!", "'", "#", "%", "+", "="]
            : ["Z", "X", "C", "V", "B", "N", "M"]

        // Row 1
        let row1 = createKeyRow(keys: row1Keys)
        mainStack.addArrangedSubview(row1)

        // Row 2
        let row2Wrapper = UIView()
        let row2 = createKeyRow(keys: row2Keys)
        row2.translatesAutoresizingMaskIntoConstraints = false
        row2Wrapper.addSubview(row2)
        let hPad: CGFloat = isNumbersMode ? 0 : 18
        NSLayoutConstraint.activate([
            row2.topAnchor.constraint(equalTo: row2Wrapper.topAnchor),
            row2.bottomAnchor.constraint(equalTo: row2Wrapper.bottomAnchor),
            row2.leadingAnchor.constraint(equalTo: row2Wrapper.leadingAnchor, constant: hPad),
            row2.trailingAnchor.constraint(equalTo: row2Wrapper.trailingAnchor, constant: -hPad)
        ])
        mainStack.addArrangedSubview(row2Wrapper)

        // Row 3 (Shift + Z..M + Backspace)
        let row3 = UIStackView()
        row3.axis = .horizontal
        row3.spacing = 6
        row3.distribution = .fill

        let shiftBtn = createFunctionKey(title: isNumbersMode ? "#+=" : (isUppercase ? "⬆️" : "⇧"), width: 42)
        shiftBtn.backgroundColor = (!isNumbersMode && isUppercase)
            ? UIColor(white: 0.85, alpha: 1.0)
            : UIColor(red: 0.20, green: 0.20, blue: 0.22, alpha: 1.0)
        shiftBtn.setTitleColor((!isNumbersMode && isUppercase) ? .black : .white, for: .normal)
        shiftBtn.addTarget(self, action: #selector(onShiftTapped), for: .touchUpInside)
        self.shiftButton = shiftBtn
        row3.addArrangedSubview(shiftBtn)

        let row3Letters = createKeyRow(keys: row3Keys)
        row3.addArrangedSubview(row3Letters)

        let bkspBtn = createFunctionKey(title: "⌫", width: 42)
        bkspBtn.addTarget(self, action: #selector(onBackspaceTapped), for: .touchUpInside)
        row3.addArrangedSubview(bkspBtn)

        mainStack.addArrangedSubview(row3)

        // Row 4 (123 + Globe + Space + Return)
        let row4 = UIStackView()
        row4.axis = .horizontal
        row4.spacing = 6
        row4.distribution = .fill

        let modeBtn = createFunctionKey(title: isNumbersMode ? "ABC" : "123", width: 44)
        modeBtn.addTarget(self, action: #selector(onMode123Tapped), for: .touchUpInside)
        self.mode123Button = modeBtn
        row4.addArrangedSubview(modeBtn)

        let globeBtn = createFunctionKey(title: "🌐", width: 42)
        globeBtn.addTarget(self, action: #selector(handleInputModeList(from:with:)), for: .allTouchEvents)
        row4.addArrangedSubview(globeBtn)

        let spaceBtn = UIButton(type: .system)
        spaceBtn.setTitle("space", for: .normal)
        spaceBtn.titleLabel?.font = UIFont.systemFont(ofSize: 15, weight: .regular)
        spaceBtn.setTitleColor(.white, for: .normal)
        spaceBtn.backgroundColor = UIColor(red: 0.28, green: 0.28, blue: 0.30, alpha: 1.0)
        spaceBtn.layer.cornerRadius = 5
        spaceBtn.addTarget(self, action: #selector(onSpaceTapped), for: .touchUpInside)
        row4.addArrangedSubview(spaceBtn)

        let retBtn = createFunctionKey(title: "⏎", width: 76)
        retBtn.addTarget(self, action: #selector(onReturnTapped), for: .touchUpInside)
        row4.addArrangedSubview(retBtn)

        mainStack.addArrangedSubview(row4)
    }

    private func createKeyRow(keys: [String]) -> UIStackView {
        let stack = UIStackView()
        stack.axis = .horizontal
        stack.distribution = .fillEqually
        stack.spacing = 6

        for k in keys {
            let btn = UIButton(type: .system)
            let display = (!isNumbersMode && !isUppercase) ? k.lowercased() : k
            btn.setTitle(display, for: .normal)
            btn.titleLabel?.font = UIFont.systemFont(ofSize: 21, weight: .regular)
            btn.setTitleColor(.white, for: .normal)
            btn.backgroundColor = UIColor(red: 0.28, green: 0.28, blue: 0.30, alpha: 1.0)
            btn.layer.cornerRadius = 5
            btn.addTarget(self, action: #selector(onLetterKeyTapped(_:)), for: .touchUpInside)
            if !isNumbersMode {
                letterButtons.append(btn)
            }
            stack.addArrangedSubview(btn)
        }
        return stack
    }

    private func createFunctionKey(title: String, width: CGFloat) -> UIButton {
        let btn = UIButton(type: .system)
        btn.translatesAutoresizingMaskIntoConstraints = false
        btn.setTitle(title, for: .normal)
        btn.titleLabel?.font = UIFont.systemFont(ofSize: 15, weight: .medium)
        btn.setTitleColor(.white, for: .normal)
        btn.backgroundColor = UIColor(red: 0.20, green: 0.20, blue: 0.22, alpha: 1.0)
        btn.layer.cornerRadius = 5
        btn.widthAnchor.constraint(equalToConstant: width).isActive = true
        return btn
    }

    // MARK: - 3. In-Place Filled Slot Chooser List (Appears When User Clicks "Paste from RATT v2")

    private func setupSlotListOverlay() {
        let scroll = UIScrollView()
        scroll.translatesAutoresizingMaskIntoConstraints = false
        // Transparent black background floating on top of the keyboard keys
        scroll.backgroundColor = UIColor(white: 0.0, alpha: 0.80)
        scroll.layer.cornerRadius = 10
        scroll.layer.borderWidth = 1.5
        scroll.layer.borderColor = UIColor(red: 0.22, green: 1.0, blue: 0.08, alpha: 1.0).cgColor
        scroll.showsVerticalScrollIndicator = true
        scroll.isHidden = true
        view.addSubview(scroll)
        self.slotListScroll = scroll

        let stack = UIStackView()
        stack.axis = .vertical
        stack.spacing = 6
        stack.distribution = .fillEqually
        scroll.addSubview(stack)
        self.slotListStack = stack

        NSLayoutConstraint.activate([
            scroll.topAnchor.constraint(equalTo: topBarButton.bottomAnchor, constant: 4),
            scroll.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 6),
            scroll.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -6),
            scroll.bottomAnchor.constraint(equalTo: view.bottomAnchor, constant: -6)
        ])
    }

    @objc private func onPasteFromRattBarTapped() {
        _ = dataManager.importSlotsFromPasteboardCarrier()
        isShowingSlotList.toggle()
        refreshTopBarAndSlotList()
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

    private func refreshTopBarAndSlotList() {
        let filled = getFilledSlots()

        // Update Top Bar Labels (Matches Screenshot: Primary Text on top, "Paste from RATT v2" below)
        if let first = filled.first {
            let previewSource = lastSelectedText.isEmpty ? first.1.content : lastSelectedText
            let cleanLine = previewSource.replacingOccurrences(of: "\n", with: " ").trimmingCharacters(in: .whitespaces)
            let shortPreview = cleanLine.count > 26 ? String(cleanLine.prefix(24)) + "..." : cleanLine
            topPrimaryLabel.text = isShowingSlotList ? "Choose a Slot Below ▴" : "\(shortPreview) ▾"
            topSecondaryLabel.text = "Paste from RATT v2 (\(filled.count) slot\(filled.count == 1 ? "" : "s"))"
        } else {
            topPrimaryLabel.text = "No Slots Saved Yet"
            topSecondaryLabel.text = "Paste from RATT v2"
        }

        // Keep the QWERTY keys visible behind the transparent black slot list overlay!
        slotListScroll.isHidden = !isShowingSlotList
        keysContainer.isHidden = false

        guard isShowingSlotList else { return }

        for sub in slotListStack.arrangedSubviews {
            slotListStack.removeArrangedSubview(sub)
            sub.removeFromSuperview()
        }

        if filled.isEmpty {
            let emptyBtn = UIButton(type: .system)
            emptyBtn.setTitle("No slots contain data yet. Tap here to return to keyboard.", for: .normal)
            emptyBtn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 13)
            emptyBtn.setTitleColor(.white, for: .normal)
            emptyBtn.addAction(UIAction { [weak self] _ in
                self?.isShowingSlotList = false
                self?.refreshTopBarAndSlotList()
            }, for: .touchUpInside)
            slotListStack.addArrangedSubview(emptyBtn)
            layoutSlotListStack()
            return
        }

        for (slotId, slot) in filled {
            let btn = UIButton(type: .system)
            let color = colorFromHex(pcSlotHexColors[slotId - 1])
            let preview = slot.content.replacingOccurrences(of: "\n", with: " ")
            let trimmed = preview.count > 38 ? String(preview.prefix(36)) + "..." : preview
            btn.setTitle("  Slot #\(slotId):  \(trimmed)", for: .normal)
            btn.contentHorizontalAlignment = .left
            btn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 13.5)
            btn.setTitleColor(.white, for: .normal)
            btn.backgroundColor = UIColor(red: 0.09, green: 0.20, blue: 0.15, alpha: 1.0)
            btn.layer.cornerRadius = 8
            btn.layer.borderWidth = 1.5
            btn.layer.borderColor = color.cgColor

            btn.addAction(UIAction { [weak self] _ in
                guard let self = self else { return }
                self.didSelectSlot(slot)
            }, for: .touchUpInside)

            slotListStack.addArrangedSubview(btn)
        }

        layoutSlotListStack()
    }

    private func layoutSlotListStack() {
        guard isShowingSlotList else { return }
        let count = max(1, slotListStack.arrangedSubviews.count)
        let rowHeight: CGFloat = 38
        let totalH = CGFloat(count) * (rowHeight + 6)
        let w = max(260, slotListScroll.bounds.width - 16)
        slotListStack.frame = CGRect(x: 8, y: 8, width: w, height: max(rowHeight, totalH - 6))
        slotListScroll.contentSize = CGSize(width: slotListScroll.bounds.width, height: totalH + 16)
    }

    func didSelectSlot(_ slot: RattSlot) {
        if self.textDocumentProxy.isSecureTextEntry == true {
            return
        }
        let (isSafe, clean) = RattSecurityGuard.sanitizeText(slot.content)
        if isSafe {
            self.textDocumentProxy.insertText(clean)
            self.lastSelectedText = clean
            UINotificationFeedbackGenerator().notificationOccurred(.success)
            self.isShowingSlotList = false
            self.refreshTopBarAndSlotList()
        }
    }

    // MARK: - 4. Key Actions

    @objc private func onLetterKeyTapped(_ sender: UIButton) {
        guard let char = sender.title(for: .normal) else { return }
        self.textDocumentProxy.insertText(char)
        if !isNumbersMode && isUppercase {
            isUppercase = false
            updateLetterCase()
        }
    }

    @objc private func onShiftTapped() {
        if isNumbersMode { return }
        isUppercase.toggle()
        updateLetterCase()
    }

    private func updateLetterCase() {
        for btn in letterButtons {
            if let cur = btn.title(for: .normal) {
                btn.setTitle(isUppercase ? cur.uppercased() : cur.lowercased(), for: .normal)
            }
        }
        shiftButton?.backgroundColor = isUppercase
            ? UIColor(white: 0.85, alpha: 1.0)
            : UIColor(red: 0.20, green: 0.20, blue: 0.22, alpha: 1.0)
        shiftButton?.setTitleColor(isUppercase ? .black : .white, for: .normal)
    }

    @objc private func onBackspaceTapped() {
        self.textDocumentProxy.deleteBackward()
    }

    @objc private func onSpaceTapped() {
        self.textDocumentProxy.insertText(" ")
    }

    @objc private func onReturnTapped() {
        self.textDocumentProxy.insertText("\n")
    }

    @objc private func onMode123Tapped() {
        isNumbersMode.toggle()
        buildKeyboardRows()
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
                if let sId = Int(k), (1...10).contains(sId), !v.isEmpty {
                    _ = self.slotStore.encryptAndStore(slot: sId, text: v)
                    _ = self.dataManager.saveSlot(id: sId, content: v)
                    updated = true
                }
            }
            if updated {
                DispatchQueue.main.async {
                    self.refreshTopBarAndSlotList()
                }
            }
        }.resume()
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
            self?.refreshTopBarAndSlotList()
        }
    }
}
