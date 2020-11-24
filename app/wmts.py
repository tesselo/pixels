import datetime
from urllib.parse import quote

WMTS_BASE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
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
        <ServiceMetadataURL xlink:href="{metadata_url}"/>
</Capabilities>
"""

TILE_MATRIX_SET_TEMPLATE = """
<TileMatrixSet>
    <ows:Identifier>epsg3857</ows:Identifier>
    <ows:BoundingBox crs="urn:ogc:def:crs:EPSG:6.18.3:3857">
    <ows:LowerCorner>-20037508.342789244 -20037508.342789244</ows:LowerCorner>
    <ows:UpperCorner>20037508.342789244 20037508.342789244</ows:UpperCorner>
    </ows:BoundingBox>
    <ows:SupportedCRS>urn:ogc:def:crs:EPSG:6.18.3:3857</ows:SupportedCRS>
    <WellKnownScaleSet>urn:ogc:def:wkss:OGC:1.0:GoogleMapsCompatible</WellKnownScaleSet>
    <TileMatrix>
    <ows:Identifier>0</ows:Identifier>
    <ScaleDenominator>559082264.0287178</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>1</MatrixWidth>
    <MatrixHeight>1</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>1</ows:Identifier>
    <ScaleDenominator>279541132.0143589</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>2</MatrixWidth>
    <MatrixHeight>2</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>2</ows:Identifier>
    <ScaleDenominator>139770566.00717944</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>4</MatrixWidth>
    <MatrixHeight>4</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>3</ows:Identifier>
    <ScaleDenominator>69885283.00358972</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>8</MatrixWidth>
    <MatrixHeight>8</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>4</ows:Identifier>
    <ScaleDenominator>34942641.50179486</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>16</MatrixWidth>
    <MatrixHeight>16</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>5</ows:Identifier>
    <ScaleDenominator>17471320.75089743</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>32</MatrixWidth>
    <MatrixHeight>32</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>6</ows:Identifier>
    <ScaleDenominator>8735660.375448715</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>64</MatrixWidth>
    <MatrixHeight>64</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>7</ows:Identifier>
    <ScaleDenominator>4367830.1877243575</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>128</MatrixWidth>
    <MatrixHeight>128</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>8</ows:Identifier>
    <ScaleDenominator>2183915.0938621787</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>256</MatrixWidth>
    <MatrixHeight>256</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>9</ows:Identifier>
    <ScaleDenominator>1091957.5469310894</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>512</MatrixWidth>
    <MatrixHeight>512</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>10</ows:Identifier>
    <ScaleDenominator>545978.7734655447</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>1024</MatrixWidth>
    <MatrixHeight>1024</MatrixHeight>
    </TileMatrix>
    <TileMatrix>
    <ows:Identifier>11</ows:Identifier>
    <ScaleDenominator>272989.38673277234</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>2048</MatrixWidth>
    <MatrixHeight>2048</MatrixHeight>
    </TileMatrix>
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
    <TileMatrix>
    <ows:Identifier>19</ows:Identifier>
    <ScaleDenominator>1066.364791924892</ScaleDenominator>
    <TopLeftCorner>-20037508.342789244 20037508.342789244</TopLeftCorner>
    <TileWidth>256</TileWidth>
    <TileHeight>256</TileHeight>
    <MatrixWidth>524288</MatrixWidth>
    <MatrixHeight>524288</MatrixHeight>
    </TileMatrix>
</TileMatrixSet>
"""

TILE_LAYER_TEMPLATE = """
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
"""

LATEST_PIXEL_URL_TEMPLATE = "{host}tiles/{{TileMatrix}}/{{TileCol}}/{{TileRow}}.png?key={key}&amp;end={end}&amp;max_cloud_cover_percentage={cloud}"
COMPOSITE_URL_TEMPLATE = (
    "{host}composite/{projectid}/{{TileMatrix}}/{{TileCol}}/{{TileRow}}.png?key={key}"
)


def gen(key, host, max_cloud_cover_percentage=100):
    """
    Generate WMTS xml string.
    """
    xml = ""
    for year in range(2000, 2021):
        for month in range(1, 13):
            end = datetime.date(year=year, month=month, day=1)
            if end > datetime.datetime.now().date():
                break
            title = "Latest Pixel " + end.strftime("%B %Y")
            url = LATEST_PIXEL_URL_TEMPLATE.format(
                host=host,
                key=key,
                end=end,
                cloud=max_cloud_cover_percentage,
            )
            xml += TILE_LAYER_TEMPLATE.format(
                title=title,
                identifier=end.strftime("%Y%m"),
                url=url,
            )

    return WMTS_BASE_TEMPLATE.format(
        metadata_url="{}wmts".format(host),
        layers=xml,
        mat=TILE_MATRIX_SET_TEMPLATE,
    )


def gen_composite(key, host, projectid):
    """
    WMTS Endpoint for one project.
    """
    xml = ""
    url = COMPOSITE_URL_TEMPLATE.format(
        host=host,
        key=key,
        projectid=projectid,
    )
    xml += TILE_LAYER_TEMPLATE.format(
        title="Composite RGB {}".format(projectid),
        identifier="".join(e for e in projectid if e.isalnum()) + "rgb",
        url=url,
    )
    xml += TILE_LAYER_TEMPLATE.format(
        title="Composite NDVI {}".format(projectid),
        identifier="".join(e for e in projectid if e.isalnum()) + "ndvi",
        url=url
        + "&amp;formula={}&amp;to=006837&amp;from=a50026&amp;over=ffffbf&amp;min=-1&amp;max=1".format(
            quote("(B08-B04)/(B08+B04)")
        ),
    )

    return WMTS_BASE_TEMPLATE.format(
        metadata_url="{}composite/{}/wmts".format(host, projectid),
        layers=xml,
        mat=TILE_MATRIX_SET_TEMPLATE,
    )
