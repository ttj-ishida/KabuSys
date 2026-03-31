# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（データパイプライン、ニュース収集・NLP、市場レジーム判定、ファクター研究、監査ログなど）を提供する Python ライブラリです。本リポジトリは、バックテスト・リサーチ環境から実運用（paper / live）までを想定したモジュール群で構成されています。

> 注: 本 README はソースコード（src/kabusys 以下）に基づいて作成しています。

---

主な特徴（概要）
- J-Quants API 経由での株価・財務・カレンダー取得（ページネーション・再試行・レート制御付き）
- DuckDB を使った ETL パイプライン（差分取得・冪等保存・品質検査）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去・サイズ制限）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別）と市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索（IC、将来リターン等）
- 監査ログ（signal → order_request → executions）のための DuckDB スキーマ初期化ユーティリティ
- 環境変数/ .env 自動読み込みと設定管理（kabusys.config.Settings）

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 環境変数（必須 / 任意）
- 使い方（サンプルコード）
- ディレクトリ構成（主要ファイルと役割）
- 補足（設計方針・安全対策）

---

プロジェクト概要
- Python ベースの日本株データプラットフォーム兼リサーチ/自動売買基盤。
- データ取得（J-Quants）、ETL、品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター研究、監査ログ管理などをモジュラーに提供します。
- DuckDB をデータストアとして使用し、再現性・冪等性を重視した設計になっています。

---

機能一覧（モジュール別）
- kabusys.config
  - 環境変数の読み込み (.env / .env.local 自動ロード、無効化フラグあり)
  - settings オブジェクトでアプリ設定取得
- kabusys.data
  - jquants_client: J-Quants API クライアント、取得・保存関数（raw_prices / raw_financials / market_calendar）、レート制御、再試行、トークン自動リフレッシュ
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）および個別 ETL ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得、前処理、SSRF 対策、raw_news への保存
  - calendar_management: JPX カレンダー管理、営業日判定・次/前営業日取得
  - audit: 監査ログ用スキーマ初期化・専用 DB 初期化ユーティリティ
  - stats: z-score 正規化等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント評価（OpenAI）
  - regime_detector.score_regime: ETF（1321）MA とマクロ記事の LLM センチメントを合成して日次の市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- その他
  - 監視・実行・戦略・発注などのレイヤ（execution, strategy, monitoring）はパッケージ公開対象として想定（__init__ にてエクスポート）

---

前提条件
- Python 3.10+
  - ソース内で | 型ヒント等を使用しているため Python 3.10 以上が必要です。
- 推奨ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, datetime, logging 等）

（実際の requirements.txt があればそれを使ってください。）

---

セットアップ手順（簡易）
1. レポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml

   - 編集・開発する場合:
     - pip install -e .

4. 環境変数/ .env を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が実行時に自動ロード）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB データベース（監査ログ用など）を初期化
   - 監査 DB を初期化して接続を得る例:
     - from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

6. ETL の実行や AI スコアリング、ファクター計算は下記「使い方」を参照。

---

必須 / 主な環境変数
- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD      (必須) — kabuステーション API 等のパスワード
- SLACK_BOT_TOKEN        (必須) — Slack 通知用
- SLACK_CHANNEL_ID       (必須) — Slack 通知先チャンネル ID
- OPENAI_API_KEY         (必須 for AI 機能) — OpenAI API キー（news_nlp / regime_detector が参照）
- DUCKDB_PATH            (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH            (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV            (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL              (任意) — DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）

（.env.example を作成して上記を記載すると分かりやすいです）

---

使い方（簡単なサンプル）

1) 設定値の参照
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path, settings.env などでアクセスできます。

2) DuckDB 接続と ETL 実行（日次 ETL）
- 例:
  - import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

  - run_daily_etl は市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック を順に実行し ETLResult を返します。

3) ニュースの AI スコアリング（銘柄別）
- from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照
  print("scored", n_written, "codes")

4) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

5) 監査 DB 初期化（発注ログ用）
- from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions のテーブルとインデックスが作成されます

6) 研究用ファクター計算
- from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, date(2026, 3, 20))
  # returns list of dicts: {"date", "code", "mom_1m", ...}

エラーハンドリング:
- AI 呼び出しや外部 API はリトライやフォールバックロジックを内包していますが、呼び出し側でも例外キャッチを行ってください。
- score_news / score_regime は API キー未設定時に ValueError を投げます。

---

ディレクトリ構成（主要ファイルと役割）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みと settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント解析（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存・レート制御）
    - pipeline.py            — ETL パイプライン（run_daily_etl / 個別ジョブ）
    - quality.py             — データ品質チェック
    - news_collector.py      — RSS 収集・前処理（SSRF 対策・サイズ制限）
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化・監査 DB 初期化
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等
  - research/（他の補助モジュール）
  - （strategy, execution, monitoring 等の名前空間はパッケージ公開対象に含める設計）

---

設計上の重要ポイント（補足）
- ルックアヘッドバイアス対策:
  - 各処理で datetime.today()/date.today() の安易な参照を避け、target_date ベースの処理を採用。
  - データ取得・スコアリング関数は必ず target_date を外部から渡す設計。
- 冪等性:
  - J-Quants から取得したデータは DuckDB へ ON CONFLICT DO UPDATE で保存（重複上書き可）。
  - news_collector は URL 正規化→SHA256 による記事IDで冪等挿入を行う。
- セキュリティ・堅牢性:
  - news_collector は SSRF 対策（ホストのプライベート判定・リダイレクト検査）・XML の defusedxml を使用。
  - jquants_client はレート制御、リトライ、401 自動リフレッシュ等の保護対策あり。
  - AI 呼び出しはエラー時にフェイルセーフ（既定スコア 0.0 を返す）を採用。
- テスト容易性:
  - OpenAI / HTTP 呼び出し部分はモック差し替え（関数を patch 可能）でユニットテストを容易にする実装。

---

よくある操作（ショートハンド）
- .env 自動ロードを無効にしてプログラム内で明示的に env を設定したい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ロギングレベルを変える:
  - export LOG_LEVEL=DEBUG

---

最後に
- 本 README はコード（src/kabusys）を基にまとめています。実運用/本番運用前に必ずローカル環境での動作検証、API キーの管理、発注部分の安全性（発注クッション・量限度等）の実装・レビューを行ってください。自動売買はリスクを伴います。

必要であれば、README に含めるサンプル .env.example、requirements.txt、あるいはより詳細な運用手順（cron ジョブ、コンテナ化、監視フロー）も作成します。どの情報が欲しいか教えてください。