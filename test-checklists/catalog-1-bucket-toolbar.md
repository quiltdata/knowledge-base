# Bucket Toolbar Test Plan

## Layout

### Buttons Layout

- Go to http://localhost:3000/b/quilt-example/tree/examples/hurdat/
- Verify the toolbar shows:
  - '➕ Add files'
  - '⬇️ Get files'
  - '📃 Organize'
  - 'Create package'
- Resize to mobile view: all buttons except "Create package" are iconized

- Go to http://localhost:3000/b/quilt-example/tree/examples/formats/JSON.json
- Verify the toolbar shows:
  - '⬇️ Get file'
  - '📃 Organize'
  - '✨ Assist'
- Resize to mobile view: all buttons are iconized

### Directory Popovers

- Go to http://localhost:3000/b/quilt-example/tree/examples/hurdat/
- Select one directory and one file
- Click each button and verify:
  - "➕ Add files"
    - "Create text file"
    - "Upload files"
  - "⬇️ Get files"
    - "Download zip (directory)"
    - "Code" (list files Python, download Python, list CLI, download CLI)
  - "📃 Organize", has (2) badge
    - "2 Selected items"
    - "Add to bookmarks"
    - "Manage selection"
    - "Clear selection"
    - "Delete selected items"
  - "Create Package"
    - s3://quilt-example

### File Popovers

- Go to http://localhost:3000/b/quilt-example/tree/examples/formats/JSON.json
- Click each button and verify:
  - "⬇️ Get file"
    - "Download file"
    - "Code" (download Python, download CLI)
  - "📃 Organize"
    - "Add to bookmarks"
    - 'Edit text content'
    - View as: '✅ JSON, 🕗 Plain text'
    - "Delete"
  - "✨ Assist"
    - Opens AI chat

## Change preferences

### Hide All Buttons

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/config.yaml
- Set:

```yaml
ui:
  actions:
    writeFile: false
    downloadObject: false
    createPackage: false
  blocks:
    qurator: false
```

- Verify only '📃 Organize' appears
- Go to http://localhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/
  - Verify only '📃 Organize' appears

### Hide "special" buttons

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/config.yaml
- Set:

```yaml
ui:
  actions:
    createPackage: false
  blocks:
    qurator: false
```

- Verify "⬇️ Get file" and '📃 Organize' appear, without '✨ Assist'
- Go to http://localhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/
  - Verify 'Create package' does not appear

### Show defaults

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/config.yaml
- Set:

```yaml
ui: {}
```

- Verify all buttons appear
- Go to http://localhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/
  - Verify all buttons appear

## Actions

### Add individual local file and create package

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/.quilt/workflows/
- Click "Add files"
- Pick ./assets/catalog-1-bucket-toolbar/workflows/config.yaml using "Add local file", and upload
- Go to http://localhost:3000/b/fiskus-us-east-1/tree/two/files/
- Select *.txt files
- Create "two/files" package

### Download

- Go to http://localhost:3000/b/quilt-example/tree/examples/formats/JSON.json
- Click "⬇️ Get file" → "Download file" - the file downloads

- Go to http://localhost:3000/b/quilt-example/tree/examples/hurdat/
- Click "⬇️ Get files" → "Download zip" - a zip file containing the selected items downloads

### Bulk upload

- Unpack hurdat.zip
- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/
- Drag and drop half of files and directories directly to the page
- Verify the Upload Dialog appears
- Drag and drop the rest of files
- Upload

### Bookmark

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/quilt_summarize.json
- Click "📃 Organize"
- Toggle "Add to Bookmark" / "Remove from Bookmark"

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/
- Select one directory and one file
- Toggle "Add to Bookmark" / "Remove from Bookmark"

### File view

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/data/atlantic-storms.csv
- Click "📃 Organize" → "View as Plain text"
  - Verify plain text view
- Click "📃 Organize" → "View as Tabular data"
  - Verify tabular view

### Delete

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/config.yaml
- Click "📃 Organize" → "Delete" - confirm in the deletion dialog; the file is removed

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/.quilt/workflows/
- Select all → Click "📃 Organize" → "Delete" - confirm in the deletion dialog; the directory is removed

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/
- Select multiple files and directories
- Click "📃 Organize" → "Delete selected items" - confirm deletion; the selected files are removed

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/
- Hover over "hurdat"
- Click "Delete" icon
- The directory is removed
