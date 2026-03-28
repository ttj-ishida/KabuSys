# KabuSys

KabuSys は日本株のデータパイプライン、AI ベースのニュースセンチメント評価、ファクター研究、監査ログ、および市場レジーム判定を含む自動売買／リサーチ基盤ライブラリです。DuckDB をデータ層に使い、J-Quants や RSS、OpenAI（gpt-4o-mini 等）を利用してデータ取得・スコアリング・解析を行います。

---

## プロジェクト概要

主な目的：
- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存（ETL）
- RSS ベースのニュース収集と LLM による銘柄ごとのニュースセンチメント評価
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティなど）
- 市場全体のレジーム（bull / neutral / bear）判定（ETF + マクロニュース）
- 発注・約定のトレーサビリティを保証する監査ログスキーマ
- 品質チェック（欠損・重複・スパイク・日付不整合）

設計上の特徴：
- ルックアヘッドバイアスに配慮（date.today() 等に依存しない設計）
- DuckDB + SQL ベースで高効率に処理
- 冪等性（INSERT の ON CONFLICT/UPDATE、ETL の差分取得）
- フェイルセーフ（API 失敗時は部分的に継続する・安全なデフォルト）

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl（市場カレンダー / 株価 / 財務 の差分 ETL）
  - J-Quants クライアント（fetch / save / トークンリフレッシュ / レート制限）
- ニュース関連
  - RSS 収集（SSRF・gzip・トラッキング除去・記事ID生成）
  - news_nlp.score_news：銘柄ごとのニュースセンチメントを OpenAI により算出し ai_scores に保存
- AI / レジーム判定
  - ai.regime_detector.score_regime：ETF（1321）MA とマクロニュースを合成して市場レジーム判定
  - ai.news_nlp.score_news：銘柄ごとのニュースセンチメント算出
- リサーチ
  - research.factor_research：mom / value / volatility 等のファクター計算
  - research.feature_exploration：将来リターン計算、IC、統計サマリー
  - data.stats.zscore_normalize：Zスコア正規化ユーティリティ
- データ品質・カレンダー
  - data.quality：欠損・スパイク・重複・日付不整合チェック
  - data.calendar_management：市場カレンダー取得・営業日判定ヘルパー
- 監査ログ
  - data.audit.init_audit_db / init_audit_schema：監査ログ用 DuckDB 初期化（signal / order_requests / executions）

---

## セットアップ手順

前提
- Python 3.10+（typing の一部で | を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリを取得
   - git clone ...（パッケージ配布方法に依存）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージのインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 最低限必要なパッケージ（例）:
     - pip install duckdb openai defusedxml

   （注）本コードベースでは OpenAI SDK と duckdb、defusedxml などを使用します。利用する環境に合わせて適切なバージョンをインストールしてください。

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（設定は kabusys.config.Settings で参照）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（例と説明）
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabu API パスワード（発注系を使う場合）
   - SLACK_BOT_TOKEN       : Slack 通知（必要なら）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（必要なら）
   - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector を動かす場合）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite（monitoring 用、デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : application environment（development / paper_trading / live）、デフォルト development
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）, デフォルト INFO

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（サンプル）

以下は Python スクリプトや REPL からの呼び出し例です。

- DuckDB 接続を用意して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（news_nlp）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（regime_detector）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以後 conn を使用して監査テーブルにアクセスできます
  ```

- 設定値参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点：
- OpenAI 呼び出しは API レートやコストに注意してください。テスト時は _call_openai_api をモック可能です。
- J-Quants 呼び出しは rate limit やトークンのリフレッシュ処理を内部で行います。JQUANTS_REFRESH_TOKEN を設定してください。
- ETL / スコアリング関数はルックアヘッドバイアス回避のため target_date に厳密に依存します。バックテスト用途では日付管理に注意してください。

---

## よくあるトラブルと対処

- ValueError: OpenAI API キーが未設定
  - OPENAI_API_KEY を環境変数に設定するか、関数の api_key 引数で渡してください。

- ValueError: 環境変数 'JQUANTS_REFRESH_TOKEN' が設定されていません
  - .env を作成して JQUANTS_REFRESH_TOKEN を設定してください。

- .env が読み込まれない
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml 基準）を探索します。
  - テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- DuckDB にテーブルが無い・スキーマエラー
  - ETL 実行や audit.init_audit_db で必要なスキーマを作成するか、初期化関数を使用してください。

---

## ディレクトリ構成

主要ファイル / モジュールの概観（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースの LLM スコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py                  — ETL メインロジック（run_daily_etl 等）
    - etl.py                       — ETLResult の公開（エイリアス）
    - news_collector.py            — RSS 収集・記事前処理
    - calendar_management.py       — マーケットカレンダー管理・営業日判定
    - quality.py                   — 品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログ定義・初期化（signal/order_requests/executions）
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー / rank
  - (その他)
    - monitoring / execution / strategy / ... (パッケージ API を __all__ で公開)

（ソース内に詳細な docstring と設計方針が含まれているため、具体的な挙動は各モジュールのドキュメントをご参照ください）

---

必要であれば README に以下を追加可能です：
- 開発向けのテスト実行方法 / CI 設定
- 具体的な DuckDB テーブル定義（スキーマ）
- サンプル .env.example の完全版
- デプロイ手順（Cron / Airflow 等でのジョブ設定）

ご希望があれば上記の追加ドキュメントを作成します。