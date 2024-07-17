def preprocessing_filter_spec(endpoints):
    filtered = []
    blacklist = ['/api_auth/']
    for (path, path_regex, method, callback) in endpoints:
        # Remove all but DRF API endpoints

        if all(not path.startswith(b) for b in blacklist):
            print(f'Path: {path}, path_regex: {path_regex}, method: {method}, callback: {callback}')
            filtered.append((path, path_regex, method, callback))
    return filtered
