#import <Foundation/Foundation.h>
#import <Vision/Vision.h>
#import <ImageIO/ImageIO.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc != 2) {
            fprintf(stderr, "uso: bft_ocr_macos imagem.png\n");
            return 2;
        }
        NSString *caminho = [NSString stringWithUTF8String:argv[1]];
        NSURL *url = [NSURL fileURLWithPath:caminho];
        CGImageSourceRef fonte = CGImageSourceCreateWithURL((__bridge CFURLRef)url, NULL);
        if (!fonte) {
            fprintf(stderr, "imagem inválida\n");
            return 3;
        }
        CGImageRef imagem = CGImageSourceCreateImageAtIndex(fonte, 0, NULL);
        CFRelease(fonte);
        if (!imagem) {
            fprintf(stderr, "imagem inválida\n");
            return 3;
        }

        VNRecognizeTextRequest *requisicao = [[VNRecognizeTextRequest alloc] init];
        requisicao.recognitionLevel = VNRequestTextRecognitionLevelAccurate;
        requisicao.usesLanguageCorrection = NO;
        VNImageRequestHandler *handler = [[VNImageRequestHandler alloc] initWithCGImage:imagem options:@{}];
        NSError *erro = nil;
        BOOL ok = [handler performRequests:@[requisicao] error:&erro];
        CGImageRelease(imagem);
        if (!ok) {
            fprintf(stderr, "OCR falhou: %s\n", erro.localizedDescription.UTF8String);
            return 4;
        }
        for (VNRecognizedTextObservation *observacao in requisicao.results) {
            VNRecognizedText *candidato = [[observacao topCandidates:1] firstObject];
            if (candidato) {
                printf("%s\n", candidato.string.UTF8String);
            }
        }
    }
    return 0;
}
