# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォームのためのライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を使用したセンチメント評価）、ファクター計算、監査ログ（発注〜約定のトレーサビリティ）など、アルゴリズムトレーディング基盤に必要な機能を提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（target_date を明示的に渡す形で実装）
- DuckDB をデータ格納エンジンとして利用
- 冪等性・フォールトトレランス重視（ON CONFLICT / ロールバック等）
- 外部 API 呼び出しはリトライ・レート制御を備える

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、上場銘柄情報、マーケットカレンダー）
  - 差分更新 / バックフィル対応の ETL パイプライン（run_daily_etl など）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（quality モジュール）
- ニュース収集
  - RSS からのニュース収集（SSRF 対策・トラッキングパラメータ除去等）
- LLM を用いたニュース NLP・市場レジーム判定
  - 銘柄別ニュースセンチメント（news_nlp.score_news）
  - マクロセンチメント + ETF MA 乖離の合成による市場レジーム判定（regime_detector.score_regime）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリーなど
- 監査ログ（Audit）
  - シグナル→発注→約定までの監査テーブル定義と初期化ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理
  - .env / 環境変数から設定を自動読み込み（kabusys.config.Settings）

---

## 必要条件

- Python 3.10+
- 必要なライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI など）

（実際の依存パッケージはプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   - もし requirements.txt / pyproject.toml があればそれを使う
   ```bash
   pip install -r requirements.txt
   # または
   pip install duckdb openai defusedxml
   ```

4. 環境変数（.env）を用意  
   プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_station_password
   OPENAI_API_KEY=sk-xxxx...       # LLM 連携を使う場合
   KABUSYS_ENV=development         # development | paper_trading | live
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   任意:
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
   - LOG_LEVEL（DEBUG/INFO/...）
   - PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値（監視用）

---

## 基本的な使い方（コード例）

読み込み例（Python コンソールやスクリプト）:

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアを取得して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う場合 None
  print("written", written)
  ```

- 市場レジーム判定を行う
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB を初期化する（監査用 DuckDB ファイルを作る）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続。テーブルが作成される。
  ```

- J-Quants から株価を直接フェッチする（テスト等）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
  ```

注意:
- LLM（OpenAI）を利用する関数は `api_key` 引数で明示的にキーを渡すか、環境変数 `OPENAI_API_KEY` をセットしてください。
- ETL / 保存処理は対象テーブル（raw_prices 等）のスキーマが存在することが前提です。最初のテーブル作成は別途スキーマ初期化スクリプトで実行してください（監査ログは audit.init_audit_db で初期化できます）。

---

## 環境変数（主要）

kabusys.config.Settings で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。OS 環境変数が優先され、`.env.local` は `.env` 上書きします。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュール（抜粋）です。

- kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメント（OpenAI 呼び出し、バッチ処理）
    - regime_detector.py   — ETF MA + マクロセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント + DuckDB 保存ユーティリティ
    - pipeline.py          — ETL パイプライン / run_daily_etl 等
    - etl.py               — ETL 公開インターフェース (ETLResult 再エクスポート)
    - news_collector.py    — RSS ニュース収集（SSRF 対策等）
    - quality.py           — データ品質チェック
    - calendar_management.py — マーケットカレンダー管理
    - stats.py             — z-score 正規化など統計ユーティリティ
    - audit.py             — 監査ログ（テーブル定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py   — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — IC, forward returns, factor_summary 等

---

## 開発・運用上の注意

- DuckDB のスキーマ（raw_prices / raw_financials / market_calendar / ai_scores 等）は ETL 側で前提とされています。初期スキーマ作成は本リポジトリに含まれる migration / schema 初期化スクリプト（存在する場合）を利用してください。監査ログは `init_audit_db` で初期化可能です。
- OpenAI / J-Quants 呼び出し時はレート制御とリトライロジックが入っていますが、API 使用量・コストは運用者が管理してください。
- 本ライブラリはバックテストやライブ売買に使う前に十分な検証（特に発注・監査部分）を行ってください。
- 設定ミスや未設定の必須環境変数は ValueError などで明示されます。CI / デプロイ時に .env を適切に設定してください。

---

必要であれば README に実行コマンド例（systemd ジョブ / cron / Airflow などでの運用方法）、初期スキーマ SQL、あるいは requirements.txt の内容を追加します。どの情報を追加しますか？