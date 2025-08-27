# Bucket Toolbar Test Plan

## Layout

### Buttons Layout

- Go to http://localhost:3000/b/quilt-example/tree/examples/hurdat/
- See toolbar with
  - '➕ Add files'
  - '⬇️ Get files'
  - '📃 Organize'
  - 'Create package'
- Squeeze to mobile view: all buttons except "Create package" iconized

- Go to http://localhost:3000/b/quilt-example/tree/examples/formats/JSON.json
- See toolbar with
  - '⬇️ Get file'
  - '📃 Organize'
  - '✨ Assist'
- Squeeze to mobile view: all buttons iconized

### Directory Popovers

- Go to http://localhost:3000/b/quilt-example/tree/examples/hurdat/
- Select one directory and one file
- Click on every button and see:
  - "➕ Add files"
    - "Create text file"
    - "Upload files"
  - "⬇️ Get files"
    - "Download zip (directory)"
    - "Code" (list files Python, download Python, list CLI, download CLI)
  - 📃 Organize, has (2) badge
    - "2 Selected items"
    - "Add to bookmarks"
    - "Manage selection"
    - "Clear selection"
    - "Delete selected items"
  - "Create Package"
    - Need to create config.yml

### File Popovers

- Go to http://localhost:3000/b/quilt-example/tree/examples/formats/JSON.json
- Click on every button and see:
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

- Go to http://loaclhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/config.yaml
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

- See only '📃 Organize'
- Go to http://loaclhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/
  - See only '📃 Organize'

### Hide "special" buttons

- Go to http://loaclhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/config.yaml
- Set:

```yaml
ui:
  actions:
    createPackage: false
  blocks:
    qurator: false
```

- See "⬇️ Get file" and '📃 Organize', without '✨ Assist'
- Go to http://loaclhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/
  - See no 'Create package'

### Show defaults

- Go to http://loaclhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/config.yaml
- Set:

```yaml
ui: {}
```

- See all buttons
- Go to http://loaclhost:3000/b/fiskus-us-east-1/tree/.quilt/catalog/
  - See all buttons

## Actions

### Add individual local file and create package

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/.quilt/workflows/
- Click "Add files"
- Pick ./assets/catalog-1-bucket-toolbar/workflows/config.yaml using "Add local file", and upload
- Go to http://localhost:3000/b/fiskus-us-east-1/tree/two/files/
- Select \*.txt files
- Create "two/files" package

### Download

- Go to http://localhost:3000/b/quilt-example/tree/examples/formats/JSON.json
- Click "⬇️ Get file" → "Download file" - file downloads

- Go to http://localhost:3000/b/quilt-example/tree/examples/hurdat/
- Click "⬇️ Get files" → "Download zip" - zip file downloads with selected items

### Bulk upload

- Unpack hurdat.zip
- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/
- Drag'n'drop half of files and directories directly to the page
- See Upload Dialog
- Drag'n'drop the rest of files
- Upload

### Bookmark

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/quilt_summarize.json
- Click "Organize"
- Toggle "Add to Bookmark" / "Remove from Bookmark"

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/
- Select one directory and one file // TODO: make able to remove from bookmarks using this menu
- Mouseover over these two items and de-select from bookmarks

### File view

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/data/atlantic-storms.csv
- Click "📃 Organize" → "View as Plain text"
- Click "📃 Organize" → "View as Tabular data"
- See a correct file viewer

### Delete

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/quilt_summarize.json
- Click "📃 Organize" → "Delete" - confirm deletion dialog, file is removed

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/hurdat/
- Select multiple files and directories
- Click "📃 Organize" → "Delete selected items" - confirm deletion, selected files removed

- Go to http://localhost:3000/b/fiskus-us-east-1/tree/
- Mouseover over "hurdat"
- Click "Delete" icon // FIXME: works only for objects
- Directory removed
