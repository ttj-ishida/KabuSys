# KabuSys

日本株向けの自動売買システム基盤ライブラリ（開発版）

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買プラットフォーム向けに設計された Python パッケージです。データ取得・保管（DuckDB ベース）、特徴量生成、発注/約定の監査（トレーサビリティ）、環境設定管理など、自動売買システムを構成する基盤機能群を提供します。設計は以下のレイヤーを想定しています：

- Raw Layer（生データ格納）
- Processed Layer（整形済み市場データ）
- Feature Layer（戦略／AI 用の特徴量）
- Execution Layer（シグナル → 発注 → 約定 → ポジション管理）
- Audit（シグナルから約定までの監査ログ）

主な機能
--------
- 環境変数/ .env 読み込みと集中設定（settings オブジェクト）
- DuckDB スキーマ定義と初期化（data.schema.init_schema）
  - Raw / Processed / Feature / Execution 各層のテーブルを作成
  - 頻出クエリ向けのインデックス作成
- 監査ログ（トレーサビリティ）用スキーマの初期化（data.audit.init_audit_schema / init_audit_db）
  - signal_events / order_requests / executions テーブル
  - 冪等性・ステータス遷移を考慮した設計
- プロジェクトルートを探索して .env / .env.local を自動的に読み込む（任意で無効化可能）
- settings による環境（development / paper_trading / live）やログレベルの検証

要件（主な依存）
----------------
- Python 3.9+（型ヒントに union 型を使用）
- duckdb
- （外部 API を利用する実装を行う場合）kabu API クライアント等

インストール
------------
1. リポジトリをクローン（またはパッケージ配布に合わせて pip install）
2. 仮想環境を作成・有効化
3. 依存パッケージをインストール（例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb
# 開発中はパッケージを editable install:
pip install -e .
```

環境変数（設定）
----------------
KabuSys は環境変数から設定を取得します。プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を自動検出し、以下の優先順で読み込みます:

OS 環境変数 > .env.local > .env

自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

必須（アプリ実行に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意／デフォルト
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）

例（.env の骨子）
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

セットアップ手順（簡易）
---------------------
1. 必要な環境変数 (.env) を用意する
2. DuckDB スキーマを初期化する（例: スクリプト内または REPL で）

Python サンプル:
```python
from kabusys import __version__
from kabusys import data, config

print("KabuSys version:", __version__)
settings = config.settings
print("env:", settings.env)
db_path = settings.duckdb_path  # Path オブジェクト

# DuckDB データベースを初期化（ファイルを作成）
conn = data.schema.init_schema(db_path)

# 監査ログテーブルを同じ接続に追加する場合
data.audit.init_audit_schema(conn)

# もしくは監査専用 DB を作る場合
# audit_conn = data.audit.init_audit_db("data/kabusys_audit.duckdb")
```

使い方（簡易ガイド）
-------------------
- 設定取得:
  - from kabusys.config import settings
  - settings.jquants_refresh_token 等のプロパティで取得（未設定時は ValueError）
- データベース初期化:
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)
- 監査ログ初期化:
  - from kabusys.data import audit
  - audit.init_audit_schema(conn)  # 既存接続へ追加
  - または audit_conn = audit.init_audit_db("path/to/audit.duckdb")
- 戦略・実行・監視モジュールはパッケージ構成に準拠して拡張する（strategy/, execution/, monitoring/）

注意点
------
- settings のプロパティは必須値を要求するものがあります（未設定だと ValueError）。
- .env の自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml を基準）。
- DuckDB の初期化関数は冪等（既にテーブルがあればスキップ）です。
- 監査ログ側の TIMESTAMP は UTC 保存となるよう init_audit_schema は SET TimeZone='UTC' を実行します。

ディレクトリ構成
----------------
リポジトリの主要なファイル構成（抜粋）:

src/kabusys/
- __init__.py                — パッケージメタ情報（__version__）
- config.py                  — 環境変数・設定管理
- data/
  - __init__.py
  - schema.py                — DuckDB スキーマ定義と init_schema / get_connection
  - audit.py                 — 監査ログ（signal_events / order_requests / executions）の定義と初期化
  - audit.py                 — 監査用 DB 初期化ユーティリティ
  - ...（その他データ関連）
- strategy/
  - __init__.py              — 戦略モジュールのエントリポイント
- execution/
  - __init__.py              — 発注・実行関連エントリポイント
- monitoring/
  - __init__.py              — 監視用エントリポイント

（上記は現状の実装ファイルに基づく抜粋です。戦略や実行ロジックは別途実装を追加してください。）

開発・貢献
----------
- バグ報告や機能要望は Issue へお願いします。
- 開発中は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使ってテスト時の環境変数読み込みを制御できます。

補足
----
- このパッケージは基盤ライブラリです。実際の戦略ロジック・発注実装・Slack 通知等は利用者側で組み合わせて利用する想定です。
- DuckDB を利用しているため、ローカルで大容量の時系列データを効率的に保存・検索できます。

以上。README に追加したい具体的な使用例や、CI・デプロイ手順があれば教えてください。README をその内容に合わせて拡張します。