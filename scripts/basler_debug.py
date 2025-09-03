from pypylon import pylon

factory = pylon.TlFactory.GetInstance()
tls = factory.EnumerateTls()

print("Available Transport Layers:")
for tl in tls:
    print(f"- {tl.GetFullName()} ")
