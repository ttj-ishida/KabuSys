# KabuSys

日本株向け自動売買システムのコアライブラリ（開発中）

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買システムのための基盤ライブラリです。市場データの取得・保管スキーマ、環境設定の管理、発注管理やモニタリングのための土台を提供します。本リポジトリはパッケージの骨組み（config、data（DuckDBスキーマ）、strategy、execution、monitoring）を含みます。

主な機能
--------
- 環境変数／.env ファイルの自動読み込み（プロジェクトルート検出に基づく）
  - 読み込み順序: OS環境変数 > .env.local > .env
  - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - 複雑なクォート、エスケープ、コメントに対応した .env パーサ
- 設定管理（settings オブジェクト）
  - J-Quants トークン、kabu API パスワード、Slack トークン、DB パスなどをプロパティとして提供
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証
- DuckDB を用いたデータベーススキーマ定義と初期化（data.schema）
  - 4 層構造（Raw / Processed / Feature / Execution）に対応したテーブル DDL を用意
  - インデックスの作成、および外部キー依存を考慮した順序でのテーブル作成
  - init_schema(db_path) による冪等な初期化と接続取得
  - get_connection(db_path) による既存 DB への接続取得

セットアップ手順
---------------
1. Python 環境を用意（推奨: 3.9+）
2. 仮想環境の作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージのインストール
   - 最低依存: duckdb
   ```bash
   pip install duckdb
   ```
   - 開発用にパッケージとして使う場合（プロジェクトルートで）
   ```bash
   pip install -e .
   ```
   （setup.cfg / pyproject.toml がある場合はそちらで管理してください）

4. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に .env や .env.local を配置することで自動読み込みされます。
   - 自動読み込みを無効にするには、起動前に環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN - J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD - kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID - Slack 通知先チャンネル ID（必須）

任意・デフォルト値あり
- KABU_API_BASE_URL - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV - 環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL - ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）

.env の簡単な例
```env
# .env
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C12345678"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

使い方（簡単な例）
-----------------

- settings の利用（環境変数から安全に取得）
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print("env:", settings.env)
print("duckdb:", settings.duckdb_path)
```

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# DUCKDB_PATH に基づきファイルを自動作成して初期化
conn = init_schema(settings.duckdb_path)

# conn は duckdb の接続オブジェクト（DuckDBPyConnection）
with conn:
    res = conn.execute("SELECT count(*) FROM prices_daily").fetchall()
    print(res)
```

- 既存 DB への接続（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- 自動 .env ロードを無効にして手動で環境をセットする（テスト時の例）
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print(settings.env)"
```

ディレクトリ構成
----------------
（主要ファイル・モジュール: 実際のリポジトリに応じて若干の差異がある場合があります）

- src/
  - kabusys/
    - __init__.py            — パッケージ宣言（__version__ = "0.1.0"）
    - config.py              — 環境設定、.env ローダ、Settings クラス
    - data/
      - __init__.py
      - schema.py           — DuckDB スキーマ定義と init_schema / get_connection
    - strategy/
      - __init__.py          — 戦略モジュール（将来的に戦略を配置）
    - execution/
      - __init__.py          — 発注/実行モジュール（将来的に実装）
    - monitoring/
      - __init__.py          — モニタリング関連（将来的に実装）

補足・設計ノート
----------------
- .env のパースはクォートやエスケープ、行内コメントを考慮した実装になっています。特殊な形式の .env を使用する場合でも比較的堅牢に動作します。
- init_schema は冪等（既にテーブルがあればスキップ）であり、親ディレクトリが存在しなければ自動的に作成します。
- settings の必須プロパティは未設定時に ValueError を送出します。CI や本番環境では必須環境変数の設定漏れに注意してください。
- KABUSYS_ENV により is_live / is_paper / is_dev といったフラグが取得できます。環境に応じた安全対策（paper_trading でのモック実行など）に利用してください。

今後の拡張案
-------------
- strategy モジュールに具体的な戦略実装（特徴量計算・シグナル生成）
- execution モジュールに kabuAPI との接続・注文フロー実装
- monitoring に Slack 通知やダッシュボード統合
- CI テスト、型チェック、フォーマッタ設定などの導入

貢献
----
興味があれば Issue / PR を歓迎します。pull request では機能単位で分け、ユニットテストと簡単な動作確認手順を添えてください。

---

この README は現状のコードベース（config.py, data/schema.py を中心）に基づいて作成しています。追加のモジュールや運用手順に合わせて随時更新してください。