# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。データ取得・ETL、特徴量作成、シグナル生成、ニュース収集、監査・実行レイヤーなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は J-Quants や各種 RSS から市場データ・財務データ・ニュースを取得して DuckDB に蓄積し、研究（research）で作成した生ファクターを正規化・合成して戦略用特徴量を作成、最終的に売買シグナルを生成することを目的とした Python ライブラリです。設計上、ルックアヘッドバイアス回避、冪等性、ログ・監査トレース、ETL 品質チェックなどを重視しています。

主要コンポーネント（抜粋）:
- data: J-Quants クライアント、ETL パイプライン、ニュース収集、DuckDB スキーマ定義、統計ユーティリティ
- research: ファクター計算・探索ユーティリティ
- strategy: 特徴量構築（feature_engineering）、シグナル生成（signal_generator）
- execution: （発注周りのプレースホルダ / 拡張点）
- monitoring: 監視・監査関連（監査テーブル定義など）

---

## 機能一覧

- J-Quants API クライアント（差分取得、ページング、トークンリフレッシュ、レート制限＆リトライ）
- DuckDB スキーマ定義と初期化（冪等）
- 日次 ETL パイプライン（market calendar / prices / financials の差分取得と保存）
- 品質チェック（quality モジュール参照：欠損・スパイク検出など）
- 特徴量エンジニアリング（research で計算した生ファクターの統合・正規化）
- シグナル生成（特徴量＋AIスコア統合、BUY/SELL 判定、エグジット判定）
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事→銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal → order → execution のトレーサビリティテーブル）
- 汎用統計ユーティリティ（Zスコア正規化、IC 計算、統計サマリー）

---

## 必要な環境変数

以下は本プロジェクトで使用する主要な環境変数です（必須は明記）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合は 1 をセット

自動ロードの振る舞い:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env と .env.local を自動読み込みします。
- 読み込み順: OS 環境 > .env.local > .env
- テスト等で自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python のインストール（推奨: 3.9+）
2. リポジトリをクローン
   - git clone <repo_url>
3. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 必要パッケージをインストール
   - pip install -U pip
   - 必要最小限の依存例:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
5. パッケージを編集モードでインストール（ローカル開発）
   - pip install -e .
6. 環境変数を設定（上記の必須項目を .env に記載）

注意:
- DuckDB ファイルの親ディレクトリは自動作成されます（デフォルト data/）。
- J-Quants API を使用するにはトークンが必要です。

---

## 使い方（主要な操作例）

以降は Python スクリプトや REPL からの利用例です。各コード例はサンプルであり、実運用前に十分なテストと設定確認を行ってください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

db_path = settings.duckdb_path  # デフォルト data/kabusys.duckdb
conn = init_schema(db_path)  # テーブルがなければ作成して接続を返す
```
- ":memory:" を渡すとインメモリ DB が使用できます。

2) 日次 ETL（J-Quants からデータ取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
print(f"signals written: {num}")
```

5) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # などの有効銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"market calendar saved: {saved}")
```

7) 監査 / 発注周り
- audit モジュールに監査テーブルの DDL が含まれているため、init_schema 後に監査ログを利用できます。発注の実装は execution 層で拡張してください。

---

## 主要モジュール説明（抜粋）

- kabusys.config
  - .env / 環境変数の読み込みと settings オブジェクトを提供
  - 自動 .env 読み込み（プロジェクトルート検出）、必須値チェック

- kabusys.data.jquants_client
  - J-Quants API とのやり取り、ページネーション、トークン取得、保存ユーティリティ（save_*）

- kabusys.data.schema
  - DuckDB のスキーマ定義と init_schema / get_connection

- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl 等 ETL ロジック

- kabusys.data.news_collector
  - RSS 収集、安全対策（SSRF、サイズ制限）、raw_news 保存、銘柄抽出

- kabusys.research
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary（探索・評価用）

- kabusys.strategy
  - build_features（特徴量作成）: research の生ファクターを統合して features テーブルへ保存
  - generate_signals（シグナル生成）: features + ai_scores → final_score → signals へ保存

- kabusys.data.stats
  - zscore_normalize 等の共通統計ユーティリティ

---

## ディレクトリ構成（src/kabusys の主なファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - stats.py
    - audit.py
    - (その他: quality.py 等が想定)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/
    - (監視・監査関連モジュール)

各モジュールの責務はソース中の docstring に詳細が記載されています。初期導入時は schema.init_schema() を実行して DB を作成してください。

---

## 運用上の注意・ベストプラクティス

- ルックアヘッドバイアス防止: 各計算は target_date 時点の情報のみを使用するよう設計されています。実際のバッチ実行では target_date の扱いに注意してください。
- 冪等性: save_* / ETL / features/signal の処理は基本的に日付単位の置換や ON CONFLICT を使って冪等に動作しますが、本番運用前に小規模なリハーサルを推奨します。
- API レート制限: J-Quants のレート制限に従う必要があります（モジュールでは固定間隔スロットリングとリトライを実装）。
- セキュリティ: RSS の取得では SSRF 対策、XML パースの安全化（defusedxml）などを実装しています。外部に公開する環境では環境変数管理・シークレット管理に注意してください。
- テスト: KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動環境読み込みを無効にし、テスト専用の設定を注入してください。

---

## 参考 / 次のステップ

- 各モジュールの docstring（ソース）を参照してパラメータや返り値の詳細を確認してください。
- execution 層（実際の注文送信・ブローカー連携）やリスク管理（ポジションサイズ算出・ドローダウン制御）はプロジェクト固有の要件に合わせて実装・拡張してください。
- CI／デプロイ、運用監視（Slack 通知等）は本 README を補完する運用ドキュメントとして別途整備してください。

---

問題や追加したい説明、コマンド例があれば教えてください。必要に応じて README の拡張（例: CI サンプル、より詳細なセットアップ手順、よくあるトラブルシュートなど）を作成します。