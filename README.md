KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株のデータ収集（ETL）、データ品質チェック、特徴量・ファクター計算、ニュースの NLP スコアリング、LLM を用いた市場レジーム判定、監査ログ（トレーサビリティ）などを含む自動売買基盤のコアライブラリです。  
主に DuckDB をデータレイヤに用い、J-Quants API からマーケットデータを取得して安全に保存・前処理し、研究（research）・戦略（strategy）・実行（execution）層へデータを提供することを目的としています。

主な機能
--------
- ETL（data.pipeline）
  - J-Quants から株価・財務・マーケットカレンダーを差分取得・保存（冪等）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- データ管理（data.*）
  - market_calendar（営業日ロジック）、raw_prices/raw_financials の保存ユーティリティ
  - ニュース収集（RSS）と前処理（news_collector）
  - J-Quants クライアント（rate limiting、token refresh、retry）
  - 監査ログスキーマの初期化（audit.init_audit_db / init_audit_schema）
- AI / NLP（ai.*）
  - ニュース記事を LLM（gpt-4o-mini 等）で銘柄ごとにセンチメントスコア化（news_nlp.score_news）
  - マクロニュースと ETF (1321) の MA200 乖離を合成して市場レジーム判定（regime_detector.score_regime）
- リサーチ（research.*）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー
- 汎用ユーティリティ
  - Z スコア正規化（data.stats.zscore_normalize）
  - 安全な RSS 取得（SSRF 対策、gzip 上限など）

セットアップ手順
----------------

前提
- Python 3.9+（typing の一部表現を利用）
- DuckDB を利用します（duckdb パッケージ）
- OpenAI API と連携する機能は openai パッケージを利用
- RSS の安全なパースに defusedxml を利用

推奨手順（ローカル開発）
1. 仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があれば）
   - pip install -e .           # パッケージとして編集可能インストール
   - または pip install -r requirements.txt

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL 用）
     - OPENAI_API_KEY — OpenAI API キー（AI モジュール用）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（実行モジュール用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
   - オプション（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

.env の例（プロジェクトルート）
--------------------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567

使い方（主要な例）
-----------------

1) ETL を実行してデータを取得・保存する（日次 ETL）
- サンプル:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  - run_daily_etl はカレンダー→株価→財務→品質チェックを順に実行し ETLResult を返します。

2) ニュースを LLM でスコアリングする
- サンプル:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込銘柄数: {written}")

  - OPENAI_API_KEY は環境変数か api_key 引数で渡します。
  - 対象記事ウィンドウは「前日 15:00 JST ～ 当日 08:30 JST」に対応する設計です。

3) 市場レジーム判定
- サンプル:
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

  - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime テーブルへ書き込みます。

4) 監査ログ（audit）初期化
- サンプル（監査用 DuckDB を初期化）:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は監査用 DB 接続（TimeZone を UTC に固定）

5) ファクター / リサーチ機能の利用
- 例: calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
  - duckdb 接続を渡して日付を指定すると、(date, code) をキーとした dict のリストが返ります。
  - 例: from kabusys.research.factor_research import calc_momentum

注意事項 / 設計方針
------------------
- ルックアヘッドバイアス対策:
  - 多くの関数は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストや再現性を確保するために target_date を指定してください。
- API 呼び出しの堅牢性:
  - J-Quants クライアントはレート制御・再試行（exponential backoff）・401 リフレッシュなどを実装しています。
  - OpenAI 呼び出しはリトライや例外ハンドリングを行い、失敗時はフォールバック（たとえば 0.0 スコア）で処理継続します。
- DB 操作は可能な限り冪等（ON CONFLICT / DO UPDATE）で実装されています。
- ニュース収集は SSRF 対策、レスポンスサイズ制限、トラッキングパラメータ除去などセキュリティ対策が施されています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定読み込みロジック（.env 自動ロード等）
- ai/
  - __init__.py
  - news_nlp.py                   — ニュース NLP スコアリング（score_news）
  - regime_detector.py            — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py                   — ETL パイプライン（run_daily_etl 他）
  - etl.py                        — ETLResult の再エクスポート
  - jquants_client.py             — J-Quants API クライアント（fetch/save）
  - news_collector.py             — RSS ニュース収集（SSRF 対策等）
  - calendar_management.py        — 市場カレンダー管理（営業日判定等）
  - quality.py                    — データ品質チェック（missing/spike/duplicates/etc.）
  - stats.py                      — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                      — 監査ログスキーマ初期化・ユーティリティ
- research/
  - __init__.py
  - factor_research.py            — Momentum/Volatility/Value の計算
  - feature_exploration.py        — forward returns, IC, summary, rank
- research/*（上記ファイル群）
- その他: strategy/, execution/, monitoring/ パッケージへのエクスポートが行われていますが、主要実装は上記モジュール中心です。

開発・運用ヒント
-----------------
- 自動 .env ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- ロギング:
  - settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- 本番・模擬（paper）環境:
  - KABUSYS_ENV を設定すると is_live / is_paper / is_dev 切り替え用のフラグが利用できます。
- OpenAI / 外部 API の呼び出し:
  - API 費用やレートに注意してバッチ処理・チャンク処理を行ってください。

貢献
----
バグレポート、改善提案、プルリクエスト歓迎です。コードの一貫性（例: ルックアヘッド対策、冪等性、例外処理）を維持するようにお願いします。

ライセンス
---------
（プロジェクトに LICENSE ファイルがあればそこを参照してください。本リポジトリには README 以上のライセンス情報をここに追記してください。）

問い合わせ
----------
不明点や導入相談はリポジトリの Issues またはプロジェクト管理者へお問い合わせください。

---  
この README はコードベース（src/kabusys/*.py）を参照して作成しました。実際の利用には pyproject.toml / requirements.txt / LICENSE 等のプロジェクトルートファイルを確認してください。