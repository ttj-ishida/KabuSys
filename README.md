# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（ライブラリ）です。  
本リポジトリは主に設定読み込み・環境管理の実装と、取引ロジック・データ・実行・監視を扱うサブパッケージのスケルトンを提供します。

バージョン: 0.1.0

---

## 概要

- パッケージ名: `kabusys`
- 目的: J-Quants / kabuステーション / Slack / ローカルDB 等と連携する日本株自動売買システムの基盤。
- 現状: 設定読み込み（.env）や環境管理を中心に実装済み。`data`、`strategy`、`execution`、`monitoring` の各サブパッケージを用意しており、ここに実装を追加していきます。

---

## 主な機能

- .env ファイルと OS 環境変数からの設定読み込み（自動ロード）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
  - プロジェクトルート検出基準: 親ディレクトリに `.git` または `pyproject.toml` が存在する場所をルートとする
- 柔軟な .env パーサ
  - `export KEY=val` 形式対応
  - シングル/ダブルクォート内のエスケープ処理対応
  - クォートなしの行でのコメント（`#`）処理（直前が空白またはタブの場合はコメントとみなす）
- 設定アクセス用の `Settings` クラス
  - J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル などをプロパティで取得
  - 必須設定が未定義の場合は例外を発生させる（明示的にエラーがわかる）
  - 環境種別は `development`, `paper_trading`, `live` のいずれか
  - ログレベルは `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` のいずれか

---

## 要求環境

- Python 3.10 以上（型注釈に PEP 604 の `|` を使用しているため）
- 必要な外部ライブラリは個別機能実装により追加される可能性があります（例: duckdb 等）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <リポジトリURL>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS / Linux: source .venv/bin/activate

3. 開発環境にインストール（プロジェクトに pyproject.toml / setup があれば）
   - 開発中: python -m pip install -e .
   - または通常インストール: python -m pip install .

4. .env の準備
   - プロジェクトルートに `.env`（必須キーを設定）と任意で `.env.local` を作成
   - `.env.local` は `.env` の上書き（OS 環境変数より優先）
   - 自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境に設定

5. 必須環境変数の設定（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - 上記は `.env` に書くか OS 環境変数として設定してください

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、デフォルト: development) — 有効値: `development`, `paper_trading`, `live`
- LOG_LEVEL (任意、デフォルト: INFO) — 有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む挙動を無効化できます

---

## 使い方（基本）

設定は `kabusys.config.settings` 経由で取得します。例:

```python
from kabusys.config import settings

# トークン取得（未設定なら ValueError）
token = settings.jquants_refresh_token

# kabu API ベース URL（デフォルトあり）
base = settings.kabu_api_base_url

# 環境判定
if settings.is_live:
    print("運用モード: live")
elif settings.is_paper:
    print("ペーパートレードモード")
else:
    print("開発モード")

# DB パス
duckdb_file = settings.duckdb_path
sqlite_file = settings.sqlite_path
```

.env ファイルのパースは次の特徴を持ちます:
- `export KEY=val` 形式を許容
- クォートされた値ではバックスラッシュエスケープを解釈
- クォートされていない値では `#` の直前にスペース／タブがある場合に以降をコメントとして無視

---

## ディレクトリ構成

プロジェクトの主要ファイル／ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py        # パッケージ初期化（__version__ = "0.1.0"）
    - config.py          # 環境変数・設定管理（自動 .env 読み込み / Settings クラス）
    - data/
      - __init__.py      # データ関連モジュール用プレースホルダ
    - strategy/
      - __init__.py      # 戦略ロジック用プレースホルダ
    - execution/
      - __init__.py      # 注文実行（kabuステーション等）用プレースホルダ
    - monitoring/
      - __init__.py      # 監視・モニタリング用プレースホルダ

その他:
- .env, .env.local      # (プロジェクトルートに配置) 環境変数ファイル（例）
- pyproject.toml / setup.cfg / setup.py (存在する場合あり)

---

## 開発メモ

- プロジェクトルートの自動検出は、実行ファイルの場所（`__file__`）を起点に親ディレクトリを探索し `.git` または `pyproject.toml` の有無で判定します。テストや CI でルート検出を無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `Settings` のプロパティは必須値が未設定の場合に明示的に例外を投げるため、起動時に必要な設定が揃っていることを早期に検出できます。
- サブパッケージ（data, strategy, execution, monitoring）に具体的な実装を追加していくことで、完全な自動売買システムを構築します。

---

ご不明点や追加してほしいドキュメント項目があれば教えてください。README の拡充（例: .env.example ファイルのテンプレート、実行コマンド例、CI 設定など）も対応できます。