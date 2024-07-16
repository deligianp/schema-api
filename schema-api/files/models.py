from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional, TypeVar, Type


@dataclass
class GenericMetadata:
    size: Optional[int] = field(default=None)
    ts_created: Optional[datetime] = field(default=None)
    ts_modified: Optional[datetime] = field(default=None)


@dataclass
class FileMetadata(GenericMetadata):
    pass


@dataclass
class DirectoryMetadata(GenericMetadata):
    pass


@dataclass(kw_only=True)
class FilesystemEntity:
    name: str
    parent: Optional['Directory'] = field(default=None, init=False)
    metadata: GenericMetadata = field(default_factory=GenericMetadata)

    @property
    def path(self) -> Path:
        return Path(self.parent.path if self.parent is not None else '').joinpath(Path(self.name))


FSE = TypeVar('FSE', bound=FilesystemEntity)


@dataclass(kw_only=True)
class File(FilesystemEntity):
    metadata: FileMetadata = field(default_factory=FileMetadata)


@dataclass(kw_only=True)
class Directory(FilesystemEntity):
    name: str = field(default='.')
    metadata: DirectoryMetadata = field(default_factory=DirectoryMetadata)
    children: Dict[str, FilesystemEntity] = field(default_factory=dict, init=False)

    @property
    def contents(self) -> Iterable[FilesystemEntity]:
        return self.children.values()

    def walk(self) -> Iterable['File']:
        files = list()
        for i in self.children.values():
            if issubclass(i.__class__, Directory):
                i: Directory
                files.extend(i.walk())
            elif issubclass(i.__class__, File):
                i: File
                files.append(i)
        return sorted(files, key=lambda f: f.path)

    def add_child(self, fs_entity: FSE, subpath='') -> FSE:
        evaluated_path = Path('/').joinpath(Path(subpath)).resolve()
        if len(evaluated_path.parts) > 1:
            subdir = evaluated_path.parts[1]
            self.children.setdefault(subdir, Directory(name=subdir))
            evaluated_subpath = Path(*evaluated_path.parts[2:])
            try:
                self.children[subdir].add_child(fs_entity, subpath=evaluated_subpath)
                self.children[subdir].parent = self
            except AttributeError as ae:
                raise AttributeError(f'Cannot add a child in `{self.path}` because it is not a directory') from ae
        else:
            self.children[fs_entity.name] = fs_entity
            fs_entity.parent = self
        return fs_entity

    def create_entity_on_path(self, entity_class: Type[FSE], path: str, **entity_data) -> FSE:
        if 'name' not in entity_data:
            entity_data['name'] = Path(path).name
            path = Path(path).parents[0]
        return self.add_child(entity_class(**entity_data), subpath=path)

    def get_file_system_entity(self, path: str) -> FilesystemEntity:
        evaluated_path = Path('/').joinpath(Path(path)).resolve()
        if len(evaluated_path.parts) > 2:
            try:
                return self.children[evaluated_path.parts[1]].get_file_system_entity(Path(*evaluated_path.parts[2:]))
            except (AttributeError, KeyError) as err:
                raise KeyError(f'File `{Path(*evaluated_path.parts[1:])}` does not exist') from err
        return self.children[evaluated_path.parts[1]]

    def get_accumulative_size(self) -> int:
        size = self.metadata.size or 0
        for c in self.contents:
            if issubclass(c.__class__, Directory):
                c: Directory
                size += c.get_accumulative_size()
            else:
                c: File
                size += c.metadata.size or 0
        return size
