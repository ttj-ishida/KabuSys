# KabuSys

日本株向けの自動売買システム骨組み (KabuSys) のリポジトリ。  
このパッケージはデータ取得、戦略実装、注文実行、監視のためのモジュール構成を提供します（現時点では構造と設定管理が実装されています）。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムを構築するためのライブラリ/骨組みです。  
設定管理や環境変数の読み込みロジックを備え、J-Quants / kabuステーション / Slack などの外部サービスに接続するための設定項目を提供します。プロジェクトルートを自動検出し、`.env` / `.env.local` から環境変数を読み込む機能があります。

主な目的:
- 環境設定の一元管理
- 自動売買の各コンポーネント（データ / 戦略 / 実行 / 監視）を分離したパッケージ構成の提供

---

## 機能一覧

- 環境変数・設定の読み込みとラッパー（`kabusys.config.Settings`）
  - 自動でプロジェクトルートを検出して `.env` / `.env.local` を読み込む
  - 必須設定の検査（未設定時は例外を発生）
  - 環境（development / paper_trading / live）判定ヘルパー
  - ログレベル検査
  - データベースパス（DuckDB / SQLite）の既定値サポート
- `.env` ファイルの柔軟なパース
  - `export KEY=val` 形式に対応
  - シングル/ダブルクォートとバックスラッシュエスケープの処理
  - コメントの取り扱い（スペース前の `#` をコメントとみなす等）
- パッケージ構成（拡張しやすいモジュール分割）
  - data / strategy / execution / monitoring

---

## 動作要件

- Python 3.10 以上（型ヒントで `X | Y` を使用しているため）

---

## セットアップ手順

1. リポジトリをクローン・移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージをインストール（開発インストール）
   - python -m pip install -e .

4. 必要な環境変数を設定
   - プロジェクトルートに `.env` を用意するか、環境変数として設定します。
   - 自動読み込みはデフォルトで有効です。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（必須・推奨）

Settings クラスで参照される主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack ボットのトークン
- SLACK_CHANNEL_ID — 通知に使う Slack チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV — 実行環境。`development`（既定）, `paper_trading`, `live`
- LOG_LEVEL — ログレベル。`INFO`（既定）など。許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL
- KABU_API_BASE_URL — kabuAPI のベース URL（既定: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB のファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — SQLite のファイルパス（既定: data/monitoring.db）

例: `.env`（簡易例）
```
# .env の例
JQUANTS_REFRESH_TOKEN='your_jquants_refresh_token'
KABU_API_PASSWORD='your_kabu_api_password'
SLACK_BOT_TOKEN='xoxb-...'
SLACK_CHANNEL_ID='C01234567'
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

注意点（.env のパースルール）
- `export KEY=val` 形式をサポートします。
- 値をシングル/ダブルクォートで囲んだ場合は、バックスラッシュでのエスケープを考慮して閉じクォートまでを値として扱います（その後の文字列は無視）。
- クォート無しの場合、`#` によるコメントは、その `#` の直前がスペースまたはタブである場合にのみコメントとみなします。

.env の読み込み優先順位:
- OS 環境変数 > .env.local > .env
- 実装上、まず OS 環境変数のセットが保護キー（protected）として扱われ、`.env` は未設定のキーのみ設定し、`.env.local` は既存のキーを上書き（ただし OS 環境変数は上書きされない）します。

---

## 使い方

基本的な設定取得例:

```python
from kabusys.config import settings

# 文字列設定を取得（未設定の場合は ValueError が送出される）
token = settings.jquants_refresh_token
password = settings.kabu_api_password

# オプション設定（パス等）
duckdb_path = settings.duckdb_path  # pathlib.Path
sqlite_path = settings.sqlite_path

# 環境判定
if settings.is_live:
    print("LIVE mode")
elif settings.is_paper:
    print("Paper trading")
else:
    print("Development")

# ログレベル
level = settings.log_level
```

自動読み込みを無効にしてテスト等で自前の環境を制御したい場合:
- 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定しておくと `.env` の自動ロードをスキップします。

プロジェクトルートの検出:
- 自動でプロジェクトルートを探すため、`.git` または `pyproject.toml` があるディレクトリをルートとして扱います。見つからない場合は自動ロードをスキップします。

---

## ディレクトリ構成

パッケージの主要なファイル・ディレクトリ構成（抜粋）:

```
src/
  kabusys/
    __init__.py          # パッケージ初期化 (version, __all__)
    config.py            # 環境変数・設定管理
    data/
      __init__.py
      ...                # データ取得関連を実装する場所
    strategy/
      __init__.py
      ...                # 売買戦略を実装する場所
    execution/
      __init__.py
      ...                # 注文送信などの実装場所
    monitoring/
      __init__.py
      ...                # 監視・ログ・通知関連
```

主要モジュール:
- kabusys.config — 設定管理（自動 .env 読み込み、Settings クラス）
- kabusys.data — データ取得・前処理用（拡張領域）
- kabusys.strategy — 戦略ロジック（拡張領域）
- kabusys.execution — 注文実行ロジック（拡張領域）
- kabusys.monitoring — 監視・通知（拡張領域）

---

## 開発メモ / 補足

- .env の自動読み込みは、プロジェクトルート（`.git` または `pyproject.toml`）を基準に行われます。パッケージを別の場所から参照するケースやテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用してください。
- `.env.local` はローカルの上書き設定用です。OS 環境変数は上書きされません。
- 現時点ではフレームワークの土台と設定管理が中心です。データ取得、戦略、実行、監視の各モジュールは用途に応じて実装を追加してください。

---

必要があれば README に動作例や CI / デプロイ手順、Slack通知サンプル、kabuAPI との接続サンプルなどの追加セクションを追記します。どの項目を優先して追加しますか？