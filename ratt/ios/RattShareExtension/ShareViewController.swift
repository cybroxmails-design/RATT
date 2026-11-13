// ShareViewController.swift — RATT v2 iOS Share Extension
// Allows sharing photos, documents (.pdf, .docx), and links directly into RATT Slots 1-10

import UIKit
import Social
import UniformTypeIdentifiers

class ShareViewController: UIViewController {
    private let dataManager = AppGroupDataManager.shared
    private var sharedData: Data?
    private var sharedFileName: String?
    private var sharedMime: String?
    private var sharedText: String?
    private var sharedKind: String = "text"

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(white: 0, alpha: 0.6)
        extractSharedItem()
    }

    private func extractSharedItem() {
        guard let item = extensionContext?.inputItems.first as? NSExtensionItem,
              let attachments = item.attachments, !attachments.isEmpty else {
            presentSlotPicker()
            return
        }

        let provider = attachments.first!

        // 1. Check for Images (PNG, JPEG)
        if provider.hasItemConformingToTypeIdentifier(UTType.image.identifier) {
            provider.loadItem(forTypeIdentifier: UTType.image.identifier, options: nil) { [weak self] (data, error) in
                guard let self = self else { return }
                if let url = data as? URL, let fileData = try? Data(contentsOf: url) {
                    self.sharedData = fileData
                    self.sharedFileName = url.lastPathComponent
                    self.sharedMime = "image/png"
                    self.sharedKind = "image"
                    self.sharedText = "Shared Image"
                } else if let image = data as? UIImage, let imgData = image.pngData() {
                    self.sharedData = imgData
                    self.sharedFileName = "photo.png"
                    self.sharedMime = "image/png"
                    self.sharedKind = "image"
                    self.sharedText = "Photo (\(Int(image.size.width))x\(Int(image.size.height)))"
                }
                DispatchQueue.main.async { self.presentSlotPicker() }
            }
            return
        }

        // 2. Check for Documents (PDF, Office, etc.)
        if provider.hasItemConformingToTypeIdentifier(UTType.data.identifier) {
            provider.loadItem(forTypeIdentifier: UTType.data.identifier, options: nil) { [weak self] (data, error) in
                guard let self = self else { return }
                if let url = data as? URL, let fileData = try? Data(contentsOf: url) {
                    self.sharedData = fileData
                    self.sharedFileName = url.lastPathComponent
                    self.sharedMime = "application/octet-stream"
                    self.sharedKind = "files"
                    self.sharedText = url.lastPathComponent
                }
                DispatchQueue.main.async { self.presentSlotPicker() }
            }
            return
        }

        // 3. Fallback to Plain Text or URL
        if provider.hasItemConformingToTypeIdentifier(UTType.plainText.identifier) {
            provider.loadItem(forTypeIdentifier: UTType.plainText.identifier, options: nil) { [weak self] (text, error) in
                guard let self = self else { return }
                self.sharedText = text as? String ?? ""
                self.sharedKind = "text"
                DispatchQueue.main.async { self.presentSlotPicker() }
            }
            return
        }

        presentSlotPicker()
    }

    private func presentSlotPicker() {
        let alert = UIAlertController(
            title: "Copy to RATT Slot",
            message: "Select which slot (1–10) to store this item into:",
            preferredStyle: .actionSheet
        )

        for slotId in 1...10 {
            alert.addAction(UIAlertAction(title: "Slot #\(slotId)", style: .default) { [weak self] _ in
                self?.saveToSlot(slotId)
            })
        }

        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel) { [weak self] _ in
            self?.extensionContext?.completeRequest(returningItems: [], completionHandler: nil)
        })

        present(alert, animated: true)
    }

    private func saveToSlot(_ slotId: Int) {
        let content = sharedText ?? sharedFileName ?? "Shared Item"
        let b64 = sharedData?.base64EncodedString()
        dataManager.saveSlot(
            id: slotId,
            content: content,
            kind: sharedKind,
            dataBase64: b64,
            fileName: sharedFileName,
            mimeType: sharedMime,
            byteSize: sharedData?.count
        )
        extensionContext?.completeRequest(returningItems: [], completionHandler: nil)
    }
}
