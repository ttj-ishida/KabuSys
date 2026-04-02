KabuSys — 日本株データプラットフォーム＆自動売買基盤
=================================================

概要
----
KabuSys は日本株向けのデータプラットフォームと研究／自動売買ユーティリティ群です。  
J-Quants（株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ETL パイプライン、特徴量計算、監査ログ（発注→約定トレース）などを備え、研究（Research）と本番（Execution）を分離して運用できるよう設計されています。

主な機能
--------
- データ取得・ETL
  - J-Quants API から日足（OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に保存
  - 差分更新、バックフィル、ページネーション対応、HTTP リトライ・レート制御
- データ品質チェック
  - 欠損（OHLC）、主キー重複、スパイク（前日比）、日付不整合（将来日付・非営業日）検出
- ニュース収集・NLP
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去）→ raw_news 保存
  - OpenAI（gpt-4o-mini）を利用した記事/銘柄別センチメントスコア算出（ai_scores へ書込）
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュース（LLM）を組み合わせて市場レジーム（bull/neutral/bear）を判定・保存
- 研究用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）、ファクター統計要約、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化（冪等）
  - order_request_id による冪等性、UTC タイムスタンプ保存
- 運用・監視関連
  - 環境設定（.env 自動読み込み、プロジェクトルート検出）
  - 各種設定（閾値・DB パス・API ベース URL 等）

セットアップ手順
----------------
前提
- Python 3.10 以上（| 型注釈や newer typing を使用）
- DuckDB、OpenAI SDK、defusedxml 等のライブラリが必要

1. クローン / ワークツリーを準備
   - リポジトリをクローンして作業ディレクトリへ移動

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がない場合は最低限以下をインストールしてください（プロジェクトに応じて追加）。
     - duckdb
     - openai
     - defusedxml
   例:
     - pip install duckdb openai defusedxml

   （実運用では slack, requests 等が必要な機能がある場合があります。パッケージ管理はプロジェクト側で requirements.txt にまとめてください）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env を置くと、自動でロードされます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

  必須（主に config.Settings で参照される環境変数）
  - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
  - KABU_API_PASSWORD=<kabu_api_password>        (kabuステーション連携時)
  - SLACK_BOT_TOKEN=<slack_bot_token>
  - SLACK_CHANNEL_ID=<slack_channel_id>
  - OPENAI_API_KEY=<openai_api_key>               （AI 機能を使う場合）

  任意（デフォルト値あり）
  - KABUSYS_ENV=development|paper_trading|live  （デフォルト development）
  - LOG_LEVEL=INFO|DEBUG|...                    （デフォルト INFO）
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PID_FILE_PATH=data/execution.pid
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

  例 .env（テンプレート）
    JQUANTS_REFRESH_TOKEN=xxxxxxxx
    OPENAI_API_KEY=sk-xxxxxxxx
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    LOG_LEVEL=DEBUG
    KABUSYS_ENV=development

使い方（主要な例）
-----------------

※ 各例は Python REPL / スクリプト内で実行する想定です。事前に環境変数と依存ライブラリ、DB（ファイルの親ディレクトリ）が整っていることを確認してください。

1) DuckDB 接続を作る
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL 実行（J-Quants から差分取得・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

3) ニュース NLP スコア付与（ai_scores に書き込む）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {count} codes")

  - OpenAI API キーを引数で渡すことも可能（api_key="sk-..."）。 None の場合は環境変数 OPENAI_API_KEY を参照。

4) 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))  # market_regime テーブルに書き込み

5) 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

6) Z スコア正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

7) 監査ログスキーマ初期化（監査用 DB を新規に作る）
  from kabusys.data.audit import init_audit_db
  from pathlib import Path
  audit_conn = init_audit_db(Path("data/audit.duckdb"))
  # これで signal_events / order_requests / executions 等のテーブルが作成されます

運用上のポイント・注意
--------------------
- 自動 .env 読み込み:
  - 実装はプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を読み込みます。
  - 読み込み優先度: OS 環境 > .env.local > .env
  - テストや特別な起動時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI 呼び出し:
  - AI モジュールはリトライやフォールバック（API 失敗時スコア 0.0）を設計に含めています。
  - テスト時は内部の _call_openai_api を mock して差し替え可能です。
- DuckDB バインド:
  - 一部関数は DuckDB の executemany に空リストを渡すと不具合を起こすバージョンを考慮して条件分岐を入れています（互換性注意）。
- Look-ahead Bias 防止:
  - 多くの関数が内部で date.today() を直接参照せず、target_date を引数で受け取る設計です。バックテスト時には target_date を逐次渡してください。
- J-Quants API:
  - レート制限（120 req/min）を守るレートリミッタ、401 時のリフレッシュ、429/5xx のリトライ等を実装済みです。
  - get_id_token() は settings.jquants_refresh_token を使います。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                : パッケージ初期化（__version__）
- config.py                  : 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py              : ニュースセンチメントスコア算出（score_news）
  - regime_detector.py       : マクロ + MA200 を使った市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py              : ETL パイプライン（run_daily_etl 等）
  - etl.py                   : ETLResult の公開
  - jquants_client.py        : J-Quants API クライアント & DuckDB 保存関数
  - news_collector.py        : RSS 収集・正規化・保存ロジック
  - quality.py               : データ品質チェック（各チェック & run_all_checks）
  - stats.py                 : 汎用統計ユーティリティ（zscore_normalize）
  - calendar_management.py   : 市場カレンダー管理（営業日判定・calendar_update_job）
  - audit.py                 : 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py       : Momentum/Value/Volatility 等の計算
  - feature_exploration.py   : 将来リターン・IC・統計サマリー 等

補足（テスト・拡張）
------------------
- OpenAI / ネットワーク呼び出し部分はモック可能に設計されています（内部関数を patch）。
- 実運用時は Slack 通知や kabuステーション連携、発注処理などを別モジュール（execution 等）で接続してください（本リポジトリはデータ・研究・監査基盤のコアを提供します）。
- 依存パッケージや CI、パッケージ化（pyproject.toml）等はプロジェクトの配布方針に合わせて追加してください。

問題報告・開発
---------------
バグや改善提案は issue を立ててください。コード内の docstring に設計方針や失敗時のフォールバックが明記されていますので、新しい変更は既存の設計原則（例: ルックアヘッドバイアス防止、冪等性、フェイルセーフ）を尊重してください。

以上。必要であれば README に含める具体的な requirements.txt 例や systemd / cron での定期実行例、デモスクリプトのテンプレートも作成します。どれを追加しますか？