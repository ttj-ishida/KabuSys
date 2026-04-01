# KabuSys

日本株向け自動売買／データプラットフォームライブラリ。J-Quants からのデータ ETL、ニュース収集・NLP による銘柄センチメント評価、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレース）などを提供します。

主に DuckDB を内部データストアとして想定し、OpenAI（gpt-4o-mini 等）をニュース／マクロセンチメント評価に利用します。

バージョン: kabusys.__version__ = 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API からの株価（日足）、財務データ、JPX カレンダー取得（差分更新・ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT / INSERT … DO UPDATE）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー管理・営業日判定

- ニュース収集 / NLP
  - RSS からのニュース収集（SSRF 対策、トラッキング除去、前処理）
  - OpenAI を用いた銘柄ごとのニュースセンチメント算出（ai_scores への書込）
  - マクロ記事を用いた市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント合成）

- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - 発注フローの完全なトレース（UUID ベースの階層構造）

- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - キー不足時は ValueError を投げる便利な Settings（kabusys.config.settings）

---

## 要件

- Python 3.10+
- 主な外部ライブラリ
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib / json / datetime 等を広く利用

（プロジェクトの requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository-url>
   - cd <repository>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - または開発インストール:
     - pip install -e .

4. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（kabusys.config.Settings が参照するもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

その他推奨設定（デフォルトあり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視設定

例 .env（簡易）
- JQUANTS_REFRESH_TOKEN=xxxx
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- KABUSYS_ENV=development

---

## 使い方（基本例）

- DuckDB 接続を作成して ETL を実行（日次 ETL）
  - Python から:
    - import duckdb
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect("data/kabusys.duckdb")
    - result = run_daily_etl(conn)  # target_date を省略すると today が使われます
    - print(result.to_dict())

- ニュースのセンチメントスコアリング（AI）
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))  # 指定日に対するウィンドウでスコア計算

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ初期化（監査専用 DB の作成）
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # これで signal_events / order_requests / executions テーブルが作成されます

- リサーチ用ファクター計算
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
  - results = calc_momentum(conn, target_date=date(2026,3,20))

注意:
- OpenAI API 呼び出しには OPENAI_API_KEY（または関数引数）を必ず設定してください。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN による認証を行います。

---

## 自動環境読み込みの挙動

- .env / .env.local はプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から相対的に読み込まれます。
- 読み込み順: OS環境変数 > .env.local > .env（.env.local は上書き）
- テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ公開（version）
- config.py — 環境変数 / 設定管理（Settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの集約・OpenAI 呼び出し・ai_scores への書込
  - regime_detector.py — マクロ + MA200 による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得／保存ユーティリティ）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS ニュース収集（SSRF 対策・正規化）
  - calendar_management.py — 市場カレンダー管理・営業日判定・バッチ更新
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログテーブルの DDL / 初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility ファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
- research/* と data/* は相互に依存するユーティリティを提供（ただし本番発注部分へ直接アクセスしない設計）

ドキュメント文字列（docstring）に各モジュールの設計意図・処理フロー・フォールバック方針が詳述されています。実装前後やユニットテストの参照に役立ちます。

---

## 注意点 / 運用上のヒント

- Look-ahead バイアス対策が各所に組み込まれています（target_date に基づくウィンドウ、データ取得時の fetched_at 記録など）。バックテスト用途での使用時はこれらの設計を尊重してください。
- OpenAI 呼び出しはリトライを含む保守的な実装（429/接続失敗/タイムアウト/5xx の扱い）になっています。API 利用量やコストに注意してください。
- J-Quants API のレート制限（120 req/min）に合わせて RateLimiter を実装しています。大量のページネーション処理でも基本的に安全ですが、独自のバルク処理を追加する際はレート制御を意識してください。
- DuckDB の executemany に空リストを渡すと例外となるバージョン依存の挙動を回避するようコード上でガードしています。

---

## 貢献 / 開発

- コードはモジュール単位で分離され、ユニットテスト用に外部呼び出し（HTTP / OpenAI 等）をモックしやすい設計になっています。
- 新しいデータソースやモデルを追加する場合は、既存の設計（冪等性、フェイルセーフ、ルックアヘッド防止）に従って実装してください。

---

必要があれば README のサンプル .env.example、実行スクリプト（cron / systemd 用）や docker-compose 例、ユニットテストの実行方法も追記します。どの追加情報が欲しいか教えてください。