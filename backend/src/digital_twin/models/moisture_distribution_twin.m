
clear; clc; close all;

% --- 1. Configuration ---
% Absolute path to the database file created by the Python GUI
dbfile = '/home/d/Documents/TIHIoTChanakya/greenhouse.db'; 
refresh_rate_sec = 5; % How often to query the database (in seconds)

% --- 2. Simulation Parameters ---
Nx = 100;           % Grid size (X-axis)
Ny = 100;           % Grid size (Y-axis)
max_iter = 1000;    % Max iterations per refresh (lower is fine for live updates)
tolerance = 1e-4;   % Convergence tolerance

% --- 3. Setup the Visualization ---
fig = figure('Name', 'Live Digital Twin - Moisture Map', 'Color', 'white');
x_axis = linspace(0, 10, Nx); 
y_axis = linspace(0, 10, Ny); % Represents a 10m greenhouse length
s = surf(x_axis, y_axis, zeros(Nx, Ny)); % Create an initial empty plot object

% Styling
shading interp;
colormap(hot);
c = colorbar;
c.Label.String = 'Soil Moisture (%)';
title('Real-Time Volumetric Soil Moisture Distribution', 'FontSize', 14);
xlabel('Greenhouse Width (m)', 'FontSize', 12);Saved data to DB at 2025-12-12 17:00:08
Received message on topic esp32/npk: {"n":61,"p":86,"k":173}
Received message on topic pico1/moisture1: 31.5
Received message on topic pico1/moisture2: 62.0
Received message on topic pico1/bme280: 25.5,0.0,483920864.0
Saved data to DB at 2025-12-12 17:00:13
ylabel('Greenhouse Length (m)', 'FontSize', 12);
zlabel('Moisture Content (%)', 'FontSize', 12);
view(45, 30);
grid on;
zlim([0 100]); %  Z-axis fixed from 0-100% for stable visualization
caxis([0 100]); %  color bar fixed from 0-100%

% --- 4. Main Live Loop ---
fprintf('Starting Live Digital Twin...\n');
fprintf('Connecting to database: %s\n', dbfile);

while ishandle(fig) % This loop runs as long as the figure window is open
    
    try
        % --- A. Connect and Fetch Live Data ---
        % Use 'readonly' to prevent locking the database file
        conn = sqlite(dbfile, 'readonly');
        
        % Fetch the most recent row from the sensor_data table
        query = 'SELECT moisture1, moisture2, moisture3, moisture4 FROM sensor_data ORDER BY timestamp DESC LIMIT 1';
        data = fetch(conn, query);
        
        close(conn); % Close connection immediately after fetching
        
        if ~isempty(data)
            % --- B. Assign Sensor Data to Corners ---
            Sensor_TopLeft = data.moisture1;     % moisture1 is top-left
            Sensor_TopRight = data.moisture2;    % moisture2 is top-right
            Sensor_BottomLeft = data.moisture3;  % moisture3 is bottom-left
            Sensor_BottomRight = data.moisture4; % moisture4 is bottom-right
            
            fprintf('Fetched new data: TL=%.1f, TR=%.1f, BL=%.1f, BR=%.1f\n', ...
                Sensor_TopLeft, Sensor_TopRight, Sensor_BottomLeft, Sensor_BottomRight);

            % --- C. Run the Simulation with Live Data ---
            Grid = 50 * ones(Nx, Ny); % Re-initialize grid

            % Apply live boundary conditions
            Grid(1, :) = linspace(Sensor_TopLeft, Sensor_TopRight, Ny);
            Grid(end, :) = linspace(Sensor_BottomLeft, Sensor_BottomRight, Ny);
            Grid(:, 1) = linspace(Sensor_TopLeft, Sensor_BottomLeft, Nx);
            Grid(:, end) = linspace(Sensor_TopRight, Sensor_BottomRight, Nx);

            % Iteratively solve the Laplace equation
            for k = 1:max_iter
                Grid_Old = Grid;
                Grid(2:end-1, 2:end-1) = 0.25 * (Grid_Old(1:end-2, 2:end-1) + Grid_Old(3:end, 2:end-1) + ...
                                                Grid_Old(2:end-1, 1:end-2) + Grid_Old(2:end-1, 3:end));
                if max(max(abs(Grid - Grid_Old))) < tolerance
                    break;
                end
            end
            
            % --- D. Update the Plot ---
            s.ZData = Grid; % Update the Z-data of the surface plot
            drawnow; % Refresh the figure window
            
        else
            fprintf('Database is empty or no data found. Waiting...\n');
        end
        
    catch ME
        fprintf('An error occurred: %s\n', ME.message);
        fprintf('Will try again in %d seconds...\n', refresh_rate_sec);
    end
    
    % Pause before the next update
    pause(refresh_rate_sec);
end

fprintf('Figure window closed. Shutting down digital twin.\n');