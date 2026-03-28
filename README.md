# KabuSys

日本株自動売買・データ基盤ライブラリ KabuSys のコードベース README。

概要、機能一覧、セットアップ手順、使い方（簡易サンプル）、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（LLM）評価、マーケットレジーム判定、監査ログ（オーダー／約定のトレーサビリティ）などを提供する内部ライブラリです。  
主に以下用途を想定しています：

- 日次 ETL パイプライン（株価・財務・カレンダーの差分取得・保存）
- ニュースを用いた銘柄ごとの NLP センチメント評価（OpenAI）
- マクロニュース＋ETF MA を使った市場レジーム判定
- ファクター計算・特徴量探索（Research 用）
- データ品質チェック
- 監査ログ（signal → order_request → execution）を DuckDB に保存するユーティリティ

設計上のポイント：
- DuckDB をコア DB として使用（軽量・ファイル保存／インメモリ対応）
- Look-ahead bias 回避（内部で date.today()/datetime.today() を不用意に参照しない設計）
- API 呼び出しはリトライ・バックオフ・レート制御を実装
- 冪等（idempotent）な DB 書き込みを優先

---

## 主な機能一覧

- data:
  - J-Quants API クライアント（fetch / save、ページネーション、トークン自動リフレッシュ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS パーサ、SSRF 対策、トラッキング除去）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化・DB 作成（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai:
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI 呼び出しは gpt-4o-mini を前提（JSON mode を利用）
- research:
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

---

## セットアップ手順

前提: Python 3.10+ を想定（typing 機能等を利用）。プロジェクトルートに移動して作業してください。

1. リポジトリをクローン（例）:
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（サンプル）:
   - 必要なパッケージ（主なもの）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

4. 環境変数（.env）を用意:
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（ただし自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルトあり:
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime は引数でも渡せます）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...

   - `.env` の例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. （任意）パッケージとしてインストール:
   ```
   pip install -e .
   ```
   （プロジェクトに pyproject.toml / setup.py がある場合）

---

## 使い方（簡易サンプル）

以下は Python スクリプトからの基本的な呼び出し例です。DuckDB 接続はパス文字列で接続を確立してください。

- 日次 ETL を実行する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で指定）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込み件数:", n_written)
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DuckDB を初期化して接続を得る:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 必要なら conn.execute(...) で監査テーブルにアクセス
  ```

- 市場カレンダー・ユーティリティ:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- OpenAI 呼び出しはモデル（gpt-4o-mini）と JSON Mode を想定しています。API エラー時はフェイルセーフ（0.0 スコアなど）で継続する実装が多くありますが、コストやレート制限に注意してください。
- J-Quants とのやり取りには rate limiter とリトライ機構が組み込まれています。ID トークンは自動更新されます。

---

## 設定項目（まとめ）

主に Settings クラスで取得される環境変数：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (オプション、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (OpenAI を使用する機能で必要)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

自動 .env ロード:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、`.env` と `.env.local` を読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他のデータ関連モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター計算、探索ツール）

各モジュールの役割：
- config.py: 環境変数読み込み・設定管理（Settings オブジェクト）
- data/jquants_client.py: J-Quants API との通信・保存ロジック
- data/pipeline.py: 日次 ETL パイプライン実装（run_daily_etl など）
- data/calendar_management.py: 市場カレンダー管理ユーティリティ
- data/news_collector.py: RSS 収集・前処理・raw_news 保存
- ai/news_nlp.py: 銘柄ニュースの LLM 集約スコア化（score_news）
- ai/regime_detector.py: ETF + マクロニュースから市場レジーム判定（score_regime）
- research/*: ファクター計算と評価ツール

---

## 注意・運用上の留意点

- API キー・シークレットは必ず安全に管理し、公開リポジトリに含めないでください。
- OpenAI や J-Quants のリクエストはコスト・レート制限があるため、バッチ設計やリトライポリシーに注意してください。
- DuckDB ファイルは用途に応じてバックアップ・ローテーションを検討してください。
- 本ライブラリはバックテストの内部ループから直接 API を呼び出すことを避ける設計方針（Look-ahead bias を防ぐ）です。バックテスト用途では事前にデータを ETL してから利用してください。

---

README は以上です。必要であれば「運用手順（cron / GitHub Actions での ETL 実行例）」「詳しい環境変数の .env.example」「CI 用のテスト実行方法」など追記できます。どの情報を優先して追加しますか？