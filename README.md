KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・自動売買に必要な共通処理群を提供する Python パッケージです。主な機能は以下のとおりです。

- J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）
- DuckDB を用いた ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集・NLP による銘柄センチメント算出（OpenAI を利用）
- 市場レジーム判定（ETF とマクロニュースの合成）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- カレンダー管理（営業日判定、next/prev trading day 等）
- 監査ログ（signal → order → execution のトレーサビリティ）スキーマの初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

特徴
----
- Look-ahead bias を避ける設計（内部処理で date.today()/datetime.today() を直接参照しない等）
- DuckDB をデータレイクとして採用（軽量かつ高速な SQL 処理）
- J-Quants API のレート制御・リトライ・トークンリフレッシュ対応
- OpenAI（gpt-4o-mini）を用いた JSON モードでの安定した NLP 呼び出し（JSON レスポンスのバリデーション実装）
- 冪等性を考慮した保存（ON CONFLICT を用いた upsert）
- セキュリティに配慮したニュース収集（SSRF 対策、XML パース防護、受信サイズ制限）

セットアップ手順
----------------

1. Python 環境を用意
   - 推奨: Python 3.10 以上（タイプヒントに union 型等を利用）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数の設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意（デフォルト値あり）:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL
   - OpenAI:
     - OPENAI_API_KEY — OpenAI 呼び出し時に使用（score_news / score_regime は引数で直接キーを渡すことも可能）

   - .env の自動読み込み:
     - パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。
     - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データディレクトリ作成
   - デフォルトの DuckDB 保存先や監視用 DB の親ディレクトリを作成しておくと良いです（例: mkdir -p data）。

使い方（主要 API）
-----------------

以下は基本的な利用例です。すべての関数は DuckDB の接続オブジェクト（duckdb.connect(...）で得られる conn）を受け取ります。

1) DuckDB に接続する
   - import duckdb
   - conn = duckdb.connect("data/kabusys.duckdb")

2) 日次 ETL を実行する（市場カレンダー・株価・財務の差分取得と品質チェック）
   - from kabusys.data.pipeline import run_daily_etl
   - from datetime import date
   - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   - print(result.to_dict())

   ETLResult オブジェクトは fetched/saved の数、品質チェックの issues、errors を確認できます。

3) ニュースセンチメントを算出して ai_scores を書き込む
   - from kabusys.ai.news_nlp import score_news
   - from datetime import date
   - score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数または api_key 引数で指定

   戻り値は書き込んだ銘柄数（int）。

4) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
   - from kabusys.ai.regime_detector import score_regime
   - score_regime(conn, target_date=date(2026, 3, 20))

   OPENAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定してください。

5) 監査ログスキーマを初期化する
   - from kabusys.data.audit import init_audit_db, init_audit_schema
   - # 既存の DuckDB 接続にスキーマ追加:
     init_audit_schema(conn, transactional=True)
   - # 監査専用 DB を作る:
     audit_conn = init_audit_db("data/audit.duckdb")

6) ファクター計算やリサーチユーティリティ
   - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
   - momentum = calc_momentum(conn, date(2026,3,20))
   - forward = calc_forward_returns(conn, date(2026,3,20))
   - ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")

環境変数の自動読み込み（config の挙動）
---------------------------------------
- kabusys.config モジュールはプロジェクトルートを探索し .env と .env.local を読み込みます（OS 環境変数が優先、.env.local は上書き）。
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 必須変数が参照されたとき未設定だと ValueError を投げます（settings.jquants_refresh_token 等）。

ディレクトリ構成（抜粋）
----------------------

ここではリポジトリ内の主なファイル / モジュールをツリー形式で示します（提供コードに基づく）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py (ETLResult 再エクスポート)
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (その他: strategy, execution, monitoring モジュールをパッケージ公開変数に含める設計になっていますが、ここには data/research/ai を中心に実装あり)

補足: 各モジュールの責務
---------------------
- data.jquants_client: J-Quants API 呼び出し、レートリミットとリトライ、DuckDB への保存（raw_prices/raw_financials/market_calendar）
- data.pipeline: 日次 ETL のオーケストレーション（カレンダー → 株価 → 財務 → 品質チェック）
- data.quality: 欠損・重複・スパイク・日付整合性チェック
- data.news_collector: RSS 取得・前処理・raw_news / news_symbols への保存（SSRF 対策、XML パース防御あり）
- ai.news_nlp: 銘柄ごとのニュース統合→OpenAI によるスコア取得→ai_scores に保存
- ai.regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定（market_regime テーブルへ保存）
- research.*: ファクター計算・将来リターン・IC・統計サマリー等のリサーチユーティリティ
- data.audit: signal / order_request / executions を記録する監査スキーマの作成と初期化

よくある質問
-------------
Q: OpenAI のキーはどのように渡すべきですか？
A: 環境変数 OPENAI_API_KEY に設定するのが簡便です。各関数は api_key 引数を受け取るため、テストや一時的なキーの注入も可能です。

Q: .env の読み込みをテストで無効化するには？
A: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数で設定してください。

Q: ETL 実行中に一部のステップが失敗したらどうなりますか？
A: pipeline.run_daily_etl は各ステップで例外ハンドリングを行い、可能な限り処理を続けます。ETLResult.errors に失敗情報が蓄積されます。品質チェックの結果は result.quality_issues に入ります。

ライセンス / 貢献
-----------------
- 本ドキュメントはコードベースの説明を目的としています。実際のライセンス表記・貢献手順はリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問題報告・改善提案
------------------
- バグ報告や機能改善提案はリポジトリの Issue に記載してください。特に外部 API 呼び出し部分やシリアライズ周りの入力検証には注意を払っていますが、実運用環境での追加検証・監視設定を推奨します。

以上。必要であれば、README に含める具体的な .env.example（キー一覧）や、より詳しい使い方（発注フロー・監視/モニタリングの運用手順）を追記します。どの情報を優先して追加しましょうか？