# KabuSys

日本株自動売買システム（KabuSys）の軽量ライブラリ・コアモジュール群です。  
本リポジトリはデータ層（DuckDBスキーマ定義）、設定管理、戦略/実行/モニタリングのためのパッケージ骨子を含みます。

バージョン: 0.1.0

---

## 概要

- 日本株の自動売買システムを構築するための基礎的なモジュール群。
- データレイヤー（Raw / Processed / Feature / Execution）向けの DuckDB スキーマ定義と初期化処理を提供。
- 環境変数 / .env ファイルからの設定読み込みを行う Settings クラスを提供。
- 将来的に strategy、execution、monitoring 用のモジュールに機能を追加するためのパッケージ構成。

---

## 主な機能

- 環境変数管理
  - .env / .env.local を自動で読み込み（プロジェクトルートの検出: .git または pyproject.toml を起点）
  - 必須設定の取得とバリデーション（Settings クラス）
  - 自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

- DuckDB スキーマ管理
  - raw / processed / feature / execution の各レイヤーのテーブル DDL を定義
  - インデックス定義とテーブル作成の冪等な初期化関数 init_schema()
  - 既存 DB へ接続するための get_connection()

- パッケージ構造
  - kabusys.data（データ・スキーマ）
  - kabusys.strategy（戦略）
  - kabusys.execution（発注/実行）
  - kabusys.monitoring（監視/ログ・メトリクス）
  - kabusys.config（環境設定）

---

## 要件

- Python 3.10 以上（型ヒントの Union 表現等を使用）
- duckdb Python パッケージ

必要に応じて、Slack API クライアントや kabu API 用クライアント等をプロジェクトに追加してください（本コードベースでは依存を明示していません）。

---

## セットアップ手順

1. リポジトリをクローンします。

   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境を作成して有効化します（例: venv）:

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストールします。最小限は duckdb：

   ```
   pip install duckdb
   ```

   プロジェクトに requirements.txt や pyproject.toml がある場合は、それに従ってインストールしてください（例: pip install -r requirements.txt または pip install -e .）。

4. 環境変数を設定します。
   - プロジェクトルートに `.env`（任意）や `.env.local`（開発用上書き）を置くと、自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

---

## 環境変数（主なキー）

下記キーは Settings クラスで参照されます。プロジェクトに応じて .env を作成してください。

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API のパスワード
- KABU_API_BASE_URL（任意、デフォルト: http://localhost:18080/kabusapi）: kabu API のベース URL
- SLACK_BOT_TOKEN（必須）: Slack Bot トークン
- SLACK_CHANNEL_ID（必須）: 通知先 Slack チャンネル ID
- DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）: DuckDB ファイルパス（:memory: も可）
- SQLITE_PATH（任意、デフォルト: data/monitoring.db）: 監視用 SQLite パス
- KABUSYS_ENV（任意、デフォルト: development）: 有効値 = development / paper_trading / live
- LOG_LEVEL（任意、デフォルト: INFO）: DEBUG / INFO / WARNING / ERROR / CRITICAL

例（.env）:

```
JQUANTS_REFRESH_TOKEN="your_token_here"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースは次の特徴を持ちます（互換性のため）:
- `export KEY=val` 形式を許容
- シングル/ダブルクォート内のバックスラッシュエスケープに対応
- クォートがない場合、`#` の直前が空白またはタブならコメントとして扱う

---

## 使い方（簡易ガイド）

- Settings の利用例

```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須: 未設定なら ValueError
print(settings.duckdb_path)            # Path オブジェクト
print(settings.is_live)                # bool
```

- DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# 初回: スキーマを作成して接続を得る
conn = init_schema(settings.duckdb_path)

# 既存 DB に接続する（スキーマ初期化は行わない）
conn2 = get_connection(settings.duckdb_path)
```

init_schema は冪等（既存テーブルはスキップ）で、db_path の親ディレクトリが存在しない場合は自動作成します。":memory:" を渡すとインメモリ DB を使用します。

- ライフサイクル（例）

  1. 設定（.env）を準備
  2. init_schema() で DB を初期化
  3. データ収集コンポーネントで raw テーブルにデータを格納
  4. ETL/加工で processed / feature テーブルを作成
  5. 戦略で signals を生成し signal_queue にプッシュ
  6. execution コンポーネントで orders/trades/positions を管理
  7. monitoring で portfolio_performance やログを監視・通知

---

## 主要 API の要約

- kabusys.config.settings: アプリケーション設定の読み取り（プロパティとして環境変数を参照）
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

- kabusys.data.schema.init_schema(db_path)
  - DuckDB に対してテーブル/インデックスを作成して接続を返す

- kabusys.data.schema.get_connection(db_path)
  - 既存の DuckDB に接続（スキーマ初期化は行わない）

---

## ディレクトリ構成

（抜粋）

```
src/
  kabusys/
    __init__.py            # パッケージエントリ（__version__ 等）
    config.py              # 環境設定・.env ローダー・Settings
    data/
      __init__.py
      schema.py            # DuckDB スキーマ定義と init_schema/get_connection
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

- schema.py に Raw / Processed / Feature / Execution レイヤー向けの DDL がまとまっています。
- 将来的な機能は各サブパッケージ（strategy、execution、monitoring）に追加してください。

---

## 注意事項 / 補足

- 自動で .env をプロジェクトルート（.git または pyproject.toml を探索して決定）から読み込みます。プロジェクト配布後やテスト時に自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Settings は必須環境変数が未設定の場合 ValueError を送出します。CI / デプロイ環境では必須キーを確実に設定してください。
- DB 初期化は冪等ですが、本番環境ではバックアップや注意深い運用を行ってください。
- 本リポジトリはコアの骨子を提供するものであり、外部 API クライアント（kabu API、J-Quants、Slack 等）の実装は別途追加してください。

---

もし README に追加したい具体的な利用例（実際の戦略サンプル、ETL スクリプト、CI 設定等）があれば教えてください。README をそれに合わせて拡張します。