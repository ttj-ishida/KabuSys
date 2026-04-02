# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買サブシステム向けのライブラリ群です。  
J-Quants API からのデータ取得・ETL、ニュースの収集と LLM によるニュースセンチメント評価、ファクター計算・研究ユーティリティ、監査ログの初期化などを含みます。

バージョン: 0.1.0

---

## 概要

主な目的は次のとおりです。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI (gpt-4o-mini 等) を用いたニュースセンチメントおよびマクロセンチメント評価
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（シグナル→発注→約定トレーサビリティ）用のスキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- ルックアヘッドバイアス対策（内部で date.today()/datetime.now() を不用意に参照しない等）
- 冪等性（DB 保存は ON CONFLICT / DELETE→INSERT 等で既存データを保護）
- フェイルセーフ（API失敗時は部分的にフォールバックして処理継続）
- DuckDB をデータレイクとして利用

---

## 機能一覧（主な公開 API）

- 環境設定
  - kabusys.config.settings: 環境変数から設定を取得（J-Quants トークン、Kabu API パスワード、Slack トークンなど）
  - .env 自動ロード（プロジェクトルートに .env / .env.local があれば自動で読み込む。無効化可）

- データ ETL / クライアント
  - kabusys.data.jquants_client
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - kabusys.data.pipeline
    - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
    - ETLResult（実行結果構造）
  - kabusys.data.news_collector
    - fetch_rss, RSS の前処理、raw_news への保存補助（トラッキング除去 / SSRF 対策 等）
  - kabusys.data.calendar_management
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job

- AI / NLP
  - kabusys.ai.news_nlp.score_news: ニュースを銘柄別に集約して OpenAI に投げ、ai_scores テーブルへ保存
  - kabusys.ai.regime_detector.score_regime: ETF (1321) の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定

- 研究（Research）
  - kabusys.research.factor_research: calc_momentum, calc_volatility, calc_value
  - kabusys.research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - kabusys.data.stats: zscore_normalize

- データ品質と監査
  - kabusys.data.quality: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - kabusys.data.audit: init_audit_schema, init_audit_db（監査ログ用の DuckDB スキーマ初期化）

注: パッケージ上位 __init__ に strategy / execution / monitoring が列挙されていますが、これらは別モジュール（戦略や発注制御等）と連携するための名前空間です。

---

## 前提・依存関係

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai (OpenAI の新 SDK が import される想定)
  - defusedxml
- 標準ライブラリの urllib, json, datetime 等を利用

インストール方法はプロジェクトの packaging に依存します。開発環境では次のように想定します：

pip install -r requirements.txt
（requirements.txt をプロジェクトに用意している場合）

または開発インストール：

pip install -e .

---

## 環境変数（.env 例）

KabuSys は以下の環境変数を利用します。プロジェクトルートに .env を置くと自動ロードされます（無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須（少なくとも ETL / AI / 通知を使う場合）:
- JQUANTS_REFRESH_TOKEN=あなたのJ-Quantsリフレッシュトークン
- KABU_API_PASSWORD=kabuステーションAPIパスワード
- SLACK_BOT_TOKEN=Slack Bot Token
- SLACK_CHANNEL_ID=Slack チャンネル ID
- OPENAI_API_KEY=OpenAI API キー（score_news / score_regime で使われることがある）

任意（デフォルト値あり）:
- KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_PASSWORD=...

---

## セットアップ手順（ローカルでの例）

1. Python 3.10+ を用意
2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 依存パッケージをインストール
   pip install duckdb openai defusedxml
   （プロジェクトが requirements.txt を用意していれば pip install -r requirements.txt）
4. プロジェクトルートに .env を作成（上記参照）
5. DuckDB 用ディレクトリ作成
   mkdir -p data

---

## 使い方（コード例）

- settings を使って設定を取得する

from kabusys.config import settings
print(settings.duckdb_path)
print(settings.jquants_refresh_token)  # 必須: 未設定なら ValueError

- DuckDB 接続を開いて日次 ETL を実行する

import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニューススコアリング（AI）を実行する

from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は DuckDB 接続。target_date はスコア生成日（ニュースウィンドウは前日 15:00 JST ～ 当日 08:30 JST）
count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"scored {count} codes")

- 市場レジーム判定

from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ DB を初期化する

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ユーティリティの例

from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize

momentum = calc_momentum(conn, target_date=date(2026,3,20))
momentum_z = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

- データ品質チェック

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i.check_name, i.severity, i.detail)

---

## 注意点・運用上のポイント

- OpenAI の呼び出しは API のレート・エラーを考慮したリトライとフェイルセーフが実装されていますが、API キーの管理やコストには注意してください。
- J-Quants API はレート制限があるため、jquants_client は内部で固定間隔スロットリングとリトライを行います。
- ETL は差分更新を行う設計です。初回は過去データのバックフィルが必要になります。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックされています。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py                    - パッケージ情報（__version__ 等）
- config.py                      - 環境変数 / 設定管理
- ai/
  - __init__.py                  - news_nlp.score_news を公開
  - news_nlp.py                  - ニュースセンチメントスコアリング（LLM 呼び出し、バッチ処理）
  - regime_detector.py           - 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py            - J-Quants API クライアント（取得・保存）
  - pipeline.py                  - ETL パイプライン（run_daily_etl など）
  - etl.py                       - ETLResult を再エクスポート
  - news_collector.py            - RSS 取得・前処理・保存ユーティリティ（SSRF 対策等）
  - calendar_management.py       - 市場カレンダー管理（is_trading_day 等）
  - stats.py                     - zscore_normalize 等の統計ユーティリティ
  - quality.py                   - データ品質チェック
  - audit.py                     - 監査ログスキーマ初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py           - calc_momentum, calc_volatility, calc_value
  - feature_exploration.py       - calc_forward_returns, calc_ic, factor_summary, rank
- (strategy/, execution/, monitoring/ は名前空間として扱われる想定)

---

## 貢献・拡張

- 新しいデータソースや RSS ソースを追加する場合は news_collector を拡張してください。
- 取引実行ロジック（broker API 連携）や戦略実装は strategy / execution 名前空間を使って実装できます。
- テストは各モジュールの I/O をモックして行うことを推奨します（特に外部 API 呼び出しやネットワーク）。

---

お問い合わせや仕様に関する変更点があれば指示ください。README をプロジェクトの実態に合わせて調整します。