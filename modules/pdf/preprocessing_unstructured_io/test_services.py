import dtlpy as dl
from preprocess_runner import PreprocessorRunner
from converter_runner import ConvertorRunner

if __name__ == '__main__':
    dl.setenv('rc')
    project = dl.projects.get(project_name='text-project')
    dataset = project.datasets.get(dataset_name='mortgage-dataset')
    item = dataset.items.get(item_id='65f9984cb6670319586ba63f')

    # dl.setenv('prod')
    # project = dl.projects.get(project_name='text-project')
    # dataset = project.datasets.get(dataset_name='mortgage-data')
    # item = dataset.items.get(item_id='660e92f3aadac605ee7713db')

    c = ConvertorRunner()
    textfiles_items = c.pdf_item_to_text(item=item, context=dl.Context())
    p = PreprocessorRunner()
    chunks_items = p.preprocess_text(items=textfiles_items, context=dl.Context())

