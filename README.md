# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / データプラットフォームのコアライブラリです。DuckDB をデータ層に使い、J-Quants API や RSS ニュースを取り込んで特徴量を計算、戦略シグナルを生成するためのモジュール群を提供します。

主な設計方針：
- 研究（research）と本番（execution）を分離
- ルックアヘッドバイアス防止（target_date ベースの計算）
- DuckDB による冪等なデータ保存（ON CONFLICT / トランザクション）
- 外部依存は必要最小限（標準ライブラリ + 必要パッケージ）

---

## 機能一覧

- 環境設定読み込み・管理（.env 自動読み込み、Settings）
- J-Quants API クライアント（認証・ページネーション・リトライ・レート制御）
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン（株価・財務・カレンダーの差分取得と保存、品質チェック統合）
- News（RSS）収集・前処理・DB保存（SSRF 対策、トラッキングパラメータ除去）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量作成（正規化・ユニバースフィルタ・features テーブル更新）
- シグナル生成（ファクター + AI スコア統合、BUY/SELL ルール、signals テーブル保存）
- カレンダー管理（営業日判定 / next/prev_trading_day 等）
- 監査ログ用スキーマ（signal → order → execution のトレーサビリティ）

---

## 前提・依存関係

- Python 3.10 以上（型表現に `X | Y` を使用）
- 必要パッケージ（例）:
  - duckdb
  - defusedxml

簡単なインストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（実際のプロジェクトでは requirements.txt / poetry 等で依存管理してください）

---

## 環境変数

パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` / `.env.local` を自動で読み込みます（OS 環境変数より下位）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用される環境変数：
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL : kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite DB（既定: data/monitoring.db）
- KABUSYS_ENV : 環境 ("development" | "paper_trading" | "live")（既定: development）
- LOG_LEVEL : ログレベル ("DEBUG","INFO",...)（既定: INFO）

Settings は `kabusys.config.settings` から参照可能です。

---

## セットアップ手順（ローカルでの初期化）

1. リポジトリをクローンし、Python 仮想環境を作成して依存をインストールします（上記参照）。

2. `.env` を作成し必要な環境変数を設定します。最低限必要なキーの例：
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

3. DuckDB スキーマを初期化します（例: Python REPL またはスクリプト）：
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```
これによりデータベースファイル（デフォルト data/kabusys.duckdb）が作成され、テーブル群とインデックスが初期化されます。

---

## 使い方（主なユースケース）

以下は代表的な操作のサンプルコードです。

- 日次 ETL（市場カレンダー・株価・財務の差分取得と保存）：
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量のビルド（features テーブルの作成）：
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへ保存）：
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
total = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals written: {total}")
```

- RSS ニュース収集（news を raw_news に保存し、銘柄紐付け）：
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
# known_codes は既知の銘柄コード集合（price テーブルなどから取得）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- J-Quants API からデータを直接フェッチして保存（手動差分取得）：
```python
from kabusys.config import settings
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(saved)
```

---

## よく使うモジュール一覧（API の抜粋）

- kabusys.config
  - settings (Settings インスタンス)：環境設定の取得

- kabusys.data
  - schema.init_schema(db_path) / get_connection(db_path)
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / save_* 系
  - pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector.fetch_rss / save_raw_news / run_news_collection
  - features.zscore_normalize

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/         (発注・broker 連携はここに実装予定)
    - monitoring/        (監視 / メトリクス関連)

※ 実際のリポジトリでは tests、docs、scripts 等の追加ディレクトリがあることを想定してください。

---

## 注意事項 / 運用上のヒント

- 環境（KABUSYS_ENV）は "development", "paper_trading", "live" のいずれかに設定してください。live モードでは実際の発注関連ロジックを有効化する想定です。
- DuckDB のファイルパスは Settings.duckdb_path で管理されます。バックアップやベンチマーク目的で ":memory:" を使用してインメモリ DB を作ることもできます。
- J-Quants API のレート制御やリトライはクライアント側で制御していますが、実行頻度には注意してください（120 req/min の制限に合わせた実装）。
- RSS フェッチは SSRF 対策や受信サイズ制限が組み込まれています。外部 URL を増やす場合は信頼できるソースを指定してください。
- ETL は各ステップ個別に例外処理され、1 ステップ失敗でも他は継続します。結果は ETLResult に集約されます。

---

## 貢献 / 開発者向け

- 型チェック・静的解析（mypy / flake8 等）を導入すると品質向上に有効です。
- DB スキーマ変更は DataSchema.md（仕様文書）に従って行ってください。既存テーブルとの互換性に注意。
- テストは DuckDB のインメモリモード（":memory:"）で行うと高速に回せます。

---

README はコードベースに基づいて書かれています。追加で README に含めたい運用手順、CI/CD、デプロイ手順、または .env.example のテンプレート等があれば教えてください。