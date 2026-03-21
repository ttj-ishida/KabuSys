# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants API からのデータ収集、DuckDB によるスキーマ管理・ETL、ファクター計算、特徴量正規化、シグナル生成、ニュース収集など、戦略実行に必要な基盤処理を提供します。

---

## 主な特徴（概要）
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた 3 層（Raw / Processed / Feature）スキーマ定義と初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（複数コンポーネントの重み付け、Bear レジーム抑制、エグジット判定）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、トラッキングパラメータ除去）
- マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
- 発注 / 監査用スキーマ（Execution / Orders / Auditing 構造を定義）

---

## 必要環境
- Python 3.10+
- 主要依存:
  - duckdb
  - defusedxml

（その他は標準ライブラリのみで実装されている箇所が多く、必要に応じて追加パッケージを導入してください）

---

## セットアップ手順（開発環境）
1. リポジトリをクローン／取得
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   # 開発用にパッケージとしてインストールする場合
   pip install -e .
   ```
4. 環境変数を設定（以下参照）

---

## 環境変数 (.env / 自動読み込み)
パッケージはプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）

オプション／設定
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト `development`）
- LOG_LEVEL: `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`（デフォルト `INFO`）
- KABUS_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト `data/monitoring.db`）

例（.env）
```
JQUANTS_REFRESH_TOKEN=あなたの_refresh_token
KABU_API_PASSWORD=あなたの_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## データベース初期化
DuckDB のスキーマを作成するには `kabusys.data.schema.init_schema` を利用します。

例（Python スクリプト）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn を使って以降の処理を実行
conn.close()
```

メモリ DB を使う場合:
```python
conn = init_schema(":memory:")
```

---

## ETL 実行例（日次 ETL）
日次 ETL （market calendar, prices, financials の差分取得 + 品質チェック）を実行するには `kabusys.data.pipeline.run_daily_etl` を使用します。

例:
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

ETL は J-Quants クライアント（認証トークン）を内部で使用します。トークンは `JQUANTS_REFRESH_TOKEN` から自動で取得しますが、テスト時には `id_token` を直接注入できます。

---

## 特徴量作成とシグナル生成
戦略層 API はシンプルです。DuckDB 接続と基準日を渡して実行します。

特徴量作成（features テーブルの生成）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

シグナル生成（signals テーブルへ書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
print(f"signals generated: {total}")
```

- `generate_signals` は重み（weights）や閾値（threshold）を引数で与えられます。
- SELL 条件（ストップロス等）や Bear レジーム抑制が組み込まれています。

---

## ニュース収集（RSS）
RSS フィードから記事を取得し `raw_news` に保存するジョブを提供します。

主要 API:
- fetch_rss(url, source, timeout=30) — フィードの取得と前処理（SSRF 対策・サイズ制限・XML サニタイズ）
- save_raw_news(conn, articles) — DuckDB に冪等保存
- run_news_collection(conn, sources=None, known_codes=None) — 複数ソースから一括収集・保存・銘柄紐付け

例:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は 4 桁銘柄コードの set（抽出用）
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(result)
```

---

## カレンダー管理
market_calendar の更新や営業日判定ユーティリティを提供します。

主要 API:
- calendar_update_job(conn, lookahead_days=90)
- is_trading_day(conn, d)
- next_trading_day(conn, d)
- prev_trading_day(conn, d)
- get_trading_days(conn, start, end)
- is_sq_day(conn, d)

例:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar rows saved: {saved}")
```

---

## 主要モジュールと機能の概観
- kabusys.config
  - 環境変数読み込み / settings オブジェクト
- kabusys.data
  - jquants_client: J-Quants API クライアント（fetch/save）
  - schema: DuckDB スキーマ定義 / init_schema / get_connection
  - pipeline: ETL ジョブ（run_daily_etl 等）
  - news_collector: RSS 収集・保存・銘柄抽出
  - calendar_management: カレンダー更新・営業日判定
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary 等
- kabusys.strategy
  - feature_engineering.build_features
  - signal_generator.generate_signals
- kabusys.execution / kabusys.monitoring
  - 発注・監視レイヤーのためのプレースホルダ（実装箇所あり）

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下）
- __init__.py
- config.py
- data/
  - jquants_client.py
  - schema.py
  - pipeline.py
  - news_collector.py
  - calendar_management.py
  - stats.py
  - features.py
  - audit.py
  - ...（その他 data 関連）
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- strategy/
  - feature_engineering.py
  - signal_generator.py
  - __init__.py
- execution/ (パッケージ化済み)
- monitoring/ (パッケージ化済み)

---

## 使い方・ワークフローの例
1. 環境変数（.env）を設定
2. DuckDB スキーマを初期化（init_schema）
3. 夜間バッチまたは Cron で run_daily_etl を実行してデータを収集・保存
4. research モジュールでファクターを検証・調査
5. build_features で特徴量を作成
6. generate_signals でシグナルを算出し signals テーブルへ保存
7. execution 層（実装済みのブリッジがあれば）で発注処理を行う

---

## ロギングとデバッグ
- 設定 `LOG_LEVEL`（環境変数）でログレベルを制御できます。
- 各モジュールは適切に logger を使っており、問題箇所のトレースが容易です。

---

## 貢献・ライセンス
- 本リポジトリは拡張可能な設計を目指しており、バグ修正・改善提案は歓迎します。
- ライセンス情報はリポジトリの LICENSE を参照してください（未指定の場合は管理者に確認してください）。

---

もし README に追加したい使い方（例: デプロイ手順、CI/CD、docker イメージ、具体的な strategy 設定ファイルサンプルなど）があれば教えてください。必要に応じてサンプルスクリプトや運用手順を追記します。