import Foundation
import Vision
import ImageIO

guard CommandLine.arguments.count == 2 else {
    fputs("uso: ocr_macos.swift imagem.png\n", stderr)
    exit(2)
}

let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
      let imagem = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
    fputs("imagem inválida\n", stderr)
    exit(3)
}

let requisicao = VNRecognizeTextRequest()
requisicao.recognitionLevel = .accurate
requisicao.usesLanguageCorrection = false
requisicao.recognitionLanguages = ["pt-BR", "en-US"]

do {
    try VNImageRequestHandler(cgImage: imagem, options: [:]).perform([requisicao])
    let observacoes = (requisicao.results ?? []).sorted {
        if abs($0.boundingBox.midY - $1.boundingBox.midY) > 0.01 {
            return $0.boundingBox.midY > $1.boundingBox.midY
        }
        return $0.boundingBox.minX < $1.boundingBox.minX
    }
    for observacao in observacoes {
        if let texto = observacao.topCandidates(1).first?.string {
            print(texto.replacingOccurrences(of: "\n", with: " "))
        }
    }
} catch {
    fputs("OCR falhou: \(error)\n", stderr)
    exit(4)
}
