# KabuSys

KabuSys は日本株向けの自動売買システムの基盤ライブラリです。データ取得、戦略（strategy）、注文実行（execution）、監視（monitoring）などのコンポーネントを含むパッケージ構成で、環境変数ベースの設定管理を備えています。

バージョン: 0.1.0

---

## 概要

- Python パッケージとして提供される自動売買フレームワークの骨格です。
- 環境変数（.env／OS環境変数）から設定を読み込み、J-Quants、kabuステーション（kabu API）、Slack、ローカルデータベース設定などを扱います。
- パッケージ配布後も動作するよう、プロジェクトルート（.git または pyproject.toml）を基準に .env を自動検出して読み込みます。

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 必須環境変数チェック（未設定時は ValueError）
  - 設定値のデフォルトと検証（KABUSYS_ENV, LOG_LEVEL など）
  - パス（DuckDB/SQLite）の Path オブジェクト返却
  - is_live / is_paper / is_dev などのヘルパー

- パッケージ構造（拡張ポイント）
  - data: データ取得・保管関連
  - strategy: 売買戦略の実装
  - execution: 注文実行ロジック
  - monitoring: 監視・アラート関連

---

## 必要条件

- Python 3.9+
- （任意）duckdb や sqlite にアクセスするパッケージは各処理で必要に応じて追加

（依存関係は現状のソースからは明示されていません。実際の利用時に必要パッケージを pyproject.toml / requirements.txt に追加してください）

---

## セットアップ手順

1. リポジトリをクローン：
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 開発インストール（推奨）：
   ```
   python -m pip install -e .
   ```
   あるいは通常インストール：
   ```
   python -m pip install .
   ```

3. .env の作成：
   リポジトリルートに `.env`（および必要なら `.env.local`）を作成します。自動読み込みはプロジェクトルートを .git または pyproject.toml により検出します。

4. 必須環境変数を設定：
   下記「環境変数」の節を参照して必須項目を設定してください。

---

## 環境変数（設定項目）

以下は Settings クラスで参照される主な環境変数です。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトあり）:
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: デフォルト "data/monitoring.db"
- KABUSYS_ENV: デフォルト "development"。有効値は "development", "paper_trading", "live"
- LOG_LEVEL: デフォルト "INFO"。有効値は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"

例（.env）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"

# kabu API
KABU_API_PASSWORD="your_kabu_password"
KABU_API_BASE_URL="http://localhost:18080/kabusapi"

# Slack
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"

# DB paths (任意)
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

パーシングの補足:
- `export KEY=val` 形式をサポート
- クォート（' または "）に対応し、バックスラッシュエスケープも処理
- コメントは行頭 `#` または 値における `#`（直前が空白またはタブの場合）として扱われます

自動読み込みの動作:
- OS 環境変数 > `.env.local` > `.env` の優先順位でロードされます
- OS 環境変数は上書きされません（保護）
- 自動読み込みを無効化するには環境変数を設定：
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 使い方（簡単な例）

- パッケージ情報の参照:
  ```python
  import kabusys
  print(kabusys.__version__)  # 0.1.0
  ```

- 設定の読み取り:
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  base_url = settings.kabu_api_base_url
  is_live = settings.is_live
  db_path = settings.duckdb_path  # pathlib.Path オブジェクト
  ```

- 各モジュールの拡張ポイント:
  - kabusys.data: データ取得や DB 保存ロジックを実装
  - kabusys.strategy: 売買戦略（シグナル生成等）を実装
  - kabusys.execution: 注文作成・送信・約定管理を実装
  - kabusys.monitoring: ログ・Slack 通知・監視用処理を実装

注意:
- Settings の必須変数が未設定だとプロパティアクセス時に ValueError が発生します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うか、必要変数をモック／設定してください。

---

## ディレクトリ構成

リポジトリの主要ファイル／ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py              # パッケージ初期化（バージョン等）
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py            # データ関連モジュール（拡張用）
    - strategy/
      - __init__.py            # 戦略モジュール（拡張用）
    - execution/
      - __init__.py            # 注文実行モジュール（拡張用）
    - monitoring/
      - __init__.py            # 監視モジュール（拡張用）
- pyproject.toml / setup.cfg / setup.py（プロジェクト設定ファイル 等）
- .env.example（利用する場合。README の .env 記述を参照）

---

## 開発上の注意点

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。パッケージをインストールして別場所から import する場合や、テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用すると良いです。
- Settings クラスはプロパティベースで値を提供します。値の取得時にバリデーション（例: KABUSYS_ENV, LOG_LEVEL）を行います。
- 実際に注文を送るモジュール（execution）を実装する際は、paper_trading/live のフラグ（settings.is_paper / settings.is_live）を活用して安全に実行環境を管理してください。

---

必要であれば、.env.example のテンプレートやサンプル戦略、実行スクリプトの README 展開も作成します。どういった利用例（バックテスト、ペーパー取引、ライブ運用）を優先してドキュメント化しましょうか？