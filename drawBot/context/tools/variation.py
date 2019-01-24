import CoreText
from collections import OrderedDict

from fontTools.ttLib import TTFont

from drawBot.misc import memoize

"""
https://developer.apple.com/documentation/coretext/ctfont/font_variation_axis_dictionary_keys?language=objc
https://developer.apple.com/documentation/coretext/1508650-ctfontdescriptorcreatecopywithva?language=objc
"""


def convertIntToVariationTag(value):
    chars = []
    for shift in range(4):
        chars.append(chr((value >> (shift * 8)) & 0xff))
    return "".join(reversed(chars))


def convertVariationTagToInt(tag):
    assert len(tag) == 4
    i = 0
    for c in tag:
        i <<= 8
        i |= ord(c)
    return i


@memoize
def getVariationAxesForFontName(fontName):
    axes = OrderedDict()
    font = CoreText.CTFontCreateWithName(fontName, 12, None)
    variationAxesDescriptions = CoreText.CTFontCopyVariationAxes(font)
    if variationAxesDescriptions is None:
        # 'normal' fonts have no axes descriptions
        return axes
    for variationAxesDescription in variationAxesDescriptions:
        tag = convertIntToVariationTag(variationAxesDescription[CoreText.kCTFontVariationAxisIdentifierKey])
        name = variationAxesDescription[CoreText.kCTFontVariationAxisNameKey]
        minValue = variationAxesDescription[CoreText.kCTFontVariationAxisMinimumValueKey]
        maxValue = variationAxesDescription[CoreText.kCTFontVariationAxisMaximumValueKey]
        defaultValue = variationAxesDescription[CoreText.kCTFontVariationAxisDefaultValueKey]
        data = dict(name=name, minValue=minValue, maxValue=maxValue, defaultValue=defaultValue)
        axes[tag] = data
    return axes


@memoize
def getVariationNamedInstancesForFontName(fontName):
    """
    Return a dict { postscriptName: location } of all named instances in a given font.
    """
    instances = {}
    font = CoreText.CTFontCreateWithName(fontName, 12, None)
    if font is None:
        return instances
    cgFont = CoreText.CGFontCreateWithFontName(fontName)
    fontDescriptor = font.fontDescriptor()
    url = CoreText.CTFontDescriptorCopyAttribute(fontDescriptor, CoreText.kCTFontURLAttribute)
    if url is None:
        return instances

    variationAxesDescriptions = CoreText.CTFontCopyVariationAxes(font)
    if variationAxesDescriptions is None:
        # 'normal' fonts have no named instances
        return instances
    tagNameMap = {}
    for variationAxesDescription in variationAxesDescriptions:
        tag = convertIntToVariationTag(variationAxesDescription[CoreText.kCTFontVariationAxisIdentifierKey])
        name = variationAxesDescription[CoreText.kCTFontVariationAxisNameKey]
        tagNameMap[tag] = name

    ft = TTFont(url.path())
    if "fvar" in ft:
        fvar = ft["fvar"]

        for instance in fvar.instances:
            fontVariations = dict()
            for axis, value in instance.coordinates.items():
                fontVariations[tagNameMap[axis]] = value

            varFont = CoreText.CGFontCreateCopyWithVariations(cgFont, fontVariations)
            postScriptName = CoreText.CGFontCopyPostScriptName(varFont)
            instances[postScriptName] = instance.coordinates

    ft.close()
    return instances
