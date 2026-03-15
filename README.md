# KabuSys

KabuSys は日本株向けの自動売買システムのコアライブラリ（初期バージョン）です。マーケットデータの保存・加工（Raw / Processed / Feature レイヤー）、戦略・実行（シグナル・オーダー・約定・ポジション）を管理するための基盤を提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境変数ベースの設定管理（.env ファイル自動読み込み対応）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution レイヤー）の定義と初期化
- シグナル・注文・約定・ポジション管理用のテーブル定義とインデックス最適化
- Slack / J-Quants / kabu API に関する設定項目を提供（API 連携用の設定を保持）
- プロジェクトルート検出による .env 自動読み込み（.git または pyproject.toml を基準）
- 自動読み込み無効化オプション（テスト向け）

---

## セットアップ

要件（最小限）
- Python 3.10+
- duckdb（Python パッケージ）

例: 仮想環境作成・依存関係インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# 他に必要なパッケージがあればここで追加
```

プロジェクトルートに `.env` または `.env.local` を配置して環境変数を設定します。自動ロードは以下の優先順位で行われます:
OS環境変数 > .env.local > .env

自動ロードを無効化するには環境変数を設定します:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

任意（デフォルト値あり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行モード（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）

.env の書式は標準的な KEY=VALUE 形式に対応し、シングル/ダブルクォートやコメント処理にも対応します。

---

## 使い方

基本的な利用例を示します。

設定値を取得する:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
kabu_base = settings.kabu_api_base_url
is_live = settings.is_live
db_path = settings.duckdb_path
```

DuckDB スキーマを初期化する:
```python
from kabusys.data.schema import init_schema

# デフォルトのファイルパスを使う場合
conn = init_schema(settings.duckdb_path)

# インメモリ DB を使ってテストする場合
conn = init_schema(":memory:")
```

既存 DB に接続する（スキーマ初期化は行わない）:
```python
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
```

パッケージバージョンを確認する:
```python
import kabusys
print(kabusys.__version__)
```

備考:
- init_schema() は必要なディレクトリを自動作成し、テーブル作成を冪等的に行います（既存テーブルはスキップ）。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に探します。CLI 等でカレントディレクトリを変えても影響しないように実装されています。

---

## データベース（スキーマ）概要

データは 3 層（実装上は Raw / Processed / Feature）および Execution レイヤーで整理されています。

- Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
- Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature Layer: features, ai_scores
- Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

主な特徴:
- 主キーや CHECK 制約でデータ整合性を担保
- 頻出クエリ向けにインデックスを作成（例: 銘柄×日付の検索、orders.status、signal_queue.status など）
- 外部キーにより一部テーブル間の依存関係を明示

---

## ディレクトリ構成

リポジトリ／パッケージのおおまかな構成（該当コードに基づく）:
```
src/
  kabusys/
    __init__.py            # パッケージメタ情報 (version, __all__)
    config.py              # 環境変数・設定管理（自動 .env ロード、Settings クラス）
    data/
      __init__.py
      schema.py            # DuckDB スキーマ定義と初期化関数 (init_schema, get_connection)
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

- data/schema.py に全テーブルの DDL とインデックス、init_schema/get_connection が定義されています。
- config.py に Settings クラスがあり、アプリケーション全体で共有する設定を提供します。

---

## 開発・テスト時の注意点

- .env の自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD をセットしてください（ユニットテストなどで利用）。
- Python の型ヒントや union 演算子 (|) を使っているため、Python 3.10 以上を想定しています。
- 現時点では DuckDB のみを必須パッケージとして想定していますが、実際の実行／通知処理（Slack、kabu / J-Quants 連携）を追加する場合は適切なクライアントライブラリを追加してください。

---

この README は現在のコードベースから生成した概要です。戦略ロジック・実行エンジン・モニタリング機能の実装や外部 API の具体的な連携は今後の拡張が必要です。必要であれば、.env.example の雛形や、サンプルの戦略／監視スクリプトのテンプレートも作成できます。必要な場合は教えてください。