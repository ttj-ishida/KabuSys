# KabuSys

日本株自動売買プラットフォームのコアライブラリ。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ／スキーマ管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムの基盤ライブラリです。主な目的は次の通りです。

- J-Quants API からの市場データ・財務データ・カレンダー取得（レート制限・リトライ・トークンリフレッシュ対応）
- DuckDB を用いたデータスキーマ定義と永続化（Raw / Processed / Feature / Execution レイヤ）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究（research）用ファクター計算と特徴量エンジニアリング
- 戦略用シグナル生成（ファクター + AI スコアの統合）
- ニュース収集と記事→銘柄紐付け（RSS）
- 監査ログ（signal → order → execution のトレーサビリティ）

設計上、ルックアヘッドバイアス回避や冪等性（オンコンフリクト更新／INSERT DO NOTHING）を重視しています。

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）と Settings API
- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン更新）
  - schema: DuckDB スキーマ定義・初期化（init_schema / get_connection）
  - pipeline: ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集・保存・銘柄抽出（SSRF 対策、サイズ制限、ID生成）
  - calendar_management: 営業日判定 / next/prev_trading_day 等のユーティリティと calendar_update_job
  - stats: 汎用統計（zscore_normalize）
  - features: zscore_normalize の再エクスポート
  - audit: 監査ログ用テーブル定義（signal_events / order_requests / executions など）
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: ファクターの正規化・フィルタ適用・features テーブルへの UPSERT
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL シグナルを作成

---

## セットアップ手順

前提: Python 3.9+（typing の記載から推定）および pip が利用可能であること。  
依存ライブラリの最小例（プロジェクトに requirements があればそちらを参照してください）:

- duckdb
- defusedxml

例（仮の requirements を想定したインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# あるいはプロジェクトがパッケージ化されている場合:
# pip install -e .
```

環境変数設定:
- プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必須環境変数（Settings から参照するキー）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
  - DUCKDB_PATH (例: data/kabusys.duckdb) — デフォルト値あり
  - SQLITE_PATH (監視用 DB) — デフォルト値あり

例 `.env`（簡易）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=secret_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234ABCDE
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

DB 初期化:
- DuckDB ファイルを初期化するには schema.init_schema を実行してください。親ディレクトリがなければ自動作成されます。

---

## 使い方（簡単な例）

以下は Python スクリプト/REPL での利用例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # :memory: を使うことも可能
```

2) 日次 ETL を実行（市場カレンダー・株価・財務を取得して品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # デフォルトで今日を対象
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2025, 1, 31))
print("features upserted:", count)
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

n_signals = generate_signals(conn, target_date=date(2025, 1, 31))
print("signals written:", n_signals)
```

5) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄抽出に使う有効な銘柄コードの集合（例: {'7203', '6758', ...}）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(['7203', '6758']))
print(results)
```

6) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意点:
- J-Quants API の呼び出しにはトークンが必要です（settings.jquants_refresh_token を通じて get_id_token を利用）。
- ETL / API 呼び出し部はネットワークエラーや API 制限に対するリトライ/ログを備えていますが、API 利用キーや利用量の管理は利用者側で行ってください。

---

## よく使う API（要点）

- settings (kabusys.config.settings)
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env など
- DB スキーマ
  - init_schema(db_path) → DuckDB 接続
  - get_connection(db_path)
- ETL
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
- 特徴量・戦略
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.6, weights=None)
- データ取得（J-Quants）
  - jquants_client.fetch_daily_quotes(...)
  - jquants_client.fetch_financial_statements(...)
  - jquants_client.fetch_market_calendar(...)
- ニュース
  - news_collector.fetch_rss(url, source)
  - news_collector.save_raw_news(conn, articles)
  - run_news_collection(conn, sources, known_codes)

---

## ディレクトリ構成

（src ディレクトリを基点に主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py                    — DuckDB スキーマ定義・init_schema
    - pipeline.py                  — ETL パイプライン（run_daily_etl など）
    - news_collector.py            — RSS 取得・前処理・保存・銘柄抽出
    - calendar_management.py       — カレンダー管理・営業日ユーティリティ
    - features.py                  — zscore_normalize 再エクスポート
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログテーブル定義
    - quality.py?                  — （品質チェック関連。README の中で参照されているが、抜粋コードに含まれない場合があります）
  - research/
    - __init__.py
    - factor_research.py           — momentum / volatility / value 等の計算
    - feature_exploration.py       — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — build_features
    - signal_generator.py          — generate_signals
  - execution/                     — 発注周りのモジュール群（抜粋では空 __init__）
  - monitoring/                    — 監視用モジュール（抜粋では未表示）
- pyproject.toml?                  — プロジェクトルート検出に用いる可能性あり（自動 .env ロード用）
- .env, .env.local                 — 環境設定ファイル（任意）

---

## 運用上の注意と設計上のポイント

- 自動環境変数読み込み:
  - プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を読み込みます。
  - テスト等で自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 冪等性:
  - DB への保存関数は可能な限り ON CONFLICT / DO UPDATE / DO NOTHING を使い冪等化しています。
- ルックアヘッドバイアス回避:
  - ファクター / シグナル計算は target_date 時点のデータのみを参照する設計になっています。
- セキュリティ:
  - news_collector は SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ制限等を実装しています。
- ログ・監査:
  - 監査テーブル（audit）により signal → order → execution のフローをトレース可能にする設計です。

---

## 開発・テスト

- モジュール単位でのユニットテストが望ましい箇所:
  - _parse_env_line（config）
  - zscore_normalize（data.stats）
  - factor 計算（research）
  - signal generation ロジック（strategy）
  - news_collector の URL 正規化 / 銘柄抽出
- ネットワーク/API 呼び出し部分はモック化してテストしてください。jquants_client._request や news_collector._urlopen などを差し替えることでテストしやすく設計されています。

---

問題や追加したい例、CI 設定例、あるいは README に含める具体的なコマンド（Makefile / Poetry / tox など）を指定いただければ、追記・調整します。