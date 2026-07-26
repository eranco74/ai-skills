SKILLSAW_VERSION := 0.17.0

.PHONY: help skillsaw

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

skillsaw: ## Lint all skills (or one: SKILL=skills/prd-creator/)
	uvx --from skillsaw==$(SKILLSAW_VERSION) skillsaw lint $(SKILL) --strict --no-baseline
