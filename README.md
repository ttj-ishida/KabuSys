# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。J-Quants からの市場データ取得・ETL、ニュース収集と NLP による銘柄センチメント評価、マーケットレジーム判定、ファクター計算や研究用ユーティリティ、監査ログ（注文・約定のトレーサビリティ）などを提供します。

以下はこのリポジトリの簡易 README.md（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env）
- 使い方（簡易コード例）
- ディレクトリ構成（主要ファイルの説明）
- 注意事項 / 設計方針（抜粋）

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）と DuckDB への保存
- ニュース RSS 収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- ETF（1321）の MA とマクロセンチメントを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査テーブル（signal, order_request, executions）の初期化/管理

設計上の特徴：
- DuckDB を主要な永続化層として利用
- Look-ahead bias を避ける実装（date の扱いに注意）
- 冪等（idempotent）な DB 保存（ON CONFLICT）
- API 呼び出しに対するリトライ/バックオフとレート制御

---

## 機能一覧（主な公開 API）

- 環境/設定
  - kabusys.config.settings: 環境変数読み込みとアクセス（自動 .env ロードあり）

- データ ETL / API クライアント
  - kabusys.data.jquants_client
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - kabusys.data.pipeline
    - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（ETLResult を返す）
  - kabusys.data.news_collector
    - fetch_rss, preprocess_text, など（RSS 取得・整形）
  - kabusys.data.calendar_management
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - kabusys.data.quality
    - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
  - kabusys.data.audit
    - init_audit_schema, init_audit_db

- AI / NLP
  - kabusys.ai.news_nlp.score_news: 指定日のニュースを集約し OpenAI で銘柄別センチメントを計算、ai_scores テーブルへ保存
  - kabusys.ai.regime_detector.score_regime: ETF 1321 の MA とマクロニュース（LLM）を組合せて market_regime テーブルへ保存

- 研究用（Research）
  - kabusys.research.factor_research: calc_momentum, calc_value, calc_volatility
  - kabusys.research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - kabusys.data.stats.zscore_normalize

---

## セットアップ手順

前提:
- Python 3.10+（Union 型 | を多用しているため）
- Git などでプロジェクトルートを保持（.env 自動読み込みに必要）

1. リポジトリをチェックアウト
   - 例: git clone ...

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限の依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトで pyproject.toml / requirements.txt がある場合はそちらを使用）

4. 環境変数の準備
   - プロジェクトルートに .env を作成（下の「環境変数」節参照）。
   - 注意: kabusys.config はプロジェクトルート（.git または pyproject.toml）を探して .env を自動読み込みします。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 環境変数（.env / 必須・任意）

主な環境変数（一例）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（fetch 系 API の認証に使用）
  - kabusys.data.jquants_client.get_id_token() で利用

オプション／サービス連携:
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（システム連携用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知連携に使用

DB / パス:
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH など: 実行監視に関するパス

システム:
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env ロードを抑止

例 (.env):
JQUANTS_REFRESH_TOKEN="xxxxxxxx"
OPENAI_API_KEY="sk-xxxx"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV="development"
LOG_LEVEL="INFO"

---

## 使い方（簡単なコード例）

以下は最小限の利用例。DuckDB に接続して ETL を実行したり、ニューススコア・レジーム判定を呼ぶパターンです。

- 日次 ETL を実行（prices/financials/calendar の差分取得 + 品質チェック）:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメントを計算して ai_scores テーブルへ保存:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None -> 環境変数 OPENAI_API_KEY を使用
print(f"書込み銘柄数: {n_written}")

- 市場レジーム判定（1321 の ma200 乖離 + LLM マクロセンチメント）:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB を初期化（監査用 DuckDB ファイル作成）:

from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_db = init_audit_db(Path("data/audit.duckdb"))
# init_audit_db は transactional=True 相当でスキーマを作成する

- 研究用：ファクター計算・IC など

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026, 3, 20))
fwd = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
print("IC:", ic)

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                         # .env 自動読み込み・Settings クラス
- ai/
  - __init__.py
  - news_nlp.py                      # ニュース NLU: score_news
  - regime_detector.py               # レジーム判定: score_regime
- data/
  - __init__.py
  - jquants_client.py                # J-Quants API client + save_* 関数
  - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
  - etl.py                           # ETLResult エクスポート
  - news_collector.py                # RSS 収集, 前処理
  - calendar_management.py           # 市場カレンダー管理・営業日判定
  - quality.py                       # データ品質チェック
  - stats.py                         # zscore_normalize 等の統計ユーティリティ
  - audit.py                         # 監査ログテーブルの初期化
- research/
  - __init__.py
  - factor_research.py               # calc_momentum/calc_value/calc_volatility
  - feature_exploration.py           # calc_forward_returns, calc_ic, factor_summary, rank

（上記は抜粋。実際のリポジトリはさらにファイルが存在する可能性があります）

---

## 注意事項 / 設計のポイント

- Look-ahead bias 回避:
  - 日付関連関数は内部で datetime.today() / date.today() を不用意に参照しないよう設計されています。ETL / スコアリングは明示的な target_date を受け取って処理することを想定しています。

- 冪等性:
  - save_* 系関数は DuckDB 側で ON CONFLICT を使った更新を行い、再実行可能な ETL を目指しています。

- API 呼び出しの堅牢性:
  - J-Quants クライアント・OpenAI 呼び出しともにリトライ・バックオフ・エラーハンドリングを実装しています。OpenAI の呼び出しに関しては JSON mode を使い厳密な JSON 出力を期待していますが、パースエラー時はフェイルセーフ（0.0 など）で継続する設計になっています。

- セキュリティ / SSRF 対策:
  - news_collector では URL の正規化、トラッキングパラメータ除去、リダイレクト検査、プライベート IP のブロックなどを行います。

- 自動環境ロード:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動読み込みします。テストや一部ユースケースで自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に追加したい内容（例: CI 実行方法、詳しい .env.example、CLI 実装、サンプルデータのロード手順など）があれば指示してください。必要があれば英語版も作成します。