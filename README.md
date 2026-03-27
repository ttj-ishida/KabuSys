# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ README。  
このドキュメントはコードベースの概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買 / データプラットフォームです。  
主に以下を提供します。

- J-Quants API からのデータ取得（株価日足、財務データ、マーケットカレンダー）
- ニュース収集（RSS）と LLM（OpenAI）を用いたニュースセンチメント解析（銘柄別 AI スコア）
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- ETL パイプライン（差分取得 / 保存 / 品質チェック）
- データ品質チェック、監査ログ（シグナル→発注→約定のトレーサビリティ）
- 研究用ツール（ファクター計算、forward returns、IC 等）
- kabuステーション と連携するための設定（発注は別モジュールで実装可能）

設計上の注意点として、バックテスト等でのルックアヘッドバイアスを回避するために多くの関数は内部で現在日時を参照せず、明示的な target_date 引数を受け取ります。

---

## 機能一覧

主なモジュールと機能（抜粋）:

- kabusys.config
  - 環境変数 / .env 自動読み込み、必須環境変数の検証
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・ページネーション・リトライ・レート制御）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得→正規化→raw_news 保存、SSRF 対策、サイズ制限
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログ（signal_events / order_requests / executions）のスキーマ初期化・DB 初期化
  - stats: z-score 正規化ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でスコア化し ai_scores に格納
  - regime_detector.score_regime: ETF の MA とマクロセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー計算
  - feature_exploration: forward returns, IC, 統計サマリー 等

---

## セットアップ手順

前提:
- Python 3.10+（型アノテーションに Union | を利用しているため）
- DuckDB（Python パッケージとしてインストール）
- OpenAI Python SDK（v1 系を想定）
- defusedxml（XML パースの安全対策）

1. リポジトリをクローン、仮想環境作成・有効化:

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストール（例）:

   ```bash
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

   ※ 実際のプロジェクトでは requirements.txt や pyproject.toml を参照してください。

3. パッケージを開発モードでインストール（任意）:

   ```bash
   pip install -e .
   ```

4. 環境変数を設定（.env ファイル作成）:

   プロジェクトルートに `.env` / `.env.local` を置くことで自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。自動検索は .git または pyproject.toml を基準に行われます。

   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack Bot トークン（監視通知等）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）

   任意 / デフォルトあり:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読み込みを無効化

   例 `.env`:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB の初期化（監査DB 例）:

   Python スクリプトまたは REPL 内で:

   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # もしくは in-memory
   # conn = init_audit_db(":memory:")
   ```

   audit.init_audit_schema を使って既存の接続に監査スキーマを適用することもできます。

---

## 使い方（基本例）

以下はライブラリの主要機能を呼び出す簡単な例です。実行前に環境変数や DuckDB のテーブル定義が適切に整っていることを確認してください。

1. 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）:

   ```python
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

2. ニュースのスコアリング（OpenAI を用いる）:

   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env 内の OPENAI_API_KEY を利用
   print(f"書き込み銘柄数: {written}")
   ```

3. 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）:

   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. 監査スキーマを既存 DB に導入:

   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema

   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

5. RSS フィードの取得（news_collector.fetch_rss）:

   ```python
   from kabusys.data.news_collector import fetch_rss

   articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
   for a in articles[:5]:
       print(a["id"], a["title"], a["datetime"])
   ```

※ 各関数は DuckDB の期待されるスキーマ（raw_prices/raw_news/raw_financials/ai_scores/market_regime 等）が存在することを前提とします。スキーマ作成用のDDL は別途管理されている想定です（audit モジュールは監査用スキーマを提供）。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite （監視 DB 等）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意) — 1 を設定すると自動 .env ロードを無効化

---

## ディレクトリ構成

主要なファイル・フォルダ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得/保存）
    - pipeline.py                  — ETL パイプライン / run_daily_etl 等
    - etl.py                       — ETL の公開インターフェース（ETLResult）
    - news_collector.py            — RSS 収集・前処理
    - quality.py                   — データ品質チェック
    - calendar_management.py       — 市場カレンダー管理・営業日判定
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログ（スキーマ初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/volatility/value）
    - feature_exploration.py       — forward returns, IC, summary, rank
  - research/*                      — 研究用ユーティリティ群
- pyproject.toml / setup.cfg       — （プロジェクト設定。存在する場合）

---

## 運用上の注意 / ベストプラクティス

- ルックアヘッドバイアス防止:
  - スコアリング / ETL / レジーム判定 は target_date を明示して呼ぶこと。
  - 内部で datetime.today() を参照しない関数設計になっていますが、呼び出し側で意図しない日付を渡さないこと。

- API キー保護:
  - .env をリポジトリにコミットしないでください。 .env.example を参照し、各環境で適切に設定してください。

- テスト:
  - OpenAI 呼び出しやネットワーク I/O はテストでモックすることを推奨します（コード内でもモックしやすい設計になっています）。

- データ品質:
  - ETL 実行後は quality.run_all_checks の結果を監視し、重大な品質問題が検出された場合は原因調査を行ってください。

---

## 参考（開発者向けメモ）

- 自動 .env 読み込みはプロジェクトルート（.git or pyproject.toml）を基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用して無効化できます。
- OpenAI 呼び出しは JSON mode（厳密な JSON 出力）を期待していますが、万が一のパース失敗時はフェイルセーフで 0.0 にフォールバックする実装が多く含まれています。
- J-Quants API へは RateLimiter（固定間隔スロットリング）とリトライを組み合わせて実装しています。大量リクエスト時は API レートに注意してください。

---

README に含めるべき追加情報（例: schema DDL、CI / テストの実行方法、具体的な runbook）などがあれば教えてください。必要に応じて追記します。