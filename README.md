# KabuSys

バージョン: 0.1.0

日本株向けの自動売買システムの基盤ライブラリ。環境変数ベースの設定管理、データ・戦略・注文実行・モニタリングのモジュール構成を提供します。現在は設定読み込みロジックを中心に実装されています。

## 概要
KabuSys は日本株の自動売買を想定したライブラリ群（data / strategy / execution / monitoring）を含むパッケージです。環境変数（.env ファイル）からの設定読み込み、アプリケーション設定をラップした `settings` オブジェクトを提供します。パッケージ内部にある自動 .env ロード機構は、プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込みます。

## 主な機能
- 環境変数 / .env ファイルからの設定自動読み込み（OS環境変数 > .env.local > .env の優先度）
- 複数モジュール構成（data, strategy, execution, monitoring）の枠組み
- 設定アクセス用の `settings` オブジェクト（必須値チェックを含む）
- .env ファイルの柔軟なパース（export 形式、クォート、エスケープ、コメント判定）

## 必須（および主な）環境変数
以下はコード内で必須あるいは参照される環境変数です。実行前に設定してください（.env を使うのが簡単です）。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション / デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO)

自動ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env 読み込みを行いません（テスト等で利用）。

## .env ロードの挙動
- プロジェクトルートはパッケージファイル位置から親方向に `.git` または `pyproject.toml` を探索して決定します。見つからない場合は自動読み込みをスキップします。
- 読み込み順と優先度:
  1. OS の環境変数（既存の環境変数は保護されます）
  2. `.env.local`（override=True：OS 環境変数を上書きしない範囲で上書き）
  3. `.env`（override=False：未設定のキーのみセット）
- `.env` のパースは次の仕様をサポート:
  - `export KEY=value` 形式に対応
  - シングルクォート / ダブルクォートで囲まれた値のエスケープ処理対応（バックスラッシュエスケープを解釈）
  - クォートなしの値では、`#` がスペースまたはタブの直前にある場合のみ以降をコメントとみなす
  - 無効行（空行、`#` で始まる行、`=` を含まない行）は無視

## セットアップ手順（開発環境）
1. Python バージョン
   - Python 3.10 以上を推奨（コード内での型記法に依存）。

2. リポジトリをクローン
   - git clone ...

3. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux)
   - .venv\Scripts\activate (Windows)

4. インストール
   - pip install -e .  （開発インストール）
   - 依存関係は pyproject.toml / requirements.txt に従ってインストールしてください（プロジェクトに応じて）。

5. 設定ファイルの準備
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成します。`.env.example` があれば参考にしてください。

サンプル .env:
```
# 必須
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_api_password"
SLACK_BOT_TOKEN="xoxb-...."
SLACK_CHANNEL_ID="C12345678"

# 任意
KABU_API_BASE_URL="http://localhost:18080/kabusapi"
DUCKDB_PATH="data/kabusys.duckdb"
SQLITE_PATH="data/monitoring.db"
KABUSYS_ENV="development"
LOG_LEVEL="INFO"
```

## 使い方（簡単な例）
パッケージから設定を読み取る基本例:

```python
from kabusys.config import settings

# 必須値は設定されていないと例外(ValueError)になる
print("J-Quants token:", settings.jquants_refresh_token)
print("Kabu API base URL:", settings.kabu_api_base_url)
print("DuckDB path:", settings.duckdb_path)
print("現在の環境:", settings.env)
print("ライブモードか:", settings.is_live)
```

自動 .env 読み込みを無効化してから設定を操作したい場合:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "from kabusys.config import settings; print(settings.env)"
```

例外処理:
- `settings.jquants_refresh_token` のように必須の環境変数が未設定の場合、`ValueError` が発生します。実行前に必須環境変数をセットしてください。

## ディレクトリ構成
（リポジトリのルートに合わせて若干差異がある場合があります）

- src/
  - kabusys/
    - __init__.py              -- パッケージ定義（__version__ など）
    - config.py                -- 環境変数・設定管理ロジック（.env 自動ロード、Settings）
    - data/
      - __init__.py            -- データ関連処理用モジュール（未実装枠）
    - strategy/
      - __init__.py            -- 売買戦略用モジュール（未実装枠）
    - execution/
      - __init__.py            -- 注文実行用モジュール（未実装枠）
    - monitoring/
      - __init__.py            -- モニタリング用モジュール（未実装枠）

主要ファイル:
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py
- src/kabusys/monitoring/__init__.py

## 今後の拡張案（参考）
- data/strategy/execution/monitoring 各モジュールの実装とドキュメント化
- テストスイートの追加（CI 統合）
- .env パースの互換性拡張やバリデーション強化
- サンプル戦略・バックテスト機能の追加

---

ご不明点があれば、どの部分（セットアップ手順、.env の扱い、settings の使い方など）について詳細が必要か教えてください。README の追加修正や翻訳は対応できます。