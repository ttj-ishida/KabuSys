# KabuSys

日本株向け自動売買システム（KabuSys）。マーケットデータ取得、データ保管（DuckDB）、特徴量生成、シグナル生成、発注・約定管理、監視など自動売買に必要な基盤を段階的に実装することを目的としたパッケージです。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / 設定の集中管理
  - .env / .env.local を自動読み込み（プロジェクトルートを基準に探索）
  - 必須環境変数を Settings クラスで取得
  - 環境（development / paper_trading / live）やログレベルのバリデーション
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution の 4 層テーブルを定義
  - インデックス作成、外部キー依存を考慮したテーブル作成順を用意
  - init_schema() による冪等的な初期化
- パッケージ構造（将来的に戦略、実行、監視モジュールを配置）
  - kabuys.data（データ操作）
  - kabuys.strategy（戦略）
  - kabuys.execution（発注等）
  - kabuys.monitoring（監視・ログ・通知）

---

## 必要要件

- Python 3.10+
- duckdb（データベース操作に使用）
- （将来的に）API クライアントや Slack 等のライブラリが必要になる可能性あり

依存パッケージはプロジェクトの requirements.txt / pyproject.toml に合わせてインストールしてください。最低限 DuckDB を使う場合は次のようにインストールします:

```
pip install duckdb
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンする

   ```
   git clone <repo-url>
   cd <repo-directory>
   ```

2. 仮想環境を作成して有効化（推奨）

   macOS / Linux:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. 必要なパッケージをインストール

   ```
   pip install -r requirements.txt
   ```

   もしくは最小限:
   ```
   pip install duckdb
   ```

4. 環境変数を設定する
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として設定を置くと、自動で読み込まれます。
   - `.env.local` は `.env` を上書きするためのローカル専用設定に使えます。

---

## 環境変数（主なもの）

以下のキーはコード中で参照されています。必須は Settings クラスの _require を通して取得され、未設定時は例外が発生します。

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視系 SQLite パス（既定: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（既定: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（既定: INFO）

.env の自動ロードを無効化したい場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の簡易例 (.env.example の形でプロジェクトに置くことを推奨):

```
JQUANTS_REFRESH_TOKEN="xxxxxxxxxxxxxxxx"
KABU_API_PASSWORD="your_kabu_password"
KABU_API_BASE_URL="http://localhost:18080/kabusapi"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"
KABUSYS_ENV="development"
LOG_LEVEL="INFO"
```

自動読み込みの挙動:
- プロジェクトルート（.git または pyproject.toml を基準）を起点に `.env` → `.env.local` の順で読み込みます。
- 既存の OS 環境変数は保護されます（上書きされません）。`.env.local` は override を許可しますが、OS 環境変数に対しては保護されます。
- 行パースはシェル互換の簡易ルールをサポート（export プレフィックス、クォート、インラインコメント扱い等）。

---

## 使い方（例）

- Settings を使って環境設定を参照する

```python
from kabusys.config import settings

token = settings.jquants_refresh_token
api_base = settings.kabu_api_base_url
if settings.is_live:
    print("ライブモードです")
```

- DuckDB スキーマの初期化

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# ファイルベースの DB を初期化（パスは settings.duckdb_path）
conn = init_schema(settings.duckdb_path)

# 以後、conn を用いてクエリ実行
res = conn.execute("SELECT count(*) FROM prices_daily").fetchall()
print(res)
```

- 既存 DB への接続（スキーマ初期化は行わない）

```python
conn = get_connection(settings.duckdb_path)
```

※ 本リポジトリは基盤ライブラリに注力しており、実際のデータ取得・戦略・発注処理は各モジュール（data/ strategy/ execution/ monitoring）内で今後実装されます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py             # 環境変数・Settings 管理（自動 .env ロード）
    - data/
      - __init__.py
      - schema.py          # DuckDB スキーマ定義・初期化
    - strategy/
      - __init__.py        # 戦略関連のエントリ（今後実装）
    - execution/
      - __init__.py        # 発注・実行関連のエントリ（今後実装）
    - monitoring/
      - __init__.py        # 監視・通知関連のエントリ（今後実装）

その他:
- .env.example（存在する場合）: 環境変数サンプル
- pyproject.toml / requirements.txt（存在すれば依存管理）

---

## 開発・運用上の注意

- init_schema は冪等であり、既存テーブルを上書きしません。初回だけ呼び出してください。
- .env の自動読み込みは便利ですが、CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- settings の必須値が未設定の場合、ValueError を送出します。運用時は必須環境変数の設定を必ず確認してください。
- DuckDB ファイルパスの親ディレクトリが存在しない場合、init_schema が自動で作成します。

---

## 今後の拡張案（参考）

- 市場データ取得ジョブ（J-Quants / kabu API からの定期取得）
- 戦略モジュール（特徴量生成、シグナル生成）
- 発注実行（kabuステーション API 経由）
- 監視・アラート（Slack 通知・監査ログ）
- ユニットテスト・CI（自動テスト、Lint、フォーマッタ）

---

この README は現状のコードベース（config と data.schema の主要機能）に基づいています。実装が進むに従って、使い方・セットアップ・依存関係のセクションを更新してください。