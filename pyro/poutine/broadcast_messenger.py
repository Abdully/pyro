from __future__ import absolute_import, division, print_function

from .messenger import Messenger


class BroadcastMessenger(Messenger):
    """
    `BroadcastMessenger` automatically broadcasts the batch shape of
    the stochastic function at a sample site when inside a single
    or nested iarange context. The existing `batch_shape` must be
    broadcastable with the size of the :class:`~pyro.iarange`
    contexts installed in the `cond_indep_stack`.
    """
    @staticmethod
    def _pyro_sample(msg):
        """
        :param msg: current message at a trace site.
        """
        if msg["done"] or msg["type"] != "sample":
            return

        dist = msg["fn"]
        actual_batch_shape = getattr(dist, "batch_shape", None)
        if actual_batch_shape is not None:
            target_batch_shape = [None if size == 1 else size for size in actual_batch_shape]
            for f in msg["cond_indep_stack"]:
                if f.dim is None or f.size == -1:
                    continue
                assert f.dim < 0
                target_batch_shape = [None] * (-f.dim - len(target_batch_shape)) + target_batch_shape
                if target_batch_shape[f.dim] not in (None, f.size):
                    raise ValueError("Shape mismatch inside iarange('{}') at site {} dim {}, {} vs {}".format(
                        f.name, msg['name'], f.dim, f.size, target_batch_shape[f.dim]))
                target_batch_shape[f.dim] = f.size
            # Starting from the right, if expected size is None at an index,
            # set it to the actual size if it exists, else 1.
            for i in range(-len(target_batch_shape) + 1, 1):
                if target_batch_shape[i] is None:
                    target_batch_shape[i] = actual_batch_shape[i] if len(actual_batch_shape) >= -i else 1
            msg["fn"] = msg["fn"].expand(target_batch_shape)
