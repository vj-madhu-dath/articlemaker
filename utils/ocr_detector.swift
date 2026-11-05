import Foundation
import Vision
import AppKit

struct RecognizedWord: Codable {
    let text: String
    let x: Int
    let y: Int
    let w: Int
    let h: Int
}

struct ImageResult: Codable {
    let filename: String
    let elements: [RecognizedWord]
}

var allResults: [ImageResult] = []
let targetDir = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "."
let fileManager = FileManager.default
let files = (try? fileManager.contentsOfDirectory(atPath: targetDir)) ?? []
let imageFiles = files.filter { 
    let lower = $0.lowercased()
    return lower.hasSuffix(".png") || lower.hasSuffix(".jpg") || lower.hasSuffix(".jpeg") 
}.sorted()

for imgName in imageFiles {
    let fullPath = (targetDir as NSString).appendingPathComponent(imgName)
    guard let img = NSImage(contentsOfFile: fullPath),
          let cgImg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    
    let w = cgImg.width
    let h = cgImg.height
    var words: [RecognizedWord] = []
    
    let req = VNRecognizeTextRequest { request, error in
        guard let observations = request.results as? [VNRecognizedTextObservation] else { return }
        for obs in observations {
            guard let top = obs.topCandidates(1).first, top.confidence > 0.4 else { continue }
            let bbox = obs.boundingBox
            let bx = Int(bbox.origin.x * Double(w))
            let by = Int((1.0 - bbox.origin.y - bbox.size.height) * Double(h))
            let bw = Int(bbox.size.width * Double(w))
            let bh = Int(bbox.size.height * Double(h))
            words.append(RecognizedWord(text: top.string, x: bx, y: by, w: bw, h: bh))
        }
    }
    req.recognitionLevel = .accurate
    let handler = VNImageRequestHandler(cgImage: cgImg, options: [:])
    try? handler.perform([req])
    allResults.append(ImageResult(filename: imgName, elements: words))
}

let encoder = JSONEncoder()
encoder.outputFormatting = .prettyPrinted
if let data = try? encoder.encode(allResults) {
    try? data.write(to: URL(fileURLWithPath: "ocr_results.json"))
    print("OCR scan complete: processed \(allResults.count) images to ocr_results.json.")
}
