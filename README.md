# Amplifier Bundle Evaluation

A one-stop-shop for evaluating AI agents, bundles, and recipes across the Amplifier ecosystem. Provides an `evaluation` mode and supporting context for running structured evaluations for a broad range of evaluation use cases.

Example Uses:

- "I have changes to an Amplifier bundle I would like to evaluate the impact of. Can you help me measure it?"
- "I have a custom agent that does Y"
- "I built a memory system and want to know if it improves my agent"


## Installation

### Prerequisites

- An existing Amplifier installation
- A bundle that provides a runtime (e.g. `amplifier-foundation`) composed in the same session
- `amplifier-bundle-modes` composed in the same session, since the evaluation mode is delivered through that capability

### Amplifier Bundle

To compose it onto an existing setup:

```bash
amplifier bundle add "git+https://github.com/microsoft/amplifier-bundle-evaluation@main#subdirectory=behaviors/evaluation.yaml" --app
```

`--app` composes the bundle onto every Amplifier session. Remove it to only register the bundle for later activation with `amplifier bundle use`.

If you also need the modes capability (required for the `evaluation` mode to be discoverable):

```bash
amplifier bundle add "git+https://github.com/microsoft/amplifier-bundle-modes@main#subdirectory=behaviors/modes.yaml" --app
```

## Contributing

> [!NOTE]
> This project is not currently accepting external contributions, but we're actively working toward opening this up. We value community input and look forward to collaborating in the future. For now, feel free to fork and experiment!

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit [Contributor License Agreements](https://cla.opensource.microsoft.com).

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
