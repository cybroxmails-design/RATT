// KeyboardViewController.swift — UIInputViewController 10-Slot Top-Bar (RATT v2 for iOS)
// Provides a 10-slot horizontal memory strip inside any iOS 16+ text field.
// - Single-tap a slot button: decrypts, sanitizes via RattSecurityGuard, and injects via
//   self.textDocumentProxy.insertText() without triggering iOS pasteboard modal prompts.
// - Long-press a slot button: captures UIPasteboard.general into that encrypted slot.
// - Gated to Premium and Enterprise subscribers (prompts Basic users to upgrade).

import UIKit

public final class KeyboardViewController: UIInputViewController {
    private let slotStore = KeychainSlotStore.shared
    private var statusBanner: UILabel?
    private var slotButtons: [Int: UIButton] = [:]

    public override func viewDidLoad() {
        super.viewDidLoad()
        _ = SecurityHardening.enforceRuntimeDefense()
        view.backgroundColor = UIColor(red: 0.05, green: 0.10, blue: 0.16, alpha: 1.0)
        setupHeaderBar()
        setupSlotToolbar()
        observeDarwinDeletionNotification()
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(onDarwinSlotCleared),
            name: .slotCleared,
            object: nil
        )
    }

    @objc private func clearAllToolbarSlots() {
        slotStore.clearAllSlots()
        AppGroupDataManager.shared.clearAllSlots()
        refreshSlotStates()
        showBannerMessage("Cleared all 10 slots", isError: false)
    }

    public func observeDarwinDeletionNotification() {
        CFNotificationCenterAddObserver(CFNotificationCenterGetDarwinNotifyCenter(),
            nil, { _, _, _, _, _ in NotificationCenter.default.post(name: .slotCleared, object: nil) },
            "com.cybrox.ratt.slotCleared" as CFString, nil, .deliverImmediately)
    }

    @objc private func onDarwinSlotCleared() {
        DispatchQueue.main.async { [weak self] in
            self?.refreshSlotStates()
            self?.showBannerMessage("Slot cleared from PC (<100ms)", isError: false)
        }
    }

    public override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        refreshSlotStates()
    }

    private func setupHeaderBar() {
        let header = UIView(frame: CGRect(x: 0, y: 0, width: view.bounds.width, height: 28))
        header.autoresizingMask = [.flexibleWidth]
        header.backgroundColor = UIColor(red: 0.04, green: 0.08, blue: 0.13, alpha: 1.0)

        let titleLabel = UILabel(frame: CGRect(x: 12, y: 4, width: 140, height: 20))
        titleLabel.text = "RATT v2 Keyboard"
        titleLabel.font = UIFont.boldSystemFont(ofSize: 12)
        titleLabel.textColor = UIColor(red: 0.01, green: 0.68, blue: 0.99, alpha: 1.0)
        header.addSubview(titleLabel)

        let banner = UILabel(frame: CGRect(x: 156, y: 4, width: view.bounds.width - 200, height: 20))
        banner.autoresizingMask = [.flexibleWidth]
        banner.font = UIFont.systemFont(ofSize: 11)
        banner.textColor = UIColor(white: 0.75, alpha: 1.0)
        banner.text = "Tap slot to paste • Hold slot to save clipboard"
        header.addSubview(banner)
        self.statusBanner = banner

        let clearAllBtn = UIButton(type: .system)
        clearAllBtn.frame = CGRect(x: view.bounds.width - 96, y: 2, width: 54, height: 24)
        clearAllBtn.autoresizingMask = [.flexibleLeftMargin]
        clearAllBtn.setTitle("Clear All", for: .normal)
        clearAllBtn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 10.5)
        clearAllBtn.setTitleColor(UIColor(red: 0.94, green: 0.27, blue: 0.27, alpha: 1.0), for: .normal)
        clearAllBtn.addTarget(self, action: #selector(clearAllToolbarSlots), for: .touchUpInside)
        header.addSubview(clearAllBtn)

        let nextKbBtn = UIButton(type: .system)
        nextKbBtn.frame = CGRect(x: view.bounds.width - 38, y: 2, width: 32, height: 24)
        nextKbBtn.autoresizingMask = [.flexibleLeftMargin]
        nextKbBtn.setTitle("🌐", for: .normal)
        nextKbBtn.addTarget(self, action: #selector(handleInputModeList(from:with:)), for: .allTouchEvents)
        header.addSubview(nextKbBtn)

        view.addSubview(header)
    }

    private func setupSlotToolbar() {
        let scroll = UIScrollView(frame: CGRect(x: 0, y: 30, width: view.bounds.width, height: 48))
        scroll.autoresizingMask = [.flexibleWidth]
        scroll.showsHorizontalScrollIndicator = false

        let stack = UIStackView()
        stack.axis = .horizontal
        stack.spacing = 8
        stack.distribution = .fillEqually
        stack.frame = CGRect(x: 8, y: 4, width: max(view.bounds.width - 16, 680), height: 40)

        for slot in 1...10 {
            let btn = UIButton(type: .system)
            btn.setTitle("Slot \(slot)", for: .normal)
            btn.titleLabel?.font = UIFont.boldSystemFont(ofSize: 12)
            btn.tintColor = UIColor(red: 0.01, green: 0.68, blue: 0.99, alpha: 1.0)
            btn.backgroundColor = UIColor(red: 0.09, green: 0.16, blue: 0.25, alpha: 1.0)
            btn.layer.cornerRadius = 6
            btn.layer.borderWidth = 1
            btn.layer.borderColor = UIColor(red: 0.01, green: 0.68, blue: 0.99, alpha: 0.45).cgColor

            btn.addAction(UIAction { [weak self] _ in
                self?.handleSlotTap(slot)
            }, for: .touchUpInside)

            let longPress = UILongPressGestureRecognizer(target: self, action: #selector(onSlotLongPress(_:)))
            longPress.minimumPressDuration = 0.45
            btn.tag = slot
            btn.addGestureRecognizer(longPress)

            slotButtons[slot] = btn
            stack.addArrangedSubview(btn)
        }

        scroll.contentSize = CGSize(width: stack.frame.width + 16, height: 48)
        scroll.addSubview(stack)
        view.addSubview(scroll)
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

    private func handleSlotTap(_ slot: Int) {
        guard slotStore.canAccessSlot(slot) else {
            showBannerMessage("Slot #\(slot) is not available on your plan.", isError: true)
            return
        }
        guard let plain = slotStore.decryptSlot(slot) else {
            showBannerMessage("Slot #\(slot) is empty. Hold Slot #\(slot) to save copied text.", isError: false)
            return
        }
        let (isSafe, clean) = RattSecurityGuard.sanitizeText(plain)
        if isSafe {
            self.textDocumentProxy.insertText(clean)
            showBannerMessage("Pasted Slot #\(slot) (Inert / Non-Exec Guard Active)", isError: false)
        } else {
            showBannerMessage("Security Guard blocked unsafe payload in Slot #\(slot)", isError: true)
        }
    }

    @objc private func onSlotLongPress(_ gesture: UILongPressGestureRecognizer) {
        guard gesture.state == .began, let btn = gesture.view as? UIButton else { return }
        let slot = btn.tag
        guard slotStore.canAccessSlot(slot) else {
            showBannerMessage("Slot #\(slot) is not available on your plan.", isError: true)
            return
        }
        guard let rawClip = UIPasteboard.general.string, !rawClip.isEmpty else {
            showBannerMessage("Clipboard is empty.", isError: true)
            return
        }
        if slotStore.encryptAndStore(slot: slot, text: rawClip) {
            refreshSlotStates()
            showBannerMessage("Saved clipboard to Slot #\(slot)", isError: false)
        } else {
            showBannerMessage("Security Guard blocked unsafe link/script from being saved.", isError: true)
        }
    }

    private func refreshSlotStates() {
        for (slot, btn) in slotButtons {
            let isUnlocked = slotStore.canAccessSlot(slot)
            let color = colorFromHex(pcSlotHexColors[slot - 1])
            let hasData = (slotStore.decryptSlot(slot) != nil)

            if !isUnlocked {
                btn.setTitle("🔒 \(slot)", for: .normal)
                btn.layer.borderColor = UIColor(white: 0.2, alpha: 0.5).cgColor
            } else if hasData {
                btn.setTitle("● Slot \(slot)", for: .normal)
                btn.layer.borderColor = color.cgColor
                btn.layer.borderWidth = 1.5
            } else {
                btn.setTitle("Slot \(slot)", for: .normal)
                btn.layer.borderColor = UIColor(white: 0.3, alpha: 0.6).cgColor
                btn.layer.borderWidth = 1.0
            }
        }
    }

    private func showBannerMessage(_ msg: String, isError: Bool) {
        statusBanner?.text = msg
        statusBanner?.textColor = isError
            ? UIColor(red: 1.0, green: 0.45, blue: 0.45, alpha: 1.0)
            : UIColor(red: 0.0, green: 0.90, blue: 1.0, alpha: 1.0)
    }
}
