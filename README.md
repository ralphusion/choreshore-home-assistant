# ChoreShore Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/ralphusion/choreshore-home-assistant.svg)](https://github.com/ralphusion/choreshore-home-assistant/releases)
[![License](https://img.shields.io/github/license/ralphusion/choreshore-home-assistant.svg)](LICENSE)

This custom integration brings ChoreShore household chore management into Home Assistant, allowing you to manage tasks, view analytics, and create automations within your smart home ecosystem.

## Features

### Core Functionality
- **Task Management**: View, complete, and skip tasks directly from Home Assistant
- **Real-time Updates**: Automatic synchronization with your ChoreShore household
- **Member Performance**: Track individual household member statistics
- **Analytics Dashboard**: Completion rates, streaks, and performance metrics
- **Smart Automations**: Trigger automations based on task status and completion
- **Secure Access**: Uses service-level authentication for reliable data access

### Entities Created
- **Sensors**: Total tasks, completed tasks, overdue tasks, completion rate, member performance
- **Binary Sensors**: Individual task status, household overdue/pending indicators
- **Switches**: One-click task completion controls

### Services Available
- `choreshore.complete_task`: Mark a task as completed
- `choreshore.skip_task`: Skip a task with optional reason
- `choreshore.refresh_data`: Force refresh of data from ChoreShore

## Installation

### Prerequisites
1. A ChoreShore account with an active household
2. Your ChoreShore Household ID and User ID (available in your ChoreShore profile under "Developer & Integration Info")
3. Home Assistant with HACS installed

### HACS Installation (Recommended)
1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/ralphusion/choreshore-home-assistant`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "ChoreShore" in HACS
8. Click "Download"
9. Restart Home Assistant
10. Go to Settings > Devices & Services > Add Integration
11. Search for "ChoreShore" and follow the configuration steps

### Manual Installation
1. Download the latest release from the [releases page](https://github.com/ralphusion/choreshore-home-assistant/releases)
2. Extract the files and copy the `custom_components/choreshore` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant
4. Go to Settings > Devices & Services > Add Integration
5. Search for "ChoreShore" and follow the configuration steps

## Configuration

### Setup Through UI (Recommended)
1. Go to Settings > Devices & Services in Home Assistant
2. Click "Add Integration"
3. Search for "ChoreShore"
4. Enter your Household ID and User ID when prompted
5. Optionally configure the update interval (default: 300 seconds)

### Legacy YAML Configuration
If you prefer YAML configuration, add the following to your `configuration.yaml`:

```yaml
choreshore:
  household_id: "your_household_id"
  user_id: "your_user_id" 
  update_interval: 300  # Optional: Update interval in seconds (default: 300)
```

### Finding Your IDs
1. Log into your ChoreShore account
2. Go to your Profile page
3. Scroll down to the "Developer & Integration Info" section
4. Copy your User ID and Household ID from there

## Authentication & Security

The integration uses secure service-level authentication to access your ChoreShore data:

- **Secure Access**: Uses service role authentication for reliable data retrieval
- **Data Isolation**: Only your household's data is accessible based on your Household ID
- **No Personal Credentials**: No need to store your personal login credentials in Home Assistant
- **Automatic Updates**: Data refreshes automatically every 5 minutes (configurable)

## Repository Structure

```
custom_components/choreshore/
├── __init__.py              # Integration setup and services
├── config_flow.py           # Configuration flow for UI setup
├── const.py                 # Constants and configuration
├── coordinator.py           # Data update coordinator
├── manifest.json            # Integration manifest
├── sensor.py               # Sensor entities
├── binary_sensor.py        # Binary sensor entities
├── switch.py               # Switch entities
├── services.yaml           # Service definitions
└── translations/
    └── en.json             # English translations
```

## Available Entities

### Sensors
- `sensor.choreshore_total_tasks`: Total number of active tasks
- `sensor.choreshore_completed_tasks`: Number of completed tasks today
- `sensor.choreshore_overdue_tasks`: Number of overdue tasks
- `sensor.choreshore_pending_tasks`: Number of pending tasks
- `sensor.choreshore_completion_rate`: Overall completion rate percentage
- `sensor.choreshore_[member_name]_tasks`: Individual member task counts

### Binary Sensors
- `binary_sensor.choreshore_has_overdue_tasks`: True if any tasks are overdue
- `binary_sensor.choreshore_has_pending_tasks`: True if any tasks are pending
- `binary_sensor.choreshore_[task_name]`: Individual task status sensors

### Switches
- `switch.choreshore_[task_name]_complete`: Toggle switches for task completion

## Services

### Complete Task
```yaml
service: choreshore.complete_task
data:
  task_id: "your_task_id"
```

### Skip Task
```yaml
service: choreshore.skip_task
data:
  task_id: "your_task_id"
  reason: "Optional reason for skipping"
```

### Refresh Data
```yaml
service: choreshore.refresh_data
```

## Automation Examples

### Morning Task Reminder
```yaml
automation:
  - alias: "Morning Chore Reminder"
    trigger:
      platform: time
      at: "08:00:00"
    condition:
      condition: template
      value_template: "{{ states('sensor.choreshore_pending_tasks') | int > 0 }}"
    action:
      service: notify.mobile_app_your_phone
      data:
        title: "Good Morning!"
        message: "You have {{ states('sensor.choreshore_pending_tasks') }} tasks for today"
```

### Overdue Task Alert
```yaml
automation:
  - alias: "Overdue Task Alert"
    trigger:
      platform: state
      entity_id: binary_sensor.choreshore_has_overdue_tasks
      to: 'on'
    action:
      service: notify.mobile_app_your_phone
      data:
        title: "⚠️ Overdue Tasks"
        message: "You have {{ states('sensor.choreshore_overdue_tasks') }} overdue tasks!"
        data:
          color: red
```

### Task Completion Celebration
```yaml
automation:
  - alias: "Task Completion Celebration"
    trigger:
      platform: state
      entity_id: sensor.choreshore_completion_rate
    condition:
      condition: template
      value_template: "{{ trigger.to_state.state | float >= 100 }}"
    action:
      - service: light.turn_on
        entity_id: light.living_room
        data:
          color_name: green
          brightness: 255
      - service: tts.google_translate_say
        entity_id: media_player.home
        data:
          message: "Congratulations! All tasks are completed!"
```

## Troubleshooting

### Common Issues

1. **Integration Not Loading**: 
   - Verify files are in the correct `custom_components/choreshore/` directory
   - Check Home Assistant logs for error messages
   - Ensure configuration is correct
   - For HACS users: Try redownloading the integration

2. **No Entities Created**: 
   - Verify your Household ID and User ID are correct
   - Check that your household has active tasks and members
   - Look for error messages in Home Assistant logs
   - Use the `choreshore.refresh_data` service to manually refresh

3. **Data Not Updating**: 
   - Use the `choreshore.refresh_data` service to manually refresh
   - Check network connectivity to ChoreShore servers
   - Verify your Household and User IDs are still valid
   - Check the update interval setting

4. **Authentication Errors**:
   - Double-check your User ID and Household ID in ChoreShore profile
   - Ensure you're a member of the specified household
   - Try reconfiguring the integration through the UI
   - The integration now uses service-level authentication, so personal login issues shouldn't affect it

5. **HACS Installation Issues**:
   - Ensure HACS is properly installed and up to date
   - Check that the repository URL is correct
   - Verify the repository is added as an "Integration" type
   - Restart Home Assistant after HACS installation

### Debug Logging
Add this to your `configuration.yaml` to enable debug logging:
```yaml
logger:
  default: warning
  logs:
    custom_components.choreshore: debug
```

### Getting Help
- Check the [GitHub Issues](https://github.com/ralphusion/choreshore-home-assistant/issues) for known problems
- Review Home Assistant logs for specific error messages
- Verify your ChoreShore account is active and accessible
- Ensure your User ID and Household ID are copied correctly from your profile

## Security & Privacy

- All communication uses HTTPS encryption
- Service-level authentication ensures reliable access without storing personal credentials
- Data is cached locally to minimize external API calls
- The integration respects ChoreShore's role-based access control
- Only necessary data is synchronized based on your household access level
- Data access is strictly limited to your configured household

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
1. Clone the repository
2. Set up a Home Assistant development environment
3. Link the integration to your development environment
4. Test with a real ChoreShore household

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/ralphusion/choreshore-home-assistant/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ralphusion/choreshore-home-assistant/discussions)
- **ChoreShore Support**: Check your ChoreShore profile page for additional integration documentation

## Roadmap

- [ ] Enhanced dashboard cards
- [ ] Voice assistant integration improvements
- [ ] Additional automation examples
- [ ] Performance optimizations
- [ ] Advanced analytics and reporting features

---

For the most up-to-date documentation and ChoreShore-specific configuration details, visit your ChoreShore profile page and check the "Developer & Integration Info" section.
