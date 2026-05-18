//
//  GJLDecryManager.h
//  GJLDecry
//
//  Created by guiji on 2025/4/27.
//

#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface GJLDecryManager : NSObject
+ (GJLDecryManager*)manager;
@property(nonatomic,strong)NSString * decryDigitalPath;
@property(nonatomic,strong)NSString * configJson;
@property(nonatomic,strong)NSString * wenet_onnx_path;
@property(nonatomic,strong)NSString * paramPath;
@property(nonatomic,strong)NSString * binPath;
@property(nonatomic,strong)NSString * weight_168u_path;
@property(nonatomic,strong)NSString * sepicalJson;


-(NSInteger)initBaseModel:(NSString*)basePath digitalModel:(NSString*)digitalPath;
@end

NS_ASSUME_NONNULL_END
