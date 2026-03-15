# KabuSys

バージョン: 0.1.0

KabuSys は「日本株自動売買システム」の基盤ライブラリです。データ取得、ストラテジ、注文発注（kabuステーション連携）、モニタリングのためのモジュール群を提供することを想定しています（現状はパッケージ骨組みと設定ローダーを含みます）。

主なパッケージ:
- kabusys.data
- kabusys.strategy
- kabusys.execution
- kabusys.monitoring
- kabusys.config (環境変数・設定管理)

---

## 機能一覧

- 環境設定管理（.env/.env.local の自動読み込み）
  - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env を読み込む
  - .env → .env.local の順で読み込み（.env.local は .env を上書き）
  - OS 環境変数は保護され、基本的に上書きされない（ただし .env.local は上書き用）
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
  - 値のパースは `export KEY=val`、クォート（シングル/ダブル）やバックスラッシュによるエスケープ、コメント（#）を考慮
- Settings オブジェクト経由の型付きアクセス
  - J-Quants / kabuステーション / Slack / DB パス / 実行環境(開発・ペーパー・本番) 等のプロパティを提供
  - 必須環境変数が未設定の場合は例外を送出して明示的に通知

---

## 必要条件

- Python 3.10 以上（型アノテーションの union 演算子 `X | Y` を使用しているため）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. パッケージをインストール（編集可能モード）
   ```
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（と必要に応じて `.env.local`）を置くと、パッケージ読み込み時に自動で読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定している場合は読み込みされません）。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. （任意）自動ロードを無効化する場合
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1   # Unix/macOS
   setx KABUSYS_DISABLE_AUTO_ENV_LOAD 1    # Windows（恒久設定の場合）
   ```

---

## 使い方

最も基本的な使い方は `kabusys.config` の `settings` を通して設定を取得することです。

例:
```python
from kabusys.config import settings

# J-Quants リフレッシュトークン（未設定だと ValueError）
token = settings.jquants_refresh_token

# kabuステーション API パスワード
kabu_pw = settings.kabu_api_password

# DB のパス（Path オブジェクト）
duckdb_path = settings.duckdb_path

# 実行環境チェック
if settings.is_live:
    print("ライブモードです")
elif settings.is_paper:
    print("ペーパートレーディングです")
else:
    print("開発モードです")
```

重要なプロパティ一覧:
- jquants_refresh_token: JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password: KABU_API_PASSWORD（必須）
- kabu_api_base_url: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token: SLACK_BOT_TOKEN（必須）
- slack_channel_id: SLACK_CHANNEL_ID（必須）
- duckdb_path: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- sqlite_path: SQLITE_PATH（デフォルト: data/monitoring.db）
- env: KABUSYS_ENV（有効値: development, paper_trading, live。デフォルト: development）
- log_level: LOG_LEVEL（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）
- is_live / is_paper / is_dev: env に基づくブール

エラー時:
- 必須環境変数が未設定の場合、Settings の該当プロパティアクセスで ValueError が発生します。メッセージに従って .env.example を参考に環境変数を設定してください。

---

## ディレクトリ構成

リポジトリの主要構成（抜粋）:
```
.
├─ pyproject.toml
├─ .git/
├─ .env            # (推奨) プロジェクトルートに配置
├─ .env.local      # (任意) .env を上書きするために使用
└─ src/
   └─ kabusys/
      ├─ __init__.py        # パッケージ初期化 (version, __all__)
      ├─ config.py          # 環境変数 / 設定管理
      ├─ data/
      │  └─ __init__.py
      ├─ strategy/
      │  └─ __init__.py
      ├─ execution/
      │  └─ __init__.py
      └─ monitoring/
         └─ __init__.py
```

- src/kabusys/config.py に設定読み込みロジックと Settings クラスが実装されています。
- その他のサブパッケージ（data / strategy / execution / monitoring）は骨組みとして存在します。各領域の実装は今後追加されます。

---

## 実装のポイント・注意事項

- 自動環境読み込みの優先順位:
  1. OS 環境変数（常に最優先で保護される）
  2. .env（プロジェクトルート）
  3. .env.local（.env の上書き用、ただし OS 環境変数は保護される）
- .env のパースは比較的柔軟:
  - export 先頭トークンのサポート（例: export KEY=val）
  - シングル/ダブルクォートで囲まれた値はエスケープシーケンスを処理
  - 非クォート値では「#」がコメントとみなされるのは直前が空白またはタブの場合のみ（値内の # を誤って切らないように設計）
- 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで有用）。

---

## 今後の拡張案（参考）

- data: 市場データ取得 / キャッシュ機能の実装
- strategy: 売買ロジック、バックテスト実行環境
- execution: kabuステーションとの接続実装（注文発行・板情報取得など）
- monitoring: Slack 通知、監視用 DB・ダッシュボード連携

---

ご不明点や README に追加してほしい具体的な情報があれば教えてください。README の拡張（使用例、API ドキュメント、開発フロー、CI 設定など）も対応します。