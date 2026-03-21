KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株のデータ取得・ETL・特徴量計算・シグナル生成・ニュース収集などを行う
自動売買プラットフォームのライブラリ群です。モジュールはデータ層（J-Quants 取得・DuckDB 保存）、
リサーチ層（ファクター計算・探索）、戦略層（特徴量正規化・シグナル生成）、
および実行・監視層のための土台機能で構成されています。

主な特徴
--------
- J-Quants API クライアント（レート制御・自動トークンリフレッシュ・リトライ付き）
- DuckDB を使ったスキーマ定義・初期化（冪等な DDL）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェックのフロー化）
- ファクター計算（Momentum / Volatility / Value など）
- 特徴量正規化（Z スコア正規化）と特徴量保存（features テーブルへの UPSERT）
- シグナル生成（複数コンポーネントの重み付き合成・BUY/SELL 判定・エグジットロジック）
- ニュース収集（RSS 取得・前処理・記事保存・銘柄抽出・SSRF 対策・サイズ検査）
- 監査ログ（order_request → execution に至るトレーサビリティ設計）

必要な環境変数（主なもの）
-------------------------
以下はコード内で必須とされる主な環境変数です（config.Settings を参照）。

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション等の API パスワード（必須）
- KABU_API_BASE_URL     : kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite ファイルパス（省略時: data/monitoring.db）
- KABUSYS_ENV           : 実行環境 ("development" / "paper_trading" / "live")（省略時: development）
- LOG_LEVEL             : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

自動 .env ロード
- パッケージルート（.git または pyproject.toml を基準）にある .env/.env.local を自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
--------------
1. Python（3.9+ 推奨）をインストールしてください。

2. 依存パッケージをインストールします（プロジェクトに requirements/pyproject がある場合はそちらに従ってください）。
   例（最小）:
   - duckdb
   - defusedxml

   pip の例:
   ```
   pip install duckdb defusedxml
   ```

   プロジェクトを開発モードでインストール可能なら：
   ```
   pip install -e .
   ```

3. 環境変数を設定します。
   - .env.example（ない場合は README の「必要な環境変数」を参考に .env を作成）を参照して .env を作成してください。
   - 重要なキー（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は必須です。

4. DuckDB スキーマの初期化
   Python REPL またはスクリプトで以下を実行して DB とテーブルを作成します（デフォルトの DUCKDB_PATH を使用する場合は settings.duckdb_path を確認）。
   例:
   ```python
   from kabusys.config import settings
   from kabusys.data import schema
   conn = schema.init_schema(settings.duckdb_path)
   ```

使い方（主要ワークフローの例）
----------------------------

1) 日次 ETL（市場カレンダー / 株価 / 財務）の実行
- DuckDB 接続を用意し、run_daily_etl を呼びます。

```python
from kabusys.config import settings
from kabusys.data import schema, pipeline

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

2) 特徴量の構築（features テーブルへ）
- research モジュールのファクター計算結果を正規化・クリップして features に書き込みます。

```python
from datetime import date
from kabusys.config import settings
from kabusys.data import schema
from kabusys.strategy import build_features

conn = schema.get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date(2025, 3, 20))
print(f"upserted features: {count}")
```

3) シグナル生成（signals テーブルへ）
- features と ai_scores / positions を参照して BUY/SELL シグナルを生成します。

```python
from datetime import date
from kabusys.data import schema
from kabusys.strategy import generate_signals

conn = schema.get_connection(settings.duckdb_path)
total = generate_signals(conn, target_date=date(2025, 3, 20), threshold=0.6)
print(f"signals written: {total}")
```

4) ニュース収集ジョブ
- RSS フィードから記事を収集して raw_news に保存し、銘柄紐付けを行います。

```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

5) J-Quants 生データ取得と保存
- jquants_client の fetch_* / save_* を直接使って差分取得・保存することもできます。
  自動トークン管理やページング対応・リトライ済みで使えます。

ディレクトリ構成（主要ファイル）
------------------------------
（src 配下の kabusys パッケージを想定）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py     — RSS ニュース収集と前処理・保存
    - schema.py             — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py              — Z スコア等の統計ユーティリティ
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - features.py           — features 用の公開ユーティリティ（再エクスポート）
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - audit.py              — 監査ログ用 DDL（order_request → execution の追跡）
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Volatility / Value のファクター計算
    - feature_exploration.py— IC 計算等の研究用ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py— 生ファクターの正規化・features テーブルへの書き込み
    - signal_generator.py   — final_score 計算・BUY/SELL 判定・signals への書き込み
  - execution/               — 発注・約定周りの実装（パッケージ用のプレースホルダ）
  - monitoring/              — 監視・通知ロジック（Slack 等）用（パッケージプレースホルダ）

設計上の注意点
-------------
- ルックアヘッドバイアス回避: 特徴量・シグナル生成は target_date 時点までのデータのみを使用します。
- 冪等性: DB への保存は ON CONFLICT / UPSERT やトランザクションで原子性を確保する設計です。
- セキュリティ: RSS 収集では SSRF 対策、XML パースに defusedxml を使用、レスポンスサイズ上限などを実装。
- テスト可能性: API トークンの注入や内部関数のモックを容易にする設計（例: id_token 注入、_urlopen の差替え）。

トラブルシューティング
---------------------
- 環境変数エラー: settings の必須プロパティ参照時に未設定だと ValueError になります。.env を確認してください。
- DuckDB の権限/パスエラー: デフォルト DB パスの親ディレクトリが存在しない場合でも init_schema は自動で作成しますが、アクセス権を確認してください。
- ネットワーク/API エラー: jquants_client はリトライしますが、認証失敗や継続的な 5xx レスポンスはログを確認してください。

開発に関して
-------------
- パッケージはモジュール単位で import して利用します。ユニットテストや CI のため、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効にできます。
- logging は各モジュールで logger.getLogger(__name__) を使用しているため、root ロガーでハンドラ・フォーマットを設定して一元管理してください。

参考（短いコードスニペット）
--------------------------
DB 初期化 → ETL → 特徴量 → シグナル生成の簡単な流れ:

```python
from kabusys.config import settings
from kabusys.data import schema, pipeline
from kabusys.strategy import build_features, generate_signals
from datetime import date

conn = schema.init_schema(settings.duckdb_path)

# ETL（デフォルトは今日）
etl_result = pipeline.run_daily_etl(conn)

# 特徴量構築（ETL の対象日で）
target = etl_result.target_date
build_features(conn, target)

# シグナル生成
generate_signals(conn, target)
```

最後に
------
本 README はコードベースの主要な機能と使い方を短くまとめたものです。各モジュール内に詳細なドキュメント文字列（docstring）が含まれているため、個別の挙動や引数仕様はソースを参照してください。必要であれば README を拡張して、サンプル .env.example、CI 設定、運用手順（cron / ワーカー）なども追加できます。