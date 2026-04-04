# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants 経由の株価・財務・マーケットカレンダー取得）、ニュース収集と LLM によるニュース NLP、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）、および市場レジーム判定などのユーティリティ群を提供します。

主な設計方針：
- ルックアヘッドバイアスを起こさない（内部で date.today() や datetime.today() を不用意に参照しない）
- DuckDB を用いたローカル ETL / 分析基盤
- J-Quants / OpenAI 等の外部 API 呼び出しはリトライ・レートリミット・フェイルセーフを考慮
- 冪等性（DB 保存は ON CONFLICT / 挿入スキップ）と監査性を重視

バージョン: 0.1.0

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存：raw_prices / raw_financials / market_calendar 等）
  - ニュース収集（RSS 取得、前処理、raw_news / news_symbols 保存）
  - データ品質チェック（欠損、スパイク、重複、日付整合性）
  - カレンダー管理（営業日判定・next/prev_trading_day）
  - 監査ログスキーマ初期化 / 監査 DB ユーティリティ
  - 汎用統計ユーティリティ（zscore 正規化 等）
- ai
  - ニュース NLP（gpt-4o-mini を用いた銘柄ごとのセンチメントスコア化）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースセンチメントの合成）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索ユーティリティ（将来リターン計算 / IC / サマリー / ランク）

設計上の重要点：
- OpenAI 呼び出しは API キー引数 or 環境変数 `OPENAI_API_KEY` で解決
- J-Quants は `JQUANTS_REFRESH_TOKEN` を用いて id_token を取得
- .env 自動ロード機構あり（プロジェクトルートを .git または pyproject.toml で探索）
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## セットアップ手順

前提
- Python 3.10 以上推奨
- DuckDB を利用するためローカルディスクに保存領域が必要

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（最低限）
   - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそれを利用してください。

3. ソースをインストール（開発用）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を配置すると自動で読み込まれます。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxx...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な例）

以下は簡単な Python スニペット例です。実行前に環境変数（J-Quants と OpenAI のキー等）を設定してください。

- DuckDB 接続の用意
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（市場カレンダー、株価、財務を差分取得）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュース NLP（指定日分の記事をスコアリングして ai_scores テーブルへ保存）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（別 DB を使う場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn へ以後の監査ログ挿入を行える
  ```

- カレンダー関係ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  from datetime import date
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点：
- OpenAI 呼び出しは失敗時にフォールバック（スコアを 0 にする等）する実装になっていますが、API 呼び出し回数やコストにはご注意ください。
- ETL / 保存処理は DuckDB のテーブルスキーマ前提です。必要なテーブルが未作成の場合は別途スキーマ初期化が必要です（プロジェクトに schema 初期化用のスクリプトがあれば利用してください）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabu API のパスワード（execution モジュール等で使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用パス
- KABUSYS_ENV: environment (development | paper_trading | live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env ロードを無効化

設定が不足している場合（例: JQUANTS_REFRESH_TOKEN が未設定）は Settings プロパティが ValueError を投げます。

---

## ディレクトリ構成

以下はリポジトリ内の主要ファイルと役割（抜粋）です。パッケージは `src/kabusys` 配下に配置されています。

- src/kabusys/
  - __init__.py  (パッケージ初期化、__version__ 等)
  - config.py    (環境変数読み込み・Settings)
  - ai/
    - __init__.py
    - news_nlp.py         (ニュースの LLM スコアリング、ai_scores への書き込み)
    - regime_detector.py  (市場レジーム判定ロジック)
  - data/
    - __init__.py
    - calendar_management.py  (市場カレンダー管理、営業日判定)
    - etl.py (ETLResult 再エクスポート)
    - pipeline.py  (ETL パイプライン実装)
    - stats.py     (zscore_normalize 等統計ユーティリティ)
    - quality.py   (データ品質チェック)
    - audit.py     (監査ログスキーマ初期化 / audit DB ヘルパー)
    - jquants_client.py (J-Quants API クライアント + 保存関数)
    - news_collector.py  (RSS 収集・前処理・raw_news への保存)
  - research/
    - __init__.py
    - factor_research.py  (モメンタム・ボラティリティ・バリュー計算)
    - feature_exploration.py (forward returns, IC, factor summary, rank)
  - execution/ (発注ロジック等はここに配置想定)
  - monitoring/ (監視・プロセス管理用モジュール想定)
  - data/ (スクリプトから参照されるデータ保存先の既定パスは settings.duckdb_path 等)

（実際のファイルやサブモジュールはプロジェクト全体を参照してください。ここでは主要モジュールを抜粋しています。）

---

## 開発 / テストに関する注意

- モジュール内の外部 API 呼び出し（OpenAI / J-Quants / RSS ネットワーク等）はユニットテストではモックすることを推奨します。コード内にもテスト用に差し替えるための一部フック（例: _call_openai_api の差し替えポイント）が用意されています。
- DuckDB を用いた統合テストでは ":memory:" を渡すことでインメモリ DB を使用できます（data.audit.init_audit_db 等が対応）。
- .env の自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を使用するため、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか作業ディレクトリに注意してください。

---

## 付記（設計上の注記）

- look-ahead bias 回避のため、target_date ベースでの集計やウィンドウ計算を行い、内部で現在日時を参照しない実装方針が徹底されています。バックテストやリサーチで過去データのみを参照する場合は本設計の恩恵を受けられます。
- API キーやシークレットは適切に管理し、リポジトリに含めないでください。

---

必要に応じて README の Usage にサンプルスクリプトやスキーマ初期化手順（DuckDB テーブル定義）を追加できます。追加したい内容があれば教えてください。