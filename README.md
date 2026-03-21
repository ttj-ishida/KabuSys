# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）

KabuSys は、J-Quants など外部データソースから日本株の市場データ・財務データ・ニュースを取得し、
DuckDB ベースのデータ層に保存、特徴量作成・シグナル生成・ETL・カレンダー管理など
戦略開発〜運用に必要な機能を提供する Python モジュール群です。

- バックエンド DB: DuckDB（ローカルファイルまたはインメモリ）
- データ取得: J-Quants API（リトライ・レート制御・トークン自動リフレッシュ対応）
- ニュース取得: RSS フィード（SSRF対策・XML安全パース）
- 戦略: 研究で算出した生ファクターを正規化して features を作成、final_score によるシグナル生成

以下はこのリポジトリの README（日本語）です。

## 機能一覧

- データ取得（J-Quants クライアント）
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務（fetch_financial_statements / save_financial_statements）
  - JPX マーケットカレンダー（fetch_market_calendar / save_market_calendar）
  - レート制御・リトライ・トークン自動リフレッシュを内蔵

- ETL / パイプライン
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分更新・バックフィル対応（APIの「後出し」訂正を吸収）

- データスキーマ（DuckDB）
  - raw / processed / feature / execution 層のテーブルを定義・初期化（init_schema）

- ニュース収集
  - RSS 収集（fetch_rss）・前処理・raw_news 保存・銘柄抽出（extract_stock_codes）
  - SSRF対策、受信サイズ制限、トラッキングパラメータ削除、記事IDは URL 正規化からハッシュ生成

- 研究（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

- 特徴量エンジニアリング（strategy）
  - build_features: 生ファクターを正規化（Zスコア）・ユニバースフィルタを適用して features に保存

- シグナル生成（strategy）
  - generate_signals: features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals に保存
  - Bear レジーム判定・エグジット（ストップロス / スコア低下）判定

- カレンダー管理（market calendar utilities）
  - 営業日判定、前後営業日取得、期間内営業日リスト、夜間カレンダー更新ジョブ

- 監査（audit）
  - シグナル→発注→約定 のトレーサビリティ用スキーマ（監査ログ）

- 汎用ユーティリティ
  - zscore_normalize（クロスセクション Z スコア正規化）
  - データ品質チェック（quality モジュール：ETL パイプラインで使用）

## 必要条件（推奨）

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

（このリポジトリ内では標準ライブラリを多用する設計ですが、DuckDB と defusedxml は明示的な外部依存です。）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発インストール（パッケージ化されていれば）
pip install -e .
```

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化する

2. 依存パッケージをインストールする
   - 必要: duckdb, defusedxml
   - テストでネットワークをモックする場合は追加のテストパッケージを用意

3. 環境変数を設定する
   - 環境変数は .env もしくは OS 環境変数から読み込まれます（パッケージ import 時に自動ロード。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（Settings._require による必須チェック）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API のパスワード
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - 任意（デフォルトあり）:
     - KABUS_API_BASE_URL    : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（監視用など）（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : 実行モード ('development' | 'paper_trading' | 'live')（デフォルト: development）
     - LOG_LEVEL             : ログレベル（'DEBUG','INFO','WARNING','ERROR','CRITICAL'）

   - サンプル .env（プロジェクトルート）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     KABU_API_PASSWORD=your_kabu_api_password_here
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化
   - Python REPL あるいはスクリプトから init_schema を呼んで DB とテーブルを作成します。
   - 例:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - ":memory:" を指定するとインメモリ DB を使用します。

## 使い方（主要な API / 実行例）

基本的に DuckDB 接続を取得して各モジュールの関数を呼び出します。以下に典型的な操作例を示します。

- ETL（日次差分 ETL）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定すればその日分を実行
print(result.to_dict())
```

- 特徴量作成（features テーブルの構築）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date(2025, 1, 31))
print(f"upserted features: {n}")
```

- シグナル生成
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
total = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals written: {total}")
```

- ニュース収集ジョブ（RSS）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コード集合
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # source_name -> 新規保存数
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

- J-Quants の低レベル呼び出し（テスト用途）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from datetime import date

# トークンは settings.jquants_refresh_token から自動取得される
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意点:
- 多くの関数は冪等（idempotent）に設計されています（INSERT ... ON CONFLICT / トランザクションで日付単位置換等）。
- 研究用モジュールは発注・execution 層へ依存しない設計です（安全にオフラインで利用可能）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると import 時の .env 自動ロードを無効化できます（テストで環境を制御したい場合に便利）。

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なディレクトリ/モジュール構成は次の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                  -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py              -- ETL パイプライン（run_daily_etl 等）
    - schema.py                -- DuckDB スキーマ定義・初期化（init_schema）
    - stats.py                 -- zscore_normalize など統計ユーティリティ
    - news_collector.py        -- RSS 取得・記事処理・保存
    - calendar_management.py   -- 市場カレンダー関連ユーティリティ
    - features.py              -- data レイヤの feature ユーティリティ再エクスポート
    - audit.py                 -- 監査ログ（発注〜約定トレーサビリティ）DDL
    - pipeline.py              -- ETL フロー（複数）
  - research/
    - __init__.py
    - factor_research.py       -- Momentum/Volatility/Value の計算
    - feature_exploration.py   -- 将来リターン・IC・サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py   -- build_features
    - signal_generator.py      -- generate_signals
  - execution/                 -- 発注／execution 層（未実装ファイル群や拡張点）
  - monitoring/                -- 監視・メトリクス関連（将来的な拡張）
  - その他モジュール：quality（品質チェック）等（パイプラインで利用）

各モジュールはドキュメンテーション文字列（docstring）が充実しており、関数ごとに引数・戻り値・例外・設計意図が明示されています。

## テスト・デバッグ

- 単体テストでは DuckDB の ":memory:" 接続を使うと副作用が少なくて便利です。
- ネットワークリクエスト（jquants / RSS）はモックしてテストすることを推奨します（関数は id_token や HTTP呼び出しの注入がしやすい設計）。
- 自動 .env ロードはテスト時に邪魔になる場合があるため KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化してください。

## 運用上の注意

- KABUSYS_ENV を "live" に設定すると本番運用フラグ (settings.is_live) が True になります。発注機能を組み合わせる場合は設定ミスによる誤発注に注意してください。
- J-Quants のレート制限や API の仕様変更に注意。jquants_client は最大リトライと固定間隔レート制御を実装していますが、運用状況に応じて調整してください。
- ニュース収集では SSRF / XML Bomb / 大容量レスポンス等への防御を実装していますが、外部データの取り扱いは常に注意してください。

---

この README はコードベース（src/kabusys）をもとに作成しています。さらに詳細な仕様（StrategyModel.md / DataPlatform.md / Research ドキュメントなど）がリポジトリに含まれている想定です。開発者向けの実行スクリプトや CLI を追加することで、運用がより簡便になります。必要であれば README の拡張（実行スクリプト例、監視・アラート設定、デプロイ手順等）を作成します。