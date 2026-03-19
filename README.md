# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリ群です。  
DuckDB をデータストアとして利用し、J-Quants API や RSS からデータを取得・保存、研究用ファクター計算、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、ETL パイプラインや監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の用途を想定したモジュール群です。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存（ETL）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量の正規化・保存（features テーブル）
- ファクター + AI スコアを統合したシグナル生成（signals テーブルへの出力）
- RSS ベースのニュース収集と銘柄紐付け
- JPX マーケットカレンダー管理（営業日判定等）
- 発注・約定・ポジション管理用のスキーマと監査ログ設計

設計方針として、ルックアヘッドバイアス回避、冪等性（DB保存は ON CONFLICT/UPsert を使用）、外部依存を最小化する（標準ライブラリ主体）点を重視しています。

---

## 主な機能一覧

- data:
  - jquants_client: J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）
  - pipeline: 日次 ETL（prices / financials / calendar）の差分更新処理
  - schema: DuckDB スキーマの初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS フィード収集・正規化・DB 保存、銘柄抽出
  - calendar_management: 営業日判定・next/prev trading day 等
  - stats: z-score 正規化等の統計ユーティリティ
- research:
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy:
  - feature_engineering: 研究で作成した raw factor を統合・正規化して features テーブルへ保存
  - signal_generator: final_score を計算して BUY/SELL シグナルを signals テーブルへ保存
- execution / monitoring / audit:
  - スキーマ・テーブル定義（orders / executions / positions / signal_events / order_requests 等）を含む監査ログ設計（UUID ベースのトレーサビリティ）

---

## セットアップ手順

1. 前提
   - Python 3.10 以上（typing での `X | Y` を使用しているため）
   - DuckDB を利用するためローカル環境に十分なディスク容量があること

2. リポジトリを取得
   - 開発環境に合わせてクローンまたはコピーしてください。

3. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

4. 必要なパッケージをインストール
   - 最低依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトが配布パッケージ化されている場合は `pip install -e .` などでインストールしてください）

5. 環境変数 / .env
   - ルートに `.env` / `.env.local` を置くと自動的に読み込まれます（ただしテスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注等を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack のチャンネルID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV — {development, paper_trading, live}（default: development）
     - LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（default: INFO）
     - DUCKDB_PATH — (default: data/kabusys.duckdb)
     - SQLITE_PATH — (default: data/monitoring.db)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

---

## 使い方（簡単なクイックスタート）

以下は Python REPL / スクリプト内での使用例です。適宜 logging 設定など行ってください。

1. スキーマの初期化（DuckDB ファイルを作成）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は .env または環境変数から取得されます
conn = init_schema(settings.duckdb_path)
```
- メモリ DB を使う場合: init_schema(":memory:")

2. 日次 ETL（J-Quants からの差分取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を与えなければ今日
print(result.to_dict())
```

3. 特徴量の作成（features テーブルへ）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date(2024, 1, 15))
print(f"features upserted: {n}")
```

4. シグナル生成（signals テーブルへ）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date(2024, 1, 15))
print(f"signals written: {count}")
```

5. ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 抽出可能な有効銘柄コードセット（省略可）
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

6. カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2024, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

7. J-Quants クライアント（直接使用したい場合）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 注意事項 / 運用メモ

- 自動で .env を読み込む仕組みがありますが、CI やユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- J-Quants API はレート制限があるため、jquants_client は内部で固定間隔スロットリングとリトライを行います。
- DuckDB への保存は各 save_* 関数で冪等になるよう ON CONFLICT を使用しています。
- features / signals の処理は「target_date 時点のデータのみ」を使用し、ルックアヘッドバイアスに配慮しています。
- news_collector は SSRF 対策、XML インジェクション対策（defusedxml）等のセキュリティ配慮を行っています。
- production（live）環境では KABUSYS_ENV を `live` に設定してください。`is_live` フラグにより実行ロジックを切替可能な場所が今後追加されます。

---

## ディレクトリ構成

（プロジェクトのルートは pyproject.toml または .git を基準に自動検出されます）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py  — J-Quants API クライアント（fetch/save 関数あり）
      - news_collector.py  — RSS 取得・前処理・DB 保存
      - schema.py  — DuckDB スキーマ定義・初期化
      - stats.py  — zscore_normalize 等の統計ユーティリティ
      - pipeline.py  — ETL パイプライン（run_daily_etl 等）
      - features.py  — data.stats の再エクスポート
      - calendar_management.py — マーケットカレンダー管理
      - audit.py — 監査ログ用スキーマ定義（signal_events / order_requests / executions 等）
      - (その他: execution / monitoring フォルダ等)
    - research/
      - __init__.py
      - factor_research.py  — Momentum/Volatility/Value の計算
      - feature_exploration.py  — forward returns / IC / summary / rank
    - strategy/
      - __init__.py
      - feature_engineering.py  — features テーブル構築（build_features）
      - signal_generator.py  — シグナル生成（generate_signals）
    - execution/  — 発注層（未実装詳細用フォルダ）
    - monitoring/ — 監視・メトリクス集計（未実装詳細用フォルダ）

主要な Python モジュール・関数:
- kabusys.config.settings
- kabusys.data.schema.init_schema / get_connection
- kabusys.data.pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.jquants_client.fetch_* / save_*
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_ic / calc_forward_returns
- kabusys.strategy.build_features / generate_signals

---

## テスト・開発

- 単体テストは外部ネットワーク依存を無効化したり、jquants_client の HTTP 呼び出しをモックすることを推奨します。
- .env の自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

もし README に追加してほしい内容（CI構成、例の .env.example、実運用時の注意事項や Slack 通知の使い方、サンプルスクリプト等）があれば教えてください。必要に応じてサンプル .env や運用手順を追記します。