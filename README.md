KabuSys — 日本株自動売買／データ基盤ライブラリ
================================

概要
----
KabuSys は日本株向けのデータプラットフォームと研究・運用ユーティリティ群を提供する Python パッケージです。  
主な目的は以下の通りです。

- J-Quants など外部 API からのデータ取得（株価、財務、マーケットカレンダー）
- ETL（差分取得・品質チェック）パイプライン
- ニュース収集・NLP による銘柄センチメント集約（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースを統合）
- 監査ログ（発注・約定のトレーサビリティ）用スキーマ初期化
- 研究用途のファクター計算・特徴量探索ユーティリティ

設計上のポイント
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を不用意に使用しない設計）
- DuckDB を用いたローカルデータストア（冪等保存、ON CONFLICT による更新）
- 外部 API 呼び出しに対するリトライ・レート制御を備えた堅牢な実装
- ニュース収集での SSRF 対策や XML 爆弾対策（defusedxml）などセキュリティ配慮

主な機能一覧
---------------
- data/
  - jquants_client: J-Quants API クライアント（取得・保存・認証・ページネーション・レート制御）
  - pipeline: 日次 ETL（差分取得、保存、品質チェック） run_daily_etl
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF/サイズ対策）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: JPX カレンダー管理（営業日判定・更新ジョブ）
  - audit: 監査ログ（signal_events / order_requests / executions）の DDL と初期化（init_audit_schema, init_audit_db）
  - stats: zscore_normalize など共通統計ユーティリティ
- ai/
  - news_nlp: ニュースをまとめて OpenAI に送信し銘柄別 ai_score を ai_scores テーブルへ保存（score_news）
  - regime_detector: ETF（1321）の 200 日 MA とマクロニュースの LLM スコアを合成して市場レジーム判定（score_regime）
- research/
  - factor_research: momentum / value / volatility 等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー等
- config.py: .env の自動読み込み（.env / .env.local、CWD に依存しないルート探索）と Settings（環境変数ラッパー）

セットアップ手順
----------------

1. 前提
   - Python 3.9+（コードベースは型アノテーションを多用）
   - duckdb, openai, defusedxml などが必要（依存はプロジェクトの requirements に合わせてインストールしてください）。

2. ソースを配置 / インストール（開発モード）
   - リポジトリルートで：
     pip install -e .

3. 必要な Python パッケージ（例）
   pip install duckdb openai defusedxml

4. 環境変数 / .env
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必要な主要環境変数（概要）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabu ステーション API パスワード（必須）
     - KABU_API_BASE_URL : kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知に使用（必須）
     - OPENAI_API_KEY : OpenAI 呼び出しで使用（ai.score_news / ai.score_regime）。関数引数で上書き可能。
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視系 DB（デフォルト data/monitoring.db）
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/…（デフォルト INFO）

   - .env のパースは Bash 風の export/クォート/コメントを扱います。詳細は kabusys.config の実装を参照してください。

   例 .env:
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

使い方（主要な例）
-----------------

- DuckDB 接続を作って ETL を実行する（run_daily_etl）:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコア付与（OpenAI キーを環境変数に設定するか api_key を渡す）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None -> OPENAI_API_KEY を参照
  print("written:", n_written)

- 市場レジーム判定:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB 初期化（監査専用 DB を作る）:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って発注ログテーブルへ書き込みなどを行えます

- 研究用ユーティリティ（例: モメンタム計算）:

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))

実装上の注記 / 運用上の注意
-------------------------
- OpenAI 呼び出し:
  - news_nlp と regime_detector は gpt-4o-mini を想定した JSON mode を使います。
  - API 呼び出しはリトライ・フォールバックを行い、失敗時は安全に 0.0 等で続行する実装です（完全失敗で例外を投げない設計が多い）。
  - テスト時は _call_openai_api をモックする想定です。

- J-Quants クライアント:
  - レート制御と 401 リフレッシュ、自動ページネーション対応を実装しています。
  - save_* 関数は DuckDB へ冪等保存（ON CONFLICT DO UPDATE）。

- ニュース収集:
  - RSS の URL 正規化、トラッキングパラメータ除去、SSRF/プライベートホスト検査、gzip サイズ上限など多数の安全対策を組み込んでいます。

- データ品質チェック:
  - quality.run_all_checks() で複数のチェックをまとめて実行し、QualityIssue オブジェクトのリストを受け取れます。ETL はチェック失敗で即中断しない設計です（呼び出し側で判断）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数/設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                — ニュース NLP / score_news
  - regime_detector.py         — 市場レジーム判定 / score_regime
- data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（fetch/save/get_id_token 等）
  - pipeline.py                — ETL パイプライン（run_daily_etl 他）
  - etl.py                     — ETLResult の再エクスポート
  - news_collector.py          — RSS 取得と raw_news 保存
  - quality.py                 — データ品質チェック
  - calendar_management.py     — 市場カレンダー管理（is_trading_day 等）
  - stats.py                   — zscore_normalize 等
  - audit.py                   — 監査ログ DDL・初期化
- research/
  - __init__.py
  - factor_research.py         — ファクター計算（momentum/value/volatility）
  - feature_exploration.py     — 将来リターン、IC、統計サマリー

追加情報 / トラブルシューティング
---------------------------------
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。パッケージ配布後やテスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対する executemany の挙動はバージョン差異に依存するため、コード内で空 params への配慮がされています（DuckDB 0.10 の制約を考慮）。
- OpenAI / J-Quants の API キーやトークンはセキュアに管理し、ログやコミットに含めないでください。

ライセンス・コントリビューション
--------------------------------
（該当情報があればここに記載してください。なければ貢献ルール・ライセンスは別途追加してください。）

以上。詳細は各モジュールの docstring（コード内コメント）を参照してください。追加で README に載せたいコマンド例や .env.example を用意したい場合は教えてください。