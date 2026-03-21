# KabuSys

日本株向け自動売買基盤（KabuSys）の README。  
このリポジトリはデータ収集・ETL、特徴量計算、シグナル生成、監査・実行レイヤーの基盤を提供します。

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants などの外部 API から株価・財務・市場カレンダーを安全に取得し DuckDB に保存する（ETL）
- 収集データを加工して研究用 / 戦略用のファクター・特徴量を生成する
- 生成した特徴量と AI スコア等を統合してシグナル（BUY/SELL）を作成する
- ニュース収集（RSS）を行い記事と銘柄の紐付けを保存する
- DuckDB 上に監査ログ/実行テーブル群を定義してトレーサビリティを確保する

設計方針として、ルックアヘッドバイアス回避、冪等性、堅牢なエラーハンドリング、安全な外部アクセス（SSRF 対策・XML の安全パース等）を重視しています。

## 主な機能一覧

- Data
  - jquants_client: J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ）
  - pipeline: 日次 ETL（差分更新・バックフィル・品質チェック）
  - schema: DuckDB のスキーマ定義と初期化
  - news_collector: RSS 収集、前処理、記事保存、銘柄抽出
  - calendar_management: 市場カレンダーの管理・営業日判定ユーティリティ
  - stats / features: Z スコア正規化などの統計ユーティリティ
- Research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- Strategy
  - feature_engineering: 生ファクターを結合・フィルタ・正規化して features テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存
- Execution / Monitoring（基盤用テーブル／モジュール多数）
  - signals, signal_queue, orders, trades, positions, portfolio_performance などのテーブルと監査ログ

## 必須要件

- Python 3.10+
- DuckDB
- defusedxml

（その他ライブラリは標準ライブラリのみを使う設計の箇所が多いですが、実行時に必要なパッケージがあれば適宜追加してください）

例（pip）:
```
python -m pip install duckdb defusedxml
# このリポジトリを editable install する場合
python -m pip install -e .
```

## 環境変数（主なもの）

.env または OS 環境変数から読み込みます。自動ロードはプロジェクトルートに `.git` または `pyproject.toml` がある場合に行われ、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション等の API パスワード
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID : 通知先チャンネル ID

任意 / デフォルト:
- KABUSYS_ENV : development | paper_trading | live（デフォルト development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）

サンプル .env（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

## セットアップ手順

1. Python 3.10+ を用意する
2. 必要パッケージをインストールする:
   - duckdb, defusedxml など
   - 任意: 開発用に pip install -e .
3. 環境変数を設定（.env をプロジェクトルートに置く）
4. DuckDB スキーマを初期化する（例）:

Python REPL またはスクリプト:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してスキーマを構築
```

これで必要なテーブルとインデックスが作成されます。

## 使い方（代表的な例）

- 日次 ETL を実行してデータを取得・保存する:
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（未実行なら init_schema を呼ぶ）
conn = init_schema("data/kabusys.duckdb")

# 今日分の ETL 実行（J-Quants トークンは設定済みで自動利用）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量をビルド（feature_engineering）:
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2026, 3, 1))
print(f"upserted features: {n}")
```

- シグナル生成:
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2026, 3, 1))
print(f"signals written: {count}")
```

- ニュース収集ジョブ（RSS 収集・保存・銘柄紐付け）:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効銘柄コードのセット（例: 全上場銘柄のコードセット）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
print(results)
```

- カレンダーの夜間更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- これらは発注・ブローカー連携（実際の売買）を行う部分とは切り離されており、発注レイヤーは別実装／別設定での接続が必要です。
- 本システムの多くは DuckDB 接続を引数に取るため、テストではインメモリ DB (":memory:") を使うことが可能です。

## ディレクトリ構成（抜粋）

src/kabusys 以下の主要ファイルとモジュール:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 + 保存ユーティリティ）
    - news_collector.py            — RSS 取得・前処理・保存・銘柄抽出
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       — 市場カレンダー関係ユーティリティ
    - features.py                  — zscore の再エクスポート
    - stats.py                     — zscore_normalize 等
    - audit.py                     — 監査ログ用 DDL
    - quality.py?                  — 品質チェック（コードベースに参照あり、実装が別ファイルである想定）
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Volatility/Value 等の計算
    - feature_exploration.py       — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — features 作成（ユニバースフィルタ・Z スコア正規化）
    - signal_generator.py          — final_score 計算と BUY/SELL シグナル生成
  - execution/
    - __init__.py                  — 発注/約定/ポジション周りのエントリ（実装拡張箇所）
  - monitoring/                    — 監視用モジュール（ログ / メトリクス等；実装箇所）

（上記はリポジトリ内の主なファイルを抜粋したものです。詳細はソースを参照してください）

## 開発・運用上の注意点

- 環境（KABUSYS_ENV）に応じて live/paper_trading/development を切替え、実際の発注・資金管理は live 時にのみ有効にするなどの安全策を講じてください。
- DuckDB のスキーマは init_schema が冪等に作成するため、本番環境での初回実行前にバックアップを検討してください。
- 外部ネットワークアクセス（RSS・API）にはタイムアウト・サイズ上限・SSRF 対策が組み込まれていますが、追加のネットワークポリシー（プロキシ、ファイアウォール）を適用する場合は動作確認をしてください。
- ID トークンなどの秘密情報は安全に管理し、リポジトリにコミットしないでください。

---

README の内容は実装の概要を示すものであり、運用の最終決定は各組織のリスク管理方針に従ってください。追加の使用例やデプロイ手順（Docker / CI / Scheduler など）が必要であれば教えてください。