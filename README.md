# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ群です。  
本リポジトリは ETL（J-Quants からのデータ取得・保存）、データ品質チェック、ニュース収集と LLM によるニュースセンチメント評価、ファクター算出・特徴量探索、監査ログ（トレース）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を想定したモジュール群を含みます。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL（DuckDB に保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI を使ったニュース NLP（銘柄別センチメント）とマクロセンチメントを用いた市場レジーム判定
- Research 用ユーティリティ（ファクター計算・将来リターン・IC・統計サマリ）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 環境変数ベースの設定管理（自動 .env ロード機能あり）

設計上の特徴：
- DuckDB をデータ層に採用（軽量かつ高速な分析向け）
- Look-ahead bias を避ける実装方針（内部で date.today() を参照しない等）
- 外部 API 呼び出しのリトライ・レート制御・フェイルセーフ実装
- 冪等性を考慮した DB 保存（ON CONFLICT / INSERT/DELETE パターン）

---

## 機能一覧

主なモジュールと機能:

- kabusys.config
  - 環境変数から設定を読み込み、Settings オブジェクトを提供
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
- kabusys.data.jquants_client
  - J-Quants からのデータ取得（株価日足 / 財務 / 上場銘柄情報 / マーケットカレンダー）
  - DuckDB への保存関数（冪等）
- kabusys.data.pipeline / etl
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl など
  - ETL 結果を ETLResult として返す（品質チェック含む）
- kabusys.data.quality
  - 欠損 / スパイク / 重複 / 日付不整合 のチェックを実行
- kabusys.data.news_collector
  - RSS 取得と前処理、記事 ID 正規化、SSRF 対策、raw_news への保存（想定）
- kabusys.ai.news_nlp
  - ニュースを銘柄別に集約し OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に保存
- kabusys.ai.regime_detector
  - ETF (1321) MA200 の乖離とマクロセンチメントを合成して market_regime を生成
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.audit
  - 監査テーブル（signal_events, order_requests, executions）定義と初期化ユーティリティ

---

## 必要条件（推奨）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK v1 系を想定)
- defusedxml
- （標準ライブラリのみで動作する部分も多いですが、上記は実運用で必要になります）

インストール例（pip）:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

プロジェクトパッケージ化されていれば開発インストール:
```bash
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンする（既にローカルにある想定）
2. 仮想環境作成・有効化（任意）
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成（例は次節参照）
   - パッケージは起動時にプロジェクトルートを自動検出し `.env` / `.env.local` を読み込みます
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して下さい

---

## 環境変数（主な一覧）

設定は kabusys.config.Settings 経由で取得します。必須/任意を記載します。

必須（実行する機能により必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行時に必要）
- KABU_API_PASSWORD: kabuステーション API に接続する場合

任意 / デフォルトあり:
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を使う場合
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: モニタリング制御用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: モニタ閾値
- KABUSYS_ENV: environment（development | paper_trading | live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

サンプル .env（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: kabusys.config はプロジェクトルート（.git か pyproject.toml が存在する場所）を基準に .env の自動読み込みを行います。

---

## 使い方（簡易サンプル）

以下は代表的な操作の使い方例です。すべて Python スクリプトや REPL で実行できます。

- 設定を参照する:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ってニューススコアを付ける（ai_scores へ書き込む）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数に設定済みなら api_key=None で OK
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み件数: {written}")
```

- 市場レジーム判定を行う:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使ってテーブルが作成されていることを確認できます
```

- ニュース RSS をフェッチ（ニュース収集の一部）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"])
```

注:
- OpenAI 呼び出しは API コストが発生します。テスト時はモック（unittest.mock.patch）を推奨します。
- ETL / 保存関数は DuckDB のスキーマ前提があります。初期スキーマ作成は別モジュール（data.schema 等）で行う想定です。

---

## 開発時の注意点 / テスト

- 環境変数の自動読み込み: kabusys.config はプロジェクトルートを自動検出して `.env` / `.env.local` を読み込みます。テスト時に自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API 呼び出しやネットワーク I/O を含む関数はモック可能な設計になっています（内部の `_call_openai_api`、`_urlopen` 等を patch）。
- DuckDB への executemany に空リストを渡すと問題になるバージョンがあるため、実装側で空判定を行っています。

---

## ディレクトリ構成

主要なファイル / モジュール構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（銘柄別センチメント）
    - regime_detector.py               — マクロ＋MA200 合成の市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                      — ETL パイプライン / run_daily_etl 等
    - etl.py                           — ETL の公開インターフェース（ETLResult）
    - news_collector.py                — RSS ニュース収集
    - calendar_management.py           — マーケットカレンダー管理（営業日判定等）
    - stats.py                         — 統計ユーティリティ（zscore_normalize 等）
    - quality.py                       — データ品質チェック
    - audit.py                         — 監査ログ用 DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum/value/volatility）
    - feature_exploration.py           — forward returns / IC / summary / rank
  - research/...                        — 各種 research utilities

上記以外にテスト／ドキュメント／スクリプト用のトップレベルファイルが存在する想定です。

---

## その他

- ライセンスや貢献方法、詳細なスキーマ定義・マイグレーション手順はリポジトリのドキュメント（別ファイル）で管理してください。
- 実運用での発注・約定処理（broker 接続など）を行う場合は十分なテストと安全対策（冪等キー、監査ログ、注文キャンセルロジック、リスク管理）を組み込んでください。

---

この README はコードベースの主要機能と使い方の概要を示したものです。細かな API の使い方や DuckDB のスキーマ（テーブル定義）は各モジュールの docstring を参照してください。必要であれば、より詳細な導入手順やサンプルスクリプトを追加で作成します。