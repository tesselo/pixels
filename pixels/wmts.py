import datetime

WMTS_BASE_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0" xmlns:ows="http://www.opengis.net/ows/1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:gml="http://www.opengis.net/gml" xsi:schemaLocation="http://www.opengis.net/wmts/1.0 http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd" version="1.0.0">
        <ows:ServiceIdentification>
                <ows:Title>Web Map Tile Service</ows:Title>
                <ows:ServiceType>OGC WMTS</ows:ServiceType>
                <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
        </ows:ServiceIdentification>
        <ows:ServiceProvider>
                <ows:ProviderName>Tesselo</ows:ProviderName>
                <ows:ProviderSite xlink:href="https://tesselo.com"/>
        </ows:ServiceProvider>
        <Contents>
        {layers}
        {mat}
        </Contents>
        <ServiceMetadataURL xlink:href="https://pixels.tesselo.com/wmts"/>
</Capabilities>
'''

TILE_MATRIX_SET_TEMPLATE = '''
<TileMatrixSet>
    <ows:Identifier>epsg3857</ows:Identifier>
    <ows:BoundingBox crs="urn:ogc:def:crs:EPSG:6.18.3:3857">
    <ows:LowerCorner>-20037508.342789244 -20037508.342789244</ows:LowerCorner>
    <ows:UpperCorner>20037508.342789244 20037508.342789244</ows:UpperCorner>
    </ows:BoundingBox>
    <ows:SupportedCRS>urn:ogc:def:crs:EPSG:6.18.3:3857</ows:SupportedCRS>
    <WellKnownScaleSet>urn:ogc:def:wkss:OGC:1.0:GoogleMapsCompatible</WellKnownScaleSet>
    <TileMatrix>
    <ows:Identifier>12</ows:Identifier>
    <ScaleDenominator>136494.69336638617</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>4096</MatrixWidth>
    <MatrixHeight>4096</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>13</ows:Identifier>
    <ScaleDenominator>68247.34668319309</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>8192</MatrixWidth>
    <MatrixHeight>8192</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>14</ows:Identifier>
    <ScaleDenominator>34123.67334159654</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>16384</MatrixWidth>
    <MatrixHeight>16384</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>15</ows:Identifier>
    <ScaleDenominator>17061.83667079827</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>32768</MatrixWidth>
    <MatrixHeight>32768</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>16</ows:Identifier>
    <ScaleDenominator>8530.918335399136</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>65536</MatrixWidth>
    <MatrixHeight>65536</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>17</ows:Identifier>
    <ScaleDenominator>4265.459167699568</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>131072</MatrixWidth>
    <MatrixHeight>131072</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>18</ows:Identifier>
    <ScaleDenominator>2132.729583849784</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>262144</MatrixWidth>
    <MatrixHeight>262144</MatrixHeight>
    </TileMatrix>
</TileMatrixSet>
'''

TILE_LAYER_TEMPLATE = '''
<Layer>
    <ows:Title>{title}</ows:Title>
    <ows:WGS84BoundingBox crs="urn:ogc:def:crs:OGC:2:84">
        <ows:LowerCorner>-180 -90</ows:LowerCorner>
        <ows:UpperCorner>180 90</ows:UpperCorner>
    </ows:WGS84BoundingBox>
    <ows:Identifier>{identifier}</ows:Identifier>
    <Style isDefault="true">
            <ows:Identifier>Default</ows:Identifier>
    </Style>
    <Format>image/png</Format>
    <TileMatrixSetLink>
        <TileMatrixSet>epsg3857</TileMatrixSet>
    </TileMatrixSetLink>
    <ResourceURL format="image/png" template="{url}" resourceType="tile"/>
</Layer>
'''

URL_TEMPLATE = 'https://pixels.tesselo.com/tiles/{{z}}/{{x}}/{{y}}.png?key={key}&amp;end={end}&amp;start={start}&amp;s2_max_cloud_cover_percentage=50'


def gen(key):
    """
    Generate WMTS xml string.
    """
    xml = ''
    for year in (2016, 2017, 2018, 2019):
        for month in range(1, 13):
            end = datetime.date(year=year, month=month, day=1)
            start = end - datetime.timedelta(weeks=4)
            if end > datetime.datetime.now().date():
                break
            title = 'Latest Pixel ' + end.strftime('%B %Y')
            url = URL_TEMPLATE.format(
                key=key,
                end=end,
                start=start,
            )
            xml += TILE_LAYER_TEMPLATE.format(
                title=title,
                identifier=end.strftime('%Y-%m'),
                url=url,
            )

    return WMTS_BASE_TEMPLATE.format(
        layers=xml,
        mat=TILE_MATRIX_SET_TEMPLATE,
    )
