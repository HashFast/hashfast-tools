.PHONY: all clean

# Requires libusb-dev libusb-1.0.0-dev libudev-dev

OUTPUT = \
	readserial \
	writeserial \
	ping \
	version \
	coremap \
	hfupdate \
	createupdate \
	enterloader \
	readdb \
	thermistor \
	hfudump \
	readdbstream \
	hfterm \
	hcm \
	hfsetfans \
	ctrltest \
	opusbinit \
	da2stest

SRCDIR = src

GCC = gcc

all: $(OUTPUT)

INCLUDE_DIRS = /usr/include/libusb-1.0 /usr/local/include/libusb-1.0
EXTRA_LINKER = -pthread -L/usr/local/lib

CFLAGS = -g -c -Wall -pthread
CCOPTS = $(CFLAGS)
CCOPTS += $(foreach INC,$(INCLUDE_DIRS),-I$(INC))

LIBS = -ludev -lpthread -lusb-1.0 -lm

LINKABLE_SOURCES = \
	board_util.c \
	crc.c \
	usbctrl.c \
	hfparse.c \
	hfusb.c

C_SOURCES = \
	enterloader.c \
	ping.c \
	readserial.c \
	writeserial.c \
	coremap.c \
	createupdate.c \
	hfupdate.c \
	readdb.c \
	readdbstream.c \
	version.c \
	thermistor.c \
	hfudump.c \
	hfterm.c \
	hcm.c \
	hfsetfans.c \
	ctrltest.c \
	opusbinit.c \
	da2stest.c

OBJS = $(C_SOURCES:%.c=$(SRCDIR)/%.o)

LINKABLE_OBJS = $(LINKABLE_SOURCES:%.c=$(SRCDIR)/%.o)

$(LINKABLE_OBJS): $(SRCDIR)/%.o: $(SRCDIR)/%.c
	$(GCC) $(CCOPTS) -o $@ $<

$(OBJS): $(SRCDIR)/%.o: $(SRCDIR)/%.c
	$(GCC) $(CCOPTS) -o $@ $<

%: $(SRCDIR)/%.o $(LINKABLE_OBJS)
	$(GCC) $(EXTRA_LINKER) -o $@ $< $(LINKABLE_OBJS) $(LIBS)

clean:
	-$(RM) $(OBJS) $(LINKABLE_OBJS) $(OUTPUT)
	-$(RM) *~

