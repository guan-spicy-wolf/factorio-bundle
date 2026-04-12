-- Simple test file for Lua

-- Basic function to test
local function add(a, b)
    return a + b
end

local function greet(name)
    return "Hello, " .. name .. "!"
end

-- Test cases
local function runTests()
    print("Running tests...")
    
    -- Test add function
    assert(add(2, 3) == 5, "Add test failed")
    print("✓ add(2, 3) == 5")
    
    assert(add(-1, 1) == 0, "Add negative test failed")
    print("✓ add(-1, 1) == 0")
    
    -- Test greet function
    assert(greet("World") == "Hello, World!", "Greet test failed")
    print("✓ greet('World') == 'Hello, World!'")
    
    print("\nAll tests passed!")
end

-- Run the tests
runTests()
