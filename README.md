KabuSys
=======

概要
----
KabuSys は日本株のデータプラットフォームと研究／自動売買基盤のための Python ライブラリです。本プロジェクトは以下の主要機能群を提供します。

- J-Quants API 経由のデータ取得（株価日足・財務・市場カレンダー）と DuckDB への冪等保存（ETL）
- ニュース収集・前処理（RSS）と LLM を用いたニュースセンチメント評価（銘柄別 ai_score）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- 研究向けファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal/order/execution）用のスキーマ初期化ユーティリティ
- 環境設定読み込みと管理

特徴
----
主な機能一覧（抜粋）：

- データ取得・保存（kabusys.data.jquants_client）
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - レート制限・認証（リフレッシュトークン）・リトライ処理を内蔵
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の日次一括処理
  - 個別の run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult データクラスで結果・品質問題を集約
- ニュース収集・NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS 取得、テキスト前処理、記事ID生成（URL 正規化 + SHA256）
  - OpenAI を用いた銘柄別センチメント評価（gpt-4o-mini、JSON-mode）
  - calc_news_window / score_news：前日 15:00 JST ～ 当日 08:30 JST を対象
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM スコア（30%）を合成
  - score_regime: market_regime テーブルへの冪等書き込み
- 研究用ユーティリティ（kabusys.research）
  - calc_momentum, calc_volatility, calc_value：ファクター計算
  - calc_forward_returns, calc_ic, factor_summary, rank：特徴量探索・IC 計算
  - zscore_normalize（kabusys.data.stats）によるクロスセクション正規化
- データ品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行
- 監査ログスキーマ（kabusys.data.audit）
  - init_audit_schema / init_audit_db：監査テーブル（signal_events, order_requests, executions）初期化

セットアップ
----------
環境の準備例（開発用）:

1. リポジトリをクローンし仮想環境を作成
   - python 3.10+ を推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. パッケージをインストール
   - 基本的な依存（抜粋）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install -e .         # 開発インストール（setup/pyproject がある場合）
     - または個別に:
       - pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能）。
   - 必須の主要環境変数（コード参照: kabusys.config.Settings）:
     - JQUANTS_REFRESH_TOKEN   -- J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD       -- kabu API パスワード（注文連携がある場合）
     - SLACK_BOT_TOKEN         -- Slack 通知用 Bot トークン（通知を使う場合）
     - SLACK_CHANNEL_ID        -- Slack チャネル ID
     - OPENAI_API_KEY          -- OpenAI API キー（AI 機能を使う場合）
   - 任意 / デフォルト（settings に記載）:
     - KABUSYS_ENV (development / paper_trading / live) (default: development)
     - LOG_LEVEL (DEBUG/INFO/...)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

例 .env（プロジェクトルート）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=passwd
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
（.env.example を参考に作成してください）

使い方（主要ユースケース例）
-------------------------

1) DuckDB に接続して日次 ETL を実行する

Python スニペット例:
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# ETL を今日分で実行（id_token を明示的に渡すことも可能）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

説明:
- run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックを順に実行し ETLResult を返します。
- settings.jquants_refresh_token が設定されていれば内部でトークンを取得して API 呼び出しを行います。

2) ニュースのセンチメント（銘柄別）を計算する

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # 指定日分をスコアリング
print(f"wrote {n_written} ai_scores")

注意:
- OPENAI_API_KEY（または引数 api_key）を設定しておく必要があります。
- raw_news / news_symbols / ai_scores テーブルが存在し、raw_news に記事が入っていることが前提です。

3) 市場レジーム判定を実行する

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026, 3, 20))  # market_regime に書き込む

注意:
- OpenAI API キー（OPENAI_API_KEY または api_key 引数）が必要です。
- prices_daily / raw_news / market_regime テーブルのスキーマが整っていることを前提とします。

4) 監査ログ用の DB 初期化

from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます

ディレクトリ構成
----------------
主要ファイル・モジュール（src/kabusys 以下）:

- __init__.py
- config.py                   : 環境変数読み込み・Settings 定義（.env 自動ロード）
- ai/
  - __init__.py               : score_news エクスポート
  - news_nlp.py               : ニュースを使った銘柄別センチメント評価
  - regime_detector.py        : 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py         : J-Quants API クライアント＋DuckDB への保存
  - pipeline.py               : ETL パイプライン（run_daily_etl 等）
  - etl.py                    : ETLResult エクスポート
  - news_collector.py         : RSS フィード取得・前処理
  - calendar_management.py    : 市場カレンダー管理（営業日判定等）
  - stats.py                  : 汎用統計（zscore_normalize）
  - quality.py                : データ品質チェック
  - audit.py                  : 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py        : calc_momentum, calc_value, calc_volatility
  - feature_exploration.py    : calc_forward_returns, calc_ic, factor_summary, rank

テーブル名（コード内で参照される代表例）
- raw_prices, prices_daily, raw_financials, ai_scores, raw_news, news_symbols, market_calendar, market_regime
- audit 用: signal_events, order_requests, executions

設計上の注意点 / ポイント
------------------------
- Look-ahead バイアス対策: 多くのモジュールで date.today() を直接参照せず、呼び出し側で target_date を渡す設計です。バックテストや再現性を確保するため、関数呼び出し時に日付を明示してください。
- 冪等性: J-Quants からの保存処理は ON CONFLICT / DO UPDATE を利用し冪等に設計されています。
- フェイルセーフ: AI API の失敗やネットワークエラーは、多くの箇所でフォールバック（ゼロスコア／スキップ）して処理継続するようになっています。
- テストしやすさ: OpenAI 呼び出し等は内部関数をモックできる設計です（例: kabusys.ai.news_nlp._call_openai_api を patch）。

依存関係（主要）
----------------
- duckdb
- openai
- defusedxml
- 標準ライブラリの urllib / json / datetime 等

（プロジェクトの pyproject.toml や requirements.txt に正確なバージョンを定義してください）

貢献・開発
---------
- テスト: 各種外部 API 呼び出しはモックしてユニットテストを作成してください。AI 呼び出しや HTTP 呼び出しは差し替え可能な内部関数が用意されています。
- コードスタイル: ロギングを多用しているので、エラー・ワーニングログを確認しやすくしておくと良いです。
- セキュリティ: news_collector では SSRF 対策や XML の安全なパースを実装していますが、外部 URL の扱いには注意してください。

ライセンス
---------
（ここにプロジェクトのライセンス情報を記載してください）

補足・参照
----------
- 環境ロード: kabusys.config はリポジトリルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を自動で読み込みます。自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の JSON Mode を利用する実装が多く含まれるため、API のレスポンス形式やエラーハンドリングに注意してください。

必要であれば README に含める例コマンド、より詳細な環境変数一覧、テーブルスキーマ、API の実行例などを追加で作成します。どの項目をさらに詳しく載せたいか教えてください。