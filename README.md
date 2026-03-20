# KabuSys

日本株自動売買システム用ライブラリ集（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・スキーマ管理など、戦略研究から実行層までの共通基盤を提供します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム構成要素をモジュール化した Python パッケージです。主な目的は次の通りです。

- J-Quants API から市場データ・財務データ・カレンダーを取得する ETL（差分更新・冪等保存）
- DuckDB 上のスキーマ定義・初期化
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 特徴量の正規化保存（features テーブル）
- シグナル（BUY/SELL）生成ロジック（重み付け、Bear レジーム判定、エグジット判定）
- ニュース収集（RSS → raw_news 保存、銘柄抽出）
- 監査ログ（order / execution のトレーサビリティ）機能

設計方針として「ルックアヘッドバイアス回避」「冪等性」「外部依存の最小化」「DuckDB を用いたオンディスク分析」を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（トークン自動更新、レート制限、リトライ）
  - raw_prices / raw_financials / market_calendar の取得・保存ユーティリティ
- data/schema.py
  - DuckDB のテーブル DDL を一括作成する init_schema()
- data/pipeline.py
  - 日次 ETL（run_daily_etl）：カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
- data/news_collector.py
  - RSS 収集、テキスト前処理、raw_news 保存、記事と銘柄の紐付け
- data/calendar_management.py
  - 営業日判定、next/prev_trading_day、calendar_update_job 等
- research/*
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary（探索的分析）
- strategy/*
  - feature_engineering.build_features: ファクター統合・Zスコア正規化・features テーブルへの保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY / SELL シグナル生成
- data/stats.py
  - zscore_normalize（クロスセクション Z スコア正規化）
- audit / execution（監査・発注周りのスキーマ、追跡用 DDL）

---

## 動作要件

- Python 3.10 以上（| 型注釈を使用しているため）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

必要に応じてプロジェクトの packaging により他パッケージが追加される可能性があります。テストや実運用ではさらに slack sdk や kabu API クライアント等が必要になることがあります。

---

## セットアップ手順

1. リポジトリをクローン（例）:
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows (PowerShell では別コマンド)

3. 必要パッケージをインストール:
   pip install --upgrade pip
   pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）
   （ローカル開発用に editable インストール: pip install -e . が使える場合があります）

4. 環境変数 / .env を準備:
   プロジェクトはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env/.env.local を自動読み込みします。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例: `.env`（必須項目を適宜設定）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボット用トークン（通知等で使用）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — データベースファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視 DB 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

---

## 使い方（サンプル）

以下は Python スクリプト／REPL での基本的な使い方例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)  # テーブル群を作成して接続を返す
```

2) 日次 ETL を実行（J-Quants から差分取得して保存）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# conn は init_schema で得た接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）の構築
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals

n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n}")
```

5) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出時に使用する有効銘柄コードの集合（例: set of "7203","6758",...）
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(result)  # {source_name: inserted_count, ...}
```

6) 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- これらの関数は DuckDB 接続を引数に取ります。テスト時に ":memory:" を使うことも可能です。
- 実運用ではログ出力、エラーハンドリング、ジョブスケジューラ（cron / Airflow 等）へ組み込むことを推奨します。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 下に配置）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 自動ロードと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py       — RSS 収集・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義 / init_schema
    - stats.py                — zscore_normalize 等統計ユーティリティ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — data 層の特徴量公開インターフェース
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - audit.py                — 監査ログ用 DDL
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py  — build_features（ファクター統合・正規化）
    - signal_generator.py     — generate_signals（最終スコア計算・BUY/SELL 生成）
  - execution/
    - __init__.py
  - monitoring/ (予定／参照)
  - その他モジュールや補助関数

---

## 開発上の注意点・設計ポイント

- DuckDB を使いローカルにオンディスクDBを置く設計のため、大規模検索や分析が高速に行えます。
- 冪等性を重視：外部データの保存は ON CONFLICT を使って上書き・重複排除を行います。
- ルックアヘッドバイアス回避：特徴量計算・シグナル生成は target_date 時点で利用可能なデータのみを使用する設計です。
- 自動 .env 読み込みはプロジェクトルート（.git / pyproject.toml）を基準に実施されます。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。

---

## 参考・補足

- この README はソース内のドキュメンテーション文字列（docstring）に基づいて要約しています。詳細な仕様（StrategyModel.md、DataPlatform.md、Research/Design doc 等）がプロジェクト内にある想定です。
- 実際の運用では J-Quants の API 制限や証券会社への接続要件（kabuステーション等）に注意してください。
- セキュリティ: .env やシークレットはリポジトリにコミットしないでください。

---

必要であれば README に「実行例スクリプト」「CI / テストの実行方法」「詳細な .env.example」などを追記します。どの部分を詳しく書くか指定してください。