import math

class Paginator:
    '''
        A helper class that implements splitting of an iterable
        into a sequence of pages of the given size
    '''

    ELEMS_PER_PAGE = 10
    PAGES_AROUND = 5

    def __init__(self, iterable, num_per_page=ELEMS_PER_PAGE, pages_around=PAGES_AROUND):
        assert num_per_page > 0

        self.elems = list(iterable)
        self.num_per_page = num_per_page
        self.pages_around = pages_around

    def __len__(self):
        '''
            Returns the the number of pages
        '''

        return int(math.ceil(len(self.elems) / float(self.num_per_page)))

    def __getitem__(self, page):
        '''
            Returns a (elems, pages) pair, where `elems` is a tuple
            of elements on the page `page` and 'pages' is a list of
            page numbers that lay around the asked page
        '''

        assert 0 < page <= len(self)

        elems = tuple(self.elems[(page - 1) * self.num_per_page : page * self.num_per_page])
        pages = [p for p in range(1, len(self) + 1)
                 if abs(page - p) <= self.pages_around]
        return (elems, pages)
