import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  interpolateColors,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const SCREENSHOT_LANDING = staticFile("day2-import-proof.png");
const SCREENSHOT_DASHBOARD = staticFile("01-dashboard-full.png");
const SCREENSHOT_EXPORT = staticFile("02-report-full.png");

const DUMMY_PHONE = "12345678";
const CUSTOMER = "Customer #1";
const ORDER_TEXT = "nasi lemak dua";
const INVOICE = "INV-2026-DEMO-001";
const PROOF_ID = "P-029";

const shellStyle = {
  color: "#1e2a24",
  fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif',
};

const slideMotion = (frame, fps) => {
  const eased = spring({
    fps,
    frame,
    config: {
      damping: 200,
      stiffness: 180,
      mass: 0.9,
    },
  });
  return {
    eased,
    rise: interpolate(eased, [0, 1], [26, 0]),
  };
};

const Shell = ({background, children}) => (
  <AbsoluteFill style={{...shellStyle, background}}>
    <div
      style={{
        position: "absolute",
        inset: 0,
        background:
          "radial-gradient(circle at 20% 10%, rgba(255,255,255,0.18), transparent 28%), radial-gradient(circle at 80% 80%, rgba(255,255,255,0.1), transparent 24%)",
      }}
    />
    {children}
  </AbsoluteFill>
);

const Pill = ({children, dark = false}) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      borderRadius: 999,
      padding: "12px 18px",
      fontSize: 18,
      fontWeight: 700,
      letterSpacing: "0.02em",
      background: dark ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.72)",
      color: dark ? "#ffffff" : "#244a38",
      border: dark
        ? "1px solid rgba(255,255,255,0.16)"
        : "1px solid rgba(36,74,56,0.08)",
      backdropFilter: "blur(10px)",
    }}
  >
    {children}
  </div>
);

const Heading = ({kicker, title, body, center = false, light = false}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {eased, rise} = slideMotion(frame, fps);
  return (
    <div
      style={{
        maxWidth: center ? 980 : 720,
        textAlign: center ? "center" : "left",
        opacity: eased,
        transform: `translateY(${rise}px)`,
      }}
    >
      <div
        style={{
          fontSize: 18,
          fontWeight: 700,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          color: light ? "#f3d7a4" : "#7a4c1f",
          marginBottom: 14,
        }}
      >
        {kicker}
      </div>
      <div
        style={{
          fontSize: 64,
          fontWeight: 900,
          lineHeight: 1.02,
          letterSpacing: "-0.04em",
          color: light ? "#ffffff" : "#1e2a24",
        }}
      >
        {title}
      </div>
      {body ? (
        <div
          style={{
            marginTop: 22,
            fontSize: 28,
            lineHeight: 1.2,
            color: light ? "rgba(255,255,255,0.88)" : "rgba(30,42,36,0.84)",
          }}
        >
          {body}
        </div>
      ) : null}
    </div>
  );
};

const ShotCard = ({src, kicker, title, body, accent = "#244a38"}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 360], [1, 1.04], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <Shell background="radial-gradient(circle at top left, #f5e6c8 0%, #e7dfd1 42%, #d3d9cf 100%)">
      <div style={{position: "absolute", inset: 42}}>
        <div
          style={{
            width: "100%",
            height: "100%",
            borderRadius: 38,
            overflow: "hidden",
            boxShadow: "0 34px 100px rgba(0,0,0,0.22)",
            border: "1px solid rgba(255,255,255,0.26)",
            transform: `scale(${scale})`,
            background: "#ffffff",
          }}
        >
          <div
            style={{
              height: 34,
              background: "linear-gradient(180deg, rgba(255,255,255,0.96), rgba(240,240,240,0.92))",
              display: "flex",
              alignItems: "center",
              padding: "0 16px",
              gap: 8,
              borderBottom: "1px solid rgba(0,0,0,0.05)",
            }}
          >
            <div style={{width: 10, height: 10, borderRadius: 999, background: "#ff6257"}} />
            <div style={{width: 10, height: 10, borderRadius: 999, background: "#ffbc2f"}} />
            <div style={{width: 10, height: 10, borderRadius: 999, background: "#28c840"}} />
          </div>
          <Img
            src={src}
            style={{width: "100%", height: "calc(100% - 34px)", objectFit: "cover"}}
          />
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          right: 64,
          bottom: 56,
          maxWidth: 560,
          backgroundColor: "rgba(248, 242, 232, 0.90)",
          borderRadius: 30,
          padding: "24px 28px",
          boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
          backdropFilter: "blur(12px)",
        }}
      >
        <div
          style={{
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: accent,
            marginBottom: 10,
          }}
        >
          {kicker}
        </div>
        <div style={{fontSize: 38, lineHeight: 1.08, fontWeight: 800}}>
          {title}
        </div>
        <div
          style={{
            marginTop: 14,
            fontSize: 23,
            lineHeight: 1.2,
            color: "rgba(30,42,36,0.84)",
          }}
        >
          {body}
        </div>
      </div>
    </Shell>
  );
};

const PhoneMock = ({children}) => {
  const frame = useCurrentFrame();
  const panel = interpolateColors(frame, [0, 360], ["#f3efe6", "#e4ede7"]);
  return (
    <div
      style={{
        width: 418,
        height: 620,
        borderRadius: 42,
        background: "#0f1a15",
        padding: 16,
        boxShadow: "0 34px 90px rgba(0,0,0,0.22)",
      }}
    >
      <div
        style={{
          width: "100%",
          height: "100%",
          borderRadius: 32,
          background: panel,
          padding: 22,
          display: "flex",
          flexDirection: "column",
          gap: 12,
          overflow: "hidden",
        }}
      >
        {children}
      </div>
    </div>
  );
};

const Bubble = ({side, children, tone = "white", small = false}) => (
  <div
    style={{
      alignSelf: side === "right" ? "flex-end" : "flex-start",
      maxWidth: side === "right" ? 360 : 396,
      background:
        tone === "green"
          ? "#dcf8c6"
          : tone === "cream"
            ? "#f8f1df"
            : "#ffffff",
      borderRadius: 24,
      padding: small ? "12px 16px" : "16px 18px",
      boxShadow: "0 6px 16px rgba(0,0,0,0.08)",
      fontSize: small ? 22 : 28,
      lineHeight: 1.2,
    }}
  >
    {children}
  </div>
);

const IntroSlide = () => (
  <Shell background="linear-gradient(135deg, #173126 0%, #2f5a47 38%, #dfc48f 100%)">
    <AbsoluteFill style={{justifyContent: "center", alignItems: "center", padding: 72}}>
      <Heading
        kicker="Kracked Devs Vibeathon"
        title="Sah.Bukti"
        body="Proof before payment. Clean books after."
        center
        light
      />
      <div
        style={{
          marginTop: 26,
          display: "flex",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <Pill dark>WhatsApp-first</Pill>
        <Pill dark>Review-gated</Pill>
        <Pill dark>Accountant-ready</Pill>
      </div>
      <div
        style={{
          marginTop: 22,
          fontSize: 21,
          fontWeight: 700,
          color: "rgba(255,255,255,0.84)",
        }}
      >
        A launch-film style walkthrough of the full Sah.Bukti loop
      </div>
    </AbsoluteFill>
  </Shell>
);

const SignupSlide = () => (
  <Shell background="linear-gradient(135deg, #f6f0e4 0%, #dbe6dd 100%)">
    <AbsoluteFill style={{justifyContent: "center", padding: "0 74px"}}>
      <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28, alignItems: "center"}}>
        <Heading
          kicker="Step 1"
          title="Owner signs up and gets a clean Sah.Bukti control plane."
          body="The website is for setup, review, analytics, and month-end. Daily operating behavior stays inside chat."
        />
        <div
          style={{
            background: "rgba(255,255,255,0.82)",
            borderRadius: 32,
            padding: 30,
            boxShadow: "0 30px 80px rgba(0,0,0,0.12)",
            backdropFilter: "blur(12px)",
          }}
        >
          <div style={{fontSize: 18, fontWeight: 700, color: "#7a4c1f"}}>Signup flow</div>
          <div style={{marginTop: 18, fontSize: 26, lineHeight: 1.3}}>
            1. Create business
            <br />
            2. Choose theme / brand
            <br />
            3. Add owner number
            <br />
            4. Start using WhatsApp immediately
          </div>
        </div>
      </div>
    </AbsoluteFill>
  </Shell>
);

const LandingSlide = () => (
  <ShotCard
    src={SCREENSHOT_LANDING}
    kicker="Front page"
    title="The site explains one clear loop."
    body="Forward messy orders and payment evidence. Review. Approve. Export."
  />
);

const ChatOrderSlide = () => (
  <Shell background="linear-gradient(135deg, #ece7db 0%, #d8e3db 100%)">
    <AbsoluteFill
      style={{
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "50px 70px",
      }}
    >
      <div style={{maxWidth: 620}}>
        <Heading
          kicker="Step 2"
          title="Customer orders in plain chat."
          body={`${CUSTOMER} at ${DUMMY_PHONE} sends: “${ORDER_TEXT}”. No forms. No portal. No spreadsheet copy-paste.`}
        />
      </div>
      <PhoneMock>
        <div style={{fontSize: 20, fontWeight: 700, color: "#365444"}}>WhatsApp conversation</div>
        <Bubble side="left">
          {CUSTOMER}
          <br />
          {ORDER_TEXT}
        </Bubble>
        <Bubble side="right" tone="green">
          Order captured.
          <br />
          Invoice created and awaiting confirmation.
        </Bubble>
        <Bubble side="right" tone="cream" small>
          Ref: {INVOICE}
          <br />
          Total: RM10.00
        </Bubble>
      </PhoneMock>
    </AbsoluteFill>
  </Shell>
);

const InvoiceSlide = () => (
  <Shell background="linear-gradient(135deg, #f7f0e5 0%, #dfe8df 100%)">
    <AbsoluteFill style={{justifyContent: "center", padding: "0 76px"}}>
      <div style={{display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: 28, alignItems: "center"}}>
        <Heading
          kicker="Step 3"
          title="Sah.Bukti turns that message into structured business data."
          body="Menu item, quantity, customer link, invoice number, and total are created from the chat itself."
        />
        <div
          style={{
            background: "#fffdf8",
            borderRadius: 32,
            padding: 30,
            boxShadow: "0 24px 60px rgba(0,0,0,0.10)",
          }}
        >
          <div style={{fontSize: 18, fontWeight: 700, color: "#7a4c1f"}}>Generated invoice</div>
          <div style={{fontSize: 30, fontWeight: 800, marginTop: 10}}>{INVOICE}</div>
          <div style={{marginTop: 18, fontSize: 24, lineHeight: 1.3}}>
            Customer: {CUSTOMER}
            <br />
            Phone: {DUMMY_PHONE}
            <br />
            Item: Nasi Lemak x2
            <br />
            Total: RM10.00
            <br />
            Status: Pending
          </div>
        </div>
      </div>
    </AbsoluteFill>
  </Shell>
);

const ChatPaymentSlide = () => (
  <Shell background="linear-gradient(135deg, #ece7db 0%, #d8e3db 100%)">
    <AbsoluteFill
      style={{
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "50px 70px",
      }}
    >
      <div style={{maxWidth: 620}}>
        <Heading
          kicker="Step 4"
          title="Customer says they paid. Sah.Bukti still does not auto-trust it."
          body={`The message “dah bayar ${INVOICE} rm10” creates a reviewable proof. It does not mutate the ledger yet.`}
        />
      </div>
      <PhoneMock>
        <div style={{fontSize: 20, fontWeight: 700, color: "#365444"}}>WhatsApp conversation</div>
        <Bubble side="left">dah bayar {INVOICE} rm10</Bubble>
        <Bubble side="right" tone="green">
          Payment evidence received.
          <br />
          Review required before invoice status updates.
        </Bubble>
        <Bubble side="right" tone="cream" small>
          Proof {PROOF_ID}
          <br />
          State: needs_review
        </Bubble>
      </PhoneMock>
    </AbsoluteFill>
  </Shell>
);

const ReviewSlide = () => (
  <Shell background="linear-gradient(135deg, #f3ecdf 0%, #dbe6de 100%)">
    <AbsoluteFill style={{justifyContent: "center", padding: "0 74px"}}>
      <div style={{display: "grid", gridTemplateColumns: "0.95fr 1.05fr", gap: 26, alignItems: "center"}}>
        <Heading
          kicker="Step 5"
          title="Review is the single gate before truth."
          body="Owner sees exactly what is waiting: invoice number, amount, source, and quick actions."
        />
        <div
          style={{
            background: "#fffaf2",
            borderRadius: 30,
            padding: 28,
            boxShadow: "0 22px 60px rgba(0,0,0,0.12)",
          }}
        >
          <div style={{fontSize: 20, fontWeight: 700, color: "#7a4c1f"}}>Review queue</div>
          <div
            style={{
              marginTop: 18,
              borderRadius: 24,
              background: "#ffffff",
              padding: 22,
              border: "1px solid rgba(30,42,36,0.08)",
            }}
          >
            <div style={{fontSize: 18, color: "#6c766f"}}>Proof {PROOF_ID}</div>
            <div style={{fontSize: 30, fontWeight: 800, marginTop: 6}}>{INVOICE}</div>
            <div style={{fontSize: 24, marginTop: 10, lineHeight: 1.25}}>
              Customer: {CUSTOMER}
              <br />
              Source: WhatsApp
              <br />
              Amount: RM10.00
              <br />
              State: needs_review
            </div>
            <div style={{display: "flex", gap: 12, marginTop: 20}}>
              <div
                style={{
                  background: "#244a38",
                  color: "white",
                  borderRadius: 999,
                  padding: "12px 18px",
                  fontSize: 20,
                  fontWeight: 700,
                }}
              >
                Approve
              </div>
              <div
                style={{
                  background: "#ead8b2",
                  color: "#573811",
                  borderRadius: 999,
                  padding: "12px 18px",
                  fontSize: 20,
                  fontWeight: 700,
                }}
              >
                Reject
              </div>
              <div
                style={{
                  background: "#f1eee7",
                  color: "#31443a",
                  borderRadius: 999,
                  padding: "12px 18px",
                  fontSize: 20,
                  fontWeight: 700,
                }}
              >
                Edit
              </div>
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  </Shell>
);

const ApprovalSlide = () => (
  <Shell background="linear-gradient(135deg, #173126 0%, #2f5a47 38%, #dfc48f 100%)">
    <AbsoluteFill style={{justifyContent: "center", alignItems: "center", padding: 72}}>
      <Heading
        kicker="Step 6"
        title="Only approval mutates ledger truth."
        body="The owner approves. Then the invoice turns paid. That trust boundary is the whole product."
        center
        light
      />
      <div style={{display: "flex", gap: 18, marginTop: 24}}>
        <div
          style={{
            background: "rgba(255,255,255,0.14)",
            color: "white",
            padding: "14px 18px",
            borderRadius: 999,
            fontSize: 24,
            fontWeight: 700,
          }}
        >
          Proof approved
        </div>
        <div
          style={{
            background: "rgba(255,255,255,0.14)",
            color: "white",
            padding: "14px 18px",
            borderRadius: 999,
            fontSize: 24,
            fontWeight: 700,
          }}
        >
          Invoice paid
        </div>
      </div>
    </AbsoluteFill>
  </Shell>
);

const DashboardSlide = () => (
  <ShotCard
    src={SCREENSHOT_DASHBOARD}
    kicker="Step 7"
    title="The dashboard becomes the owner’s audit view."
    body="Review queue, invoices, customer records, and performance metrics all reflect approved truth."
    accent="#244a38"
  />
);

const ReceiptSlide = () => (
  <Shell background="linear-gradient(135deg, #f8f1e6 0%, #dfe8df 100%)">
    <AbsoluteFill style={{justifyContent: "center", padding: "0 76px"}}>
      <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28, alignItems: "center"}}>
        <Heading
          kicker="Step 8"
          title="After approval, records are clean enough to hand off."
          body="Receipts, invoice status, reminders, and exports now line up. The owner no longer has to reconcile chat memory against the books."
        />
        <div
          style={{
            background: "#fffdf8",
            borderRadius: 32,
            padding: 30,
            boxShadow: "0 24px 60px rgba(0,0,0,0.12)",
          }}
        >
          <div style={{fontSize: 18, fontWeight: 700, color: "#7a4c1f"}}>After approval</div>
          <div style={{fontSize: 30, fontWeight: 800, marginTop: 10}}>{INVOICE}</div>
          <div style={{marginTop: 18, fontSize: 24, lineHeight: 1.3}}>
            Customer: {CUSTOMER}
            <br />
            Status: Paid
            <br />
            Settled amount: RM10.00
            <br />
            Receipt: Ready
            <br />
            Export: Ready
          </div>
        </div>
      </div>
    </AbsoluteFill>
  </Shell>
);

const ExportSlide = () => (
  <ShotCard
    src={SCREENSHOT_EXPORT}
    kicker="Step 9"
    title="Month-end export is the payoff."
    body="What started as a chat message ends as accountant-ready data instead of a screenshot graveyard."
    accent="#244a38"
  />
);

const DifferentiationSlide = () => (
  <Shell background="linear-gradient(135deg, #f4ecdd 0%, #d9e5dd 100%)">
    <AbsoluteFill style={{justifyContent: "center", alignItems: "center", padding: 72}}>
      <Heading
        kicker="Why this wins"
        title="Not another invoice form. Not a generic chatbot."
        body="Sah.Bukti lives where sellers already work, but keeps a hard approval gate before financial truth changes."
        center
      />
    </AbsoluteFill>
  </Shell>
);

const OutroSlide = () => (
  <Shell background="linear-gradient(135deg, #f2eadb 0%, #ddd4bf 54%, #b5c5b9 100%)">
    <AbsoluteFill style={{justifyContent: "center", alignItems: "center", textAlign: "center", padding: 72}}>
      <Heading
        kicker="Sah.Bukti"
        title="Real flow. Real gate. Real export."
        body="Forward messy evidence. Review it. Approve what is true. Hand off cleaner books."
        center
      />
      <div style={{marginTop: 28, fontSize: 24, fontWeight: 700, color: "#7a4c1f"}}>
        arifaqyl.me
      </div>
    </AbsoluteFill>
  </Shell>
);

export const SahBuktiDemo = () => {
  const slideFrames = 360;
  return (
    <AbsoluteFill>
      <Audio src={staticFile("audio/sahbukti-bed.wav")} volume={0.18} />
      <Sequence from={0 * slideFrames} durationInFrames={slideFrames}>
        <IntroSlide />
      </Sequence>
      <Sequence from={1 * slideFrames} durationInFrames={slideFrames}>
        <SignupSlide />
      </Sequence>
      <Sequence from={2 * slideFrames} durationInFrames={slideFrames}>
        <LandingSlide />
      </Sequence>
      <Sequence from={3 * slideFrames} durationInFrames={slideFrames}>
        <ChatOrderSlide />
      </Sequence>
      <Sequence from={4 * slideFrames} durationInFrames={slideFrames}>
        <InvoiceSlide />
      </Sequence>
      <Sequence from={5 * slideFrames} durationInFrames={slideFrames}>
        <ChatPaymentSlide />
      </Sequence>
      <Sequence from={6 * slideFrames} durationInFrames={slideFrames}>
        <ReviewSlide />
      </Sequence>
      <Sequence from={7 * slideFrames} durationInFrames={slideFrames}>
        <ApprovalSlide />
      </Sequence>
      <Sequence from={8 * slideFrames} durationInFrames={slideFrames}>
        <DashboardSlide />
      </Sequence>
      <Sequence from={9 * slideFrames} durationInFrames={slideFrames}>
        <ReceiptSlide />
      </Sequence>
      <Sequence from={10 * slideFrames} durationInFrames={slideFrames}>
        <ExportSlide />
      </Sequence>
      <Sequence from={11 * slideFrames} durationInFrames={slideFrames}>
        <DifferentiationSlide />
      </Sequence>
      <Sequence from={12 * slideFrames} durationInFrames={slideFrames}>
        <OutroSlide />
      </Sequence>
    </AbsoluteFill>
  );
};
