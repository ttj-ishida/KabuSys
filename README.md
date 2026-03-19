# KabuSys

日本株向けの自動売買システム用ライブラリ（ライブラリ形式）
このリポジトリはデータ取得・ETL、特徴量生成、シグナル生成、ニュース収集、監査・実行レイヤの骨組みを提供します。DuckDB を内部データベースとして用い、J-Quants API や RSS などからデータを収集して戦略処理を行えるよう設計されています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡易コード例）
- 環境変数
- ディレクトリ構成（主要ファイルの説明）
- 補足・設計上の注意

---

## プロジェクト概要

KabuSys は日本株の自動売買インフラを構成するためのモジュール群です。主な用途は次のとおりです。

- J-Quants API からの市場データ（OHLCV、財務、マーケットカレンダー）収集
- DuckDB によるデータ格納・スキーマ管理（冪等な保存）
- ETL（差分更新、バックフィル、品質チェック）
- 研究（research）で算出した素ファクターの正規化・合成（feature layer）
- 戦略シグナル生成（features + AI スコアの統合 → BUY/SELL判定）
- RSS ベースのニュース収集と銘柄紐付け
- カレンダー管理・営業日計算、監査ログ/実行レイヤのスキーマ

設計方針として、ルックアヘッドバイアス防止・冪等性・外部発注 API への直接依存分離・テストに配慮したインターフェースを重視しています。

---

## 主な機能（抜粋）

- data/jquants_client.py
  - J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ、ページネーション対応）
  - fetch_* / save_* 系で API と DuckDB の橋渡しを行う（冪等）
- data/schema.py
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層のテーブル）
  - init_schema() / get_connection()
- data/pipeline.py
  - 日次 ETL パイプライン（run_daily_etl）や個別 ETL ジョブ（prices, financials, calendar）
  - 差分取得・バックフィル・品質チェックとの統合
- data/news_collector.py
  - RSS 取得・前処理・記事保存、銘柄抽出・紐付け
  - SSRF 対策、XML デフェンス、サイズ制限、ID生成による冪等性
- data/calendar_management.py
  - market_calendar を用いた営業日判定、next/prev_trading_day、calendar_update_job
- research/
  - factor_research.py: momentum / volatility / value 等のファクター算出
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー
- strategy/
  - feature_engineering.build_features(conn, target_date): features テーブル作成
  - signal_generator.generate_signals(conn, target_date, ...): signals テーブルへ出力
- config.py
  - 環境変数の読み込み（.env / .env.local 自動ロード機能）と settings オブジェクト

---

## セットアップ手順

前提:
- Python 3.10+（typing | None を使っているため）を推奨
- DuckDB を利用（pip パッケージ duckdb）
- RSS パースに defusedxml を使用

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを使って下さい）

3. パッケージを開発モードでインストール（任意）
   - プロジェクトルートで: pip install -e .

4. 環境変数の用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（config.py の自動読み込み）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. DuckDB スキーマ初期化（例は使い方セクション参照）

---

## 必要な環境変数（主なもの）

config.Settings から参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client が ID トークンを取得するために利用。
- KABU_API_PASSWORD (必須)
  - kabuステーション等の API パスワード（execution 層で使用想定）。
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
  - kabu API のベース URL。
- SLACK_BOT_TOKEN (必須)
  - Slack 通知に利用する Bot Token。
- SLACK_CHANNEL_ID (必須)
  - Slack 通知先チャンネル ID。
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)
  - DuckDB ファイルパス（expanduser 対応）。
- SQLITE_PATH (任意, default: data/monitoring.db)
  - 監視用 SQLite 等のパス（用途に応じて）。
- KABUSYS_ENV (任意, default: development)
  - 有効値: development, paper_trading, live
  - settings.is_live / is_paper / is_dev が利用可能。
- LOG_LEVEL (任意, default: INFO)
  - DEBUG/INFO/WARNING/ERROR/CRITICAL

.env のサンプル（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: .env の読み込みは config._find_project_root() によりリポジトリルート（.git または pyproject.toml がある場所）を探索して行われます。

---

## 使い方（コード例）

以下は典型的なワークフローの簡易例です。実行は Python スクリプトやジョブから行います。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path からパスを取得して初期化
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J-Quants からデータを差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量の構築（research ファクターから features テーブルを作成）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"build_features: {n} 銘柄")
```

4) シグナル生成（features と ai_scores を統合）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"generate_signals: {count} シグナルを書き込みました")
```

5) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar_update_job: saved={saved}")
```

---

## API・ユーティリティの簡易説明

- init_schema(db_path)
  - DuckDB のファイルパスを与えてテーブル群を作成します（冪等）。

- run_daily_etl(conn, target_date, id_token=None, ...)
  - ETL をまとめて実行し ETLResult を返します。

- jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - API からデータをページング取得（内部でレート制御・リトライ・401 リフレッシュを扱う）

- jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - DuckDB の raw_* テーブルへ冪等に保存（ON CONFLICT UPDATE）

- research.calc_momentum / calc_volatility / calc_value
  - prices_daily / raw_financials を参照してファクターを計算

- strategy.build_features(conn, target_date)
  - research 側の生ファクターを統合・正規化して features テーブルへ保存

- strategy.generate_signals(conn, target_date, threshold, weights)
  - features + ai_scores を使って final_score を計算し signals テーブルへ書き込む

- news_collector.fetch_rss / save_raw_news / run_news_collection
  - RSS フィード収集と raw_news 保存、銘柄抽出の一連処理

---

## ディレクトリ構成（抜粋）

（パッケージは src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py          # API クライアント + 保存ユーティリティ
    - news_collector.py          # RSS 収集 / 保存 / 銘柄抽出
    - schema.py                  # DuckDB スキーマ定義・init_schema
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py     # カレンダー更新・営業日判定
    - features.py                # zscore_normalize の再エクスポート
    - stats.py                   # zscore_normalize 等の統計ユーティリティ
    - audit.py                   # 監査ログ用スキーマ（signal_events, order_requests 等）
    - audit (続きのファイル群...) 
  - research/
    - __init__.py
    - factor_research.py         # momentum/volatility/value の計算
    - feature_exploration.py     # forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py     # build_features
    - signal_generator.py        # generate_signals
  - execution/
    - __init__.py                # 発注関連は空スタブ（実装を想定）
  - monitoring/                   # monitoring モジュールは __all__ に含まれるが実装ファイルが無い場合あり

（README 用に主要モジュールを抜粋しています。実際のリポジトリにはさらに細かな実装ファイルが含まれます）

---

## 補足・運用上の注意

- 自動 .env 読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探して .env / .env.local を自動ロードします。テスト時や特殊な環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
  - .env.local は OS 環境変数より優先して上書きされます（ただし既存 OS 環境変数は protected されます）。

- ルックアヘッドバイアス対策
  - ファクター算出・シグナル生成は target_date 時点までのデータのみを使用するよう設計されています（過去データの利用に注意）。

- 冪等性
  - save_* 系関数は ON CONFLICT を用いて冪等に保存します。ETL ジョブは再実行可能であることを前提としています。

- レート制限とリトライ
  - J-Quants クライアントは 120 req/min の制限に合わせてスロットリングを行います。HTTP 408/429/5xx などは指数バックオフでリトライします。401 はトークンをリフレッシュして再試行します。

- セキュリティ
  - news_collector は SSRF を避けるためにリダイレクト先の検査やプライベートアドレス拒否、XML パースには defusedxml を使用しています。

---

## ライセンス・貢献

（ライセンス情報がない場合はここに追記してください。プルリク歓迎）

---

この README はソースコードの公開部分に基づく簡易的な導入ガイドです。実運用や本番接続（特に発注・execution 部分）を行う場合は、さらにリスク管理・権限管理・監査ポリシーを整備してください。質問や追加で欲しいサンプル（例: cron ジョブ定義、Docker 化、CI 設定等）があれば教えてください。