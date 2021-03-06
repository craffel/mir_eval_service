#!/usr/bin/env python

import flask
import mir_eval
import json
import numpy as np

# construct application object
app = flask.Flask(__name__)
# Max file size = 100 kilobytes
app.config['MAX_CONTENT_LENGTH'] = 100*1024

TASKS = {'beat': mir_eval.beat,
         'chord': mir_eval.chord,
         'melody': mir_eval.melody,
         'onset': mir_eval.onset,
         'pattern': mir_eval.pattern,
         'segment': mir_eval.segment,
         'tempo': mir_eval.tempo,
         'transcription': mir_eval.transcription,
         'key': mir_eval.key}


def load_annotation_file(task, file):
    if task == mir_eval.beat or task == mir_eval.onset:
        return mir_eval.io.load_events(file)
    elif task == mir_eval.chord or task == mir_eval.segment:
        return mir_eval.io.load_labeled_intervals(file)
    elif task == mir_eval.melody:
        return mir_eval.io.load_time_series(file)
    elif task == mir_eval.pattern:
        return mir_eval.io.load_patterns(file)
    elif task == mir_eval.tempo:
        return mir_eval.io.load_delimited(file, [float, float, float])
    elif task == mir_eval.transcription:
        return mir_eval.io.load_valued_intervals(file)
    elif task == mir_eval.key:
        return mir_eval.io.load_key(file)
    else:
        raise ValueError('Task not recognized.')


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if flask.request.method == 'POST':
        try:
            task = TASKS[flask.request.form['task']]
        except KeyError:
            return 'ERROR: Task {} not recognized, should be one of {}'.format(
                flask.request.form['task'],
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
               task == mir_eval.pattern or task == mir_eval.key:
                results = task.evaluate(reference_data, estimated_data)
            elif (task == mir_eval.melody or task == mir_eval.chord or
                  task == mir_eval.segment or task == mir_eval.transcription):
                results = task.evaluate(reference_data[0], reference_data[1],
                                        estimated_data[0], estimated_data[1])
            elif task == mir_eval.tempo:
                # load_delimited will return a list of lists
                # [[tempo_1, tempo_2, tempo_weight]]
                # So, we need to extract the parameters
                reference_tempi = np.array([reference_data[0][0],
                                            reference_data[1][0]])
                reference_weight = reference_data[2][0]
                estimated_tempi = np.array([estimated_data[0][0],
                                            estimated_data[1][0]])
                results = task.evaluate(
                    reference_tempi, reference_weight, estimated_tempi)
        except Exception as e:
            return 'ERROR when computing metrics: {}'.format(e.message)

        return flask.Response(json.dumps(results),
                              mimetype='application/json')

    return '''
    <!doctype html>
    <html>
        <head>
            <title>mir_eval</title>
        </head>
        <body style="font-family:sans-serif">
            <div style="padding: 10px">
                <b><h1>mir_eval</h1></b>
                <i>Note: This web service is running an out-of-date version of mir_eval and should be treated only as a proof-of-concept.</i><br /><br />
                Use the form below to evaluate annotations for a given MIR task.<br />
                The file format should be as described in <a href="http://craffel.github.io/mir_eval/#module-mir_eval.io">mir_eval</a>'s documentation.<br />
                Some example annotation files can be found in within <a href="https://github.com/craffel/mir_eval/tree/master/tests/data">mir_eval's tests</a>.<br />
                You can also query this web service as an API, e.g.:<br />
                <pre style="padding-left: 20px; font-size: 90%">curl -F "task=beat" -F "estimated_file=@est.txt" -F "reference_file=@ref.txt" http://labrosa.ee.columbia.edu/mir_eval/</pre>
                task should be one of beat, chord, melody, onset, pattern, segment, tempo, key, or transcription.<br />
                If you're running a large-scale evaluation, it will probably be more efficient to run mir_eval locally.<br />
                Installation instructions for mir_eval can be found <a href="http://craffel.github.io/mir_eval/#installing-mir-eval">here</a>.<br />
                You can even run mir_eval with minimal Python knowledge by using the <a href="https://github.com/craffel/mir_evaluators">evaluators</a>.<br />
                If you use mir_eval in a research project, please cite the following paper:<br />
                <p style="padding-left: 20px">
                    Colin Raffel, Brian McFee, Eric J. Humphrey, Justin Salamon, Oriol Nieto, Dawen Liang, and Daniel P. W. Ellis.<br />
                    <a href="http://colinraffel.com/publications/ismir2014mir_eval.pdf">"mir_eval: A Transparent Implementation of Common MIR Metrics"</a><br />
                    Proceedings of the 15th International Conference on Music Information Retrieval, 2014.
                </p>
                <form action="" method="post" enctype="multipart/form-data">
                    <h3>Reference file</h3>
                        <p><input type="file" name="reference_file"></p>
                    <h3>Estimated file</h3>
                        <p><input type="file" name="estimated_file"></p>
                    <h3>Task</h3>
                        <select name="task">
                            <option value="beat">Beat detection</option>
                            <option value="chord">Chord recognition</option>
                            <option value="melody">Melody extraction</option>
                            <option value="onset">Onset detection</option>
                            <option value="pattern">Pattern recognition</option>
                            <option value="segment">Strucural segmentation</option>
                            <option value="tempo">Tempo estimation</option>
                            <option value="transcription">Automatic Transcription</option>
                            <option value="key">Key detection</option>
                        </select>
                    <p><input type="submit" value="Get results JSON"></p>
                </form>
            </div>
        </body>
    </html>
    '''

if __name__ == "__main__":
    app.run()
