# KabuSys

日本株向け自動売買 / データ基盤ユーティリティ群（KabuSys）

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質チェック・特徴量生成・ニュース NLP（LLM）評価・市場レジーム判定・監査ログ初期化など、アルゴリズムトレーディングの基盤処理を集めた Python パッケージです。  
主に以下の責務を持ちます。

- J-Quants API を用いた株価 / 財務 / カレンダーの ETL パイプライン
- ニュース収集・前処理・LLM による銘柄センチメントスコア付与
- 市場レジーム判定（ETF + マクロニュースセンチメントの合成）
- ファクター計算・特徴量解析（研究用途）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order → execution）用の DB 初期化とスキーマ
- 環境変数管理（.env 自動読み込み、設定クラス）

設計面では「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API障害時の安全なフォールバック）」「DuckDB を用いたローカル永続化」を重視しています。

---

## 主な機能一覧

- データ取得 / 保存（J-Quants API）
  - 日足（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダー
  - ページネーション、レート制御、リトライ、401 自動リフレッシュ対応
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックの一括実行（run_daily_etl）
- ニュース収集・NLP
  - RSS 取得・前処理（URL除去・正規化・SSRF対策）
  - OpenAI（gpt-4o-mini）を用いた銘柄センチメント付与（score_news）
  - マクロセンチメント + ETF MA乖離から市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
- 監査ログスキーマ初期化
  - signal_events / order_requests / executions テーブルと索引を作成
  - init_audit_db で DuckDB を初期化

---

## 必要条件

- Python 3.10 以上（`|` 型アノテーション、PEP 604 等を使用）
- 推奨ライブラリ（一例）:
  - duckdb
  - openai
  - defusedxml

実行環境によっては追加で標準ライブラリ以外のパッケージ（requests 等）は不要ですが、上記は少なくとも必要になります。

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化（任意だが推奨）
   - Unix/macOS:
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
   例（最小限）:
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください：
   ```
   pip install -e .
   # または
   pip install -r requirements.txt
   ```

4. 環境変数 (.env)
   - プロジェクトルートの .env / .env.local を自動的に読み込みます（デフォルト）。
     読み込み順: OS 環境変数 > .env.local > .env
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
     - KABU_API_PASSWORD : kabu API （kabuステーション）パスワード
     - OPENAI_API_KEY : OpenAI API キー（score_news / regime_detector 呼び出し時に未指定なら参照）
   - 任意・設定可能
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

---

## 使い方（基本例）

以下はライブラリの主要な呼び出し例です。詳細は各モジュールの docstring を参照してください。

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続を使った日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア付与（OpenAI API を使用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定しておく
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  print("score_regime result:", res)
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)  # :memory: も可
  ```

- 研究用ファクター計算例
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意事項:
- OpenAI を使う関数（score_news / score_regime）は API 呼び出しの失敗時にフェイルセーフ動作（デフォルトスコアなど）を行いますが、APIキーの設定がないと ValueError を出します。
- ETL / データ更新は DuckDB のテーブル構造と既存スキーマを前提としています。必要なテーブルがない場合の動作は各関数の docstring を確認してください。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント・保存ロジック
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL 型再エクスポート（ETLResult）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック
    - calendar_management.py  — 市場カレンダー管理（営業日判定等）
    - news_collector.py       — RSS 取得・前処理
    - audit.py                — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - ai/ (上記) etc.

各モジュールは docstring に設計方針や処理フローが詳細に記載されています。内部動作や SQL ロジック、例外扱いの挙動は各ファイルのコメントと docstring を参照してください。

---

## 実運用 / 注意点

- 環境変数の管理 (.env) は自動読み込みされます。機密情報（API キー等）は安全に管理してください。
- OpenAI・J-Quants API 呼び出しは料金やレート制限があるため、必要に応じてテスト用キーやモックを利用してください。テスト用には各モジュール内で API 呼び出し関数をモックできる設計になっています（例: unittest.mock.patch）。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に保存されます。バックアップやローテートを検討してください。
- 時刻・タイムゾーン: 監査ログ等では UTC を使用します。news window や RSS 処理では UTC naive datetime を前提に設計されています（docstring を確認）。

---

必要であれば README に実際の .env.example の雛形、より詳しい API の使い方、運用時の実行スクリプト例（systemd / cron / Airflow）なども追加できます。追加希望があれば教えてください。