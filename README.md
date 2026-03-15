# KabuSys

日本株向け自動売買システムのコアライブラリ（骨組み）。  
このリポジトリはデータレイヤ、特徴量レイヤ、戦略・発注レイヤを管理するための基盤モジュール群を提供します。

---

## 概要

KabuSys は日本株の自動売買に必要な以下の要素を想定した内部ライブラリです。

- データ収集・保存（Raw / Processed / Feature 層）
- DuckDB を用いたローカルデータベーススキーマ定義と初期化
- 環境変数ベースの設定管理（.env / .env.local の自動読み込み）
- 発注・モニタリング・戦略用のパッケージ構成（プレースホルダ）

このリポジトリはコアとなるスキーマ・設定管理を実装しており、上位の戦略や実行ロジックはこの基盤に組み込んで拡張します。

---

## 主な機能

- 環境設定管理（`kabusys.config`）
  - .env / .env.local の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）
  - QUANTS / kabu ステーション / Slack / DB パスなどの設定プロパティを提供
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
- DuckDB スキーマ定義と初期化（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution の各レイヤに対応したテーブル群を定義
  - インデックス作成、外部キー制約、冪等的なテーブル作成処理を提供
  - `init_schema(db_path)` による DB 初期化および接続取得、`get_connection(db_path)` による接続取得
- パッケージ構成（拡張ポイント）
  - `kabusys.data`（データ処理）
  - `kabusys.strategy`（戦略）
  - `kabusys.execution`（発注ロジック）
  - `kabusys.monitoring`（監視・ログ格納等）

---

## 要件

- Python 3.10+（typing: `Path | None` などの構文を使用）
- duckdb（DuckDB Python パッケージ）
- （戦略や実行に応じて追加ライブラリが必要）

pip で最低限必要なパッケージを入れる例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
```

プロジェクトに requirements.txt や pyproject.toml がある場合はそちらに従ってください。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数ファイルを用意する
   - プロジェクトルート（.git または pyproject.toml がある場所）を基準に `.env`、`.env.local` を読み込みます。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。
4. DuckDB スキーマを初期化する（後述の使用例参照）

---

## 環境変数（主なキー）

kabusys.config.Settings が参照する主な環境変数一覧（必須のものには注意）:

必須 (未設定時は例外が発生します)
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト値あり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)、デフォルトは development
- LOG_LEVEL — ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)、デフォルトは INFO

.env のパース仕様（主なポイント）
- コメント行（先頭が `#`）や空行は無視
- `export KEY=val` 形式に対応
- クォート付きの値はエスケープ `\` に対応して閉じクォートまでを値とする
- クォート無しの行では `#` の前にスペース/タブがある場合以降をコメントとして無視

---

## 使い方（簡単な例）

1) 設定の読み込み（自動的に .env / .env.local をロードします）

```python
from kabusys.config import settings

# 必須項目にアクセスすると未設定時に ValueError が出ます
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.env)
```

2) DuckDB スキーマを初期化する

```python
from kabusys.data.schema import init_schema, get_connection
from pathlib import Path

# ファイル DB を初期化（必要なら parent ディレクトリを自動作成）
db_path = Path("data/kabusys.duckdb")
conn = init_schema(db_path)  # 初回はこれでテーブルとインデックスが作成される

# メモリ DB を使う場合
mem_conn = init_schema(":memory:")
```

3) 既存 DB に接続する（初期化は行わない）

```python
conn = get_connection("data/kabusys.duckdb")
# conn.execute("SELECT count(*) FROM prices_daily").fetchall()
```

4) 自動ロードを無効にしたい場合（テスト等）

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print('auto load disabled')"
```

---

## ディレクトリ構成

プロジェクト内の主なファイル・ディレクトリ（このリポジトリの現状に基づく）:

- src/kabusys/
  - __init__.py              — パッケージ初期化（バージョン等）
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py              — DuckDB スキーマ定義・初期化（raw/processed/feature/execution）
  - strategy/
    - __init__.py            — 戦略用モジュール（拡張ポイント）
  - execution/
    - __init__.py            — 発注/実行用モジュール（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視用モジュール（拡張ポイント）

README 等やドキュメント (例: DataSchema.md) があればプロジェクトルートに配置する想定です。

---

## 開発メモ / 注意事項

- init_schema() は冪等です。既にテーブルが存在する場合はスキップされます。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を検出）を基準に行います。CWD に依存しない探索ロジックです。
- 環境 `KABUSYS_ENV` は "development", "paper_trading", "live" のいずれかでなければエラーになります。
- ログレベル `LOG_LEVEL` は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" のいずれかでなければエラーになります。
- .env に OS の既存環境変数を上書きしたくない場合、.env の読み込みは OS 環境変数が保護されます（.env.local は override=True ですが保護リストを考慮します）。

---

## 貢献・ライセンス

この README は現在のソースに基づく簡易ドキュメントです。戦略や実行ロジック、外部 API との連携部分は拡張実装してください。ライセンスや貢献ルールはプロジェクトルートに LICENSE / CONTRIBUTING.md を追加して管理してください。

---

必要であれば、.env.example のテンプレートやさらなる使用例（戦略→シグナル→発注フロー、監視 DB 連携など）を追加して README を拡張します。どの部分を詳しく書きたいか教えてください。