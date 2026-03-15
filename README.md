# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買システム向けの軽量なライブラリ基盤です。データ取得・ストラテジー実行・注文実行・監視を想定したモジュール構成を提供します。環境変数管理や設定読み込みのユーティリティを備え、ローカル開発〜ペーパートレード〜本番運用までの切り替えを想定しています。

主なモジュール
- kabusys.data — データ取得／保存に関する処理（プレースホルダ）
- kabusys.strategy — 売買戦略（プレースホルダ）
- kabusys.execution — 注文実行（プレースホルダ）
- kabusys.monitoring — 監視／ログ／アラート（プレースホルダ）
- kabusys.config — 環境変数／設定管理（実装あり）

---

## 機能一覧

- 環境変数読み込みと型安全な設定取得（kabusys.config.Settings）
- .env / .env.local の自動読み込み（プロジェクトルートを検出して読み込み）
- J-Quants / kabuステーション / Slack / データベースの設定プロパティ
- 実行環境（development / paper_trading / live）のバリデーション
- LOG_LEVEL のバリデーション（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- .env の柔軟なパース（export 形式、クォート、エスケープ、コメント対応）
- OS 環境変数を保護する読み込みロジック（.env.local で上書き可。ただし既存OS環境は保護）

---

## 動作要件

- Python 3.10 以上（PEP 604 の union 型（X | Y）を使用しているため）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化
   (例: venv)
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトに pyproject.toml がある想定です。pip で開発インストールする場合:
     ```
     pip install -e .
     ```
   - または Poetry を使う場合:
     ```
     poetry install
     ```

4. 環境変数 (.env) を用意
   - プロジェクトルートに `.env`（と必要に応じて `.env.local`）を置きます。
   - 自動読み込みは、パッケージのソース位置からプロジェクトルート（.git または pyproject.toml がある場所）を探索して行われます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必須環境変数の例（.env の最小例）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"

   # kabuステーション API
   KABU_API_PASSWORD="your_kabu_api_password"
   # KABU_API_BASE_URL は省略可（デフォルト: http://localhost:18080/kabusapi）

   # Slack
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="CXXXXXXXX"

   # オプション（データベースファイルパスの上書き）
   DUCKDB_PATH="data/kabusys.duckdb"
   SQLITE_PATH="data/monitoring.db"

   # 実行環境
   KABUSYS_ENV=development   # development / paper_trading / live

   # ログレベル
   LOG_LEVEL=INFO
   ```

---

## 使い方

基本的な設定の読み込み方法（例）:

```python
from kabusys.config import settings

# 必須値は未設定だと ValueError が発生する
token = settings.jquants_refresh_token
kabu_pw = settings.kabu_api_password
slack_token = settings.slack_bot_token
slack_channel = settings.slack_channel_id

# データベースパス（デフォルト値がある）
print(settings.duckdb_path)   # Path オブジェクト
print(settings.sqlite_path)

# 実行環境の判定
if settings.is_live:
    print("本番モード")
elif settings.is_paper:
    print("ペーパートレードモード")
else:
    print("開発モード")
```

.env パーサーの挙動（ポイント）
- 空行や `#` で始まる行は無視
- `export KEY=val` フォーマットをサポート
- シングル・ダブルクォート内はエスケープ（\）に対応してクォート閉じ位置まで取り込む
- クォートなしの場合、`#` がスペースまたはタブの直前にある場合はコメントとして扱う
- 自動読み込み順: OS 環境変数 > .env > .env.local（ただし .env.local は override=True のため .env の上書きになるが、OS 環境は保護される）

エラーとバリデーション
- 必須環境変数が未設定の場合、Settings プロパティは ValueError を投げます（例: JQUANTS_REFRESH_TOKEN 等）
- KABUSYS_ENV の値が development / paper_trading / live のいずれかでなければ ValueError
- LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかでなければ ValueError

モジュールの利用
- 現在、data/strategy/execution/monitoring 各パッケージはプレースホルダ（__init__.py が存在）です。各機能の具象実装を追加して利用してください。

---

## ディレクトリ構成

主要ファイル（抜粋）:

- src/
  - kabusys/
    - __init__.py         # パッケージ初期化: __version__ = "0.1.0"
    - config.py           # 環境変数・設定管理（実装済み）
    - data/
      - __init__.py       # データ関連モジュール（プレースホルダ）
    - strategy/
      - __init__.py       # ストラテジーモジュール（プレースホルダ）
    - execution/
      - __init__.py       # 注文実行モジュール（プレースホルダ）
    - monitoring/
      - __init__.py       # 監視モジュール（プレースホルダ）

---

## 開発メモ / 注意点

- プロジェクトルートの検出はパッケージファイルの位置を基準に階層上を探索します。CWD（カレントディレクトリ）に依存しないため、パッケージ配布後も期待どおり動作します。
- 自動で .env を読み込む仕組みはテストや CI で邪魔になる場合があるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- OS 環境変数は「保護」され、.env/.env.local による上書きを防ぐ仕組みがあります（ただし .env.local は .env より優先して読み込まれます）。

---

必要であれば、利用例（データ取得→戦略→注文→監視のフロー）、CI 設定、テストの雛形などの章を追加できます。どの部分を優先して拡張したいか教えてください。