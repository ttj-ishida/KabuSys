# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。本リポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、監査ログスキーマなど、売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数一覧（主要）
- テスト／開発メモ
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買システム構築に必要な基盤コンポーネントを集めた Python パッケージです。
- 主に以下の領域をカバーします:
  - J-Quants API を使った株価・財務・カレンダーの差分 ETL（ETL パイプライン、保存、品質チェック）
  - DuckDB を用いたローカルデータベース管理
  - ニュース収集（RSS）とニュースに対する LLM（OpenAI）によるセンチメント評価（銘柄単位）
  - 市場レジーム判定（ETF + マクロニュースの融合）
  - 監査ログ（シグナル→発注→約定を追跡するテーブル定義・初期化）
  - 研究支援（ファクター計算、将来リターン、IC、統計ユーティリティ）

---

主な機能一覧
- data
  - jquants_client: J-Quants API クライアント（認証、ページネーション、保存関数）
  - pipeline: 日次 ETL の実装 run_daily_etl 等
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - news_collector: RSS 取得、前処理、raw_news への保存用ユーティリティ
  - calendar_management: JPX カレンダー管理・営業日判定
  - audit: 監査ログスキーマ（テーブル＋インデックス定義、初期化ユーティリティ）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを取得して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースを合成して market_regime を作成
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings: 環境変数管理（.env 自動読み込み機能、必須変数チェック）

---

セットアップ手順

1. Python 環境
   - Python 3.10+ を想定しています。仮想環境を作ることを推奨します。
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate.bat  # Windows
     ```

2. 依存パッケージをインストール
   - 必要最低限の依存（例）:
     - duckdb
     - openai (OpenAI の新しい SDK を使用するコードがあるため適切なバージョンを使用)
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実運用では requirements.txt / poetry / pyproject.toml を用意している想定です。

3. 環境変数（.env）
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に自動で `.env` と `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の主要変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL に必須）
     - KABU_API_PASSWORD — kabu ステーション API 用パスワード（発注等で使用）
     - SLACK_BOT_TOKEN — Slack 通知用 BOT トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector など）
   - 任意の変数（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト: INFO
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

   - .env のパーサはシェル形式（コメント、export KEY=...、クォート、インラインコメント）にかなり忠実に対応しています。

4. データベース初期化（監査ログなど）
   - 監査ログ専用 DB を初期化:
     ```py
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマを追加:
     ```py
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn)
     ```

---

使い方（簡単な例）

- DuckDB 接続を作成して ETL を実行（日次 ETL）
  ```py
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア（銘柄別）を生成
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を直接指定するか、環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- J-Quants の ID トークンを取得（テストや手動呼び出し）
  ```py
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- RSS フィード取得（ニュースコレクタのユーティリティ）
  ```py
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

注意点 / 実運用メモ
- OpenAI 呼び出しは各モジュールごとに内部の _call_openai_api を使っています。テストではこの関数を patch してモックすることが推奨されます。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", return_value=mock_resp)
- APIキーやトークンは環境変数か関数引数で注入できます。セキュリティに注意して管理してください。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、コード内で空チェックが行われています。呼び出し側は通常意識する必要はありません。

---

主要な環境変数（概要）
- 必須（少なくともその機能を使う場合）
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（fetch / ETL に必須）
  - OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector）
  - KABU_API_PASSWORD — kabu ステーション API のパスワード（発注系）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- 任意 / デフォルトあり
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル（デフォルト: INFO）
  - DUCKDB_PATH — data/kabusys.duckdb
  - SQLITE_PATH — data/monitoring.db
  - PID_FILE_PATH — data/execution.pid
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視しきい値
- 自動 .env 読み込みを無効化する:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

サンプル .env（最低限）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
```

---

テスト / 開発メモ
- OpenAI 呼び出しなど外部 API はモックしてテストすることを強く推奨します。
  - news_nlp と regime_detector の _call_openai_api はモジュール内の private 関数として定義されており、テスト時に patch できます。
- news_collector ではネットワーク / SSRF 保護（リダイレクト検査・プライベート IP ブロック）やレスポンスサイズ制限を実装しています。fetch_rss のテストではネットワークコールの差し替えが有用です。
- DuckDB をファイルで使うと永続化できるため、テストでは ":memory:" を使うか、テスト用ディレクトリを用意してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数と .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + 保存関数
    - pipeline.py — ETL パイプライン / run_daily_etl 等
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集 / 正規化 / 前処理
    - quality.py — データ品質チェック（QualityIssue）
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - stats.py — zscore_normalize 等
    - audit.py — 監査ログスキーマ定義 / init_audit_db / init_audit_schema
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

各モジュールは docstring と設計方針を備えており、DuckDB 接続を受け取って操作する設計です（副作用は最小化、IDEMPOTENT な保存を実施）。

---

貢献 / 拡張アイデア
- 監査ログのクエリ・集計ユーティリティを追加して監査レポートを出す
- 発注実装層（kabu ステーション等）と連携する execution モジュールの追加
- バックテスト用インターフェースの追加（Look-ahead バイアスを排除するための履歴データ取り扱い補助）
- 新しい LLM モデルや API の実装抽象化（プロバイダごとのアダプタ）

---

ライセンス / 注意事項
- 実運用での資金運用は自己責任です。本リポジトリは教育・実験目的の基盤実装を提供するものであり、取引に伴うリスクや法的責任に関する保証はありません。
- 外部 API キーは安全に管理してください。

---

質問や追加のドキュメントが必要であれば、どの部分（ETL の使い方、news_nlp のプロンプト設計、監査スキーマの運用例 など）を詳しく説明するか教えてください。