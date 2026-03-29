# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants、kabuステーション、OpenAI／LLM、RSS ニュースなどを組み合わせて
- データ ETL（株価・財務・市場カレンダー）
- ニュース NLP による銘柄センチメント算出
- 市場レジーム判定（MA + マクロニュース）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 研究用ファクター計算・特徴量探索
などを提供します。

バージョン: 0.1.0

---

## 主な機能（機能一覧）

- data:
  - J-Quants API クライアント（差分取得・ページネーション・レート制御・リトライ・ID トークン自動更新）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 収集、SSRF 対策、前処理、冪等保存）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化・DB 操作ユーティリティ（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai:
  - ニュース NLP による銘柄センチメント算出（score_news）
  - 市場レジーム判定（ETF MA200 乖離 + マクロニュース LLM を合成する score_regime）
  - OpenAI (gpt-4o-mini) を JSON mode で利用（リトライ・パース保護あり）
- research:
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
- config:
  - 環境変数の自動読み込み（.env / .env.local、自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
  - settings オブジェクトで設定値を提供（paths・API トークン・環境種別等）

---

## 前提（Prerequisites）

- Python 3.10+
- duckdb（Python パッケージ）
- OpenAI Python SDK（OpenAI を使う機能を使う場合）
- ネットワークアクセス（J-Quants API、RSS、OpenAI など）
- 必要な環境変数（下記参照）

パッケージ依存はプロジェクトの packaging / requirements に従ってインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン（またはプロジェクトを取得）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 開発パッケージをインストール
   - setuptools / pyproject 指定がある場合は
     ```
     pip install -e .
     ```
   - もしくは requirements を指定している場合はそれに従ってください。
   - 主要依存例:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数を設定
   - プロジェクトルート（pyproject.toml または .git がある階層）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。
   - 必須（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot Token
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意（OpenAI を使う場合は必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に引数で渡すことも可能）
   - その他
     - KABUSYS_ENV — environment: development / paper_trading / live（既定: development）
     - LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
     - DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

---

## 使い方（基本的な例）

以下はライブラリを使った代表的な操作例です。DuckDB 接続は duckdb.connect() で作成します。

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 個別 ETL ジョブ（株価のみ）を実行
  ```python
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  print(f"fetched={fetched}, saved={saved}")
  ```

- ニュース NLP スコアリング（OpenAI API キーは引数または環境変数で指定）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"scored {n} symbols")
  ```

- 市場レジーム判定（1321 の MA200 とマクロニュースを組み合わせる）
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査ログ用 DuckDB を初期化してスキーマを作る
  ```python
  from kabusys.data.audit import init_audit_db, init_audit_schema

  # ファイルベース DB を作成してスキーマ初期化
  audit_conn = init_audit_db("data/audit.duckdb")
  # あるいは既存接続に対してスキーマを追加
  # init_audit_schema(conn, transactional=True)
  ```

- market calendar の夜間更新ジョブを手動で実行
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  calendar_update_job(conn)
  ```

注意点:
- ほとんどの関数は「内部で datetime.today() を参照しない」設計になっています（引数で target_date を渡す）ため、バックテストや再実行時にルックアヘッドバイアスを避けられます。
- OpenAI 呼び出しや外部 API 呼び出しはリトライ・フェイルセーフ設計です。API の失敗時はゼロ値にフォールバックする場合があります（例: macro_sentiment=0）。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack ボットトークン（Slack 通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

OpenAI 関連:
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に指定可能）

その他:
- KABUSYS_ENV — development / paper_trading / live（既定: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、既定 INFO）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（既定 data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（既定 data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するには 1 を設定

設定は .env/.env.local から自動ロードされます（プロジェクトルートを自動検出）。テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ログと実行モード

- KABUSYS_ENV によって実行環境を区別（development / paper_trading / live）
  - settings.is_live / is_paper / is_dev で判定可能
- LOG_LEVEL でログ出力レベルを制御
- OpenAI・J-Quants 等の外部 API 呼び出しは失敗時にログを出力します。運用時は監視設定（Slack 通知等）を組み合わせてください。

---

## ディレクトリ構成（主なファイルと説明）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py — パッケージメタ情報（__version__）
  - config.py — 環境変数 / 設定のロードと settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 含む）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py — RSS ニュース収集と前処理
    - quality.py — データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログテーブル定義・初期化（init_audit_schema, init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - monitoring / execution / strategy 等（パッケージ公開に含まれている可能性あり）

各モジュールはドキュメント文字列と設計方針が詳細に記載されており、安全性（SSRF 防止、JSON パース耐性、リトライ、冪等性）やルックアヘッドバイアス対策を考慮した実装です。

---

## 運用上の注意

- OpenAI や J-Quants の使用は API コスト・レート制限に注意してください（モジュールでレート制御やリトライを行っていますが、過剰な同時実行は避けること）。
- DuckDB ファイルは適切にバックアップしてください。監査ログは削除しない設計を想定しています。
- 本ライブラリは取引執行の一助を担いますが、実際のライブ発注時は必ず十分な検証・リスク管理を行ってください（設定 KABUSYS_ENV=live のときのみ実取引機能を有効にする等の運用を推奨します）。

---

## 貢献・開発

バグ報告や機能追加は Issue を立ててください。コントリビュートの際はスタイル・テスト方針に従い、重要な変更はドキュメントと互換性に配慮してください。

---

以上がこのリポジトリの README です。必要であれば、具体的なコマンド例や .env.example のテンプレート、CI / デプロイ方法、より詳細な API リファレンスを追加できます。どの情報を追記しましょうか？