# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム向けライブラリ群です。  
DuckDB をデータレイヤに用い、J-Quants API からの ETL、ニュース収集と AI を用いたニュースセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）など、自動売買システムの基盤機能を提供します。

- Python パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 特徴（機能一覧）

- 環境設定読み込み
  - .env / .env.local / OS 環境変数を自動で読み込む仕組み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で型安全に設定取得

- データ ETL（J-Quants 連携）
  - 日次株価（OHLCV）差分取得・保存（ページネーション・リトライ・レートリミット対応）
  - 財務データの差分取得・保存
  - JPX マーケットカレンダー取得・保存
  - ETL パイプライン（run_daily_etl）と結果オブジェクト（ETLResult）

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue）

- ニュース収集
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、XML 安全パーサ）
  - raw_news / news_symbols への冪等保存想定（ON CONFLICT 対応）

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント評価（news_nlp.score_news）
  - マクロセンチメント + ETF MA200乖離を合成して市場レジーム判定（regime_detector.score_regime）
  - LLM 呼び出し時のリトライ・フォールバックロジックを実装

- リサーチ用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
  - 監査データベース初期化関数（init_audit_db）

---

## 動作環境・依存

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai（OpenAI の公式 Python SDK）
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI API）を行うため、環境変数で API キーを設定してください。

requirements.txt 等が無い場合は最低限次のパッケージが必要です（バージョンは適宜選択）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール（開発時は editable モード推奨）
   - pip install -e .

   もしくは必要パッケージを個別にインストール:
   - pip install duckdb openai defusedxml

3. 環境変数の準備
   - プロジェクトルート（pyproject.toml または .git のある階層）に .env を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabu API のパスワード（発注連携などで使用）
   - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必要
   - KABU_API_BASE_URL (省略可, デフォルト http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知等に使用)
   - DUCKDB_PATH (Default: data/kabusys.duckdb)
   - SQLITE_PATH (Default: data/monitoring.db)
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development | paper_trading | live, default: development)
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL, default: INFO)

   .env の書式は shell の KEY=VAL に準じます。詳細なパース挙動は kabusys.config モジュールを参照してください（クォート・コメント処理などに対応）。

4. データフォルダの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL での利用例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY）を設定してください。

- DuckDB 接続の準備（デフォルトパスを使用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- ETL（日次）を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュースセンチメントをスコア化（target_date は date オブジェクト）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, date(2026, 3, 20))
  print("scored codes:", written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（専用 DB を作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- RSS フィード取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  print(len(articles))
  ```

注意:
- OpenAI を用いる機能（score_news, score_regime）は OPENAI_API_KEY を必要とします。API レートやコストに注意してください。
- ETL / データ書き込みは DuckDB に直接書き込みます。重要データはバックアップしてください。

---

## よく使う API（モジュール別）

- kabusys.config
  - settings: 環境設定（settings.jquants_refresh_token, settings.duckdb_path, settings.env, ...）

- kabusys.data
  - pipeline.run_daily_etl(conn, target_date=None, id_token=None, ...)
  - pipeline.ETLResult（実行結果）
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - news_collector.fetch_rss
  - quality.run_all_checks
  - calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - audit.init_audit_db / init_audit_schema

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats と併用）

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py           — ニュースセンチメント（LLM）処理
      - regime_detector.py    — 市場レジーム判定（MA200 + マクロセンチメント）
    - data/
      - __init__.py
      - jquants_client.py     — J-Quants API クライアント（取得・保存）
      - pipeline.py           — ETL パイプライン（run_daily_etl 等）
      - etl.py                — ETLResult エクスポート
      - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
      - news_collector.py     — RSS ニュース収集（SSRF 対策あり）
      - quality.py            — データ品質チェック
      - stats.py              — 汎用統計ユーティリティ（z-score 等）
      - audit.py              — 監査ログ（DDL・初期化ユーティリティ）
    - research/
      - __init__.py
      - factor_research.py    — ファクター計算（Momentum/Value/Volatility）
      - feature_exploration.py— 将来リターン / IC / 統計サマリー
    - ai/、data/、research/ の下にさらに補助関数やユーティリティが配置されています。

---

## 注意点 / 運用上のヒント

- Look-ahead バイアス対策
  - 多くの処理（ETL、news window、regime scoring 等）は datetime.today()/date.today() を不適切に参照しない設計になっています。target_date を明示して呼ぶことでバックテストやフェアな評価が可能です。

- フェイルセーフ
  - OpenAI API や外部 API の失敗時はゼロ値にフォールバックしたり処理をスキップして続行する設計です（ログ出力は行います）。重大な障害はログで把握してください。

- 自動 .env 読み込み
  - プロジェクトルートにある .env（と .env.local）が自動読み込みされます。テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB の executemany の挙動
  - 一部コードで DuckDB のバージョン互換性（0.10 等）に配慮した空リストチェックを行っています。DuckDB のマイナーバージョン差に注意してください。

---

## 貢献・拡張

- 新しいデータソースの追加（news ソースや API）
- 追加の品質チェックやアラート連携（LINE / Slack）
- 発注実行（kabu API）周りのラッパー実装（監査ログと連携）
- バックテスト用モジュール（Strategy モデル）やリスク管理モジュールの追加

---

不明点や README に追記してほしい項目があれば教えてください。具体的に使いたい機能（例: ETL スケジューリング、監査ログの活用、OpenAI 呼び出しのテスト方法など）を挙げていただければ、利用例や運用ガイドを追記します。