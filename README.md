# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、データ品質チェック、特徴量 / 研究ユーティリティ、LLM を使ったニュース解析、監査ログ・発注周りのスキーマなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを支えるための内部ライブラリ群です。主に以下の役割を持ちます。

- J-Quants API からの株価・財務・カレンダー取得（差分 ETL、ページネーション、リトライ、レート制御）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去、前処理）
- OpenAI（gpt-4o-mini） を用いたニュースセンチメント / マクロレジーム判定
- DuckDB を用いた ETL パイプライン、品質チェック、統計ユーティリティ
- 監査ログ（signal → order_request → execution の追跡）のスキーマ初期化
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー等）と特徴量解析ユーティリティ

設計上、バックテストやフェイルセーフ（API障害時のフォールバック）、ルックアヘッドバイアス回避を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存関数、認証・レート制御・リトライ）
  - pipeline: 日次 ETL（run_daily_etl／run_prices_etl 等）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック
  - calendar_management: 市場カレンダーの判定（is_trading_day / next_trading_day 等）と更新ジョブ
  - quality: データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
  - audit: 監査ログテーブルの初期化（init_audit_schema / init_audit_db）
  - stats: z-score 正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント生成（OpenAI）
  - regime_detector.score_regime: マクロセンチメント＋ETF MA200乖離で市場レジーム判定（bull/neutral/bear）
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー計算
  - feature_exploration: 将来リターン計算、IC（情報係数）、統計サマリーなど
- config: 環境変数読み込み・設定管理（.env, .env.local 自動ロード、必須設定チェック）
- audit/schema: 監査テーブル DDL / インデックス

---

## 必要条件（依存関係）

主なランタイム依存（実際の setup.py/pyproject.toml で指定されるものを参照してください）:

- Python 3.9+
- duckdb
- openai
- defusedxml

（※ その他 urllib, json など標準ライブラリを使用）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化

   ```bash
   git clone <your-repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. パッケージをインストール（開発モード）

   - プロジェクトに pyproject.toml / setup.py があれば:

     ```bash
     pip install -e .
     ```

   - 必要パッケージを個別にインストールする場合:

     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数の準備

   ルート（.git のあるディレクトリ または pyproject.toml と同じディレクトリ）に `.env` / `.env.local` を置くと自動的に読み込まれます（パッケージ import 時に自動ロード）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（例）:

   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

   任意（既定値あり）:

   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: execution 環境 (development | paper_trading | live)（デフォルト: development）
   - LOG_LEVEL: ログレベル (DEBUG/INFO/...)（デフォルト: INFO）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に必要）

   例 .env:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化（監査ログ用など）

   監査ログテーブルを new DB に作成する例:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は initialized DuckDB 接続
   ```

---

## 使い方（代表的な API）

以下は最小限の使用例です。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

- ETL（日次パイプライン）の実行例

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄ごと）のスコアリング

  news_nlp.score_news は DuckDB 接続、target_date、OpenAI API キーを受け取り、ai_scores テーブルに書き込みます。

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（1321 MA200 + マクロニュース）

  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査 DB の初期化（メソッドを使う）

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # テーブルを作成して接続を返す
  ```

- 研究用ファクター計算

  ```python
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

---

## 主要なディレクトリ構成

（`src/kabusys` 配下の主要ファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env ロード / Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（OpenAI）と score_news
    - regime_detector.py           — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch / save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL ユーティリティ再エクスポート
    - news_collector.py            — RSS 取得 / 前処理
    - calendar_management.py       — 市場カレンダー管理 / 更新ジョブ
    - quality.py                   — データ品質チェック群
    - stats.py                     — zscore_normalize 等
    - audit.py                     — 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / ボラ / バリュー等
    - feature_exploration.py       — 将来リターン / IC / summary / rank

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス防止: 多くの関数は内部で現在時刻を参照せず、引数で与えた target_date 未満 / 以前のデータのみを使う設計です。バックテストでの利用時は注意深く日付を指定してください。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）障害時は極力例外を上位に伝える／もしくはデフォルト値で継続する等のフェイルセーフ処理が組み込まれています（モジュールごとに異なります）。
- .env 自動ロード: パッケージ import 時にプロジェクトルート（.git or pyproject.toml）を探索して `.env` / `.env.local` を自動読み込みします。テスト時等に自動ロードを抑制するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し: news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、ユニットテストで差し替え可能です（unittest.mock.patch を想定）。

---

## 追加情報 / 開発者向け

- ログレベルや環境（development / paper_trading / live）は Settings で検証されます（`KABUSYS_ENV`, `LOG_LEVEL`）。
- DuckDB への INSERT は冪等化（ON CONFLICT DO UPDATE / DO NOTHING）を多用しています。
- news_collector は SSRF・XML BOM・gzip bomb・トラッキングパラメータなどを考慮した堅牢な実装になっています。
- OpenAI は JSON Mode（response_format={"type": "json_object"}）で呼び出し、レスポンスの厳密なパースとバリデーションを行います。

---

もし README に追加してほしい実例（CI、デプロイ手順、.env.example の雛形、より詳しい API ドキュメント等）があれば教えてください。必要に応じて API リファレンスや使用例を追記します。