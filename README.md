# KabuSys

日本株向け自動売買基盤ライブラリ（プロトタイプ）

KabuSys は、日本株のデータ収集・特徴量生成・戦略・発注・監査ログを扱うための内部ライブラリ群の骨格を提供します。DuckDB を用いた永続化スキーマ、環境変数ベースの設定管理、および監査ログ（発注トレーサビリティ）初期化機能が含まれます。

---

## 主な機能

- 環境変数 (.env/.env.local) からの設定自動読み込み（必要に応じて無効化可）
  - export 形式やクォート・エスケープ、コメントの扱いに対応
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
- settings オブジェクトによる型付き・検証付き設定取得
  - 必須設定は未設定時に明示的にエラーを投げる
  - 環境（development / paper_trading / live）・ログレベルの検証
- DuckDB ベースのデータスキーマ初期化
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - インデックス作成・DDL は冪等（存在チェック）で実行
  - init_schema() による自動ディレクトリ作成、:memory: 対応
- 監査ログ（Audit）スキーマ
  - signal_events / order_requests / executions を定義
  - 発注フローの UUID 連鎖により完全なトレーサビリティを確保
  - init_audit_schema() / init_audit_db() による初期化（UTC タイムゾーン設定）
- モジュール分割（data / strategy / execution / monitoring）による拡張性

---

## 動作要件

- Python 3.10+（型注釈の union 表記など）
- duckdb Python パッケージ
- （運用で使う場合）各種 API トークン（J-Quants, kabuステーション, Slack など）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# パッケージ配布形式がある場合:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb
   # もしパッケージをeditableでインストールする場合:
   # pip install -e .
   ```

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。
   - `.env` のパースは Bash ライクな書式に準拠（export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープを考慮）。コメントの扱いなど細かいルールがあります。

4. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants API
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN (必須) — Slack 通知用
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (任意) — development / paper_trading / live（既定: development）
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）

   必須変数が未設定の場合、settings の該当プロパティ参照時に ValueError が発生します。

---

## 使い方（基本例）

- settings を使って構成値を参照する例:
```python
from kabusys.config import settings

print(settings.env)  # development / paper_trading / live
print(settings.is_live)  # True/False
token = settings.jquants_refresh_token  # 未設定なら ValueError
```

- DuckDB スキーマを初期化する（メイン DB）:
```python
from kabusys.data.schema import init_schema, get_connection
from pathlib import Path

# ファイル DB を初期化（親ディレクトリが無ければ自動作成）
conn = init_schema(Path("data/kabusys.duckdb"))

# 既存 DB へ接続（スキーマの初期化は行わない）
conn2 = get_connection("data/kabusys.duckdb")
```

- 監査ログ（audit）スキーマを既存接続に追加する:
```python
from kabusys.data.audit import init_audit_schema

# conn は init_schema() 等で取得した duckdb 接続
init_audit_schema(conn)
```

- 監査ログ専用の DB を作る:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.kabusys.duckdb")
```

- 自動 .env 読み込みを無効にしてテスト実行:
```bash
KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python -c "from kabusys.config import settings; print('ok')"
```

---

## 実装上のポイント・注意事項

- .env のパースはかなり寛容ですが、いくつかのルールがあります（クォート処理、コメントの解釈等）。複雑なケースは `.env` でクォートして記述してください。
- settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN）は参照時に検証します。サービス起動前に必ず .env を整備してください。
- init_schema() は冪等で、安全に何度でも実行できます。既存テーブルはスキップされます。
- init_audit_schema() はタイムゾーンを UTC にセットします（すべての TIMESTAMP は UTC で保存する設計）。
- DuckDB の :memory: を指定するとインメモリ DB を使用できます（テスト時に便利）。
- 監査ログ設計は削除を想定していません（ON DELETE RESTRICT）。監査証跡を保つ設計です。

---

## ディレクトリ構成（概観）

以下はこのリポジトリに含まれる主要ファイルの構成例です（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - schema.py              # DuckDB スキーマ定義と init_schema(), get_connection()
      - audit.py               # 監査ログ（audit）スキーマと初期化関数
      - audit.py
      - audit.py
      - audit.py
    - strategy/
      - __init__.py            # 戦略モジュール群（拡張ポイント）
    - execution/
      - __init__.py            # 発注・取引実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py            # モニタリング・監視用モジュール（拡張ポイント）

（注）上記は現状提供されているファイル群を反映した最小構成です。strategy / execution / monitoring は拡張用のパッケージプレースホルダとして用意されています。

---

## 参考 API（抜粋）

- kabusys.config
  - settings: Settings インスタンス
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env, log_level, is_live, is_paper, is_dev

- kabusys.data.schema
  - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
  - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection

- kabusys.data.audit
  - init_audit_schema(conn: duckdb.DuckDBPyConnection) -> None
  - init_audit_db(db_path: str | Path) -> duckdb.DuckDBPyConnection

---

## 最後に

このリポジトリは、自動売買基盤のコアとなるスキーマと設定管理の骨格を提供します。戦略実装、実際の発注ロジック、監視・アラート機能などはこの上に組み立ててください。質問やドキュメントの追記要望があればお知らせください。