# KabuSys

日本株向けの自動売買システム向けライブラリ。データ収集・スキーマ定義・環境設定・戦略・発注・監視のための基盤機能を提供します（まだ開発初期: v0.1.0）。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株自動売買システムのコアコンポーネントを提供する Python パッケージです。  
主な目的は以下の通りです。

- 市場データ・ファンダメンタル・ニュース・約定などのデータ格納用 DuckDB スキーマを提供
- 環境変数ベースの設定管理（.env 自動読み込み、必須チェック等）
- 戦略・発注・監視（モジュールの骨格を提供）

現在はデータスキーマと設定周りが整備されています。他モジュール（strategy、execution、monitoring）は今後拡張されます。

---

## 機能一覧

- 環境設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動で読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）
  - 必須環境変数が未設定の場合は明示的にエラーを出す
  - 環境（development / paper_trading / live）およびログレベルの検証
- DuckDB スキーマ管理（冪等にテーブル作成）
  - Raw / Processed / Feature / Execution 層に分かれたテーブル定義
  - インデックス作成
  - 初期化用 API: init_schema(db_path)
- パッケージ構成の土台（strategy、execution、monitoring 各モジュールの名前空間）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に union 型演算子 `|` を使用）
- git（プロジェクトルート検出のために推奨）

1. リポジトリをクローンして移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最低限 DuckDB が必要です:
     ```
     pip install duckdb
     ```
   - 実運用で Slack 連携等を使う場合は追加パッケージ（python-slack-sdk など）をインストールしてください。

   - パッケージ開発時は editable インストール:
     ```
     pip install -e .
     ```
     （プロジェクトに pyproject.toml / setup.cfg / setup.py がある場合）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env`（および必要なら `.env.local`）を作成すると自動で読み込まれます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   - 必要な環境変数（例）
     ```
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     # KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     # DB パスは省略可（デフォルトは data/kabusys.duckdb）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     # 環境: development | paper_trading | live
     KABUSYS_ENV=development
     # ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL
     LOG_LEVEL=INFO
     ```

---

## 使い方

ここでは代表的な利用例を示します。

1. 設定値の取得
   ```python
   from kabusys.config import settings

   token = settings.jquants_refresh_token
   base_url = settings.kabu_api_base_url
   is_live = settings.is_live
   ```

   - settings はプロパティ経由で環境変数の値を返します。必須変数が未設定の場合は ValueError が発生します。

2. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返します
   # conn は duckdb.DuckDBPyConnection オブジェクト
   ```

   - db_path に ":memory:" を渡すとインメモリ DB を使用します。
   - 初回実行時に親ディレクトリがなければ自動で作成されます。
   - 既にテーブルがある場合はスキップします（冪等）。

3. 既存 DB へ接続（スキーマは作成しない）
   ```python
   from kabusys.data.schema import get_connection
   conn = get_connection("data/kabusys.duckdb")
   ```

4. .env 読み込みの挙動
   - プロジェクトルートを、自身のファイル位置から親ディレクトリ方向へ探索し、`.git` または `pyproject.toml` を見つけたディレクトリをルートと判断します。
   - 読み込み順序: OS 環境変数 > .env.local > .env
     - .env は既存の OS 環境変数を上書きしません（override=False）
     - .env.local は上書き可能（override=True）
   - `.env` のパースは一般的な `KEY=VALUE`、`export KEY=VALUE`、シングル/ダブルクォート、エスケープ、行コメント等に対応しています。

---

## ディレクトリ構成

プロジェクト内の主要ファイル・ディレクトリ構成（抜粋）:

```
.
├─ pyproject.toml / setup.cfg / .git (いずれかでプロジェクトルートを判定)
└─ src/
   └─ kabusys/
      ├─ __init__.py           # パッケージ定義（__version__ = "0.1.0"）
      ├─ config.py             # 環境変数・設定管理
      ├─ data/
      │  ├─ __init__.py
      │  └─ schema.py          # DuckDB スキーマ定義と init_schema / get_connection
      ├─ strategy/
      │  └─ __init__.py        # 戦略モジュール（拡張ポイント）
      ├─ execution/
      │  └─ __init__.py        # 発注関連（拡張ポイント）
      └─ monitoring/
         └─ __init__.py        # 監視・ログ連携（拡張ポイント）
```

主にデータ層（DuckDB スキーマ）と設定周りが実装されています。strategy / execution / monitoring は骨組み（namespace）として存在し、今後の実装で機能が追加されます。

---

## 追加情報・注意点

- 環境変数の検証
  - KABUSYS_ENV の有効値: "development", "paper_trading", "live"
  - LOG_LEVEL の有効値: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
- .env の自動読み込みは便利ですが、テストや CI 等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- DuckDB を運用で用いる場合はバックアップ・ファイル管理に注意してください。
- Slack 連携や kabu API 連携等は別途ライブラリの追加や実装が必要です（このリポジトリでは設定と土台のみ提供）。

---

フィードバックや拡張の提案があれば issue または PR を送ってください。