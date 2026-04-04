# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株のデータ取得・品質管理・特徴量生成・AIベースのニュースセンチメント評価・監査ログなどを備えた、自動売買プラットフォーム向けのライブラリ群です。DuckDB をデータレイヤに用い、J-Quants / J-Quants の株価・財務・カレンダー API、および OpenAI を利用した NLP コンポーネントを含みます。

---

## 主な機能概要

- Data ETL
  - J-Quants からの日足（OHLCV）・財務データ・市場カレンダーの差分取得と DuckDB への冪等保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS フィード取得 → 前処理 → raw_news / news_symbols への冪等保存（SSRF 対策・トラッキング除去）
- AI（OpenAI）を使った NLP
  - 銘柄ごとのニュースセンチメントスコア生成（score_news）
  - マクロセンチメントとETF（1321）の MA200乖離を合成した市場レジーム判定（score_regime）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算、将来リターン・IC・統計サマリ
- 監査ログ（Audit）
  - signal → order_request → execution までのトレーサビリティを確保する監査用スキーマと初期化ユーティリティ
- 設定管理
  - .env / 環境変数を自動ロード（プロジェクトルート基準）。自動ロードは環境変数で無効化可能

---

## 要件（想定）

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリとして urllib, datetime, json, logging 等を使用

実際のパッケージ要件はプロジェクトの pyproject.toml / requirements.txt を参照してください（本リポジトリの例では依存定義ファイルはここに含まれていません）。

---

## セットアップ手順

1. リポジトリをクローン（例）

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）

   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）

4. 環境変数の準備

   プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   最低限設定すべき環境変数（例）:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabu ステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # LINE（任意、通知用）
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=

   # DB / パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   - `.env.local` は `.env` より優先してロードされます（OS 環境変数はさらに優先）。
   - `JQUANTS_REFRESH_TOKEN` / `KABU_API_PASSWORD` / `OPENAI_API_KEY` は機密情報です。公開リポジトリに含めないでください。

5. データディレクトリ作成（README のパス例に従う場合）

   ```bash
   mkdir -p data
   ```

---

## 使い方（主要 API の例）

以下は代表的な利用例です。ほとんどの関数は DuckDB の接続（duckdb.connect(...））と target_date（datetime.date）を受け取ります。

- DuckDB に接続して ETL を日次実行する

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- OpenAI を使ってニューススコアを生成（score_news）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

  - `OPENAI_API_KEY` が環境変数に無ければ `api_key` 引数で渡してください。
  - 大量の銘柄はバッチ（20件/回）で API 呼び出しされます。OpenAI の利用料・レートに注意してください。

- 市場レジーム（score_regime）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

  - ETF 1321 の MA200 とマクロニュース（LLM）による合成スコアを market_regime テーブルへ書き込みます。

- 監査ログスキーマの初期化・監査DB作成

  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db, init_audit_schema

  # 監査専用 DB の初期化（ファイル or ":memory:"）
  audit_conn = init_audit_db("data/audit.duckdb")

  # 既存接続にスキーマを追加する場合
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn)
  ```

- RSS フィードから記事を取得（news_collector.fetch_rss）

  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

---

## 主要設定（Settings / 環境変数）

設定は `kabusys.config.settings` 経由で取得します。代表的なプロパティ:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabu ステーション API パスワード（必須）
- kabu_api_base_url: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- line_channel_access_token / line_user_id: LINE 通知用（任意）
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- kill_flag_path / pid_file_path など監視関連
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: ログレベル

環境変数が未設定の場合、Settings は ValueError を投げるものがあります（必須項目）。

自動 .env 読み込みの挙動:
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に `.env` と `.env.local` を読み込みます。
- OS 環境変数 > .env.local > .env の順で優先。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 注意点 / 実装上の特徴

- Look-ahead バイアス対策
  - 全てのスコアリング・ETL 関数は内部で `date.today()` を直接参照しないよう設計されています（外部から `target_date` を渡す形）。バックテストでの適切な時刻トレースを意図しています。
- 冪等性
  - ETL の保存処理（save_*）は ON CONFLICT DO UPDATE などで冪等を担保します。
- 再試行・レート管理
  - J-Quants クライアントは 120 req/min に合わせた RateLimiter、OpenAI 呼び出し系はリトライと指数バックオフを実装しています。
- セキュリティ対策
  - RSS 取得では SSRF 対策、XML パースの安全化（defusedxml）、トラッキングパラメータ除去、最大受信サイズチェックなどを行います。
- テスト容易性
  - OpenAI / HTTP 呼び出し箇所はモック差し替え可能（内部関数を patch してテストしやすく設計されています）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py     — 市場カレンダー管理
    - etl.py                     — ETL 公開インターフェース
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py          — J-Quants API クライアント・保存ロジック
    - news_collector.py          — RSS 収集・前処理
    - etc...
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum / volatility / value）
    - feature_exploration.py     — 将来リターン / IC / summary
  - monitoring/                   — 監視・実行系（存在する場合）
  - strategy/                     — 戦略定義（存在する場合）
  - execution/                    — 発注実行（存在する場合）
  - monitoring/                   — 監視・PID / kill-flag 等（存在する場合）

（上記は本コードベースに含まれる主要モジュールを抜粋しています）

---

## 開発・運用上のヒント

- ローカルでのテスト・開発時は `KABUSYS_ENV=development` を使用し、実売買時は `live` を使って保護された挙動を適用してください（ログレベルや実際の発注処理の抑制など）。
- OpenAI API を使う処理はコストとレート制限に注意。テスト時は API 呼び出しをモックしてください。
- DuckDB はファイルベースの軽量 DB です。バックアップや排他アクセスに注意して運用してください。
- .env / .env.local に機密情報を置く場合はファイル権限や CI シークレット管理に注意してください。

---

## 追加情報

- 自動ロードされる .env のパースはシェル風の構文（export KEY=val, クォート、インラインコメント）に対応しています。
- 以降の発展では戦略モジュール（strategy）、発注実行（execution）、監視（monitoring）を結びつける CLI / サービスランナー等を追加する想定です。

---

README に書き漏れがある、あるいは特定の操作（例：ETL のスケジュール化、監査ログの参照クエリ、news_collector の DB 保存フロー等）について詳細が必要であれば、用途に合わせた使用例や運用手順を追記します。必要な箇所を教えてください。