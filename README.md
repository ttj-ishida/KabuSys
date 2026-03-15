# KabuSys

日本株向け自動売買システムのコアライブラリです。市場データ収集、データベーススキーマ、特徴量生成、シグナル／発注管理など、アルゴリズム取引基盤の共通機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- 市場データ（価格、財務情報、ニュース、約定情報など）の保存・管理
- DuckDB を用いた階層化されたデータスキーマ（Raw / Processed / Feature / Execution）
- 環境変数ベースの設定管理（.env の自動読み込み機能を含む）
- 発注／約定・ポジション管理用テーブル定義
- 将来的に戦略モジュール・実行モジュール・モニタリング統合を想定した構成

コードベースの主要モジュール:
- kabusys.config: 環境変数・設定管理
- kabusys.data.schema: DuckDB スキーマ定義と初期化
- kabusys.data: データ関連ユーティリティ（将来的な拡張点）
- kabusys.strategy: 戦略ロジック（未実装雛型）
- kabusys.execution: 発注実行ロジック（未実装雛型）
- kabusys.monitoring: モニタリング用ユーティリティ（未実装雛型）

---

## 主な機能一覧

- 環境変数の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` および `.env.local` を読み込む
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能
  - export 形式やクォート、コメント（#）の取り扱いに対応

- 設定取得ラッパー (kabusys.config.Settings):
  - J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）などの取得
  - 必須環境変数が未設定の場合に明確なエラーを送出

- DuckDB スキーマ管理 (kabusys.data.schema):
  - Raw / Processed / Feature / Execution の各レイヤーのテーブル定義
  - インデックスや外部キー依存を考慮したテーブル作成
  - 冪等的な初期化関数 `init_schema(db_path)` と接続取得 `get_connection(db_path)`

---

## セットアップ手順

1. Python のインストール
   - 推奨: Python 3.9+（実際の互換性は環境に合わせて確認してください）

2. 仮想環境を作成（任意）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   - このリポジトリには明示的な requirements.txt を含めていませんが、少なくとも DuckDB が必要です。
     ```
     pip install duckdb
     ```
   - 実際に外部 API（J-Quants、kabuステーション、Slack など）を利用する機能を使う場合は、それらに必要な HTTP クライアントや SDK（例: requests, slack-sdk 等）を追加でインストールしてください。

4. パッケージをインストール（開発モード）
   - リポジトリルートに pyproject.toml / setup.cfg 等がある想定で:
     ```
     pip install -e .
     ```
   - ローカルで直接使うだけなら、インポートパスに `src` を含めて実行できます。

5. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。自動読み込み機能はデフォルトで有効です（CWD に依存せず、ソースファイル位置からプロジェクトルートを検出）。

例: `.env` の雛形（.env.example として保存すると良い）
```
# 必須 (J-Quants)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# Kabuステーション API
KABU_API_PASSWORD=your_kabu_password
# 任意: API ベース URL (デフォルト http://localhost:18080/kabusapi)
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# データベースパス（省略時はデフォルトを使用）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境 (development|paper_trading|live)
KABUSYS_ENV=development

# ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
LOG_LEVEL=INFO
```

環境変数の自動読み込みを無効にする場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（基本例）

- 設定を取得する:
```python
from kabusys.config import settings

# 必須項目は設定されていなければ ValueError が発生する
token = settings.jquants_refresh_token
kabu_url = settings.kabu_api_base_url
duckdb_path = settings.duckdb_path  # pathlib.Path オブジェクト
```

- DuckDB スキーマを初期化する:
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリが存在しない場合は自動作成）
conn = init_schema(settings.duckdb_path)

# ":memory:" を渡すとインメモリ DB を使用
# conn = init_schema(":memory:")
```

- 既存 DB へ接続する:
```python
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
# 注意: get_connection はスキーマ初期化を行わない。初回は init_schema を利用してください。
```

- .env の読み込み動作
  - パッケージ読み込み時（kabusys.config が import されるとき）に、プロジェクトルートを探索して `.env` と `.env.local` を順に読み込みます。
  - OS の環境変数は保護され、デフォルトでは上書きされません。`.env.local` は `.env` をオーバーライドするために使用します。

---

## DuckDB スキーマ概要

KabuSys は次のレイヤーでテーブルを定義しています。

- Raw Layer: 取得した生データをそのまま保存
  - raw_prices, raw_financials, raw_news, raw_executions

- Processed Layer: 市場データの整形済みテーブル
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols

- Feature Layer: 戦略や AI 用の特徴量・スコア
  - features, ai_scores

- Execution Layer: シグナル／オーダー／約定／ポジション／パフォーマンス
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

インデックスや外部キー（可能な範囲）もテーブル生成時に作成されます。

---

## ディレクトリ構成

以下はこのリポジトリの主要なファイル・ディレクトリ構成です（抜粋）。

```
src/
└── kabusys/
    ├── __init__.py               # パッケージ定義（__version__ 等）
    ├── config.py                 # 環境変数・設定管理
    ├── data/
    │   ├── __init__.py
    │   └── schema.py             # DuckDB スキーマ定義・初期化
    ├── strategy/
    │   └── __init__.py           # 戦略モジュール（拡張ポイント）
    ├── execution/
    │   └── __init__.py           # 発注実行モジュール（拡張ポイント）
    └── monitoring/
        └── __init__.py           # 監視／モニタリング（拡張ポイント）
```

---

## 注意点 / 実運用への留意事項

- 環境変数に機密情報（API トークン、パスワード等）を格納する際は取り扱いに十分注意してください。`.env` はバージョン管理に含めない（`.gitignore` へ追加）ことを推奨します。
- 実際に発注を行う「live」環境で使用する際は十分なテストと安全確認を行ってください（paper_trading モードでの十分な検証を推奨）。
- スキーマや型定義は今後の拡張に合わせて変更される可能性があります。マイグレーション方針を検討してください。
- 依存ライブラリ（HTTP クライアント、Slack SDK、J-Quants クライアントなど）は本 README に網羅していません。必要に応じてプロジェクト要件に合うパッケージを追加してください。

---

必要な説明や具体的な使い方（API 例、戦略実装テンプレート、発注フローのサンプルなど）を追加で作成できます。どの部分を優先して詳述しましょうか？