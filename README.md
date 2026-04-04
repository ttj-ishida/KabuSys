# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、品質チェック、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株に関するデータパイプラインと研究・自動売買基盤の共通ライブラリ群を提供します。主な目的は以下です。

- J-Quants API からのデータ取得（株価日足、財務、JPXカレンダー）
- ETL（差分取得／バックフィル）と品質チェック
- ニュース収集（RSS）と LLM を用いた銘柄別センチメント評価
- 市場レジーム判定（ETF + マクロニュースの合成）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用スキーマ
- DuckDB を想定したローカル DB 連携

設計上の特徴:
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() を盲目的に参照しない設計
- LLM / 外部 API はリトライ / フェイルセーフ実装
- DuckDB を主要な永続化先として想定、冪等保存を重視

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、Settings クラス）
- J-Quants クライアント
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - get_id_token (refresh)
- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - ETLResult データクラス
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェック
- ニュース収集
  - RSS フィードの取得、前処理、raw_news への保存支援
  - SSRF 対策や受信サイズ制限など安全対策実装
- ニュース NLP / LLM
  - score_news: 銘柄ごとのセンチメントを ai_scores に書き込む
  - score_regime: ETF 1321 の MA とマクロニュースを組み合わせて市場レジーム判定
- 研究用モジュール
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- 監査ログスキーマ
  - signal_events / order_requests / executions の作成・初期化ユーティリティ
  - init_audit_schema / init_audit_db

---

## セットアップ手順

※ Python 3.10+ を想定しています（型ヒントで | が使われています）。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成と有効化
   - Linux / macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール
   開発用の pyproject/setup があれば `pip install -e .` を推奨します。ない場合は最低限必要な外部ライブラリをインストールしてください。
   ```
   pip install duckdb openai defusedxml
   ```
   （実行環境に応じて追加で logging 設定や DB ドライバを入れてください）

4. 環境変数の設定
   プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（CWD ではなくパッケージファイル位置から .git / pyproject.toml を基準に検出）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（発注連携がある場合）
   - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知連携（任意）
   - DUCKDB_PATH: デフォルト data/kabusys.duckdb
   - SQLITE_PATH: 監視用 SQLite (data/monitoring.db)
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   例 .env の抜粋:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=~/data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（サンプル）

以下は典型的な利用例です。実行前に必要なテーブルスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily など）を用意してください（ETL / schema 初期化機能は各自実装・管理）。

- DuckDB 接続を作成して日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI キーは OPENAI_API_KEY 環境変数または api_key に直接指定）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成される
  ```

- 設定値取得:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

テスト時のヒント:
- LLM 呼び出しは内部で独立関数（例: kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api）に集約されています。unittest.mock.patch で差し替えてテストできます。
- 自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

主要なファイル／モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API client + DuckDB 保存
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult 公開（簡易）
    - stats.py                     — 汎用統計（zscore_normalize）
    - quality.py                   — 品質チェック（missing/spike/duplicates/...）
    - calendar_management.py       — カレンダー判定・更新ロジック
    - news_collector.py            — RSS 取得・前処理・保存支援
    - audit.py                     — 監査スキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py           — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py       — forward returns / IC / summary / rank

各モジュールは DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を引数として受け、DB 操作と計算を実行します。外部 API（OpenAI / J-Quants）呼び出しはそれぞれ専用のモジュールで管理されています。

---

## 注意事項 / 運用上のポイント

- OpenAI / J-Quants API キーは安全に管理してください。テストや CI ではモック化を推奨します。
- run_daily_etl や ETL 周りは部分失敗時に他のデータを破壊しないよう設計されていますが、運用ではバックアップやバージョニングを行ってください。
- DuckDB のバージョン差異（executemany の空リスト扱い等）に注意していますが、運用環境での動作確認を必ず行ってください。
- ニュース収集は外部 RSS に依存するため、SSRF 対策やレスポンスサイズ上限などの安全策が実装されています。ただし実運用ではフィードソースのメンテナンスが必要です。
- KABUSYS_ENV を適切に設定し、本番（live）モードでは十分な検証を行ってください。

---

この README はコードベースの主要機能と利用手順を簡潔にまとめたものです。詳細は各モジュールの docstring を参照してください（src/kabusys/** の各ファイルに説明があります）。必要であれば、運用ガイドや API リファレンスの別資料を作成できます。