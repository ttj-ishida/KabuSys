# KabuSys

日本株向けの自動売買プラットフォーム（データパイプライン・リサーチ・AIセンチメント・監査ログを含む）  
このリポジトリはデータ収集（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター算出、ETL、データ品質チェック、監査ログ（約定トレース）などの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けの基盤ライブラリ群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー取得（差分ETL と保存）
- RSS ベースのニュース収集と前処理（安全対策付き）
- OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score）および市場レジーム判定
- ファクター計算（Momentum / Value / Volatility 等）と探索機能（Forward returns / IC / summary）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査（signal → order_request → execution）用テーブルと初期化ユーティリティ
- DuckDB を中心としたオンプレ/ローカル DB 管理

設計方針として「バックテスト時のルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API障害時の継続）」を重視しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証、自動リトライ、ページネーション、保存）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS、安全対策、正規化、raw_news への保存）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化（audit スキーマ、init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores へ書込
  - regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュースを融合して市場レジーム判定
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - .env / 環境変数の自動読み込み（プロジェクトルート基準）と設定ラッパー（settings）

---

## 必要条件（推奨）

- Python 3.10+
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（ai モジュールを利用する場合）
- defusedxml（RSS パースの安全化）
- 標準ライブラリ（urllib, datetime 等）

最低限の Python パッケージ例:
- duckdb
- openai
- defusedxml

pip 例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発時: pip install -e . など
```

（プロジェクトに pyproject.toml がある場合は pip install -e . を利用してください）

---

## 環境変数（主なもの）

パッケージはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須/重要な環境変数（用途含む）:

- JQUANTS_REFRESH_TOKEN  
  - J-Quants のリフレッシュトークン（必須、ETL で使用）
- OPENAI_API_KEY  
  - OpenAI の API キー（AI モジュールを使う場合、score_news / score_regime で使用）
- KABU_API_PASSWORD  
  - kabuステーション API のパスワード（発注を行う場合）
- KABU_API_BASE_URL  
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID  
  - LINE 通知用（任意）
- DUCKDB_PATH  
  - デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH  
  - 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE  
  - Paper trading のフィルモード（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH  
  - Paper trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START  
  - 実行監視関連
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT  
  - 監視の閾値（パーセント）
- KABUSYS_ENV  
  - 実行モード（development | paper_trading | live）
- LOG_LEVEL  
  - ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

簡易 `.env.example`:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存インストール
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトの依存ファイルがあれば pip install -r requirements.txt
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` を作成（上の example を参照）
   - もしくは OS 環境変数として設定

5. DuckDB 初期化（任意: 監査DB作成）
   Python REPL で:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # もしくは ":memory:" でインメモリ
   ```

---

## 使い方（主要ユーティリティの呼び出し例）

以下は Python から直接利用する場合の簡易例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の返り値）を受け取ります。

- DuckDB 接続の作成:
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア生成（ai/news_nlp.score_news）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written codes:", n_written)
  # OPENAI_API_KEY は環境変数か api_key 引数で指定できます
  ```

- 市場レジーム判定（ai/regime_detector.score_regime）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- カレンダー更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn, lookahead_days=90)
  ```

- 監査DB 初期化（別 DB として）:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

注意:
- AI モジュールを使用する際は `OPENAI_API_KEY` が必要です（引数で直接渡すことも可能）。
- ETL は外部 API（J-Quants）を呼ぶため `JQUANTS_REFRESH_TOKEN` の設定が必要です。
- 関数は例外やログで障害情報を出す設計です。ログレベルを適宜設定してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # ニュースセンチメント（銘柄別）
    - regime_detector.py   # マクロ + ETF MA で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント（取得・保存）
    - pipeline.py          # ETL パイプライン（run_daily_etl など）
    - calendar_management.py
    - news_collector.py    # RSS 収集・前処理・安全対策
    - quality.py           # データ品質チェック
    - audit.py             # 監査テーブル定義 / 初期化
    - stats.py             # zscore_normalize 等の統計ユーティリティ
    - etl.py               # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py   # Momentum/Value/Volatility
    - feature_exploration.py # forward returns, IC, summary, rank
  - research/*（関数群）
  - その他モジュール（strategy/execution/monitoring 等は __all__ に含まれることを想定）

※ 実際のファイル構成はリポジトリのトップディレクトリを参照してください。

---

## 実装上の注意 / 補足

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml の存在を探索）を基準に行います。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- AI 周り（news_nlp, regime_detector）は OpenAI の JSON mode を使う想定でレスポンスのバリデーションやリトライを行います。API 障害時はフォールバック（スコア 0）で継続する設計です。
- J-Quants クライアントはレート制御・トークン自動リフレッシュ・指数バックオフを実装しています。
- データベース操作は DuckDB を使い、保存処理は冪等（ON CONFLICT）を利用しています。
- テストしやすさのため、外部呼び出し（OpenAI 呼び出しや HTTP）を差し替え可能な内部関数を用意しています（unittest.mock.patch 等でモック可能）。

---

## 開発 / 貢献

- コードの理解には各モジュール内の docstring を参照してください。多くの関数は「設計方針」「処理フロー」「返り値」を明記しています。
- 新しい機能追加やバグ修正はブランチを切って Pull Request を送ってください。CI / テストがあればそれに従ってください。

---

必要であれば README にサンプル .env ファイル、より詳細な使用例（CLI スクリプトや systemd ユニットの例）、DB スキーマ一覧などを追加します。どの追加情報が必要か教えてください。