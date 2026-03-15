# KabuSys

KabuSys は日本株向けの自動売買システム用ライブラリ（プロジェクト雛形）です。データ層（DuckDB スキーマ）、環境設定管理、戦略／実行／監視モジュールのためのパッケージ構成を提供します。

バージョン: 0.1.0

---

## 概要

このリポジトリは以下の責務を持つモジュール群を含みます。

- 環境変数・設定の読み込みと管理（.env の自動読み込み、必須チェック）
- DuckDB を利用したデータスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 戦略（strategy）、発注/実行（execution）、監視（monitoring）用パッケージの骨組み

プロジェクトは、ローカル環境やペーパー取引、実運用（live）を切り替えられる設定や、Slack 通知用の設定など、実運用を想定した基盤を持ちます。

---

## 主な機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルの自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）
  - OS 環境変数を保護しつつ .env の上書き制御
  - 必須環境変数の取得（未設定時に例外を送出）
  - KABUSYS_ENV（development / paper_trading / live）やログレベル検証

- データスキーマ管理（src/kabusys/data/schema.py）
  - DuckDB 向けの DDL をまとめて実行し、テーブル・インデックスを冪等に作成
  - Raw / Processed / Feature / Execution 層を想定したテーブル定義（価格、財務、ニュース、シグナル、オーダー、トレード、ポジション等）
  - init_schema(db_path) で初期化、get_connection(db_path) で接続取得

- パッケージ化（src/kabusys パッケージ）
  - strategy / execution / monitoring のサブパッケージ（骨組み）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で | を使用しているため）
- pip 利用可能

推奨手順（例）

1. リポジトリをクローンし、仮想環境を作る
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - duckdb が必要です。最低限:
     - pip install duckdb
   - 開発用にパッケージをインストールする場合:
     - pip install -e .

   （将来的には requirements.txt / pyproject.toml に依存を追加してください）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと、自動的に読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意/デフォルト
- KABUS_API_BASE_URL — (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH — (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH — (デフォルト: data/monitoring.db)
- KABUSYS_ENV — development / paper_trading / live （デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）

例 .env（安全上、実際のトークンは置き換えてください）
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-...."
SLACK_CHANNEL_ID="C01234567"
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

.env のパースはシンプルなシェル風仕様に対応します（export プレフィックス、シングル/ダブルクォート、エスケープ、コメント処理など）。

---

## 使い方

主に設定へのアクセスと DuckDB スキーマ初期化を紹介します。

1. 設定にアクセスする

Python から簡単に設定へアクセスできます。

例:
```
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 未設定なら例外
print(settings.duckdb_path)            # Path オブジェクト
print(settings.env)                    # development / paper_trading / live
```

注意: 必須の環境変数が設定されていない場合、settings のプロパティは ValueError を送出します。

2. DuckDB スキーマを初期化する

データベースファイルを作成し、すべてのテーブルとインデックスを作成します（冪等）。

例:
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
```

メモ:
- db_path に ":memory:" を渡すとインメモリ DB を使用できます。
- 初回のみ init_schema を呼び、以降は get_connection を使う想定です。

3. 既存 DB への接続
```
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

4. パッケージ情報
```
import kabusys
print(kabusys.__version__)
```

---

## .env 自動読み込みの挙動（補足）

- 自動ロードの優先順位:
  1. OS 環境変数（既存の環境変数は保護されます）
  2. .env.local（存在する場合、override=True として読み込み）
  3. .env（override=False: 未設定のキーのみ設定）

- プロジェクトルートの判定は、config モジュール内のロジックで __file__ を起点に親ディレクトリを上向きに探索し、.git または pyproject.toml が見つかった場所をルートとします。これにより、CWD に依存せずパッケージ配布後も正しく動作する設計です。

- 自動読み込みを無効化したい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py            # パッケージ初期化（__version__ 等）
    - config.py              # 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py           # DuckDB スキーマ定義と初期化（init_schema, get_connection）
    - strategy/
      - __init__.py         # 戦略モジュール（今は骨組み）
    - execution/
      - __init__.py         # 発注/実行モジュール（今は骨組み）
    - monitoring/
      - __init__.py         # 監視モジュール（今は骨組み）

README や追加ドキュメント（DataSchema.md など）は別途用意すると良いです。

---

## 今後の拡張案（提案）

- requirements.txt / pyproject.toml に依存関係を明示
- CI / テストコード、ユニットテスト追加
- サンプル戦略・エグゼキューション実装
- マイグレーション / バージョニング機構（DDL 変更対応）
- 実運用向けのロギング、監視、Slack 通知の実装例

---

必要があれば、README に含める具体的な例（.env.example、サンプルスクリプト、DuckDB クエリ例など）を追加します。どの情報を優先して追記しますか？