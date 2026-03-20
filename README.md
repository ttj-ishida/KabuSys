# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの機能を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 簡単な使い方（API例）
- 環境変数（.env 例）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株の自動売買システム構築に必要なデータプラットフォームおよび戦略実行基盤のコアロジック群を集約した Python パッケージです。J-Quants API を用いた市場データ/財務データ取得、DuckDB を用いたローカル DB スキーマ、クロスセクションの特徴量正規化、戦略シグナル生成、RSS によるニュース収集、マーケットカレンダー管理、ETL パイプライン、監査ログ等を含みます。

設計上の特徴：
- DuckDB をデータストアに採用（軽量で高速な分析向け組み込み DB）
- J-Quants API レート制御・リトライ処理・トークン自動リフレッシュ実装
- ルックアヘッドバイアス防止（取得時刻や日付を明確に扱う）
- 冪等性（DB への保存は ON CONFLICT/UPDATE で重複を排除）
- テストしやすい設計（ID トークン注入や環境ロードの無効化等）

---

## 主な機能一覧
- データ取得・保存
  - J-Quants から日足（OHLCV）、財務、マーケットカレンダーを取得・DuckDBへ保存
  - 保存関数は冪等（ON CONFLICT）
- ETL パイプライン
  - 差分取得（最終取得日基準の差分）、バックフィル、品質チェックを含む日次 ETL
- スキーマ管理
  - DuckDB のスキーマ初期化（raw / processed / feature / execution 層）
- 研究 / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - クロスセクション Z スコア正規化
  - IC（Spearman）や将来リターン計算等の分析ユーティリティ
- 特徴量構築（feature_engineering）
  - ユニバースフィルタ（最低株価・流動性）と Z スコア正規化、features テーブルへの UPSERT
- シグナル生成（signal_generator）
  - features / ai_scores / positions を用いて最終スコアを計算、BUY/SELL シグナル作成・signals テーブル保存
  - Bear レジーム検知による BUY 抑制、エグジット条件（ストップロス等）
- ニュース収集（news_collector）
  - RSS フィードから記事収集、前処理、raw_news / news_symbols への保存（SSRF対策・XML安全パース）
- マーケットカレンダー管理（calendar_management）
  - JPX カレンダーの取得・営業日判定・次/前営業日取得等
- 監査ログ（audit）
  - シグナル → 発注 → 約定 のトレース用テーブル群

---

## 前提条件
- Python 3.10 以上（型ヒントで `X | Y` を使用）
- 以下の Python パッケージ（代表的なもの）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS）
- J-Quants リフレッシュトークン、kabu API パスワード、Slack トークンなどの環境変数

（依存パッケージはプロジェクトに requirements.txt があればそれを使用してください。無い場合は上記パッケージを pip で個別にインストールしてください。）

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得

2. Python 仮想環境作成（推奨）
- macOS / Linux:
  python -m venv .venv
  source .venv/bin/activate
- Windows:
  python -m venv .venv
  .venv\Scripts\activate

3. 必要パッケージをインストール
  pip install duckdb defusedxml

（プロジェクトで requirements.txt / poetry / pyproject.toml があればそれに従ってください）

4. 環境変数設定
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- オプション:
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - LOG_LEVEL (DEBUG|INFO|...) — default: INFO
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db

（下記に .env の例を掲載）

5. DuckDB スキーマ初期化
Python REPL またはスクリプトで schema.init_schema() を呼び出して DB を初期化します（例は次章参照）。

---

## 使い方（簡単な API 例）

以下は主要な操作のサンプルコード例です。実運用ではエラーハンドリングやログ設定を追加してください。

- DuckDB スキーマの初期化
```python
from kabusys.data import schema

# ディスク上のファイルに初期化
conn = schema.init_schema("data/kabusys.duckdb")

# インメモリ DB（テスト用）
# conn = schema.init_schema(":memory:")
```

- 日次 ETL 実行（J-Quants からデータ取得 → 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 先に init_schema を実行しておく
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（features テーブルの作成／置換）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 4))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルに BUY/SELL を書き込む）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 4))
print(f"signals generated: {count}")
```

- RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes: 銘柄コードの集合を渡すと記事中の4桁コードから紐付けを行う
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

- 環境設定の参照（設定値は kabusys.config.settings から取得）
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)   # 必須: 環境変数 JQUANTS_REFRESH_TOKEN
print(settings.duckdb_path)            # デフォルト data/kabusys.duckdb
```

---

## 環境変数（.env 例）
プロジェクトはルートにある `.env` / `.env.local` を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

例: .env
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス等（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- Settings クラスは一部の環境変数を必須として _require() を通じて参照します。未設定の場合は ValueError が発生します。
- テスト時に自動 env の読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）
以下はコードベースの主要なファイル／モジュールとその役割です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py  — パッケージ初期化、バージョン定義
  - config.py    — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（レート制御・リトライ・保存関数）
    - news_collector.py      — RSS ニュース収集・前処理・DB保存
    - schema.py              — DuckDB スキーマ定義と初期化（init_schema）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - audit.py               — 監査ログ関連テーブル定義
    - features.py            — data.stats のインターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value 計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成（ユニバースフィルタ・正規化）
    - signal_generator.py    — final_score 計算・BUY/SELL シグナル生成
  - execution/
    - __init__.py
  - monitoring/ (モジュールが存在することを __all__ に明示)
  - その他: 監査・実行層関連ファイル

---

## 開発・運用上の注意
- 本ライブラリはデータ取得や発注を行うコンポーネントを含みます。実際の運用で証券会社 API に接続する前にテスト環境（paper_trading）で十分に検証してください。
- J-Quants API のレート制限・認証仕様に従う必要があります。get_id_token() や _request() で自動リフレッシュ・リトライを行いますが、API の契約や利用制限を確認してください。
- DuckDB ファイルは破損防止のため適切なバックアップ・ローテーションを行ってください。
- news_collector は外部 URL を取得するため SSRF に注意し、fetch_rss 実行環境のネットワークポリシーを検討してください。
- signals → 発注 → executions のフローは監査上重要です。audit モジュールのテーブルは削除せず監査目的で保持することを想定しています。

---

もし README に追加したい内容（例: CI/CD ワークフロー、テスト実行方法、より詳細な API ドキュメント）の要望があれば教えてください。