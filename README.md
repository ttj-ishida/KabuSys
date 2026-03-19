# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
DuckDB をデータストアに用い、J-Quants から市場データ・財務データ・カレンダーを取得し、ファクター計算、特徴量正規化、シグナル生成、ニュース収集などを行うモジュール群を提供します。

---

## 主な特徴（概要）

- データ収集（J-Quants）／差分ETL（株価・財務・マーケットカレンダー）
- DuckDB ベースのスキーマ（Raw / Processed / Feature / Execution レイヤ）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量生成（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（複数コンポーネントの重み付け統合、BUY/SELL の作成）
- ニュース収集（RSS → 前処理 → DB 保存 / 銘柄抽出）
- カレンダー管理（営業日判定、next/prev_trading_day 等）
- 冪等性（DB への保存は ON CONFLICT を利用）

---

## 主要機能一覧

- data.jquants_client
  - J-Quants API クライアント（レート制限・リトライ・トークン自動更新・ページネーション対応）
  - fetch/save：日足・財務・カレンダーの取得・保存
- data.schema
  - DuckDB スキーマ定義・初期化（init_schema）
- data.pipeline
  - 日次 ETL（run_daily_etl）・差分 ETL ジョブ（run_prices_etl 等）
- data.news_collector
  - RSS フィード取得・前処理・raw_news 保存・銘柄紐付け
- data.calendar_management
  - market_calendar の更新、営業日判定・取得ユーティリティ
- data.stats / data.features
  - Z スコア正規化などの統計ユーティリティ
- research.factor_research / feature_exploration
  - ファクター計算・将来リターン / IC / サマリー
- strategy.feature_engineering
  - ファクター統合・ユニバースフィルタ・features テーブルへの UPSERT
- strategy.signal_generator
  - features + ai_scores を統合した final_score 計算、BUY/SELL の判定・signals テーブル保存

---

## 前提・依存

- Python >= 3.10（PEP 604 の型記法などを使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS）
- 環境変数に API トークンなどを設定する

インストール例（開発環境）:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# パッケージをローカルで editable install する場合
pip install -e .
```

（必要に応じて slack 等の追加ライブラリをインストールしてください）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

必須の環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（使用する場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトがある場合）:
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

簡易 .env 例（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=secret_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール
   - 例: `pip install duckdb defusedxml`
4. 環境変数（または .env）を用意
5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してテーブルを初期化
conn.close()
```

---

## 使い方（例）

Python コードからライブラリを呼び出して使う一連の例を示します。

- DuckDB 接続 & スキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection

# 初回: スキーマ作成
conn = init_schema("data/kabusys.duckdb")

# 既存 DB へ接続する場合
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）構築
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date(2024, 1, 1))
print(f"built features: {n}")
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

count = generate_signals(conn, target_date=date(2024, 1, 1))
print(f"signals generated: {count}")
```

- ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection

# known_codes を渡すと記事から銘柄コード抽出して news_symbols に保存します
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count}
```

- カレンダー更新ジョブ（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"market calendar saved: {saved}")
```

- J-Quants から日足を直接取得して保存（テスト用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,2))
saved = save_daily_quotes(conn, records)
```

---

## 開発用メモ / テスト

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います。テスト時に環境の影響を避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- モジュールは外部 API 呼び出しを含む部分（jquants_client、news_collector など）を分離しているため、テストでは該当部分のネットワーク呼び出しをモック可能です。
- Python の型注釈を多用しているため、型チェック（mypy 等）を導入すると品質向上に役立ちます。

---

## ディレクトリ構成（抜粋）

以下は本パッケージ内の主なファイル・パッケージ（src/kabusys）です。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理（.env 自動ロード等）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - schema.py          — DuckDB スキーマ定義・init_schema
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - features.py        — features の公開インターフェース
    - news_collector.py  — RSS 収集・前処理・保存
    - calendar_management.py — カレンダー管理・バッチ更新
    - audit.py           — 監査ログ（order_requests, executions 等）
    - quality.py?        — 品質チェック（pipeline が参照、実装ファイルがある想定）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル構築（build_features）
    - signal_generator.py     — signals 生成（generate_signals）
  - execution/             — 発注処理（パッケージ領域、実装は別途）
  - monitoring/            — 監視用モジュール（実装は別途）

（実際のリポジトリではさらにテスト・ドキュメント・スクリプト等が含まれることがあります）

---

## 補足 / 設計ノート

- ルックアヘッドバイアス回避のため、各集計・シグナル生成は必ず target_date 時点のデータのみを参照する設計です。
- DB 保存は冪等化（ON CONFLICT / UPSERT）を基本とし、再実行可能な処理フローを想定しています。
- J-Quants API はレート制限（120 req/min）があるため、固定間隔の RateLimiter と指数バックオフ再試行を組み合わせています。
- news_collector には SSRF 対策、XML の安全パース、応答サイズ制限などセキュリティ・堅牢性対策が含まれます。

---

## 連絡先・貢献

この README はコードベースからの抜粋に基づく概要ドキュメントです。実装の詳細や未記載のユーティリティについてはソースコードの docstring を参照してください。バグ修正・機能追加の貢献は Pull Request を歓迎します。

--- 

以上。README.md をプロジェクトルートに配置して利用してください。必要であれば利用例のスクリプト（cron / systemd 用の runner）や、CI / テスト手順のテンプレートも作成できます。希望があればお伝えください。