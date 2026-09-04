// Retorna: ID,X,Y,LARGURA,ALTURA (pontos lógicos) da janela da IQ Option
#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        CFArrayRef janelas = CGWindowListCopyWindowInfo(
            kCGWindowListOptionAll | kCGWindowListExcludeDesktopElements,
            kCGNullWindowID
        );
        NSArray *arr = (__bridge NSArray *)janelas;
        NSString *fallbackId = nil;
        CGRect fallbackBounds = CGRectZero;
        for (NSDictionary *info in arr) {
            NSNumber *layer = info[(id)kCGWindowLayer];
            if (layer && [layer intValue] != 0) continue;
            NSString *dono = info[(id)kCGWindowOwnerName];
            if (!dono || ![dono.lowercaseString containsString:@"iqoption"]) continue;
            NSNumber *num = info[(id)kCGWindowNumber];
            NSString *titulo = info[(id)kCGWindowName];
            NSDictionary *bounds = info[(id)kCGWindowBounds];
            CGRect r = CGRectZero;
            if (bounds) {
                r.origin.x = [bounds[@"X"] doubleValue];
                r.origin.y = [bounds[@"Y"] doubleValue];
                r.size.width = [bounds[@"Width"] doubleValue];
                r.size.height = [bounds[@"Height"] doubleValue];
            }
            if (titulo && titulo.length > 0) {
                printf("%s,%.0f,%.0f,%.0f,%.0f\n",
                    num.stringValue.UTF8String, r.origin.x, r.origin.y,
                    r.size.width, r.size.height);
                if (janelas) CFRelease(janelas);
                return 0;
            }
            if (!fallbackId) { fallbackId = num.stringValue; fallbackBounds = r; }
        }
        if (fallbackId) {
            printf("%s,%.0f,%.0f,%.0f,%.0f\n",
                fallbackId.UTF8String, fallbackBounds.origin.x, fallbackBounds.origin.y,
                fallbackBounds.size.width, fallbackBounds.size.height);
            if (janelas) CFRelease(janelas);
            return 0;
        }
        if (janelas) CFRelease(janelas);
        printf("0,0,0,0,0\n");
    }
    return 0;
}
