__docformat__ = "reStructuredText"
import zope.component
import zope.interface
import zope.schema.interfaces
from plone.memoize.request import cache

from z3c.form import interfaces
from z3c.form.widget import Widget, FieldWidget
from z3c.form.browser import widget

from collective.easyform.interfaces import ILikertWidget


def widget_key(func, self, *args, **kwargs):
    """We can't use the request cache because it doesn't account for the
    field name."""
    key = (
        '/'.join(self.context.getPhysicalPath() or ()),
        self.__class__.__name__,
        func.__name__,
        self.field.__name__,
        tuple(args),
        frozenset(kwargs.items()),
    )
    return tuple(key)


@zope.interface.implementer_only(ILikertWidget)
class LikertWidget(widget.HTMLTextInputWidget, Widget):
    """Input type text widget implementation."""

    klass = u'likert-widget'
    css = u'text'
    value = u''

    def update(self):
        super(LikertWidget, self).update()
        widget.addFieldClass(self)

    def extract(self, default=interfaces.NO_VALUE):
        """See z3c.form.interfaces.IWidget."""
        answers = []
        if self.field.questions is None:
            return ''
        for index, question in enumerate(self.field.questions):
            question_answer = self.extract_question_answer(index, default)
            if question_answer is not None:
                answers.append(question_answer)
        return u', '.join(answers)

    def extract_question_answer(self, index, default):
        """See z3c.form.interfaces.IWidget."""
        name = '%s.%i' % (self.name, index)
        if (name not in self.request and
            '%s-empty-marker' % name in self.request):
            return None
        value = self.request.get(name, default)
        if value != default:
            return '%i: %s' % (index + 1, value)
        else:
            return None

    @cache(widget_key, 'self.request')
    def parsed_values(self):
        return self.field.parse(self.value)

    def checked(self, question_number, answer_number):
        values = self.parsed_values()
        if not values or (question_number) not in values:
            return False
        else:
            return values[question_number] == self.field.answers[answer_number - 1]

    def display_value(self):
        return u', '.join(
            u'{}: {}'.format(self.field.questions[a - 1], q)
            for a, q in self.parsed_values().items()
            if a >= 1 and len(self.field.questions) >= a
        )


@zope.component.adapter(zope.schema.interfaces.IField, interfaces.IFormLayer)
@zope.interface.implementer(interfaces.IFieldWidget)
def LikertFieldWidget(field, request):
    """IFieldWidget factory for TextWidget."""
    return FieldWidget(field, LikertWidget(request))
