// Lista janelas com ID, título e dono (processo) para captura direcionada.
// Uso: bft_listar_janelas
#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        CFArrayRef janelas = CGWindowListCopyWindowInfo(
            kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
            kCGNullWindowID
        );
        NSArray *arr = (__bridge NSArray *)janelas;
        for (NSDictionary *info in arr) {
            NSNumber *num = info[(id)kCGWindowNumber];
            NSString *dono = info[(id)kCGWindowOwnerName];
            NSString *titulo = info[(id)kCGWindowName];
            NSNumber *layer = info[(id)kCGWindowLayer];
            if (layer && [layer intValue] != 0) continue; // só janelas normais
            printf("id=%s\tdono=%s\ttitulo=%s\n",
                   num.stringValue.UTF8String,
                   (dono ? dono.UTF8String : "?"),
                   (titulo ? titulo.UTF8String : "?"));
        }
        if (janelas) CFRelease(janelas);
    }
    return 0;
}
