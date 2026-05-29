function __init_sandbox__()
    sandbox_dir = fileparts(mfilename('fullpath'));
    addpath(sandbox_dir, '-begin');
    fprintf('MATLAB MCP Sandbox initialized. Dangerous functions shadowed.\n');
end
