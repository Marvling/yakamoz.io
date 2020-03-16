import os
import json
import torch
import torchaudio
import base64
import io
import tempfile
from bottle import run
from bottle import route
from bottle import post
from bottle import request
from bottle import static_file
from indices import indices
from neutral import neutral


indices = (torch.Tensor(indices) - 1).tolist()
ROOT = os.path.expanduser('~/sandbox/yakamoz.io/')
tracedScriptPath = os.path.join(ROOT, 'yakamoz.pt')


def inference(frameCount, audio, mood):
    if not os.path.exists(tracedScriptPath):
        print('torch script not found')
        return
    else:
        tracedScript = torch.jit.load(tracedScriptPath)

    tokens = audio.split(';base64,')
    audio = tokens[1]
    audio = io.BytesIO(base64.b64decode(audio))
    with tempfile.NamedTemporaryFile(suffix='.' + tokens[0].split('/')[1]) as audioFile:
        audioFile.write(audio.read())
        waveform, sampleRate = torchaudio.load(audioFile.name)

    if sampleRate != 16000:
        waveform = torchaudio.transforms.Resample(sampleRate, 16000)(waveform)
        sampleRate = 16000

    MFCC = torchaudio.compliance.kaldi.mfcc(
        waveform,
        channel=0,
        remove_dc_offset=True,
        window_type='hanning',
        num_ceps=32,
        num_mel_bins=64,
        frame_length=16,
        frame_shift=16,
    )
    MFCCLen = MFCC.size()[0]

    frames = []
    for i in range(frameCount):
        audioIdxRoll = int((i / frameCount) * MFCCLen)
        resultScaled = tracedScript(
            torch.cat(
                (
                    torch.roll(
                        MFCC,
                        (audioIdxRoll * -1) + 32,
                        dims=0,
                    )[:32],
                    torch.roll(
                        MFCC,
                        (audioIdxRoll * -1),
                        dims=0,
                    )[:32],
                ),
                dim=0,
            ).view(1, 1, 64, 32),
            torch.Tensor(mood).float()
        ).view(-1, 3) * 2.
        # blender has a different coordinate system than three.js
        frames.append(torch.cat(
            (
                torch.index_select(resultScaled, 1, torch.LongTensor([0])),
                torch.index_select(resultScaled, 1, torch.LongTensor([2])),
                torch.index_select(resultScaled, 1, torch.LongTensor([1]))*-1
            ),
            dim=1
        ).view(1, 8320 * 3))

    return frames


@post('/mask')
def mask():
    mood = json.loads(request.forms.get('mood'))
    audio = request.forms.get('audio')
    frameCount = int(float(request.forms.get('frameCount')))
    return json.dumps(list(map(lambda x: x.tolist(), inference(frameCount, audio, mood))))


@route('/maskIndices')
def maskIndices():
    return json.dumps(indices)


@route('/maskNeutral')
def maskNeutral():
    return json.dumps(neutral)


@route('/')
def index():
    return static_file('index.html', ROOT)


@route('/<staticFile>')
def staticStuff(staticFile):
    return static_file(staticFile, ROOT)


@route('/external/js/<staticFile>')
def externalJS(staticFile):
    return static_file(staticFile, os.path.join(ROOT, 'external/js/'))


@route('/external/fonts/<staticFile>')
def externalFonts(staticFile):
    return static_file(staticFile, os.path.join(ROOT, 'external/fonts/'))


if __name__ == '__main__':
    run(server='bjoern')