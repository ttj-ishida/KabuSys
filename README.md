# KabuSys

日本株向け自動売買／データプラットフォーム（KabuSys）のリポジトリ用 README。  
本ドキュメントはプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ収集・品質管理・リサーチ・AI評価・監査ログ・自動売買のためのモジュール群を提供する Python パッケージです。主な設計方針は以下の通りです。

- DuckDB をデータストアとして利用（ローカル ETL、分析用）
- J-Quants API からの差分取得（レート制限・再試行・トークン自動リフレッシュ対応）
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメント評価
- 市場レジーム判定（ETF の移動平均乖離 + マクロニュースの LLM 評価）
- ファクター計算・特徴量探索・IC 等の研究ユーティリティ
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマと初期化ロジック
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 自動環境変数ロード（プロジェクトルートの .env / .env.local から）

設計ではバックテスト等での look-ahead bias を避けるため、内部で `date.today()` や `datetime.today()` を直接参照しないよう配慮されています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API からの取得・DuckDB への保存（差分・ページネーション・リトライ・レート制御）
  - pipeline: 日次 ETL（カレンダー、株価、財務）の実行と品質チェック
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
  - news_collector: RSS 取得・前処理・SSRF 対策・冪等保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ定義と DB 初期化ユーティリティ（監査用 DuckDB）
  - stats: Zスコア正規化などの統計ユーティリティ

- ai
  - news_nlp: ニュースを LLM（OpenAI）でスコアリングして ai_scores に書き込む
  - regime_detector: ETF (1321) の MA200 乖離とマクロニュース LLM スコアを合成して市場レジームを判定

- research
  - factor_research: Momentum / Volatility / Value 等のファクター算出
  - feature_exploration: 将来リターン計算、IC、統計サマリーなど

- config
  - 環境変数管理（.env 自動ロード、必須チェック、各種パス・閾値設定）

その他、monitoring / execution / strategy 等のパッケージ境界が想定されています（パッケージ __init__ にて公開）。

---

## セットアップ手順

前提：
- Python 3.10 以上（ソース内で `X | Y` 型ヒントを使用）
- ネットワーク接続（J-Quants/API, OpenAI）, DuckDB を利用可能な環境

1. リポジトリをクローン
   ```bash
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 必要パッケージのインストール（最低限の例）
   - 代表的に必要なパッケージ：duckdb, openai, defusedxml
   ```bash
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   ```
   ※プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。

4. 開発インストール（パッケージが pyproject.toml に基づく場合）
   ```bash
   pip install -e .
   ```

5. 環境変数の設定
   - プロジェクトルートの `.env` または `.env.local` に設定するか、OS 環境変数として設定します。
   - 自動ロードはデフォルトで有効。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi (任意)
   - OPENAI_API_KEY=sk-...
   - LINE_CHANNEL_ACCESS_TOKEN=（通知用、任意）
   - LINE_USER_ID=（通知用、任意）
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   参考：config.Settings で必須項目はチェックされ、未設定時にエラーが出ます（例：JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須プロパティとして参照されることがあります）。

6. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（基本例）

以下は各主要機能の利用例です。実行には事前に環境変数（特に API キー）を設定してください。

- DuckDB 接続を作る（例）
  ```python
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect('data/kabusys.duckdb')
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアの実行（OpenAI API 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect('data/kabusys.duckdb')
  count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env の OPENAI_API_KEY を使用
  print(f"scored {count} codes")
  ```

- 市場レジームの計算
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db('data/audit.duckdb')
  ```

- J-Quants のデータ取得を個別に呼ぶ（テスト／デバッグ用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
  ```

注意点:
- OpenAI 的な呼び出しはレスポンスバリデーションやリトライ処理が組み込まれています。ユニットテストではモック（例: unittest.mock.patch）による差し替えを想定しています。
- ETL の run_daily_etl は内部でカレンダー調整を行い、look-ahead を防ぐように設計されています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行監視用ファイル設定
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル (DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効にする

config.py の Settings クラスを参照すると詳細が確認できます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル・モジュール構成です（主要ファイルのみ抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数・設定管理（.env 自動読み込み等）
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュースの LLM スコアリングと ai_scores 書込
    - regime_detector.py                — ETF MA200 と マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（取得・保存・認証）
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - etl.py                            — ETLResult の再エクスポート
    - calendar_management.py            — 市場カレンダー管理と営業日ユーティリティ
    - news_collector.py                 — RSS 取得・前処理・SSRF 対策
    - quality.py                        — データ品質チェック
    - stats.py                          — 統計ユーティリティ（Zスコア等）
    - audit.py                          — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py                — Momentum / Volatility / Value 等のファクター算出
    - feature_exploration.py            — 将来リターン・IC・統計サマリー
  - (その他) strategy / execution / monitoring などの名前空間が __all__ に含まれる想定

---

## 運用上の注意・設計上のポイント

- Look-ahead bias 防止:
  - スコアリングや ETL では内部で現在時刻を盲目的に参照せず、明示的な target_date を渡す設計です。バッチ処理では target_date を明示してください。
- 冪等性:
  - J-Quants の保存処理や監査スキーマ初期化は冪等に設計されています（ON CONFLICT / INSERT 等）。
- OpenAI 依存:
  - news_nlp と regime_detector は OpenAI API（gpt-4o-mini を想定）を使います。テストでは API 呼び出し関数をモックすることが推奨されています。
- セキュリティ:
  - news_collector は SSRF 対策、XML パーサの防御（defusedxml）などを実装しています。
- レート制限:
  - J-Quants クライアントはレート制限（120 req/min）を守る実装になっています。

---

## テスト・開発ヒント

- OpenAI 呼び出しはモジュール内部で分離されているため、unittest.mock.patch によるモックが容易です（例: kabusys.ai.news_nlp._call_openai_api）。
- DuckDB はインメモリ接続（":memory:"）もサポートしているため単体テストでの利用が簡単です。
- .env の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定します。

---

必要に応じて README をプロジェクトの実際の pyproject.toml / requirements.txt に合わせて補正してください。追加で「インストール手順の詳細」「運用 (systemd / supervisor) 用サンプル」「.env.example のテンプレート」などを作成することも可能です。必要であればその点も作成します。