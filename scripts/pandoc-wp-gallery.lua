local utils = require 'pandoc.utils'

local function has_class(attr, class)
  for _, c in ipairs(attr.classes) do
    if c == class then
      return true
    end
  end
  return false
end

local function clean_src(src)
  if not src then
    return src
  end
  local cleaned = src:gsub('%?.*$', '')
  local uploads = cleaned:match('^https?://[^/]+/wp%-content/uploads/%d+/%d+/(.+)$')
  if uploads then
    cleaned = uploads
  end
  return cleaned:match('[^/]+$') or cleaned
end

local function first_image(block)
  local found
  pandoc.walk_block(block, {
    Image = function(img)
      if not found then
        found = img
      end
      return img
    end
  })
  return found
end

local function escape_attr(text)
  if not text or text == '' then
    return ''
  end
  return text:gsub('"', '\\"')
end

function Figure(elem)
  if has_class(elem.attr, 'wp-block-gallery') then
    local lines = {'{{< gallery >}}'}
    for _, child in ipairs(elem.content) do
      local img = first_image(child)
      if img then
        local caption = utils.stringify(img.caption)
        local src = clean_src(img.src)
        table.insert(lines, string.format('  <img src="%s" alt="%s" />', src, escape_attr(caption)))
      end
    end
    table.insert(lines, '{{< /gallery >}}')
    return {pandoc.RawBlock('markdown', table.concat(lines, '\n'))}
  elseif has_class(elem.attr, 'wp-block-image') then
    local img = first_image(elem)
    if img then
      local src = clean_src(img.src)
      local image = pandoc.Image(img.caption, src)
      return {pandoc.Para({image})}
    end
  end
end
