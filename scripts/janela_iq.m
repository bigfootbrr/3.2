// Retorna o ID da janela da IQ Option (ou 0 se não encontrada).
// Prefere a janela com título (a principal), pois janelas sem título podem
// não ser capturáveis pelo screencapture -l.
// Uso: bft_janela_iq
#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        CFArrayRef janelas = CGWindowListCopyWindowInfo(
            kCGWindowListOptionAll | kCGWindowListExcludeDesktopElements,
            kCGNullWindowID
        );
        NSArray *arr = (__bridge NSArray *)janelas;
        NSString *fallback = nil;
        for (NSDictionary *info in arr) {
            NSNumber *layer = info[(id)kCGWindowLayer];
            if (layer && [layer intValue] != 0) continue;
            NSString *dono = info[(id)kCGWindowOwnerName];
            if (!dono || ![dono.lowercaseString containsString:@"iqoption"]) continue;
            NSNumber *num = info[(id)kCGWindowNumber];
            NSString *titulo = info[(id)kCGWindowName];
            if (titulo && titulo.length > 0) {
                printf("%s\n", num.stringValue.UTF8String);
                if (janelas) CFRelease(janelas);
                return 0;
            }
            if (!fallback) fallback = num.stringValue;
        }
        if (fallback) {
            printf("%s\n", fallback.UTF8String);
            if (janelas) CFRelease(janelas);
            return 0;
        }
        if (janelas) CFRelease(janelas);
        printf("0\n");
    }
    return 0;
}
