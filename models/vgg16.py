from torchvision.models import vgg16
from .base_model import _BaseModel
from torch import nn

class VGG16(_BaseModel):
    def __init__(self, nClass, pretrain=True):
        super(VGG16, self).__init__(nClass, pretrain)
        original_mod = vgg16(pretrain)

        # change input_num of vgg16
        in_kernel2 = original_mod.features[2].in_channels
        original_mod.features[0] = nn.Conv2d(in_channels=1, out_channels=in_kernel2, kernel_size = 3)
        
        self.encoder = nn.Sequential(original_mod.features, original_mod.avgpool)
        
        self.classify = nn.Sequential(
            nn.Linear(25088, 4096),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(4096, nClass),
            nn.Sigmoid()
        )
