# espa-api

This is an API for interacting with the ESPA ordering system. 

For questions regarding this source code, or the ESPA project, please use the
[Landsat Contact Us](https://landsat.usgs.gov/contactus.php) page and specify
USGS ESPA in the "Subject" section.

## Related Pages
* [Description of Products Available](docs/AVAILABLE-PRODUCTS.md)
* [Abbreviations & Definitions](docs/TERMS.md)
* [ESPA Customizations](docs/CUSTOMIZATION.md)

<details>
<summary>Need a scene list?</summary>
The USGS EROS offers two resources for finding valid scene acquisitions:

1. [USGS/EROS Inventory Service API](https://earthexplorer.usgs.gov/inventory/documentation)
1. [Entire Collection of Metadata](https://landsat.usgs.gov/download-entire-collection-metadata)
</details>

## User API
The User API is public facing and available for anyone to code and interact with.  
Version 1 provides the minimum functionality necessary to determine available 
products from a list of inputs, place orders, and view order status. There are 
endpoints for providing available projections, resampling methods, and output formats.

Now that the User API has reached a stable version 1.0, it will always be 
backwards compatible using a _never remove, only add_ strategy. If there will 
ever be a need to break compatibility, it will be announced in the 
[Changelog](CHANGELOG.md) and include a [Warning](#) for a year (if possible) 
before it’s finally really broken.

All user interactions with API functions must be accompanied by valid credentials. 
Accounts are managed in the [USGS EROS Registration system](https://ers.cr.usgs.gov/register/).

The api host is `https://espa.cr.usgs.gov/api`. 

### Quick Unix Walk-through

The ESPA ordering system provides an API for users to interact with using
simple HTTP communications through the programming language of their choice.

For example, to find what products ESPA can produce for a given Landsat 
acquisition: 
```json
curl  --user <erosusername>:<erospassword> https://espa.cr.usgs.gov/api/v0/available-products/LC08_L1TP_029030_20161008_20170220_01_T1
{
    "olitirs8": {
        "inputs": ["LC08_L1TP_029030_20161008_20170220_01_T1"], 
        "products": [
            "source_metadata", "l1", "toa", "bt", "cloud", 
            "sr", "lst", "swe", "sr_ndvi", "sr_evi", "sr_savi",
            "sr_msavi", "sr_ndmi", "sr_nbr", "sr_nbr2", "stats"
        ]
    }
}
```

Then, if the acquisition can be processed into a desired product, create a 
processing order request, including at minimum the output formatting:
```json
curl  --user <erosusername>:<erospassword> https://espa.cr.usgs.gov/api/v0/order -d '
{
  "note": "this is going to be sweet...",
  "format": "gtiff",
  "olitirs8": {
        "inputs": ["LC08_L1TP_029030_20161008_20170220_01_T1"], 
        "products": ["sr_ndvi"]
    }
}'

{
  "orderid": "eros@email.com-01011997-000000-000",
  "status": "ordered"
}
```

Finally, use this order-ID to determine when the scene has completed processing, 
and get the download URL while the output is still on disk:
```json
curl --user <erosusername>:<erospassword> https://espa.cr.usgs.gov/api/v0/item-status/eros@email.com-01011997-000000-000/LC08_L1TP_029030_20161008_20170220_01_T1
{
    "orderid": {
        "eros@email.com-01011997-000000-000": [
            {
                "cksum_download_url": "https://.../orders/.../LC080290302016100801-SC20170329224231.md5",
                "completion_date": "1997-01-01T23:59:59.908435",
                "name": "LC08_L1TP_029030_20161008_20170220_01_T1",
                "note": "''",
                "product_dload_url": "https://.../orders/.../LC080290302016100801-SC20170329224231.tar.gz",
                "scene_id": 00000001,
                "status": "complete"
            }
        ]
    }
}
```

For a more detailed list of available User API operations, see the 
[Available Resources List](docs/API-RESOURCES-LIST.md). 

For a language-specific (python) example, please see [an API Demo](docs/api_demo.html). 

## Fixing Issues

If you think you have found a bug, please see our [Contributing guide](docs/CONTRIBUTING.md)
before opening a new issue.
