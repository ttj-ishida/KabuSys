# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・AIによるニュースセンチメント、ファクター計算、監査ログ等を含み、DuckDB を中心にデータを蓄積・分析・監視することを想定しています。

---

## 主な目的 / プロジェクト概要

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL。
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去など）。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄別）とマクロセンチメントを組み合わせた市場レジーム判定。
- ファクター（モメンタム・バリュー・ボラティリティ）計算、特徴量探索ユーティリティ。
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ。
- データ品質チェック（欠損、重複、スパイク、日付不整合）の実行。

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（営業日判定・next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS 取得、前処理、raw_news 保存）
  - データ品質チェック（missing / duplicates / spike / date consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize 等）
- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約し LLM でセンチメント算出 → ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュースセンチメントを合成して market_regime を作成
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量評価（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数管理（.env 自動ロード、必須チェック、設定ラッパー settings）

---

## 前提 / 要件（推奨）

- Python 3.10+
- DuckDB
- OpenAI（openai Python SDK v1 互換）を使える環境
- J-Quants API のリフレッシュトークン
- （実際の取引連携を行う場合）kabu API 用パスワードなど

パッケージ依存は本リポジトリに requirements.txt がある想定で、以下のようにインストールしてください:

pip install -r requirements.txt
# または（開発時）
pip install -e .

（実際の依存バージョンはプロジェクトの requirements / pyproject を参照してください）

---

## 環境変数 / 設定

settings（kabusys.config.Settings）で利用する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（ETL で用いる）
- KABU_API_PASSWORD (必須)
  - kabuステーション等の API パスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (必須 for AI 関数 実行時)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知等で使用する場合)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) — 環境判定
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を起点に
  読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env のパースはシェル風の export KEY=VAL, 引用符とコメントの取り扱い等に対応しています。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv && source .venv/bin/activate
3. 依存インストール
   - pip install -r requirements.txt
   - または pip install -e .
4. 環境変数設定
   - プロジェクトルートに .env を作成するか、環境変数を設定
   - 参考: .env.example（プロジェクトにある場合）を参照
     必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（AI 機能を使う場合）
5. DuckDB データベース（監査用など）を初期化（オプション）
   - Python から init_audit_db を呼び出して初期テーブルを作成できます（例を下記参照）

---

## 使い方（例）

以下は代表的なユースケースの簡易例です。各関数は DuckDB 接続（duckdb.connect(...)）を受け取ります。

- DuckDB 接続の作成例:

from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:

from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)
print(result.to_dict())

- ニュースセンチメントを算出して ai_scores に書き込む:

from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")

- 市場レジーム判定を実行する:

from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

※ 上記 AI 関数は OpenAI API キーが環境変数 OPENAI_API_KEY に設定されているか、api_key 引数で渡す必要があります。

- 監査ログ DB 初期化:

from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成します

- RSS をフェッチする（ニュースコレクタを単体で使う）:

from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["datetime"], a["title"])

---

## 開発者向けメモ / 実装上の注意

- Look-ahead バイアス対策: 日付参照箇所は基本的に外部から渡す target_date を使い、内部で date.today() / datetime.today() を直接参照しない設計です（ETL / AI モジュール共に）。
- DB 書き込みは冪等化（ON CONFLICT DO UPDATE / DO NOTHING 等）を意識しているため、再実行が許容されるようになっています。
- J-Quants クライアントはレート制御（120 req/min）のための簡易 RateLimiter と、401 のトークン自動リフレッシュ、リトライロジックを備えています。
- ニュース収集では SSRF 対策（リダイレクト検査、プライベートアドレス拒否）、XML の安全パーサ（defusedxml）を使っています。
- OpenAI 呼び出しはレスポンスの JSON 検証・リトライやフェイルセーフ（失敗時はスコア 0.0 にフォールバック）を行う実装です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント / score_news
  - regime_detector.py  — 市場レジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント / save_* fetch_* 
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETLResult の再エクスポート
  - news_collector.py   — RSS 収集・前処理
  - calendar_management.py — 市場カレンダー管理 / calendar_update_job
  - quality.py          — データ品質チェック
  - stats.py            — 統計ユーティリティ（zscore_normalize）
  - audit.py            — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記以外に strategy / execution / monitoring 等のパッケージ参照が lib 初期化で宣言されていますが、リポジトリ内に該当実装があれば同階層に配置されます）

---

## 参考・運用ヒント

- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env がロードされないため、テスト向けの明示的な環境制御がしやすくなります。
- AI 呼び出しはコストやレート制限に注意してください。news_nlp では銘柄ごとに記事をトリムしてバッチ化（最大 20 銘柄/コール）するなどの対策がありますが、運用時はコール頻度・バッチサイズを適切に設定してください。
- DuckDB ファイルはバックアップを取るかスナップショット運用を検討してください（ETL 実行による上書き更新が行われます）。

---

必要であれば、README にサンプル .env.example、CLI スクリプト例、cron / systemd での運用例（ETL バッチのスケジューリング）、詳しい API 使用例（J-Quants / kabuステーション）などを追記できます。どの部分を優先して追加しますか？