# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買基盤（データプラットフォーム＋戦略エンジン）を想定した Python パッケージです。J-Quants API 等から市場データを取得して DuckDB に保存し、特徴量計算・シグナル生成・ニュース収集・カレンダー管理などの機能を提供します。

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務データ / マーケットカレンダー）
  - データの冪等保存（DuckDB テーブルへ ON CONFLICT DO UPDATE 相当の処理）
  - 差分更新（最終取得日を見て必要な範囲のみ取得）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義を含む初期化ユーティリティ
- ETL パイプライン
  - 日次 ETL（カレンダー、株価、財務） + 品質チェック
  - 差分取得、バックフィル、品質チェック（spike 等）
- 特徴量計算（Research）
  - Momentum / Volatility / Value 等のファクター計算
  - Z スコア正規化ユーティリティ
  - 将来リターン / IC / 統計サマリー等の探索機能
- 特徴量エンジニアリング（Strategy）
  - 生ファクターのユニバースフィルタ、正規化、features テーブルへの UPSERT
- シグナル生成（Strategy）
  - features + ai_scores を統合して final_score を計算
  - Bear レジームの抑制、BUY/SELL シグナル生成、signals テーブルへの書き込み（冪等）
- ニュース収集
  - RSS フィード取得（SSRF 防止、トラッキング除去、gzip 対応）
  - raw_news と news_symbols への保存（重複除去、チャンク挿入）
- マーケットカレンダー管理
  - 営業日判定、次/前営業日取得、calendar の夜間更新ジョブ
- 実行/監査レイヤ（スキーマ）
  - signals / signal_queue / orders / trades / positions / audit 用テーブル群

## 必要な環境変数

設定は .env（または環境変数）から読み込まれます。プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env の自動読み込みを無効化
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト設定あり）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用等）パス（デフォルト: data/monitoring.db）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

## セットアップ手順

1. Python の仮想環境を作成・有効化（例: venv / pyenv / conda）
2. 必要な依存パッケージをインストール（DuckDB 等）
   - 例（pip）:
     pip install duckdb defusedxml
   - 実際の要件はプロジェクトの requirements.txt / pyproject.toml を参照してください
3. リポジトリルートに .env を作成し、上記の必須環境変数を設定
4. DuckDB スキーマの初期化:
   - Python REPL やスクリプトで以下を実行:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   init_schema は親ディレクトリがなければ自動作成します（":memory:" でインメモリ DB 可）。

## 使い方（主要 API と実行例）

以下は簡単な利用例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続とスキーマ初期化:
```
from kabusys.data.schema import init_schema, get_connection

# 永続 DB を作成・初期化
conn = init_schema("data/kabusys.duckdb")

# 既存 DB に接続（スキーマ初期化は行わない）
conn2 = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行:
```
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築:
```
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 10))
print("features upserted:", count)
```

- シグナル生成:
```
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2025, 1, 10))
print("signals written:", n)
```

- ニュース収集ジョブ（RSS）:
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes に有効な銘柄コードセットを渡すと news_symbols を生成
res = run_news_collection(conn, known_codes=set(["7203", "6758"]))
print(res)
```

- カレンダー更新ジョブ:
```
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意:
- J-Quants API はレート制限（120 req/min）や認証リフレッシュロジックが組み込まれています。実行時には JQUANTS_REFRESH_TOKEN を設定してください。
- ETL / API 呼び出しはネットワーク依存です。適切なエラーハンドリングを行ってください。

## ディレクトリ構成（要約）

- src/kabusys/
  - __init__.py (パッケージエクスポート)
  - config.py (環境変数 / 設定読み込み)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存ユーティリティ)
    - news_collector.py (RSS → raw_news 保存、銘柄抽出)
    - schema.py (DuckDB スキーマ定義と初期化)
    - stats.py (zscore_normalize 等の統計ユーティリティ)
    - pipeline.py (ETL パイプライン: run_daily_etl 等)
    - calendar_management.py (market_calendar 管理とジョブ)
    - audit.py (監査ログ用スキーマ / DDL)
    - features.py (データ層の特徴量ユーティリティ公開インターフェース)
  - research/
    - __init__.py
    - factor_research.py (mom/vol/value のファクター計算)
    - feature_exploration.py (forward returns, IC, summary 等)
  - strategy/
    - __init__.py (build_features, generate_signals を公開)
    - feature_engineering.py (features テーブル構築フロー)
    - signal_generator.py (final_score 計算と signals 書き込み)
  - execution/ (発注関連の処理を想定したモジュール群、現状空ファイル)
  - monitoring/ (監視・メトリクス用モジュール群、将来的な実装想定)

（上記はコードベースに含まれる主なファイルを抜粋した要約です）

## 開発上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス防止: 全ての戦略ロジックは target_date 時点の情報のみを参照するよう設計されています（取得日時や fetched_at を記録）。
- 冪等性: DB への保存処理は重複挿入を防ぐため ON CONFLICT / INSERT ... DO UPDATE 等の手法で実装されています。
- ネットワーク防御: RSS 取得は SSRF 防止、gzip サイズチェック、defusedxml による XML 攻撃対策が施されています。
- レート制限 / リトライ: J-Quants クライアントは固定間隔のスロットリングと指数バックオフを組み合わせています。401 では自動トークンリフレッシュを行います。

## テスト / ローカル開発ヒント

- .env の自動ロードを無効にしたいテストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のインメモリ DB を使う場合は db_path に ":memory:" を指定すると一時 DB を利用できます（init_schema(":memory:")）。
- ネットワーク依存部分（jquants_client.fetch_* / news_collector._urlopen 等）はユニットテストでモックを挿入しやすいように設計されています。

---

詳細な API 仕様やデータモデル（DataPlatform.md / StrategyModel.md）に関するドキュメントは別途用意してください。本 README はコードベースから抽出した概要と主要な使い方のガイドです。必要であれば、各モジュール向けの詳しい使用例や設計ドキュメントを追補できます。