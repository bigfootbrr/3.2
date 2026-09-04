// Diagnóstico: imprime textos com suas bounding boxes (posições) na imagem.
// Uso: bft_ocr_posicoes imagem.png
#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <ImageIO/ImageIO.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 2) {
            fprintf(stderr, "uso: bft_ocr_posicoes imagem.png\n");
            return 2;
        }
        NSString *caminho = [NSString stringWithUTF8String:argv[1]];
        NSURL *url = [NSURL fileURLWithPath:caminho];
        CGImageSourceRef fonte = CGImageSourceCreateWithURL((__bridge CFURLRef)url, NULL);
        if (!fonte) { fprintf(stderr, "imagem inválida\n"); return 3; }
        CGImageRef imagem = CGImageSourceCreateImageAtIndex(fonte, 0, NULL);
        CFRelease(fonte);
        if (!imagem) { fprintf(stderr, "imagem inválida\n"); return 3; }

        VNRecognizeTextRequest *requisicao = [[VNRecognizeTextRequest alloc] init];
        requisicao.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
        requisicao.usesLanguageCorrection = NO;
        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:imagem options:@{}];
        NSError *erro = nil;
        BOOL ok = [handler performRequests:@[requisicao] error:&erro];
        CGImageRelease(imagem);
        if (!ok) { fprintf(stderr, "OCR falhou: %s\n", erro.localizedDescription.UTF8String); return 4; }

        // Coordenadas do Vision: origem no canto inferior esquerdo, em pixels.
        for (VNRecognizedTextObservation *obs in requisicao.results) {
            VNRecognizedText *cand = [[obs topCandidates:1] firstObject];
            if (!cand) continue;
            CGRect b = obs.boundingBox; // normalizado (0-1), origem inferior-esquerda
            printf("%s\tx=%.3f\ty=%.3f\tw=%.3f\th=%.3f\n",
                   cand.string.UTF8String, b.origin.x, b.origin.y, b.size.width, b.size.height);
        }
    }
    return 0;
}
