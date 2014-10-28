#!/usr/bin/env python

import flask
import mir_eval
import json

# construct application object
app = flask.Flask(__name__)
# Max file size = 100 kilobytes
app.config['MAX_CONTENT_LENGTH'] = 100*1024

TASKS = {'beat': mir_eval.beat,
         'chord': mir_eval.chord,
         'melody': mir_eval.melody,
         'onset': mir_eval.onset,
         'pattern': mir_eval.pattern,
         'segment': mir_eval.segment}


def load_annotation_file(task, file):
    if task == mir_eval.beat or task == mir_eval.onset:
        return mir_eval.io.load_events(file)
    elif task == mir_eval.chord or task == mir_eval.segment:
        return mir_eval.io.load_labeled_intervals(file)
    elif task == mir_eval.melody:
        return mir_eval.io.load_time_series(file)
    elif task == mir_eval.pattern:
        return mir_eval.io.load_patterns(file)
    else:
        raise ValueError('Task not recognized.')


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if flask.request.method == 'POST':
        try:
            task = TASKS[flask.request.form['task']]
        except KeyError:
            return 'ERROR: Task not recognized, should be one of {}'.format(
                ', '.join(key for key in TASKS.keys()))

        reference_file = flask.request.files['reference_file']
        if not reference_file:
            return 'ERROR: Did not receive a reference annotation file.'
        try:
            reference_data = load_annotation_file(task, reference_file)
        except Exception as e:
            return 'ERROR when parsing reference file: {}'.format(e.message)

        estimated_file = flask.request.files['estimated_file']
        if not estimated_file:
            return 'ERROR: Did not receive a estimated annotation file.'
        try:
            estimated_data = load_annotation_file(task, estimated_file)
        except Exception as e:
            return 'ERROR when parsing estimated file: {}'.format(e.message)

        try:
            if task == mir_eval.beat or task == mir_eval.onset or \
               task == mir_eval.pattern:
                results = task.evaluate(reference_data, estimated_data)
            elif (task == mir_eval.melody or task == mir_eval.chord or
                  task == mir_eval.segment):
                results = task.evaluate(reference_data[0], reference_data[1],
                                        estimated_data[0], estimated_data[1])
        except Exception as e:
            return 'ERROR when computing metrics: {}'.format(e.message)

        return json.dumps(results)

    return '''
    <!doctype html>
    <title>mir_eval</title>
    <form action="" method="post" enctype="multipart/form-data">
        <h1>Reference file</h1>
            <p><input type="file" name="reference_file"></p>
        <h1>Estimated file</h1>
            <p><input type="file" name="estimated_file"></p>
        <h1>Task</h1>
            <select name="task">
                <option value="beat">Beat detection</option>
                <option value="chord">Chord recognition</option>
                <option value="melody">Melody estimation</option>
                <option value="onset">Onset detection</option>
                <option value="pattern">Pattern recognition</option>
                <option value="segment">Strucural segmentation</option>
            </select>
        <p><input type="submit" value="Get results JSON"></p>
    </form>
    '''

if __name__ == "__main__":
    app.run()
