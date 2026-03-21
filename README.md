# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを備えたモジュール群を提供します。

バージョン: 0.1.0

---

## 主要な目的（プロジェクト概要）

- J-Quants API からの株価・財務・カレンダー取得を行い、DuckDB に保存する差分ETLパイプラインを提供。
- 取得した市場データを基にファクター（Momentum / Volatility / Value / Liquidity 等）を計算し、クロスセクション正規化して特徴量テーブル（features）を作成。
- 特徴量と AI スコアを統合して最終スコアを算出し、BUY / SELL シグナルを生成して signals テーブルへ格納。
- RSS ベースのニュース収集から raw_news、news_symbols への保存と銘柄抽出処理を提供。
- マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）など運用に必要な機能を備える。

---

## 機能一覧

- データ収集
  - J-Quants クライアント（差分取得・ページネーション・自動トークンリフレッシュ・レート制御・リトライ）
  - 市場カレンダー取得
  - 財務データ・日足取得
- ETL
  - 差分取得ロジック（バックフィル対応）
  - 品質チェック（quality モジュール経由、障害を集約して通知可能）
  - 日次 ETL 実行エントリ run_daily_etl
- データ格納
  - DuckDB スキーマの初期化（init_schema）
  - raw / processed / feature / execution レイヤーを含むテーブル設計（冪等保存）
- 特徴量・リサーチ
  - calc_momentum / calc_volatility / calc_value
  - zscore_normalize（クロスセクション Z スコア）
  - 将来リターン計算・IC（Spearman）・summary 統計
- 戦略
  - build_features: features テーブルの作成（正規化・クリップ・UPSERT）
  - generate_signals: final_score 計算と BUY/SELL シグナル生成（冪等）
- ニュース処理
  - RSS フィード取得（SSRF対策・gzip制限・XML攻撃対策）
  - raw_news 保存、銘柄抽出、news_symbols への紐付け
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（nightly lookahead 更新）
- 監査（audit）ログ用スキーマ（信頼できるトレースを保持）

---

## 必要要件（依存ライブラリ）

最低限必要な Python ライブラリ（例）:
- Python 3.10+
- duckdb
- defusedxml

（プロジェクトのセットアップ方法に応じて requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone ... またはパッケージとして配置

2. 仮想環境の作成と依存導入
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb defusedxml
     ```
   - 実プロジェクトでは pyproject.toml / requirements.txt からインストールしてください。

3. 環境変数の設定
   - .env（または .env.local）をプロジェクトルートに配置すると自動で読み込みます。
   - 自動 env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。
   - 必須の環境変数（Settings で参照）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネルID（必須）
   - 任意／デフォルト
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   - .env の例（簡易）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. DuckDB スキーマ初期化
   - Python から実行:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - ":memory:" を渡すとインメモリ DB が使えます（テスト用）。

---

## 使い方（クイックスタート）

以下は主要なワークフローの例です。実行はアプリ側のスクリプトやジョブから呼び出してください。

1. DB 初期化（上記）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL の実行（株価・財務・カレンダーの差分取得 + 品質チェック）
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   # conn は init_schema の戻り値
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量作成（features テーブルを作る）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

4. シグナル生成（signals テーブルへ）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   total = generate_signals(conn, target_date=date.today())
   print(f"signals written: {total}")
   ```

5. ニュース収集と保存
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   # known_codes: 銘柄抽出に利用する有効コードの集合（None なら抽出スキップ）
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   print(res)
   ```

6. カレンダーの夜間更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

補足:
- ETL / 保存関数は冪等（ON CONFLICT）に設計されており、再実行で上書き・追加されるだけです。
- J-Quants API へのリクエストは内部でレート制御・リトライ・トークン自動更新を行います。

---

## よく使う API / エントリポイント

- kabusys.config.settings — 環境設定アクセス
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ作成 + 接続取得
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL パイプライン
- kabusys.strategy.build_features(conn, target_date) — 特徴量生成
- kabusys.strategy.generate_signals(conn, target_date, threshold=..., weights=...) — シグナル生成
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar — 低レベル API
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection — ニュース関連

---

## ディレクトリ構成（主要ファイル概要）

src/kabusys/
- __init__.py — パッケージ初期化
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（認証・レート制御・保存ユーティリティ）
  - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
  - pipeline.py — ETL パイプライン（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - news_collector.py — RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management.py — market_calendar 管理、営業日判定ユーティリティ
  - features.py — features の公開インターフェース（再エクスポート）
  - audit.py — 監査ログ用スキーマ定義（signal_events, order_requests, executions など）
  - pipeline.py（ETL）
- research/
  - __init__.py — 研究向けユーティリティの公開
  - factor_research.py — calc_momentum / calc_volatility / calc_value（prices_daily/raw_financials を参照）
  - feature_exploration.py — 前方リターン計算、IC、統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py — build_features（normalize / universe filter / UPSERT）
  - signal_generator.py — generate_signals（final_score 算出、BUY/SELL 判定）
- execution/ — 発注 / execution 層（モジュール群の入口、将来的な拡張）
- monitoring/ — 監視・アラート用コード（SQLite 等を想定）

---

## 運用上の注意点

- 環境変数の管理は .env を推奨。プロジェクトルート検出は .git または pyproject.toml を基準に行います。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかにしてください。is_live/is_paper/is_dev プロパティが利用可能です。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。バックアップ・ローテーションを計画してください。
- ニュース収集は外部 HTTP を扱うため SSRF 対策・レスポンスサイズ制限を行っています。fetch_rss の挙動に注意してください。
- generate_signals / build_features はルックアヘッドバイアス回避のため target_date 時点までのデータのみを参照します。
- 本システムは発注層（実際のブローカー送信）と切り離して設計されています。実運用での発注ロジックは execution 層とブローカー固有の実装で接続してください。

---

## テスト・デバッグのヒント

- 自動 .env ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- テスト用にインメモリ DB を使用する: init_schema(":memory:")
- ログレベルは LOG_LEVEL 環境変数で制御（DEBUG を設定すると内部処理ログが増えます）

---

問題点や機能追加、外部連携（ブローカーAPI、Slack通知等）については README を更新していきます。必要があれば README に含める追加の使用例や CLI スクリプト例を作成します。