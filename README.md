KabuSys — 日本株自動売買プラットフォーム
===================================

概要
---
KabuSys は日本株のデータプラットフォーム・リサーチ・AI 評価・監査ログ・ETL を備えた
自動売買基盤のライブラリ群です。本コードベースは以下の責務を持つモジュール群で構成されています。

- データ取得・ETL（J-Quants API 経由で株価・財務・カレンダー等を取得し DuckDB に保存）
- データ品質チェック
- ニュース収集・NLP（OpenAI を用いた銘柄別センチメント算出）
- 市場レジーム判定（MA とマクロニュースセンチメントの合成）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ用テーブル）

特徴（ハイライト）
-----------------
- DuckDB を用いたローカル分析データベース（デフォルト path: data/kabusys.duckdb）
- J-Quants API 用の堅牢なクライアント（レートリミット・リトライ・トークン自動リフレッシュ対応）
- ニュース収集での SSRF 対策、XML パース防御（defusedxml）
- OpenAI（gpt-4o-mini）を用いた JSON モードでの堅牢な NLP 呼び出し（リトライ/パース耐性）
- ETL、品質チェック、監査ログ初期化等の idempotent な実装
- バックテスト時のルックアヘッドバイアスを避ける設計（内部で datetime.today() を直接参照しない）

必要条件
--------
- Python 3.10+
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib, json, logging 等）

セッティング（環境変数）
-----------------------
自動的にプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
主に使用される環境変数（一部）:

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector で必要）
- KABU_API_PASSWORD      : kabuステーション API のパスワード
- KABU_API_BASE_URL      : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE        : Paper Trading のモック約定モード (instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- KABUSYS_ENV            : environment (development|paper_trading|live)
- LOG_LEVEL              : ログレベル (DEBUG/INFO/...)

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際にはプロジェクトの requirements.txt / pyproject.toml を使ってインストールしてください。

4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を作成し、必要なキーを設定します。
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_key
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

基本的な使い方
-------------
以下は代表的なモジュールの呼び出し例です。全ての関数は DuckDB の接続オブジェクト（duckdb.connect(...)）を受け取ります。

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n = score_news(conn, target_date=date(2026, 3, 20))
  print("scored stocks:", n)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査テーブル用 DuckDB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- リサーチ: ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 3, 20))
  ```

注意点 / 設計上の補足
--------------------
- バックテスト・研究用途を意識し、ライブラリ内部では datetime.today()/date.today() を直接参照しない設計です（ルックアヘッドを防止）。
- OpenAI 呼び出しはエラー時にフォールバック（0.0）する等、フェイルセーフが組み込まれています。
- J-Quants クライアントはレート制限とリトライ・トークン再発行に対応しています。
- ニュース収集は SSRF 対策および XML Exploit 対策（defusedxml）を行っています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ初期化、バージョン情報
- config.py — 環境変数 / 設定管理（.env 自動読込）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの NLP スコアリング（score_news, calc_news_window 等）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / auth）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）・ETLResult
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理・営業日ロジック
  - news_collector.py — RSS 収集・前処理
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ（テーブル作成 / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- research パッケージ内の関数は研究用途（バックテスト）向けで、実運用での発注は行いません。

よくある操作
------------
- .env の自動読み込みを無効化したい（テスト時など）:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Paper Trading の挙動制御:
  - PAPER_FILL_MODE=instant|partial|never|reject

サポート / 開発
----------------
- ロギングは環境変数 LOG_LEVEL で制御できます（例: LOG_LEVEL=DEBUG）。
- テストでは OpenAI / ネットワーク呼び出しをモックすることを想定した実装になっています（モジュール内の _call_openai_api 等をパッチする）。

ライセンス
---------
（リポジトリに従って適切なライセンスを記載してください）

以上。実際に運用を開始する前に .env.example を基に必要な環境変数を設定し、DuckDB スキーマや監査テーブルの初期化を行ってください。質問や追加で README に載せたい内容があれば教えてください。