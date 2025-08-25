# Quilt Platform Release 1.62.0

This release fixes a critical issue that was prevening some 1.61 upgrades, and introduces several new quality of life improvements.

## Major Enhancements

### Support for More Stack Names

The new `EsIngestBucket` introduced in 1.61 to support advanced package searches was incompatible with certain stack names.
That limitation has been removed, so all customers can now safely upgrade.

### HTTP Redirects for Opening QuiltSync

To support clients that cannot directly open the Quilt+ URIs used by [QuiltSync](https://www.quilt.bio/quiltsync),
we have added a [new `redir` route](https://docs.quilt.bio/quilt-platform-catalog-user/uri#catalog-usage) to the Quilt Catalog.
Appending the URL-encoded `quilt+s3://` URI for a package or path to `https://your-catalog-host/redir/`
generates a standard URL that will redirect to the Quilt+ URI, automatically opening QuiltSync (if installed).

For example: `https://open.quiltdata.com/redir/quilt%2Bs3%3A%2F%2Fquilt-example%23package%3Dakarve%2Fcord19%26path%3DCORD19.ipynb`

### Expanded Qurator Developer Tools

The built-in Developer Tools (available in the upper right menu of the Qurator AI chat window) have been expanded with two new features:

#### Session Recordings

Similar to web session inspectors, users can record a portion of their Qurator session,
and then download (or clear) the resulting JSON log.
This is primarily intended for tuning or debugging prompts,
but is also a convenient way to capture structured results.

#### Swappable Models

For the first time, you can modify Qurator to use a different Bedrock Model than the default (currently Claude 3.7).

Please note:

1. You must paste in the exact Bedrock Model ID
2. The model (specifically, the inference profile) must be enabled in the same region as your Quilt stack
3. Qurator expects the model to support both text and image inputs, and may not function with less capable models.

## Other Improvements

- Users can now use the keyboard to enter dates for faceted search filters
- Searches are less likely to experience timeouts when searching large indices on small clusters
- Search filters handle invalid input more gracefully
- Secure search performs better under high load
