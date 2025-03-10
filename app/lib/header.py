from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem


def generate_user_agent():
    software_names = [
        SoftwareName.CHROME.value,
        SoftwareName.ANDROID.value,
        SoftwareName.SAFARI.value,
        SoftwareName.FIREFOX.value,
        SoftwareName.EDGE.value,
    ]
    operating_systems = [
        OperatingSystem.IOS.value,
        OperatingSystem.ANDROID.value,
    ]

    user_agent_rotator = UserAgent(
        software_names=software_names, operating_systems=operating_systems, limit=100
    )

    user_agent = user_agent_rotator.get_random_user_agent()
    return user_agent


def generate_desktop_user_agent():
    software_names = [
        SoftwareName.CHROME.value,
        SoftwareName.SAFARI.value,
        SoftwareName.FIREFOX.value,
        SoftwareName.EDGE.value,
    ]
    operating_systems = [
        OperatingSystem.WINDOWS.value,
        OperatingSystem.MACOS.value,
    ]

    user_agent_rotator = UserAgent(
        software_names=software_names, operating_systems=operating_systems, limit=100
    )

    user_agent = user_agent_rotator.get_random_user_agent()
    return user_agent
