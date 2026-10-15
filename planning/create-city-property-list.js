// Creates the "Explore Burton City Property for Sale" SharePoint list with its
// columns, using your own signed-in session. Run it ONCE:
//   1. Open https://burtonmi.sharepoint.com/sites/ITDepartment in your browser.
//   2. Press F12, open the Console tab, paste this whole file, press Enter.
// It is idempotent: re-running it skips the list and any column that already exists.
// Companion to planning/city-property-self-service.md (list schema section).
(async () => {
  const site = 'https://burtonmi.sharepoint.com/sites/ITDepartment';
  const title = 'Explore Burton City Property for Sale';
  const ci = await fetch(site + '/_api/contextinfo', { method: 'POST', headers: { Accept: 'application/json;odata=verbose' } });
  const digest = (await ci.json()).d.GetContextWebInformation.FormDigestValue;
  const H = { Accept: 'application/json;odata=verbose', 'Content-Type': 'application/json;odata=verbose', 'X-RequestDigest': digest };
  const listUrl = site + `/_api/web/lists/getbytitle('${encodeURIComponent(title)}')`;

  let r = await fetch(listUrl + '?$select=Id', { headers: H });
  if (!r.ok) {
    r = await fetch(site + '/_api/web/lists', { method: 'POST', headers: H, body: JSON.stringify({
      __metadata: { type: 'SP.List' }, Title: title, BaseTemplate: 100,
      Description: 'Parcels the City offers for sale. Purchasing edits this list; a flow publishes it to Explore Burton after IT review. One row per parcel; Parcel is the BS&A parcel number.' }) });
    if (!r.ok) { console.error('create list failed', r.status, await r.text()); return; }
    console.log('list created');
  } else console.log('list exists');

  const existing = new Set((await (await fetch(listUrl + '/fields?$select=InternalName', { headers: H })).json()).d.results.map(f => f.InternalName));
  const xml = {
    Address:   '<Field Type="Text" DisplayName="Address" Name="Address" StaticName="Address" Required="TRUE" MaxLength="120" Description="Situs street line, e.g. 1234 E BRISTOL RD. A lot with no number: VACANT E BRISTOL RD" />',
    Track:     '<Field Type="Choice" DisplayName="Track" Name="Track" StaticName="Track" Required="TRUE" Format="Dropdown"><Default>No bid</Default><CHOICES><CHOICE>No bid</CHOICE><CHOICE>Bid Required</CHOICE></CHOICES></Field>',
    Status:    '<Field Type="Choice" DisplayName="Status" Name="Status" StaticName="Status" Required="TRUE" Format="Dropdown"><Default>Available</Default><CHOICES><CHOICE>Available</CHOICE><CHOICE>Sale pending</CHOICE><CHOICE>Sold</CHOICE></CHOICES></Field>',
    Price:     '<Field Type="Number" DisplayName="Price" Name="Price" StaticName="Price" Decimals="0" Min="0" Description="Asking price (No bid) or minimum bid; leave blank for Sealed bid" />',
    LotSize:   '<Field Type="Text" DisplayName="Lot size" Name="LotSize" StaticName="LotSize" MaxLength="60" Description="e.g. 60 x 120 ft or 0.41 acre" />',
    Zoning:    '<Field Type="Text" DisplayName="Zoning" Name="Zoning" StaticName="Zoning" MaxLength="20" />',
    Listed:    '<Field Type="DateTime" DisplayName="Listed" Name="Listed" StaticName="Listed" Format="DateOnly" Description="Date the parcel went on the list" />',
    SoldDate:  '<Field Type="DateTime" DisplayName="Sold date" Name="SoldDate" StaticName="SoldDate" Format="DateOnly" Description="Council approval date; required when Status is Sold" />',
    SoldPrice: '<Field Type="Number" DisplayName="Sold price" Name="SoldPrice" StaticName="SoldPrice" Decimals="0" Min="0" />',
    Photo:     '<Field Type="Text" DisplayName="Photo" Name="Photo" StaticName="Photo" MaxLength="120" Description="Filename under public/property/ (IT adds the file)" />',
    Note:      '<Field Type="Text" DisplayName="Note" Name="Note" StaticName="Note" MaxLength="200" Description="One public sentence" />',
    PacketUrl: '<Field Type="URL" DisplayName="Packet URL" Name="PacketUrl" StaticName="PacketUrl" Required="TRUE" Format="Hyperlink" Description="The offer form or bid packet for this parcel (https only)" />',
  };
  for (const [name, schema] of Object.entries(xml)) {
    if (existing.has(name)) { console.log('exists', name); continue; }
    const f = await fetch(listUrl + '/fields/createfieldasxml', { method: 'POST', headers: H, body: JSON.stringify({
      parameters: { __metadata: { type: 'SP.XmlSchemaFieldCreationInformation' }, SchemaXml: schema, Options: 8 } }) });
    console.log(f.ok ? 'added' : 'FAILED', name, f.ok ? '' : await f.text());
  }
  // Rename Title to Parcel and add every column to the default view.
  await fetch(listUrl + "/fields/getbyinternalnameortitle('Title')", { method: 'POST', headers: { ...H, 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' },
    body: JSON.stringify({ __metadata: { type: 'SP.Field' }, Title: 'Parcel', Description: 'BS&A parcel number, e.g. 59-12-776-262' }) });
  const view = (await (await fetch(listUrl + '/defaultview?$select=Id', { headers: H })).json()).d.Id;
  const inView = new Set((await (await fetch(listUrl + `/views('${view}')/viewfields`, { headers: H })).json()).d.Items.results);
  for (const name of Object.keys(xml)) {
    if (inView.has(name)) continue;
    await fetch(listUrl + `/views('${view}')/viewfields/addviewfield('${name}')`, { method: 'POST', headers: H });
  }
  console.log('done: ' + site + '/Lists/' + encodeURIComponent(title.replace(/ /g, '')));
})();
