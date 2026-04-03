# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants からのデータ取得・ETL、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（発注→約定トレース）などを一貫して提供します。

主にバックテスト用データパイプラインや、実運用の前段（データ収集・品質チェック・シグナル生成補助）を目的としたモジュール群です。

- 注意: 本リポジトリは「データ取得・解析・監査」層が中心で、実際の発注ラッパー（証券会社 API 連携）や戦略の最終発注ループは別途実装する想定です。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- インストール
- 環境変数 (.env) — サンプル
- セットアップ手順
- 使い方（主要 API サンプル）
- ディレクトリ構成（抜粋）
- 設計上の注意点

---

## プロジェクト概要

KabuSys は次の要素を中心に設計された Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への冪等保存
- RSS ニュース収集と LLM（OpenAI）による銘柄別・マクロセンチメント評価
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ファクター（Momentum / Value / Volatility）計算、将来リターン・IC 計算、統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（signal_events / order_requests / executions）と DB 初期化ユーティリティ
- 設定管理（.env 自動読み込み、環境判定、閾値等）

設計方針として「ルックアヘッドバイアスの回避」「冪等性」「フェイルセーフ（API失敗時はゼロ/スキップして継続）」を重視しています。

---

## 機能一覧

主要機能の要約：

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への save_* 関数（ON CONFLICT DO UPDATE による冪等保存）
- ニュース処理 / NLP
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF 対策・XML デフューズ）
  - news_nlp.score_news: OpenAI で銘柄別センチメントを算出して ai_scores に保存
- レジーム判定
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースを合成して market_regime に保存
- 研究（Research）
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize
- データ品質チェック
  - quality.run_all_checks（欠損、重複、スパイク、日付整合性）
- カレンダー管理
  - calendar_management: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ
  - audit.init_audit_db / init_audit_schema（監査テーブルを初期化）
- 設定管理
  - config.settings（.env 自動読み込み、必須キーチェック、パス・閾値の既定値）

---

## 前提条件

- Python 3.10+
- ネットワークアクセス（J-Quants API / OpenAI API / RSS）
- DuckDB
- OpenAI Python SDK
- 必要な環境変数（下記参照）

外部ライブラリ（代表例）:
- duckdb
- openai
- defusedxml

（実プロジェクトに組み込む際は pyproject.toml / requirements.txt を参照して依存をインストールしてください）

---

## インストール

ローカル開発環境での例：

1. リポジトリをクローン
2. 仮想環境の作成・有効化
3. 必要パッケージをインストール

例：
- python -m venv .venv
- source .venv/bin/activate
- pip install -e .        # setuptools/poetry 等のセットアップに依存します
- pip install duckdb openai defusedxml

（実際の依存はプロジェクトのパッケージ管理ファイルに合わせてください）

---

## 環境変数 (.env) — サンプル

プロジェクトルートの .env または .env.local に設定を置くと自動で読み込まれます（config モジュール）。
自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須（最低限）:
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...         （news_nlp / regime_detector 用。関数引数で上書き可能）
- KABU_API_PASSWORD=...      （kabu ステーション連携用）

任意（デフォルトが設定されるものや運用に便利なもの）:
- KABUSYS_ENV=development|paper_trading|live    （default=development）
- LOG_LEVEL=INFO|DEBUG|...                      （default=INFO）
- DUCKDB_PATH=data/kabusys.duckdb               （デフォルトの DuckDB ファイル）
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0|1
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（基本）

1. 環境変数を設定（.env をプロジェクトルートに置く）
2. DuckDB ファイルの場所を確認（デフォルト: data/kabusys.duckdb）
3. 監査ログ用 DB を初期化（必要な場合）

監査 DB 初期化の例（Python スニペット）:
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

ETL 実行前に DuckDB コネクションが必要です（例えば duckdb.connect(settings.duckdb_path)）。

---

## 使い方（主要 API サンプル）

以下はライブラリの代表的な呼び出し方例です。実際の運用ではログ設定や例外ハンドリングを追加してください。

- DuckDB 接続の作成:
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行:
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニューススコアリング（OpenAI 必須）:
from kabusys.ai.news_nlp import score_news
from datetime import date
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"written {n_written} ai_scores")

- 市場レジームスコアリング:
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026,3,20))  # OpenAI の API キーは環境変数か引数で

- ファクター計算（例: モメンタム）:
from kabusys.research.factor_research import calc_momentum
from datetime import date
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{"date":..., "code":"XXXX", "mom_1m":..., ...}, ...]

- 研究ユーティリティ（Zスコア正規化）:
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m"])

- カレンダー操作:
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
is_trading = is_trading_day(conn, date(2026,3,20))
next_td = next_trading_day(conn, date(2026,3,20))

- 監査スキーマ初期化（既存接続へ）:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)

- J-Quants の生 API 呼び出し:
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# get_id_token は settings.jquants_refresh_token を使って id token を取得します
quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定読み込みロジック（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースの LLM スコアリング
  - regime_detector.py             — 市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py         — 市場カレンダー管理
  - etl.py / pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py              — J-Quants API クライアントと保存関数
  - news_collector.py              — RSS 収集・前処理
  - quality.py                     — データ品質チェック
  - stats.py                       — Zスコア等の統計ユーティリティ
  - audit.py                       — 監査ログテーブル定義・初期化
  - etl.py                         — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py             — Momentum / Value / Volatility 等
  - feature_exploration.py         — 将来リターン / IC / 統計サマリー
- ai/...、research/... は研究用・解析用の API を提供

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 設計上の注意点

- ルックアヘッドバイアス回避:
  - 多くの関数（news_nlp, regime_detector, pipeline など）は内部で date.today() を直接参照せず、target_date を明示的に受け取るか、呼び出し側で日付を決定します。
- 冪等性:
  - J-Quants からの保存処理は ON CONFLICT DO UPDATE を用いて冪等に設計されています。
- フェイルセーフ:
  - 外部 API の一時障害時は多くの処理で例外を投げずにスキップ・デフォルト値（例: macro_sentiment=0.0）にフォールバックします。ただし、致命的な状況は上位に伝搬します。
- セキュリティ:
  - news_collector は SSRF 対策、XML の defusedxml 利用、受信サイズ制限などの対策を実装しています。
- 並列化・レート制御:
  - jquants_client は API レート制限を守るため固定間隔でのスロットリングを実装しています（120 req/min）。

---

## さらに読む・拡張

- 戦略層（signal 生成、発注ロジック、ポジション管理）は本パッケージ外で構築します。order_requests / executions テーブルを用いて監査ログを保ちつつ、実際のブローカー連携は別モジュールに実装してください。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使い .env 自動読み込みを無効化できます。
- OpenAI 呼び出し部分は抽象化されているため unittest.mock を用いて簡単に差し替え・モック可能です（score_news, regime_detector の内部呼び出しはテストフレンドリーに設計されています）。

---

疑問点や README に追記したい内容があれば教えてください。具体的なユースケース（例: バックテスト向けの初期データロード手順、運用の cron 設定例 等）があれば、その手順やサンプルも追加できます。