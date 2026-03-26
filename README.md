# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データETL、ニュースNLP（LLMベースのセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ用スキーマなど、取引システム／リサーチプラットフォームで必要な共通機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージ群です。

- J-Quants API からの株価・財務・カレンダーデータの差分取得と DuckDB への保存（ETL）
- RSS によるニュース収集と OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- ファクター（Momentum/Value/Volatility 等）の計算および研究用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal / order_request / executions）用の DuckDB スキーマ初期化
- 簡易的な設定管理（.env 自動ロード、環境変数）

設計上のポイント:
- Look-ahead バイアスを避けるため、内部処理は引数で与えた日付のみ参照する（date.today() を日常的に参照しない）。
- DuckDB を主要なローカル DB として使用（ETL 等で大量データ処理に最適化）。
- OpenAI 呼び出しには冪等性やリトライ、JSON モードの応答パースを考慮。

---

## 機能一覧

- data（データプラットフォーム）
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存関数、認証・リトライ・レート制御）
  - カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS の取得・前処理・SSRF 対策）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai（LLM を用いた処理）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書込み
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュースを統合して market_regime に書込み
  - 両モジュールとも OpenAI API 呼び出しに堅牢なリトライ/フォールバック実装あり
- research（リサーチ/ファクター計算）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
- config（環境変数管理）
  - .env ファイルの自動読み込み（プロジェクトルート検出）および settings オブジェクト

---

## セットアップ手順

前提:
- Python 3.9+（型注釈や一部の構文を利用）
- システムに DuckDB がインストール可能であること

推奨手順（開発環境）:

1. レポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   必要な主要ライブラリ（例）:
   - duckdb
   - openai
   - defusedxml

   例:
   - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt がある場合はそれを利用してください。

4. パッケージをインストール（開発モード）
   - pip install -e .

5. 環境変数の準備
   プロジェクトルートに .env ファイルを用意してください（.env.example を参考に作成）。自動ロードの挙動:
   - OS 環境変数 > .env.local > .env の順に読み込み
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須の環境変数（モジュール利用に応じて）:
- JQUANTS_REFRESH_TOKEN : J-Quants 用のリフレッシュトークン（ETL で必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（注文実行等で使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
- OPENAI_API_KEY        : OpenAI 呼び出しに必要（news_nlp / regime_detector）
オプション:
- KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL (DEBUG|INFO|...)
- DUCKDB_PATH, SQLITE_PATH（データベースパス上書き）

---

## 使い方（基本例）

以下は代表的な使い方のコード例です。実行は Python スクリプトまたは REPL で行います。各例では既に必要な環境変数が設定されている前提です。

- DuckDB 接続作成（デフォルトパスを使用）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメントを計算して ai_scores に保存（OpenAI キーは環境変数か api_key 引数で指定）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026,3,20))  # returns number of codes written

  # 明示的に API キーを渡す場合:
  written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")

- 市場レジーム判定を行う
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))

- 研究用ファクター計算
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))

- 監査ログ用 DB 初期化（監査専用ファイルを作成）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions のテーブルとインデックスが作成されます

- カレンダー周りのユーティリティ
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  is_trading_day(conn, date(2026,3,20))
  next_trading_day(conn, date(2026,3,20))

- RSS からニュースを取得（ニュース収集の一部）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  # 返るのは前処理済みの NewsArticle 型リスト（id, datetime, source, title, content, url）

注意:
- OpenAI 呼び出しは API レートや料金が発生するため、テスト時はモックすることを推奨します（モジュール内の _call_openai_api を patch 可能）。
- ETL / 保存処理は DuckDB のスキーマに依存します。実運用前にスキーマ（テーブル）作成ステップを用意してください。

---

## 設定 (.env と自動ロード)

kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env/.env.local を自動読み込みします。優先順位は以下の通りです:

1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env（存在すれば設定、ただし OS で既に設定されたキーは上書きしない）

自動ロードを無効にする:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定

必須の環境変数が参照された場合、未設定だと ValueError が発生します。例えば settings.jquants_refresh_token は JQUANTS_REFRESH_TOKEN が必要です。

.env のフォーマットとパースは shell ライク（export 対応、クォート・コメント処理）に対応しています。

---

## ディレクトリ構成

主要ファイル・モジュールの概観（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                      : 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   : ニュースの LLM スコアリング（score_news）
    - regime_detector.py            : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             : J-Quants API クライアント（fetch/save）
    - pipeline.py                   : ETL パイプライン（run_daily_etl 等）
    - etl.py                        : ETL 公開インターフェース（ETLResult）
    - calendar_management.py        : マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py             : RSS 取得・前処理
    - quality.py                    : データ品質チェック
    - stats.py                      : 統計ユーティリティ（zscore_normalize）
    - audit.py                      : 監査ログスキーマ初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py            : Momentum/Volatility/Value 計算
    - feature_exploration.py        : 将来リターン・IC・統計サマリー等
  - monitoring/ (存在宣言のみ in __all__、実装は別途)
  - execution/ (注文実行関連、実装は別途)

リポジトリルートには .env.example を配置して、必要な環境変数名とサンプル値を示すことを推奨します。

---

## 開発・テスト上の注意

- OpenAI や外部 API への呼び出しはテストでモック可能に設計されています。news_nlp._call_openai_api や regime_detector._call_openai_api を patch してテストすることを推奨します。
- DuckDB をインメモリ（":memory:"）で使えば単体テストが容易です（例: duckdb.connect(":memory:")）。
- ETL 実行や DB 書き込みはトランザクション制御がある箇所とない箇所があるため、統合テスト時はロールバックや一時 DB を使って影響を隔離してください。
- ニュース収集では SSRF 対策や受信サイズ制限を実装していますが、外部接続を伴う処理は CI では外部依存を切る（モック）ことを推奨します。

---

## さらに詳しく / 貢献

- バグ報告や機能要望は Issue を作成してください。
- 新機能はブランチを切って Pull Request を送ってください。コーディング規約・テストを含めた提出をお願いします。

---

以上が KabuSys の概要・セットアップ・基本的な使い方です。必要であれば README に含めるサンプル .env.example、requirements.txt、あるいは具体的な CLI や systemd / cron ジョブの例を追加で作成します。どの情報を補足しますか？