import math
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Iterator, Dict, Any, Set, Optional, List
import re

from util.exceptions import ApplicationWorkflowParsingError


@dataclass
class RequirementsYieldsCatalogEntry:
    requirements: Optional[Set[str]] = field(default_factory=set)
    yields: Optional[Set[str]] = field(default_factory=set)


class SchemaNativeWorkflowParser:
    METAVARIABLE_NAMING_PATTERN = r'[a-zA-Z][a-zA-Z0-9_]+'
    METAVARIABLE_MARKER_PATTERN = r'\$\$'

    @classmethod
    def parse_metavariable_context(cls, definition: str) -> Iterator[re.Match[str]]:
        metavariable_detection_pattern = \
            rf'({cls.METAVARIABLE_MARKER_PATTERN})({cls.METAVARIABLE_NAMING_PATTERN})'

        return re.finditer(metavariable_detection_pattern, definition)

    @classmethod
    def get_referenced_metavariables(cls, definition: str) -> Set[str]:
        return {m.group(2) for m in cls.parse_metavariable_context(definition)}

    @classmethod
    def substitute_metavariables(cls, definition: str, metavariable_context: Dict[str, Any]) -> str:
        substituted_definition = ''
        latest_match_end_idx = 0
        for match in cls.parse_metavariable_context(definition):
            metavariable = match.group(2)

            # TODO: examine whether check may be dropped in the future so that undefined metavariables just keep
            #       their literal - potentially order resolution algorithm needs to take this into account as well
            if metavariable not in metavariable_context:
                # raise ValueError('Metavariable {} not defined in context'.format(metavariable))
                continue

            substituted_definition += definition[latest_match_end_idx:match.start()] + str(
                metavariable_context[metavariable])
            latest_match_end_idx = match.end()
        substituted_definition += definition[latest_match_end_idx:]
        return substituted_definition

    @classmethod
    def infer_workflow_inputs(cls, ray_catalog: List[RequirementsYieldsCatalogEntry]) -> Set[str]:
        all_requirements = set.union(*(e.requirements for e in ray_catalog))
        all_yields = set.union(*(e.yields for e in ray_catalog))
        return all_requirements - all_yields

    @classmethod
    def get_requirements_and_yields(cls, workflow_definition: Dict[str, Any]) -> List[RequirementsYieldsCatalogEntry]:
        declared_yields = set()

        ray_catalog = list()
        executors = workflow_definition['executors']

        for executor in executors:
            command = ' '.join(executor['command'])

            references = cls.get_referenced_metavariables(command)

            requirements = cls.get_referenced_metavariables(executor.get('stdin', ''))

            expected_yields = cls.get_referenced_metavariables(executor.get('stdout', '')).union(
                cls.get_referenced_metavariables(executor.get('stderr', ''))
            )

            yields = set()

            executor_yields = executor.get('yields', [])
            for y in executor_yields:
                yield_name = y['name']
                if yield_name in declared_yields:
                    raise ApplicationWorkflowParsingError('Yield name is already declared')
                declared_yields.add(yield_name)

                yields.add(yield_name)

            # Anything referenced in the command but not found as a yield, assume it is a requirement
            requirements = requirements.union(references.difference(yields))

            # Ensure that final requirements and final yields do not share a reference
            # This may happen if a yield metavariable is referenced in `stdin` field
            common_references = requirements.intersection(yields)
            if len(common_references) > 0:
                raise ApplicationWorkflowParsingError(
                    f'Reference {common_references.pop()} is used as both a requirement and a yield'
                )

            # Ensure that all expected yield references defined within output related-fields, stdout and stderr are
            # declared as executor yields
            missing_yields = expected_yields.difference(yields)
            if len(missing_yields) > 0:
                raise ApplicationWorkflowParsingError(
                    f'Yield {missing_yields.pop()} is referenced but not declared in executor yields'
                )

            ray_catalog.append(RequirementsYieldsCatalogEntry(requirements=requirements, yields=yields))

        # Map pseudo-executor for inputs
        expected_inputs = cls.infer_workflow_inputs(ray_catalog)
        declared_inputs = set(i['name'] for i in workflow_definition.get('inputs', []))
        missing_inputs = expected_inputs - declared_inputs
        if len(missing_inputs) > 0:
            raise ApplicationWorkflowParsingError(
                f'Workflow executors expect {missing_inputs.pop()} as an input but no such input is declared'
            )
        ray_catalog.insert(0, RequirementsYieldsCatalogEntry(requirements=set(), yields=expected_inputs))

        # Map pseudo-executor for outputs
        all_workflow_yields = set.union(*(e.yields for e in ray_catalog))
        output_pseudo_requirements = set()
        for output in workflow_definition.get('outputs', []):
            if output['name'] not in all_workflow_yields:
                raise ApplicationWorkflowParsingError(
                    f'Referenced output {output["name"]} does not exist within the workflow context'
                )
            output_pseudo_requirements.add(output['name'])
        ray_catalog.append(RequirementsYieldsCatalogEntry(requirements=output_pseudo_requirements, yields=set()))

        return ray_catalog

    @classmethod
    def calculate_execution_layers(cls, ray: List[RequirementsYieldsCatalogEntry]) -> List[Set[int]]:
        mutable_ray = deepcopy(ray)
        inputs_layer = mutable_ray.pop(0)
        satisfied_requirements = set(inputs_layer.yields)

        outputs_layer = mutable_ray.pop(-1)
        expected_yields = set(outputs_layer.requirements)

        layers = []
        executors_scheduled = 0
        executors_exhausted = len(ray) == 0

        while not executors_exhausted:

            # Get indices of executors that can be run at this stage, because their requirements are satisfied
            layer_executors = set()
            layer_yields = set()

            ex_idx = 0
            for executor in mutable_ray:
                if executor and len(executor.requirements.difference(satisfied_requirements)) == 0:
                    layer_executors.add(ex_idx)
                    layer_yields = layer_yields.union(executor.yields)
                ex_idx += 1

            # Check for inability of selecting layer executors
            if len(layer_executors) == 0:
                raise ApplicationWorkflowParsingError(
                    f'Can\'t schedule any of the remaining executors since their requirements are not satisfied '
                    f'(potential circular dependency)'
                )

            layers.append(layer_executors)

            satisfied_requirements = satisfied_requirements.union(layer_yields)

            for ex_idx in layer_executors:
                mutable_ray[ex_idx] = None
                executors_scheduled += 1
            executors_exhausted = executors_scheduled == len(mutable_ray)

        if len(expected_yields.difference(satisfied_requirements)) > 0:
            raise ApplicationWorkflowParsingError(
                f'Not all expected outputs are yielded by the defined executors'
            )

        return layers

    @classmethod
    def validate(cls, workflow_definition: Dict[str, Any]) -> List[Set[int]]:
        requirements_yields_matrix = cls.get_requirements_and_yields(workflow_definition)
        return cls.calculate_execution_layers(requirements_yields_matrix)

    @classmethod
    def resolve(cls,
                workflow_definition: Dict[str, Any],
                layers: List[Set[int]],
                scoring_function=lambda ex: ex.get('priority', -math.inf)) -> List[int]:
        flattened_execution_order = list()
        for layer in layers:
            if len(layer) > 1:
                executor_scores = dict()
                for executor_idx in layer:
                    score = scoring_function(workflow_definition['executors'][executor_idx])
                    executor_scores[executor_idx] = score
                layer_flat_execution_order = sorted(
                    executor_scores.keys(), key=lambda k: executor_scores[k], reverse=True
                )
                flattened_execution_order += layer_flat_execution_order
            else:
                flattened_execution_order.append(layer.pop())
        return flattened_execution_order

    @classmethod
    def validate_order(cls, workflow_definition: Dict[str, Any], order: List[int]):
        requirements_yields_matrix = cls.get_requirements_and_yields(workflow_definition)

        satisfied_requirements = set(requirements_yields_matrix.pop(0).yields)

        expected_yields = set(requirements_yields_matrix.pop(-1).requirements)

        for executor_idx in order:
            try:
                executor_ray = requirements_yields_matrix[executor_idx]
            except IndexError:
                raise ApplicationWorkflowParsingError(
                    f'Provided workflow execution order references an invalid executor index')
            executor_requirements = set(executor_ray.requirements)
            unmet_dependencies = executor_requirements.difference(satisfied_requirements)
            if len(unmet_dependencies) == 0:
                satisfied_requirements = satisfied_requirements.union(executor_ray.yields)
            else:
                raise ApplicationWorkflowParsingError(
                    f'Provided workflow execution order is invalid. Executor with index {executor_idx} requires '
                    f'transient file named "{unmet_dependencies.pop()}", but no such file is set to be persisted by '
                    f'previous executors')

        unmet_dependencies = expected_yields.difference(satisfied_requirements)
        if len(unmet_dependencies) > 0:
            raise ApplicationWorkflowParsingError(
                f'Provided workflow execution order is invalid. Workflow output layer requires transient file named '
                f'"{unmet_dependencies.pop()}", but no such file is set to be persisted by the defined executors')
