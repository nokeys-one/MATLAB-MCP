function [status, cmdout] = system(varargin)
    error('MATLABMCP:SecurityViolation', ...
        'system() is blocked in MATLAB MCP sandbox. Use predefined tools instead.');
end
