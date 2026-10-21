import Foundation
import Vision
import ImageIO

let root = URL(fileURLWithPath: CommandLine.arguments[1])
let files = (FileManager.default.enumerator(at: root, includingPropertiesForKeys: nil)!.allObjects as! [URL]).filter { $0.pathExtension == "jpg" }.sorted { $0.path < $1.path }
var count = 0
for file in files {
    let out = file.deletingPathExtension().appendingPathExtension("ocr.json")
    if FileManager.default.fileExists(atPath: out.path) { continue }
    autoreleasepool {
        do {
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.recognitionLanguages = ["zh-Hans", "en-US"]
            request.usesLanguageCorrection = false
            let handler = VNImageRequestHandler(url: file)
            try handler.perform([request])
            let rows = (request.results ?? []).compactMap { obs -> [String: Any]? in
                guard let text = obs.topCandidates(1).first else { return nil }
                return ["text": text.string, "confidence": text.confidence, "y": obs.boundingBox.origin.y]
            }
            try JSONSerialization.data(withJSONObject: rows).write(to: out)
            count += 1
        } catch { print("OCR failed: \(file.lastPathComponent): \(error)") }
    }
    if count % 100 == 0 { print("OCR frames: \(count)"); fflush(stdout) }
}
print("OCR completed: \(count) new frames")
