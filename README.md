# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL、ニュースNLP、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログなどを提供します。

> 本 README はソースツリー（src/kabusys 以下）に基づいて作成しています。

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・特徴量生成・AI によるニュースセンチメント評価・市場レジーム判定・監査ログ管理などを行うためのモジュール群です。  
主に次の用途を想定しています。

- J-Quants API から株価/財務/カレンダーを取得して DuckDB に格納する ETL パイプライン
- RSS ニュース収集と OpenAI を使った銘柄ごとの NLP スコアリング
- ETF（1321）の MA とマクロニュースを組み合わせた市場レジーム判定
- リサーチ用のファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 発注～約定に向けた監査ログスキーマ生成・初期化

設計上の特徴:
- DuckDB を用いたローカルデータベース中心の実装
- Look-ahead bias 防止（内部で date.today() に依存しない設計の関数が多数）
- API 呼び出しに対するリトライ / バックオフ / レート制御を実装
- OpenAI（gpt-4o-mini）を JSON mode で利用するインタフェースを実装
- .env 自動ロード（プロジェクトルートの .env/.env.local）をサポート

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch/save 日足・財務・カレンダー）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / get_trading_days）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - ニュース収集（RSS -> raw_news）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコア（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC・統計サマリー（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数管理（.env 自動ロード、Settings クラス）

## セットアップ手順

前提
- Python 3.10 以上（ソースで `X | Y` 型ヒントを利用）
- DuckDB を使用（ローカルファイルに保存）

推奨手順（開発環境での例）

1. 仮想環境作成・有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. パッケージをインストール
   ソースから editable インストールする例:
   ```
   pip install -U pip setuptools
   pip install -e .
   ```
   主要な外部依存は（プロジェクトに requirements.txt がない場合の例）:
   ```
   pip install duckdb openai defusedxml
   ```
   （必要に応じて他パッケージを追加してください）

3. 環境変数の設定
   プロジェクトルートに `.env`（と必要なら `.env.local`）を作成します。自動ロードは既定で有効です（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

   主要な環境変数（必須に注意）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知用
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV : development / paper_trading / live （デフォルト development）
   - LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

   例 (`.env`):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. 自動 .env ロード
   - パッケージはインポート時にプロジェクトルート（.git または pyproject.toml のある親）を探索して `.env` / `.env.local` を読み込みます。
   - テスト時などで自動ロードを抑止する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

## 使い方（主要 API と実行例）

以下は Python REPL やスクリプトからの利用例です。`duckdb` は事前に pip インストールしてください。

- DuckDB 接続を作成し ETL を実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(database=str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアを取得して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(database=str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジーム判定を実行して market_regime テーブルに書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(database=str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)  # ":memory:" を渡すとインメモリ
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect(database="data/kabusys.duckdb")
  d = date(2026, 3, 20)
  mom = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  value = calc_value(conn, d)
  ```

注意点:
- score_news / score_regime は OpenAI API キー（OPENAI_API_KEY）を環境変数または関数引数で必要とします。
- 多くの関数は DuckDB の所定テーブル（raw_prices / raw_financials / raw_news / ai_scores / market_regime 等）を前提とします。ETL を通してテーブルを作成・整備してください。
- API 呼び出しはレート制限・リトライ・バックオフを実装していますが、実運用では鍵・レート計画に注意してください。

## ディレクトリ構成

主要なファイル/モジュールと簡単な説明:

- src/kabusys/
  - __init__.py  — パッケージ初期化（version 等）
  - config.py    — 環境変数 / Settings（.env 自動ロード、必須キー取得ユーティリティ）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの集約・OpenAI での銘柄別センチメント算出（score_news）
    - regime_detector.py — ETF MA と LLM マクロセンチメントを混合した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集 / 前処理 / raw_news への格納ユーティリティ
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック（missing / spike / duplicates / date_consistency）
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ用スキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランク関数
  - monitoring/ (パッケージ API へは含まれているが詳細はソース参照)
  - execution/, strategy/ (公開 API に含まれるが詳細実装は別ファイル群へ)

（上記は本コードベースに含まれる主要モジュールを抜粋したものです。実際のファイル一覧は src/kabusys 以下を参照してください。）

## 注意事項 / 運用上のヒント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml がある親）を基準に行います。テスト環境で挙動を固定したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出しは外部サービス依存です。API キーの管理・利用量の監視を行ってください。API エラー時はフェイルセーフとして 0.0 を返すロジックを多くの箇所で採用しています（ログは出ます）。
- DuckDB スキーマは ETL や init_audit_schema を通じて作成されます。バックテストや研究を行う場合はデータ取得タイミング（fetched_at 等）に注意して Look-ahead bias を避けてください。
- 実運用で発注処理を組み込む際は audit テーブルや order_requests の冪等キー（order_request_id）を必ず利用してください。

---

この README はソースコードのドキュメント化を目的として作成しています。追加の利用例やインストール手順（CI/CD、Docker 化、より詳細な依存関係管理等）が必要であれば、その要件に合わせて追記できます。