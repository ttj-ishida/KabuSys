# KabuSys

日本株自動売買システムの基盤ライブラリ（試作版）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム用の Python パッケージの基礎部分です。  
モジュールはデータ取得・戦略・注文実行・監視などの責務に分かれており、環境変数による設定管理や .env ファイルの自動読み込み機能を備えています。

主な目的は、J-Quants・kabuステーション（kabu API）・Slack 等と連携する自動売買アプリケーションの共通インフラを提供することです。

---

## 機能一覧

- 環境変数 / .env ファイルからの設定値読み込み（自動読み込み機能あり）
  - プロジェクトルート（.git / pyproject.toml を探索）を基準に .env / .env.local を読み込む
  - .env のパースはシングル/ダブルクォート、エスケープ、コメント（条件付き）に対応
  - OS 環境変数を保護しつつ .env.local で上書き可能
  - 自動読み込みを無効にするためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- Settings クラスによる型付き・検証付きの設定アクセス
  - J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等を提供
  - 環境（development / paper_trading / live）やログレベルの検証
- パッケージ構成: data / strategy / execution / monitoring のためのモジュールスケルトン

---

## 要求環境

- Python 3.10 以上（型注釈の union `X | Y` を使用しているため）
- 推奨: 仮想環境 (venv / pyenv 等)

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. パッケージを開発モードでインストールします（プロジェクトルートに pyproject.toml / setup がある想定）。

   ```
   pip install -e .
   ```

3. 環境変数を準備します（以下の「設定 (.env)」参照）。

---

## 設定 (.env)

プロジェクトルートに `.env`（および任意で `.env.local`）を配置します。`.env.local` は `.env` の上書き用です。OS 環境変数が優先され、.env の読み込み時に保護されます。

自動読み込みを無効にしたい場合は、実行前に環境変数を設定します:

```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

例: `.env` の最小例

```
# J-Quants
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"

# kabuステーション API
KABU_API_PASSWORD="your_kabu_api_password"
# KABU_API_BASE_URL はデフォルトで http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN="xoxb-xxxxxxxxxx-xxxxxxxxxx-xxxxxxxxxx"
SLACK_CHANNEL_ID="C01234567"

# システム
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO

# DB パス（省略時はデフォルト）
# DUCKDB_PATH=data/kabusys.duckdb
# SQLITE_PATH=data/monitoring.db
```

注意:
- `.env` の行パーサはシングル/ダブルクォートとバックスラッシュエスケープに対応しています。
- クォート無しの値における `#` は、直前がスペース/タブの場合にコメントとして扱われます。

---

## 使い方（サンプル）

設定値をプログラム内で参照する基本例:

```python
from kabusys.config import settings

# 必須キーは取得時に存在チェックされる
jquants_token = settings.jquants_refresh_token
kabu_password = settings.kabu_api_password

# DB パス（デフォルト値あり）
duckdb_path = settings.duckdb_path

# 実行環境の確認
if settings.is_live:
    print("LIVE 環境で実行中")
elif settings.is_paper:
    print("ペーパートレード環境")
else:
    print("開発環境")
```

ログレベルや環境の値は設定時に検証され、不正な値があると ValueError が発生します。

---

## Settings（設定項目の一覧）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants 用の refresh token
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
  - kabu API のベース URL
- SLACK_BOT_TOKEN (必須)
  - Slack ボット用トークン
- SLACK_CHANNEL_ID (必須)
  - 通知先の Slack チャンネル ID
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルパス
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
  - SQLite（監視用）ファイルパス
- KABUSYS_ENV (任意、デフォルト: development)
  - 有効な値: "development", "paper_trading", "live"
- LOG_LEVEL (任意、デフォルト: INFO)
  - 有効な値: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

## 自動 .env 読み込みの挙動

- 読み込み優先順位:
  1. OS 環境変数
  2. .env.local（プロジェクトルート）
  3. .env（プロジェクトルート）
- プロジェクトルートの検出:
  - このパッケージのファイル位置を起点に親ディレクトリを上がり、`.git` または `pyproject.toml` を見つけたディレクトリをプロジェクトルートとします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で利用）。

---

## ディレクトリ構成

（パッケージの主要ファイル）

```
src/
└─ kabusys/
   ├─ __init__.py        # パッケージ情報 (version, __all__)
   ├─ config.py          # 環境変数・設定管理（.env ローダ、Settings）
   ├─ execution/
   │  └─ __init__.py     # 注文実行関連モジュール（スケルトン）
   ├─ strategy/
   │  └─ __init__.py     # 戦略モジュール（スケルトン）
   ├─ data/
   │  └─ __init__.py     # データ取得・管理（スケルトン）
   └─ monitoring/
      └─ __init__.py     # 監視・ログ・DB関連（スケルトン）
```

---

## 開発メモ / 注意点

- Python のバージョンは 3.10 以上を推奨します（typing の `X | Y` を使用）。
- Settings の必須項目は参照時にチェックされ、未設定の場合は ValueError が発生します。CI / デプロイ環境では必須環境変数を確実に設定してください。
- .env のパースは POSIX シェルの export 形式（`export KEY=val`）にも部分対応しています。
- 現在のリポジトリには各サブモジュールの実装はスケルトンの状態です。戦略ロジック・実行ロジック・監視ロジックはそれぞれ実装を追加してください。

---

必要であれば、README に以下の内容を追記できます:
- 具体的な API 呼び出し例（kabu API / J-Quants）や Slack 通知のサンプル
- テスト実行方法、CI 設定例
- デプロイ / 実運用に関する注意（セキュリティ、タイムゾーン、レート制限など）

ご希望があれば追記します。