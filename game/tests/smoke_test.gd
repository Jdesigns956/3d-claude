extends SceneTree
## Headless gameplay smoke test. Run via scripts/check.sh, or directly:
##   godot --headless --path game -s res://tests/smoke_test.gd
## Prints one PASS/FAIL line per check and exits 1 if anything failed.
## Every new mechanic should add a check here; the Stop hook blocks "done" while this fails.

const MAIN_SCENE := "res://scenes/main.tscn"
const SCENES_DIR := "res://scenes"

var _failed := 0


func _initialize() -> void:
	_run.call_deferred()


func _run() -> void:
	_check_all_scenes_load()

	var main := (load(MAIN_SCENE) as PackedScene).instantiate()
	root.add_child(main)
	await _physics_frames(30)

	var player := main.get_node_or_null("Player") as CharacterBody3D
	_check(player != null, "main scene has a Player")
	if player:
		_check(player.is_on_floor(), "player lands on the ground")

		var start := player.global_position
		Input.action_press("move_forward")
		await _physics_frames(60)
		Input.action_release("move_forward")
		_check(player.global_position.distance_to(start) > 1.0, "player moves with move_forward")

		await _physics_frames(20)
		Input.action_press("jump")
		await _physics_frames(1)
		Input.action_release("jump")
		await _physics_frames(10)
		_check(not player.is_on_floor(), "player leaves the ground on jump")

	main.queue_free()
	await process_frame
	print("SMOKE %s (%d failed)" % ["FAIL" if _failed else "PASS", _failed])
	quit(1 if _failed else 0)


func _check_all_scenes_load() -> void:
	for file in DirAccess.get_files_at(SCENES_DIR):
		if not file.ends_with(".tscn"):
			continue
		var path := SCENES_DIR.path_join(file)
		var packed := load(path) as PackedScene
		var ok := packed != null and packed.can_instantiate()
		if ok:
			var node := packed.instantiate()
			ok = node != null
			if node:
				node.free()
		_check(ok, "scene loads: " + path)


func _check(condition: bool, label: String) -> void:
	if condition:
		print("PASS  " + label)
	else:
		_failed += 1
		printerr("FAIL  " + label)


func _physics_frames(count: int) -> void:
	for i in count:
		await physics_frame
