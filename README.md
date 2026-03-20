# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
DuckDB をデータレイヤに使い、J-Quants API や RSS ニュースを取り込み、ファクター計算、シグナル生成、実行監査までを想定したモジュール群を提供します。

## 主要な特徴
- データ収集（J-Quants 経由の株価・財務・市場カレンダー）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- DuckDB ベースのスキーマ（Raw / Processed / Feature / Execution 層）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量正規化（Z スコア）
- シグナル生成（ファクター + AI スコア統合、BUY / SELL 判定）
- ニュース収集（RSS → raw_news、銘柄抽出）
- カレンダー管理（営業日判定・前後営業日取得）
- 冪等性を意識した DB 保存（ON CONFLICT 等）、およびトレーサビリティ用監査テーブル

## 主な機能一覧（モジュール）
- kabusys.config: 環境変数 / .env 自動読み込み、設定オブジェクト
- kabusys.data:
  - schema: DuckDB スキーマ初期化（init_schema）
  - jquants_client: J-Quants API クライアント + 保存関数
  - pipeline: 日次 ETL 実行 run_daily_etl 等
  - news_collector: RSS 収集 / DB 保存 / 銘柄抽出
  - calendar_management: 営業日判定・更新ジョブ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research: 研究用ファクター計算・探索ユーティリティ
- kabusys.strategy:
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
- kabusys.execution / monitoring: 実行・監視関連（パッケージ公開対象）

## 動作要件（推奨）
- Python 3.10+
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）

例（pip インストール）:
```
pip install duckdb defusedxml
```

## 環境変数（主要）
kabusys.config.Settings で参照する主要な環境変数：

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション等を使う場合のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知チャンネル ID

オプション（デフォルトを持つもの）:
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

テスト等で自動 .env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env はプロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数優先）。

## セットアップ手順（ローカル）
1. リポジトリをチェックアウトし、仮想環境を作成・有効化
2. 依存パッケージをインストール（duckdb, defusedxml 等）
3. 環境変数を設定（.env に必要なキーを記載）
4. DuckDB スキーマを初期化

例:
```bash
# 仮想環境作成
python -m venv .venv
source .venv/bin/activate

pip install duckdb defusedxml

# .env を用意（例）
cat > .env <<EOF
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
EOF

# DuckDB スキーマを作成（Python REPL / スクリプト）
python - <<'PY'
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
print("init done")
PY
```

## 使い方（代表的な操作例）
以下は Python スクリプト / REPL から使う想定の例です。

- DuckDB 接続の初期化:
```python
from kabusys.data.schema import init_schema, get_connection
# 初回: init_schema でファイルとテーブルを作成
conn = init_schema("data/kabusys.duckdb")
# 既存 DB に接続するだけなら
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants からデータ取得 → 保存 → 品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# conn は DuckDB 接続
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

- 特徴量の構築（features テーブルへ書き込み）:
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date.today())
print(f"built features for {n} codes")
```

- シグナル生成（signals テーブルへ書き込み）:
```python
from datetime import date
from kabusys.strategy import generate_signals

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"written {count} signals")
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出のための有効な銘柄コード集合（例: {"7203","6758",...}）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- カレンダー更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar updated, saved:", saved)
```

注意:
- 各処理は DuckDB 接続（duckdb.DuckDBPyConnection）を要求します。
- トークンや API 呼び出しは設定に依存するため、事前に .env 等で設定してください。
- ETL の差分取得・バックフィル挙動は pipeline.run_* の引数で制御可能です。

## ディレクトリ構成（抜粋）
リポジトリの主要ファイル / モジュール構造（src/kabusys 以下の概観）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - schema.py                 # DuckDB スキーマ定義 / init_schema
    - jquants_client.py         # J-Quants API クライアント + 保存
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - news_collector.py         # RSS 収集 / raw_news 保存 / 銘柄抽出
    - calendar_management.py    # 営業日判定・カレンダー更新
    - stats.py                  # zscore_normalize 等
    - features.py               # 再エクスポート
    - audit.py                  # 監査ログ用 DDL
    - audit... (続く)
  - research/
    - __init__.py
    - factor_research.py        # モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py    # 将来リターン・IC・統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py    # features の構築（build_features）
    - signal_generator.py       # signals の生成（generate_signals）
  - execution/
    - __init__.py
  - monitoring/
    - (モニタリング関連モジュール)

（実際のファイル数は多く、上記は主要モジュールの抜粋です）

## 開発 / テストのヒント
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト時に便利）。
- DuckDB のインメモリ DB を使う場合は db path として ":memory:" を渡してください（init_schema(":memory:")）。
- ネットワーク依存部分（J-Quants / RSS）はモックして単体テストを行うことを推奨します（例: jquants_client._request や news_collector._urlopen をモック）。

## セキュリティ考慮
- RSS の取得は SSRF 対策やレスポンスサイズ制限を組み込んでいます（news_collector モジュールを参照）。
- J-Quants のレート制御と自動リトライ / トークンリフレッシュを実装済みです。
- 環境変数やトークンは安全に管理してください（CI/デプロイではシークレットストアの使用を推奨）。

---
この README はコードベースの公開 API と使い方のサマリです。詳細な設計仕様（StrategyModel.md、DataPlatform.md、等）や DB スキーマ設計はコード内ドキュメント・コメントを参照してください。質問や追加の使用例があれば教えてください。