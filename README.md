# KabuSys

KabuSys は日本株向けのデータパイプライン、リサーチ、AI ニュース解析、監査ログ、および（将来的な）自動売買フローを支援する内部ライブラリ群です。DuckDB を用いたローカルデータベースを中心に、J-Quants API からのデータ取得、RSS ニュース収集、OpenAI を用いたニュースセンチメント評価、ファクター計算・特徴量探索、データ品質チェック、監査ログ（order / execution のトレーサビリティ）などを提供します。

主な用途:
- 日次の ETL パイプライン（株価・財務・市場カレンダー取得）
- ニュースの NLP スコアリング（銘柄別センチメント）
- 市場レジーム判定（MA200 とマクロセンチメントの合成）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェックと監査ログ初期化

---

## 機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数ラッパー（必須値チェック、環境別フラグ等）
- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダー、上場銘柄一覧
  - レートリミット管理、トークン自動リフレッシュ、ページネーション対応、冪等保存
- ETL パイプライン
  - run_daily_etl / 個別 ETL ジョブ（prices / financials / calendar）
  - 差分更新、backfill、品質チェック統合
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 解凍、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存用ロジック
- ニュース NLP（OpenAI）
  - 銘柄別ニュース集約 → gpt-4o-mini を用いた JSON モードでセンチメント取得
  - チャンク処理、リトライ、レスポンスバリデーション、スコアクリップ
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM（重み30%）を合成
  - レジーム結果を market_regime テーブルへ冪等書き込み
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリー
  - Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
  - QualityIssue 型で詳細を返却
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査用 DB の初期化（UTC タイムゾーン固定、インデックス作成）

---

## 要件（主な依存ライブラリ）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

実行環境に応じて追加で必要になる可能性のある標準ライブラリ外パッケージ:
- これらを pip でインストールして利用してください（例を下に記載）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン（既にファイルがある場合は省略）
   - git clone ...

2. 仮想環境の作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt を用意していれば `pip install -r requirements.txt`）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと、自動でロードされます。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（必要に応じて）
     - SLACK_BOT_TOKEN — Slack 通知を行う場合
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル
     - OPENAI_API_KEY — OpenAI API を利用する場合（score_news / score_regime）
   - 任意:
     - KABUSYS_ENV = development | paper_trading | live
     - LOG_LEVEL = DEBUG | INFO | ...
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
   - 自動 env 読み込みを無効にする:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. データベース周り（監査 DB 初期化の例）
   - Python REPL やスクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要な例）

以下はライブラリの主要 API を呼び出す簡単な使用例です。

- ETL（日次パイプライン）の実行（DuckDB 接続を渡す）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースのセンチメントスコア取得（OpenAI API キー必須）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
    print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（MA + マクロセンチメント）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査 DB の初期化（独立 DB）
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って監査テーブルに対する操作を行う

- J-Quants API を直接使う（ID トークン取得など）
  - 例:
    from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
    token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を参照
    records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))

---

## 環境変数（主要）

自動的に読み込まれる .env ファイルのキー例（.env.example を参考に作成してください）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須: kabu API を使う場合)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (必須: AI モジュールを使う場合)
- SLACK_BOT_TOKEN (必須: Slack 通知を使う場合)
- SLACK_CHANNEL_ID (必須: Slack 通知を使う場合)
- DUCKDB_PATH (任意, デフォルト data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live, デフォルト development)
- LOG_LEVEL (INFO / DEBUG / ...)

注意:
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行われます。
- テストや CI で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール一覧です（代表的なファイルを抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（銘柄別 ai_scores）
    - regime_detector.py            — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py             — RSS ニュース収集・前処理
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - quality.py                    — データ品質チェック（欠損・スパイク等）
    - audit.py                      — 監査ログテーブル定義と初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン・IC・統計サマリー等
  - research/（その他ファイル群）
  - （strategy/ execution/ monitoring などの高レイヤーは別途実装予定または他ディレクトリ）

この README はコードベースの主要な用途・使い方を簡潔にまとめたものです。実運用では API キーやシークレットの取り扱い、権限分離、監査ログの運用、テスト（ユニット・統合）、および本番・ペーパー取引環境切替に十分注意してください。

---

もし README に追記したいサンプルスクリプト、.env.example のテンプレート、または CI / デプロイ手順があれば指示ください。必要に応じて具体的なコード例や運用上の注意点を追加します。