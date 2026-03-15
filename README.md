# KabuSys

日本株向け自動売買システム（ライブラリ）の骨組み。  
このリポジトリは設定管理やモジュール構成を含む基盤部分を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買を想定したパッケージです。  
主要コンポーネントとして、データ取得（data）、戦略（strategy）、注文実行（execution）、モニタリング（monitoring）用のサブパッケージを持ち、環境変数ベースの設定管理機能を提供します。

主な目的:
- 環境変数 / .env ベースの設定読み込み
- J-Quants / kabuステーション / Slack など外部サービスとの接続設定の管理
- DB パス等のデフォルト設定管理

---

## 機能一覧

- 環境変数と .env ファイルの自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に .env, .env.local を読み込む
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - export プレフィックス、クォート文字（シングル／ダブル）、エスケープ、コメントの取り扱いに対応
- 設定アクセス用オブジェクト `settings`
  - J-Quants トークン、kabu API パスワード、Slack トークン／チャンネル、DB パス、実行環境種別などをプロパティ経由で取得
  - 必須の環境変数が未設定の場合は ValueError を送出して早期検出
- サブパッケージのプレースホルダ
  - kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring

---

## セットアップ手順

基本手順（開発環境想定）:

1. リポジトリをクローン／配置
2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows の場合は .venv\Scripts\activate）
3. パッケージのインストール（ローカル開発インストール）
   - pip install -e .  （パッケージ化されている場合）
4. 環境変数の準備
   - プロジェクトルートに `.env` を作成（後述の例参照）
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 必須がセットされていない場合、settings の該当プロパティアクセスで ValueError が発生します。

注意:
- 自動で .env を読み込む際、OS 環境変数は保護され、.env.local が OS 環境変数を上書きすることはありません（.env はさらに優先度が低い）。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。

---

## 使い方（サンプル）

設定値の取得例:

```python
from kabusys.config import settings

# J-Quants のリフレッシュトークンを取得（未設定なら ValueError）
token = settings.jquants_refresh_token

# kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
base_url = settings.kabu_api_base_url

# 実行環境判定
if settings.is_live:
    print("ライブモードです")
elif settings.is_paper:
    print("ペーパートレードモードです")
```

ログレベルや環境の検証:
- KABUSYS_ENV（小文字可、内部で lower() して検証）
  - 有効値: development, paper_trading, live
- LOG_LEVEL
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

DB のデフォルトパス:
- duckdb: data/kabusys.duckdb
- sqlite (モニタリング用): data/monitoring.db

---

## .env の書き方（例）

基本的な `.env` 例:

```
# J-Quants
JQUANTS_REFRESH_TOKEN="your_refresh_token_here"

# kabu ステーション
KABU_API_PASSWORD='your_kabu_password'

# Slack
SLACK_BOT_TOKEN= xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C12345678

# DB パス（省略可）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development

# ログレベル
LOG_LEVEL=INFO
```

パーシングの注意点:
- 行頭の `export ` はサポートされます（例: export KEY=val）。
- 値がシングルまたはダブルクォートで囲まれている場合、エスケープ（\）を考慮して閉じクォートまでを値として扱います。
- クォート無しの行では `#` が直前にスペースまたはタブがある場合にコメントとみなします（それ以外は値の一部として扱います）。

---

## ディレクトリ構成

現状の主要ファイル・ディレクトリ構成（抜粋）:

```
src/
  kabusys/
    __init__.py          # パッケージ初期化、__version__
    config.py            # 環境変数・設定管理
    data/
      __init__.py        # データ関連モジュール（プレースホルダ）
    strategy/
      __init__.py        # 戦略モジュール（プレースホルダ）
    execution/
      __init__.py        # 注文実行モジュール（プレースホルダ）
    monitoring/
      __init__.py        # モニタリングモジュール（プレースホルダ）
```

---

## 注意事項 / 補足

- settings のプロパティは必要に応じて ValueError を送出します。アプリ起動時に必須環境変数が揃っていることを確認してください。
- 自動 .env 読み込みは、パッケージ内のファイル位置（__file__ を基に）から上位ディレクトリに向かって `.git` または `pyproject.toml` を探し、見つかったルート下の .env / .env.local を読み込みます。プロジェクトルートが特定できない場合は自動ロードはスキップされます。
- まだ各サブパッケージ（data, strategy, execution, monitoring）は実装の起点となる空ファイルであり、具体的なロジックは必要に応じて実装してください。

---

必要があれば、README にセットアップのより詳細な手順（パッケージ化手順、CI、テスト実行方法）、各サブパッケージの使用例や API ドキュメントを追加できます。どの情報を優先して追加しますか？