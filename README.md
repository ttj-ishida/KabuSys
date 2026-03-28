KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株のデータ基盤・リサーチ・AI（ニュースNLP / レジーム判定）および監査・ETL ユーティリティを揃えた自動売買 / 研究プラットフォームのコアライブラリです。本コードベースは以下の目的を想定しています:

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への ETL
- RSS ニュース収集とニュースに基づく銘柄センチメント（AI スコア）生成
- マーケットレジーム判定（ETF MA とマクロニュースの LLM センチメントを合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量探索
- データ品質チェック・カレンダー管理・監査ログ（発注・約定のトレーサビリティ）

特徴（主な機能）
----------------
- data/jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- data/pipeline, data/etl: 日次差分 ETL パイプライン（株価・財務・カレンダー）と ETL 結果クラス
- data/news_collector: RSS 収集（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
- data/quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
- data/calendar_management: JPX カレンダー管理・営業日ヘルパー
- data/audit: 監査テーブル定義と初期化ユーティリティ（signal → order_request → execution を追跡）
- ai/news_nlp: ニュースを LLM（gpt-4o-mini 等）で評価し ai_scores に保存する処理（バッチ・JSON Mode・リトライ）
- ai/regime_detector: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定し market_regime に保存
- research/*: ファクター計算（モメンタム / バリュー / ボラティリティ）、将来リターン / IC / 統計サマリー等
- config: .env 自動読み込み（.env,.env.local）、アプリ設定の抽象化（settings オブジェクト）

準備（セットアップ）
--------------------
1. 必要な Python パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （その他、標準ライブラリ以外の依存があればプロジェクトの requirements.txt を参照してください）

   例:
   pip install duckdb openai defusedxml

2. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml がある場所）に .env または .env.local を置くと自動読み込みされます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須環境変数（主要）:
   - JQUANTS_REFRESH_TOKEN  - J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      - kabu ステーション API パスワード
   - SLACK_BOT_TOKEN        - Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID       - Slack チャンネル ID
   - OPENAI_API_KEY         - OpenAI API キー（score_news / score_regime 呼び出し時に引数で渡すことも可）

   任意 / デフォルト付き:
   - KABUSYS_ENV (development / paper_trading / live) デフォルト: development
   - LOG_LEVEL (DEBUG/INFO/…) デフォルト: INFO
   - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH デフォルト: data/kabusys.duckdb
   - SQLITE_PATH デフォルト: data/monitoring.db

   .env の自動パースはシェル形式の export やコメント、クォートをサポートします。

3. DuckDB データベース用ディレクトリ作成
   settings.duckdb_path の親ディレクトリを作成してください（必要ならスクリプト内で自動作成される関数も利用可）。

使い方（簡単な例）
-----------------

- 設定と DB 接続

  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行してデータを取得・保存・品質チェック

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（AI）スコア生成（前日 15:00 JST ～ 当日 08:30 JST のウィンドウ）

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込み銘柄数: {n_written}")

  注意: api_key を渡さない場合は環境変数 OPENAI_API_KEY が使用されます。

- 市場レジーム判定

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログスキーマ初期化（既存の DuckDB 接続に監査テーブルを作成）

  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

  監査用に独立 DB を作る場合:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

設計上の重要な注意点
-------------------
- ルックアヘッドバイアス回避:
  ファクター計算 / ニュース集計 / レジーム判定などは内部で datetime.today() や date.today() を参照しないよう設計されています。target_date を明示的に渡すことでバックテスト環境での正しい挙動を保証します。
- フェイルセーフ:
  OpenAI 呼び出し失敗時はゼロや中立スコアにフォールバックし、処理を継続します（例外を上位へ送出しない設計が多い）。
- .env 自動読み込み:
  プロジェクトルートの .env/.env.local を自動で読み込みます。テスト時に自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany 空リスト制約:
  一部 DuckDB バージョンでは executemany に空リストを渡すと失敗するため、コード内で空チェックを行っています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                         パッケージ初期化（__version__）
- config.py                           環境変数 / 設定管理（settings オブジェクト）
- ai/
  - __init__.py                        score_news を公開
  - news_nlp.py                         ニュース NLU スコアリング（LLM 呼び出し・バッチ処理）
  - regime_detector.py                  レジーム判定ロジック（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py                   J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py                         ETL パイプライン（run_daily_etl 等）
  - etl.py                              ETL 型再エクスポート（ETLResult）
  - news_collector.py                   RSS 収集（SSRF/サイズ対策・前処理）
  - quality.py                          データ品質チェック（欠損・重複・スパイク・日付）
  - calendar_management.py              市場カレンダー/営業日ロジック
  - stats.py                            統計ユーティリティ（zscore_normalize）
  - audit.py                            監査ログスキーマの定義・初期化
- research/
  - __init__.py
  - factor_research.py                  ファクター計算（momentum/value/volatility）
  - feature_exploration.py              将来リターン / IC / 統計サマリー
- research/* その他ユーティリティ（zscore 正規化の再エクスポートなど）

補足（実運用向けメモ）
---------------------
- OpenAI 利用: gpt-4o-mini 等を想定。API レスポンスは JSON Mode（response_format={"type":"json_object"}）でパースを簡潔にしていますが、堅牢なバリデーションを行っています。
- J-Quants API: レート制御（120 req/min）およびトークン自動リフレッシュ、ページネーション対応を組み込んでいます。
- ニュース RSS: URL 正規化・トラッキング除去、SSRF 対策、gzip サイズチェック等の安全対策を実装しています。
- テスト: 一部内部関数（OpenAI 呼び出し等）はモック差し替えを想定して設計されています（例: unittest.mock.patch）。

ライセンス・貢献
----------------
このリポジトリにライセンス表記がない場合はプロジェクトオーナーに確認してください。コントリビューション方針・コードスタイルはプロジェクト内の CONTRIBUTING.md や pyproject.toml を参照してください（存在する場合）。

問い合わせ
----------
実装や API 使用法について不明点があれば、ソース内ドキュメント（関数 docstring）を参照してください。README の補足を希望する場合は具体的な利用シナリオ（ETL スケジューリング / バックテスト連携など）を教えてください。