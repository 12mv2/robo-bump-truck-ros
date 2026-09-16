from setuptools import setup

package_name = 'truck_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Rooney Industries LLC',
    maintainer_email='12mv2@users.noreply.github.com',
    description='Outputs-disabled ROSie command policy and diagnostics.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={'console_scripts': ['shadow = truck_bridge.node:main']},
)
