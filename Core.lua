-- ============================================================================
-- BiS Buddy - Core
-- Minimap icon click -> BiS list for current class/spec
-- Data source: SimulationCraft profiles (auto-updated)
-- ============================================================================

local addonName, addon = ...

-- ============================================================================
-- Saved Variables & Defaults
-- ============================================================================
BiSBuddyDB = BiSBuddyDB or {}

local defaults = {
    minimapPos = 225,
}

local function EnsureDefaults()
    for k, v in pairs(defaults) do
        if BiSBuddyDB[k] == nil then
            BiSBuddyDB[k] = v
        end
    end
end

-- ============================================================================
-- Helper Functions
-- ============================================================================

local function GetPlayerClassKey()
    local _, classFilename = UnitClass("player")
    return classFilename
end

local function GetPlayerSpecIndex()
    return GetSpecialization() or 1
end

local function GetPlayerSpecName()
    local specIndex = GetPlayerSpecIndex()
    local _, name = GetSpecializationInfo(specIndex)
    return name or "Unknown"
end

-- Item link cache (items load asynchronously)
local itemCache = {}

local function LoadItemAsync(itemID, callback)
    if itemCache[itemID] then
        callback(itemCache[itemID])
        return
    end

    local item = Item:CreateFromItemID(itemID)
    item:ContinueOnItemLoad(function()
        local name, link, quality, _, _, _, _, _, _, icon = C_Item.GetItemInfo(itemID)
        if link then
            itemCache[itemID] = {
                name = name,
                link = link,
                quality = quality,
                icon = icon,
            }
        end
        callback(itemCache[itemID])
    end)
end

-- ============================================================================
-- Minimap Button
-- ============================================================================

local minimapButton = CreateFrame("Button", "BiSBuddyMinimapButton", Minimap)
minimapButton:SetSize(32, 32)
minimapButton:SetFrameStrata("MEDIUM")
minimapButton:SetFrameLevel(8)
minimapButton:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")

local icon = minimapButton:CreateTexture(nil, "ARTWORK")
icon:SetTexture("Interface\\Icons\\INV_Misc_Book_09")
icon:SetSize(20, 20)
icon:SetPoint("CENTER", 0, 0)

local border = minimapButton:CreateTexture(nil, "OVERLAY")
border:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
border:SetSize(54, 54)
border:SetPoint("TOPLEFT", 0, 0)

local function UpdateMinimapPosition()
    local angle = math.rad(BiSBuddyDB.minimapPos or 225)
    local radius = 80
    minimapButton:SetPoint("CENTER", Minimap, "CENTER",
        math.cos(angle) * radius, math.sin(angle) * radius)
end

minimapButton:RegisterForDrag("LeftButton")
minimapButton:SetMovable(true)

minimapButton:SetScript("OnDragStart", function(self)
    self:SetScript("OnUpdate", function()
        local mx, my = Minimap:GetCenter()
        local cx, cy = GetCursorPosition()
        local scale = Minimap:GetEffectiveScale()
        BiSBuddyDB.minimapPos = math.deg(math.atan2(cy / scale - my, cx / scale - mx))
        UpdateMinimapPosition()
    end)
end)

minimapButton:SetScript("OnDragStop", function(self)
    self:SetScript("OnUpdate", nil)
end)

minimapButton:SetScript("OnEnter", function(self)
    GameTooltip:SetOwner(self, "ANCHOR_LEFT")
    GameTooltip:SetText("BiS Buddy", 1, 0.82, 0)
    GameTooltip:AddLine("Left-click: Show BiS list", 1, 1, 1)
    GameTooltip:AddLine("Right-click: Reload data", 0.7, 0.7, 0.7)
    GameTooltip:AddLine("Drag: Move icon", 0.7, 0.7, 0.7)
    if BiSBuddyData and BiSBuddyData.dataVersion then
        GameTooltip:AddLine(" ")
        GameTooltip:AddLine("Data: " .. (BiSBuddyData.dataTier or "?") ..
            " | Updated: " .. BiSBuddyData.dataVersion, 0.4, 0.8, 1)
    end
    GameTooltip:Show()
end)

minimapButton:SetScript("OnLeave", function()
    GameTooltip:Hide()
end)

-- ============================================================================
-- Main Frame
-- ============================================================================

local bisFrame = CreateFrame("Frame", "BiSBuddyFrame", UIParent, "BackdropTemplate")
bisFrame:SetSize(450, 560)
bisFrame:SetPoint("CENTER")
bisFrame:SetMovable(true)
bisFrame:EnableMouse(true)
bisFrame:RegisterForDrag("LeftButton")
bisFrame:SetScript("OnDragStart", bisFrame.StartMoving)
bisFrame:SetScript("OnDragStop", bisFrame.StopMovingOrSizing)
bisFrame:SetFrameStrata("DIALOG")
bisFrame:Hide()

bisFrame:SetBackdrop({
    bgFile   = "Interface\\DialogFrame\\UI-DialogBox-Background-Dark",
    edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
    tile = true, tileSize = 32, edgeSize = 32,
    insets = { left = 8, right = 8, top = 8, bottom = 8 },
})
bisFrame:SetBackdropColor(0.05, 0.05, 0.08, 0.95)

-- Title
local titleBar = bisFrame:CreateTexture(nil, "ARTWORK")
titleBar:SetTexture("Interface\\DialogFrame\\UI-DialogBox-Header")
titleBar:SetSize(280, 64)
titleBar:SetPoint("TOP", 0, 12)

local titleText = bisFrame:CreateFontString(nil, "OVERLAY", "GameFontNormal")
titleText:SetPoint("TOP", 0, -2)
titleText:SetText("BiS Buddy")

-- Close button
local closeBtn = CreateFrame("Button", nil, bisFrame, "UIPanelCloseButton")
closeBtn:SetPoint("TOPRIGHT", -5, -5)

-- Class + Spec info
local infoText = bisFrame:CreateFontString(nil, "OVERLAY", "GameFontHighlight")
infoText:SetPoint("TOP", 0, -30)

-- Data source
local sourceText = bisFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
sourceText:SetPoint("TOP", 0, -48)
sourceText:SetTextColor(0.6, 0.6, 0.6)

-- Progress display (X/Y BiS items equipped)
local progressText = bisFrame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
progressText:SetPoint("TOP", 0, -62)

-- Scroll frame
local scrollFrame = CreateFrame("ScrollFrame", "BiSBuddyScrollFrame", bisFrame, "UIPanelScrollFrameTemplate")
scrollFrame:SetPoint("TOPLEFT", 16, -78)
scrollFrame:SetPoint("BOTTOMRIGHT", -32, 16)

local scrollChild = CreateFrame("Frame", nil, scrollFrame)
scrollChild:SetSize(390, 1)
scrollFrame:SetScrollChild(scrollChild)

-- ============================================================================
-- Item Rows
-- ============================================================================

local itemRows = {}

local function CreateItemRow(parent, index)
    local row = CreateFrame("Frame", nil, parent)
    row:SetSize(385, 32)
    row:SetPoint("TOPLEFT", 0, -(index - 1) * 34)

    -- Item icon
    row.icon = row:CreateTexture(nil, "ARTWORK")
    row.icon:SetSize(26, 26)
    row.icon:SetPoint("LEFT", 4, 0)
    row.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)

    -- Slot name
    row.slotText = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    row.slotText:SetPoint("LEFT", row.icon, "RIGHT", 6, 0)
    row.slotText:SetWidth(80)
    row.slotText:SetJustifyH("LEFT")
    row.slotText:SetTextColor(0.8, 0.7, 0.2)

    -- Item name button (clickable)
    row.itemBtn = CreateFrame("Button", nil, row)
    row.itemBtn:SetPoint("LEFT", row.slotText, "RIGHT", 4, 0)
    row.itemBtn:SetPoint("RIGHT", row, "RIGHT", -30, 0)
    row.itemBtn:SetHeight(20)

    row.itemBtn.text = row.itemBtn:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    row.itemBtn.text:SetAllPoints()
    row.itemBtn.text:SetJustifyH("LEFT")

    -- Status icon (equipped?)
    row.statusIcon = row:CreateTexture(nil, "OVERLAY")
    row.statusIcon:SetSize(16, 16)
    row.statusIcon:SetPoint("RIGHT", -4, 0)

    -- Alternating background
    local bg = row:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    bg:SetColorTexture(1, 1, 1, (index % 2 == 0) and 0.03 or 0.06)

    return row
end

-- ============================================================================
-- Show BiS List
-- ============================================================================

local function ShowBiSList()
    local classKey = GetPlayerClassKey()
    local specIndex = GetPlayerSpecIndex()
    local specName = GetPlayerSpecName()

    -- Class color
    local cc = RAID_CLASS_COLORS[classKey] or { r = 1, g = 1, b = 1 }
    infoText:SetText(string.format("|cff%02x%02x%02x%s|r - %s",
        cc.r * 255, cc.g * 255, cc.b * 255, UnitClass("player"), specName))

    -- Check data
    if not BiSBuddyData or not BiSBuddyData.items then
        sourceText:SetText("|cffff4444Data.lua is missing or empty!|r")
        progressText:SetText("")
        for _, r in ipairs(itemRows) do r:Hide() end
        bisFrame:Show()
        return
    end

    local classData = BiSBuddyData.items[classKey]
    if not classData then
        sourceText:SetText("|cffff4444No BiS data for " .. (UnitClass("player") or classKey) .. "!|r")
        progressText:SetText("Run the updater or wait for an addon update.")
        for _, r in ipairs(itemRows) do r:Hide() end
        bisFrame:Show()
        return
    end

    local specData = classData[specIndex]
    if not specData then
        sourceText:SetText("|cffff4444No data for " .. specName .. "!|r")
        progressText:SetText("")
        for _, r in ipairs(itemRows) do r:Hide() end
        bisFrame:Show()
        return
    end

    sourceText:SetText("Source: " .. (specData.source or "SimulationCraft") ..
        " | Updated: " .. (specData.updated or "?"))
    sourceText:SetTextColor(0.6, 0.6, 0.6)

    -- Hide all rows
    for _, r in ipairs(itemRows) do r:Hide() end

    -- Sorted slots
    local sortedSlots = {}
    for slotID, slotInfo in pairs(BiSBuddyData.SLOTS) do
        if specData.gear[slotID] then
            table.insert(sortedSlots, { slotID = slotID, slotName = slotInfo.name })
        end
    end
    table.sort(sortedSlots, function(a, b) return a.slotID < b.slotID end)

    local equippedCount = 0
    local totalCount = #sortedSlots

    for i, slotEntry in ipairs(sortedSlots) do
        local row = itemRows[i]
        if not row then
            row = CreateItemRow(scrollChild, i)
            itemRows[i] = row
        end

        local itemData = specData.gear[slotEntry.slotID]
        row.slotText:SetText(slotEntry.slotName)

        -- Placeholder text
        row.itemBtn.text:SetText("|cffaaaaaa" .. (itemData.name or "Loading...") .. "|r")
        row.itemBtn.link = nil
        row.itemBtn.itemID = itemData.itemID
        row.icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")

        -- Load item asynchronously (name, link, icon, quality)
        local currentRow = row
        local currentItemID = itemData.itemID
        LoadItemAsync(currentItemID, function(info)
            if not info or currentRow.itemBtn.itemID ~= currentItemID then return end
            currentRow.itemBtn.text:SetText(info.link or info.name or "?")
            currentRow.itemBtn.link = info.link
            if info.icon then
                currentRow.icon:SetTexture(info.icon)
            end
        end)

        -- Tooltip
        row.itemBtn:SetScript("OnEnter", function(self)
            if self.link then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:SetHyperlink(self.link)
                GameTooltip:Show()
            elseif self.itemID then
                GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
                GameTooltip:SetItemByID(self.itemID)
                GameTooltip:Show()
            end
        end)

        row.itemBtn:SetScript("OnLeave", function()
            GameTooltip:Hide()
        end)

        -- Click -> chat link
        row.itemBtn:SetScript("OnClick", function(self)
            if self.link then
                if ChatFrame1EditBox:IsVisible() then
                    ChatFrame1EditBox:Insert(self.link)
                else
                    print(self.link)
                end
            end
        end)

        -- Equipped check
        local equippedID = GetInventoryItemID("player", slotEntry.slotID)
        if equippedID and equippedID == itemData.itemID then
            row.statusIcon:SetTexture("Interface\\RaidFrame\\ReadyCheck-Ready")
            equippedCount = equippedCount + 1
        else
            row.statusIcon:SetTexture("Interface\\RaidFrame\\ReadyCheck-NotReady")
        end
        row.statusIcon:Show()

        row:Show()
    end

    -- Progress
    local pctColor = equippedCount == totalCount and "|cff00ff00" or "|cffffff00"
    progressText:SetText(string.format("%s%d/%d BiS items equipped|r",
        pctColor, equippedCount, totalCount))

    scrollChild:SetHeight(#sortedSlots * 34 + 10)
    bisFrame:Show()
end

-- ============================================================================
-- Click Handler
-- ============================================================================

minimapButton:RegisterForClicks("LeftButtonUp", "RightButtonUp")
minimapButton:SetScript("OnClick", function(self, button)
    if button == "LeftButton" then
        if bisFrame:IsShown() then
            bisFrame:Hide()
        else
            ShowBiSList()
        end
    elseif button == "RightButton" then
        ShowBiSList()
        print("|cff00ccff[BiS Buddy]|r Data reloaded!")
    end
end)

-- ============================================================================
-- Slash Commands
-- ============================================================================

SLASH_BISBUDDY1 = "/bis"
SLASH_BISBUDDY2 = "/bisbuddy"
SlashCmdList["BISBUDDY"] = function(msg)
    msg = (msg or ""):lower():trim()
    if msg == "hide" then
        bisFrame:Hide()
    elseif msg == "reset" then
        BiSBuddyDB = {}
        EnsureDefaults()
        UpdateMinimapPosition()
        print("|cff00ccff[BiS Buddy]|r Settings reset.")
    elseif msg == "version" or msg == "info" then
        print("|cff00ccff[BiS Buddy]|r Info:")
        if BiSBuddyData then
            print("  Data version: " .. (BiSBuddyData.dataVersion or "unknown"))
            print("  Tier: " .. (BiSBuddyData.dataTier or "unknown"))
            print("  Source: " .. (BiSBuddyData.dataSource or "unknown"))
        else
            print("  No data loaded!")
        end
    elseif msg == "help" then
        print("|cff00ccff[BiS Buddy]|r Commands:")
        print("  /bis         - Show BiS list")
        print("  /bis hide    - Close window")
        print("  /bis info    - Show data version")
        print("  /bis reset   - Reset settings")
    else
        if bisFrame:IsShown() then
            bisFrame:Hide()
        else
            ShowBiSList()
        end
    end
end

-- ============================================================================
-- Events
-- ============================================================================

local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("PLAYER_LOGIN")
eventFrame:RegisterEvent("ACTIVE_PLAYER_SPEC_CHANGED")

eventFrame:SetScript("OnEvent", function(self, event)
    if event == "PLAYER_LOGIN" then
        EnsureDefaults()
        UpdateMinimapPosition()
        local version = BiSBuddyData and BiSBuddyData.dataVersion or "no data"
        print("|cff00ccff[BiS Buddy]|r Loaded! Data: " .. version ..
            " | Use |cff00ff00/bis|r or click the minimap icon.")
    elseif event == "ACTIVE_PLAYER_SPEC_CHANGED" then
        if bisFrame:IsShown() then
            ShowBiSList()
        end
    end
end)

-- ESC closes the window
tinsert(UISpecialFrames, "BiSBuddyFrame")
