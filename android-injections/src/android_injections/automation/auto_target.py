"""Auto-target selection based on game state (higher_plane and minimap_counter)."""
from .performance_logger import log_operation


@log_operation("get_current_auto_target")
def get_current_auto_target(instance):
    """
    Determine current target based on higher_plane and minimap_counter state values.
    
    The game has multiple climbing sequences that cycle through targets based on:
    - higher_plane: Boolean indicating whether player is on a raised platform (1) or ground level (0)
    - minimap_counter: Counter indicating position within the raised platform sequence
    
    Target mapping:
    - higher_plane=0: 'ladder' (ground level)
    - higher_plane=1, counter=4: 'tightrope'
    - higher_plane=1, counter=3: 'tightrope2'
    - higher_plane=1, counter=2: 'rope'
    - higher_plane=1, counter=1: 'ladder2'
    - higher_plane=1, counter=0: 'zipline'
    
    Args:
        instance: Instance with state_tracking, higher_plane, and minimap_counter attributes
    
    Returns:
        Target name string or None if unable to determine target
    """
    if not instance.state_tracking:
        return None
        
    if instance.higher_plane == 0:
        return "ladder"
    elif instance.higher_plane == 1:
        if instance.minimap_counter == 4:
            return "zipline"
        elif instance.minimap_counter == 3:
            return "tightrope2"
        elif instance.minimap_counter == 2:
            return "rope"
        elif instance.minimap_counter == 1:
            return "ladder2"
        elif instance.minimap_counter == 0:
            return "tightrope"
    
    return None
