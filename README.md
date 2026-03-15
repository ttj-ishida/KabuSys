# KabuSys

日本株向けの自動売買システム（KabuSys）  
バージョン: 0.1.0

このリポジトリは、環境変数管理や設定読み込みの仕組みを中心とした基盤コードと、データ取得・戦略・注文実行・監視のためのサブパッケージの雛形を含みます。

---

## 概要

KabuSys は日本株の自動売買システム向けのライブラリ/フレームワークです。現時点では主に以下を提供します:

- 環境変数／設定の読み込みと管理（.env/.env.local の自動読み込み）
- アプリケーション設定（J-Quants や kabuステーション、Slack、DB パスなど）のプロパティアクセス
- ディレクトリ構成として、データ取得、戦略、実行、監視のためのサブパッケージの雛形

（戦略ロジックや実行ロジックはサブパッケージ内に実装して拡張します。）

---

## 機能一覧

- 環境変数の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能
- .env パーサーの特徴
  - `export KEY=val` 形式に対応
  - シングル/ダブルクォートされた値（エスケープシーケンス対応）
  - 非クォート値のインラインコメント対応（`#` が行頭もしくは直前が空白/タブの場合のみコメントと判断）
- Settings クラス経由で型付きにアクセス可能
  - 必須値取得時は未設定なら例外を送出（ValueError）
  - 環境（development / paper_trading / live）とログレベルのバリデーション
  - DB パスなどのデフォルト値の提供

---

## セットアップ

前提: Python 3.10 以上（PEP 604 の型記法などを使用しているため）

1. リポジトリをクローンしてプロジェクトルートへ移動
   ```bash
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意だが推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. パッケージをインストール（ローカル開発）
   ```bash
   pip install -e .
   ```
   またはプロダクション向けに:
   ```bash
   pip install .
   ```

4. 必要な環境変数を設定
   - `.env` または `.env.local` をプロジェクトルートに置くか、OS 環境変数として設定します。
   - 主要な必須環境変数（下記の「環境変数と設定」参照）

---

## 環境変数と設定

自動読み込みの動作
- 起点はこのパッケージ内のコード位置から親ディレクトリを辿って `.git` または `pyproject.toml` を見つけ、そのディレクトリをプロジェクトルートとみなします。
- プロジェクトルートが見つからない場合は自動読み込みをスキップします。
- OS 環境変数が優先され、`.env` → `.env.local` の順に読み込み（.env.local は .env の上書き、ただし既に OS にあるキーは保護される）。

重要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack の投稿先チャンネル ID

任意 / デフォルト値
- KABU_API_BASE_URL — デフォルト: `http://localhost:18080/kabusapi`
- DUCKDB_PATH — デフォルト: `data/kabusys.duckdb`
- SQLITE_PATH — デフォルト: `data/monitoring.db`
- KABUSYS_ENV — `development`（デフォルト）/ `paper_trading` / `live`
- LOG_LEVEL — `INFO`（デフォルト、許容: DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — `1` を設定すると自動で .env の読み込みを無効化

.env のパース上の注意
- `export KEY=VALUE` を許容
- 値がクォートされた場合はクォート内部を適切にデコード（バックスラッシュエスケープ等）
- クォートなしの値では `#` が行頭または直前が空白/タブの場合にコメントと判定

.env の例（.env.example）
```
JQUANTS_REFRESH_TOKEN="your-jquants-refresh-token"
KABU_API_PASSWORD="your-kabu-password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方

Settings の基本的な使い方は以下の通りです。

例: 設定を読み取る
```python
from kabusys.config import settings

# 必須値の取得（未設定なら ValueError）
token = settings.jquants_refresh_token
kabu_password = settings.kabu_api_password

# オプション値（デフォルトがある）
api_base = settings.kabu_api_base_url
db_path = settings.duckdb_path  # pathlib.Path を返す

# 環境判定ユーティリティ
if settings.is_live:
    print("ライブ運用モード")
elif settings.is_paper:
    print("ペーパートレーディングモード")
else:
    print("開発モード")
```

パッケージ読み込み:
```python
import kabusys
print(kabusys.__version__)  # 0.1.0
```

サブパッケージ（雛形）
- kabusys.data: データ取得・保存用
- kabusys.strategy: 戦略（シグナル生成）用
- kabusys.execution: 注文実行・ブローカー連携用
- kabusys.monitoring: ログ・監視・メトリクス用

各サブパッケージに具体的な実装を追加してシステムを構築してください。

---

## ディレクトリ構成

プロジェクト内の主要ファイルとディレクトリは以下のようになっています:

```
src/
  kabusys/
    __init__.py         # パッケージ定義（__version__ 等）
    config.py           # 環境変数・設定管理
    data/
      __init__.py
      ...               # データ関連実装を追加
    strategy/
      __init__.py
      ...               # 戦略実装を追加
    execution/
      __init__.py
      ...               # 注文実行の実装を追加
    monitoring/
      __init__.py
      ...               # 監視・DB等の実装を追加
.env.example
pyproject.toml (※存在する場合、プロジェクトルート判定に使用)
.git/           (※存在する場合、プロジェクトルート判定に使用)
```

---

## トラブルシューティング

- ValueError: 環境変数が設定されていない場合  
  - settings の必須プロパティ（例: jquants_refresh_token）にアクセスすると、未設定時に ValueError を送出します。`.env` を作成するか OS 環境変数を設定してください。

- .env が読み込まれない  
  - プロジェクトルートが `.git` または `pyproject.toml` のいずれも見つからない場合、自動読み込みはスキップされます。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` が設定されていると自動読み込みは無効です。

- .env の読み込みで警告が出る  
  - ファイルのオープンに失敗した場合、警告を出して読み込みをスキップします。権限やエンコーディングを確認してください（UTF-8 を期待します）。

---

必要に応じて、戦略のテンプレート、実行フロー、監視ダッシュボードや DB スキーマの例などの追加ドキュメントを作成します。初期状態では設定管理とパッケージ構成の土台が整っているので、ここから実運用ロジックを実装してください。