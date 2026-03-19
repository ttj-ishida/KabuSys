# KabuSys

日本株向けの自動売買システム用ライブラリ群（KabuSys）。  
データ収集（J-Quants API）、ETL、特徴量作成、シグナル生成、ニュース収集、カレンダー管理、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引のための内部ライブラリセットです。主な目的は以下の通りです。

- J-Quants API からのデータ収集（株価・財務・市場カレンダー）
- DuckDB を用いたデータ格納スキーマと ETL パイプライン
- 研究用ファクター計算（momentum / value / volatility 等）
- 特徴量正規化・合成（features テーブルへの保存）
- 特徴量＋AI スコアの統合による売買シグナル生成（signals テーブル）
- RSS ベースのニュース収集と銘柄紐付け
- JPX カレンダー管理（営業日判定等）
- 発注・約定・監査ログ用スキーマ（実行層のためのテーブル定義）

設計は「ルックアヘッドバイアスの防止」「冪等性」「DBトランザクションによる原子性保証」「API レート制御/リトライ」等の実運用上の配慮を反映しています。

---

## 機能一覧

- 環境設定管理（.env 自動ロード / 必須キーの検査）
- DuckDB スキーマ定義・初期化（init_schema）
- J-Quants API クライアント（認証・ページネーション・レート制御・リトライ）
- ETL パイプライン（日次差分取得、バックフィル、品質チェック）
- 研究モジュール（ファクター計算 / 将来リターン / IC 計算 / 統計サマリー）
- 特徴量生成（Zスコア正規化・ユニバースフィルタ・features テーブルへのUPSERT）
- シグナル生成（最終スコア計算・BUY/SELL 判定・signals テーブルへのUPSERT）
- ニュース収集（RSS フィード取得、前処理、raw_news 保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 発注/約定/監査向けスキーマ（signal_events / order_requests / executions 等）

---

## 前提・必須ソフトウェア

- Python 3.9+
- duckdb（DuckDB Python パッケージ）
- defusedxml（RSS/XML パースの安全化）
- （任意）その他のライブラリは用途に応じて追加

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（実際のプロジェクトでは requirements.txt / poetry 等で依存管理してください）

---

## 環境変数（.env）

自動で `.env` / `.env.local` をプロジェクトルートからロードします（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。主要な環境変数:

- JQUANTS_REFRESH_TOKEN （必須）: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD （必須）: kabuステーション API 用パスワード
- KABU_API_BASE_URL（任意）: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN （必須）: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID （必須）: 通知先 Slack チャンネル ID
- DUCKDB_PATH（任意）: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意）: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV（任意）: 実行環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL（任意）: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

簡易 `.env` 例（.env.example を参考に作成）:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（duckdb, defusedxml など）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB スキーマを初期化

初期化例:

```python
# 例: schema 初期化（Python REPL またはスクリプト）
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

あるいはワンライナー:

```bash
python - <<'PY'
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
print("schema initialized")
PY
```

---

## 使い方（代表的な呼び出し）

以下はライブラリの代表的な利用例です。実運用ではこれらを定期ジョブ（cron / Airflow 等）に組み込みます。

1) 日次 ETL 実行（市場カレンダー・株価・財務の差分取得と品質チェック）

```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# DB が未作成なら init_schema、既存なら get_connection
conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

2) 特徴量の構築（features テーブルへの書き込み）

```python
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {n}")
conn.close()
```

3) シグナル生成（signals テーブルへの書き込み）

```python
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 1, 31), threshold=0.6)
print(f"signals generated: {count}")
conn.close()
```

4) ニュース収集ジョブ（RSS -> raw_news, news_symbols）

```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection("data/kabusys.duckdb")
# known_codes は抽出時に有効な銘柄コードのセット（例: {"7203","6758",...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)
conn.close()
```

5) カレンダー更新バッチ

```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
conn.close()
```

---

## 実装上の注意点（運用メモ）

- J-Quants API のレート制限（120 req/min）をモジュール内で守る実装があります（RateLimiter）。
- API へのリクエストはリトライと指数バックオフを実装し、401 では自動でトークンをリフレッシュします。
- DB 操作は可能な限りトランザクションでまとめ、日付単位での置換（DELETE → INSERT）により冪等性を確保しています。
- features / signals などは target_date の時点のみのデータを用いることでルックアヘッドバイアスを防止する設計です。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

## ディレクトリ構成

主要ファイル/モジュールの一覧（src/kabusys 以下を抜粋）:

```
src/kabusys/
├── __init__.py
├── config.py                       # 環境変数 / 設定管理
├── data/
│   ├── __init__.py
│   ├── jquants_client.py           # J-Quants API クライアント・保存処理
│   ├── news_collector.py           # RSS ニュース収集・保存
│   ├── schema.py                   # DuckDB スキーマ定義・初期化
│   ├── stats.py                    # 統計ユーティリティ（zscore 等）
│   ├── pipeline.py                 # ETL パイプライン（run_daily_etl 等）
│   ├── features.py                 # features の公開インターフェース
│   ├── calendar_management.py      # 市場カレンダー管理
│   └── audit.py                    # 監査ログテーブル定義
├── research/
│   ├── __init__.py
│   ├── factor_research.py          # ファクター計算（momentum/value/volatility）
│   └── feature_exploration.py      # 研究用指標（IC, forward returns 等）
├── strategy/
│   ├── __init__.py
│   ├── feature_engineering.py      # features を組成して DB に保存
│   └── signal_generator.py         # final_score 計算と signals 書込
├── execution/                       # 発注／実行層（将来の実装箇所）
│   └── __init__.py
└── monitoring/                      # 監視関連（将来の実装箇所）
```

---

## テスト・開発向けヒント

- 簡易テストや開発では DuckDB のインメモリ ":memory:" を使うと便利です（init_schema(":memory:")）。
- 自動 .env ロードを無効化するには環境変数をセット: `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- news_collector の RSS パーサは defusedxml を使用しているため、安全な XML パースが可能です。
- 研究モジュールは外部依存を最小化しており、pandas 等に依存しない実装になっています（性能要件に応じて置き換え可能）。

---

## ライセンス・貢献

本 README はコードベースの概要説明です。実際の配布リポジトリに README.md、LICENSE、CONTRIBUTING を併設してください。

---

以上。必要であればセットアップの詳細な手順（systemd / cron / Docker / CI 用定義）や、各テーブルのカラム定義・サンプルクエリ、運用チェックリスト等の追加ドキュメントも作成できます。どの情報を優先的に追加しますか？