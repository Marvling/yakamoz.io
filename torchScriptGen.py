import os
import torch
import imp
from yakamoz import ROOT


if __name__ == '__main__':
    surat = imp.load_source(
        'surat',
        os.path.join(ROOT, 'surat/surat.py')
    )

    MODEL_CP_PATH = os.path.join(
        ROOT,
        '/20_03_15_08_34_12/',
        '20_03_15_08_34_12_E00100.pth'
    )

    model = surat.Model(1)
    model.load_state_dict(torch.load(
        MODEL_CP_PATH,
        # for cpu
        # map_location=torch.device('cpu')
    ))

    model.eval()

    traced_script_module = torch.jit.trace(
        model,
        (
            torch.zeros((1, 1, 64, 32)),
            torch.zeros(16)
        )
    )

    traced_script_module.save(os.path.join(ROOT, 'yakamoz.pt'))
