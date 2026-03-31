KabuSys
======

概要
----
KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買補助ライブラリです。  
主な目的は J-Quants（株価・財務・マーケットカレンダー）や RSS ニュースを取得・正規化し、DuckDB に格納、品質チェック・ファクター算出・AI（OpenAI）によるニュースセンチメント評価・市場レジーム判定・監査ログの初期化を行うことです。  
設計上、ルックアヘッドバイアスを避ける実装方針や API リトライ・レート制御、ETL の冪等性（idempotency）に配慮しています。

主な機能一覧
-------------
- データ取得・ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、マーケットカレンダーの差分取得と DuckDB への冪等保存
  - 差分更新・バックフィル・ページネーション対応
- データ品質チェック
  - 欠損、重複、スパイク（急変）、日付不整合（未来日付／非営業日）検出
- ニュース収集・前処理
  - RSS フィード取得（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - raw_news / news_symbols への保存ロジック
- AI（LLM）連携
  - ニュースの銘柄別センチメントスコア算出（news_nlp.score_news）
  - マクロニュースと ETF（1321）MA200 乖離の合成による市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI API 呼び出しはリトライなどのフェイルセーフあり（失敗時は安全側のスコアで継続）
- リサーチ系ユーティリティ
  - モメンタム / ボラティリティ / バリュー系ファクター計算
  - 将来リターン計算、IC（情報係数）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査（Audit）
  - signal → order_request → executions をトレースする監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）

セットアップ手順
----------------
前提
- Python 3.9+（typing の一部記法を使用）
- 必要な外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

推奨手順
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（プロジェクトに setup/pyproject がある想定での例）
   - pip install -e .            # editable install（パッケージ化されている場合）
   - あるいは個別に:
     - pip install duckdb openai defusedxml

3. 環境変数設定
   - プロジェクトルートの .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（get_id_token に使用）
     - KABU_API_PASSWORD      : kabuステーション API のパスワード（発注等に使用）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack 通知送信先チャンネル ID
     - OPENAI_API_KEY        : OpenAI を使う機能（news_nlp / regime_detector）を使う場合に必要
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) デフォルト "development"
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト "INFO"
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (監視DB、デフォルト data/monitoring.db)

.env の自動ロード
- 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードは kabusys.config モジュールがプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。
- テスト時に自動ロードを無効にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（簡易サンプル）
--------------------

基本的な DuckDB 接続と ETL 実行
- Python REPL やスクリプトで:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # 当日分の ETL を実行（target_date を明示することが推奨）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

news_nlp（ニュースセンチメント）を実行する
- OpenAI API キーが必要（環境変数 OPENAI_API_KEY または api_key 引数）。
- サンプル:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date に対して前日15:00 JST～当日08:30 JST の記事を対象にスコア化
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

regime_detector（市場レジーム判定）の実行
- ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime テーブルに書き込みます。

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

監査ログスキーマ初期化（audit）
- 監査テーブルを初期化する例:

  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # 既存の DuckDB ファイルを監査DBとして初期化（別DBを用意することを推奨）
  conn = init_audit_db(settings.duckdb_path)
  # conn は初期化済み DuckDB 接続

データ取得（J-Quants）を直接呼ぶ例
- jquants_client の fetch/save 関数は直接呼べます（テスト用や個別実行時）。

  from kabusys.data import jquants_client as jq
  from kabusys.config import settings

  id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  # DuckDB に保存する場合は save_daily_quotes(conn, records)

注意点（運用上のポイント）
- Look-ahead バイアス:
  - モジュール多くが内部で datetime.today() / date.today() を直接参照しない実装。target_date を明示的に渡すことでバックテスト安全性を高めています。
- OpenAI 呼び出し:
  - API 失敗時はフォールバック動作（例: macro_sentiment = 0.0、または該当銘柄スキップ）を行い、例外で全処理を止めない設計です。
- レート制御:
  - jquants_client は 120 req/min のレート制御とリトライ（指数バックオフ）を実装済みです。
- .env 自動読み込み:
  - プロジェクトルート (.git or pyproject.toml) を基準に .env/.env.local を自動読み込みします。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ディレクトリ構成（抜粋）
-----------------------
プロジェクトは src/kabusys 以下に実装されています。主要ファイル:

- src/kabusys/__init__.py
- src/kabusys/config.py                         : 環境変数と設定
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py                                 : ニュースセンチメント（score_news）
  - regime_detector.py                          : 市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - pipeline.py                                 : ETL パイプライン (run_daily_etl など)
  - jquants_client.py                            : J-Quants API クライアント（fetch / save）
  - news_collector.py                            : RSS 収集・前処理
  - calendar_management.py                       : 市場カレンダー管理（is_trading_day など）
  - quality.py                                   : データ品質チェック
  - stats.py                                     : 統計ユーティリティ（zscore_normalize）
  - audit.py                                     : 監査テーブル定義・初期化
  - etl.py                                       : ETLResult 再エクスポート
- src/kabusys/research/
  - __init__.py
  - factor_research.py                            : モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py                        : 将来リターン・IC・統計サマリー等

ライセンス・コントリビュート
----------------------------
（この README にはライセンス情報・貢献方法は含めていません。必要に応じてプロジェクトルートに LICENSE / CONTRIBUTING.md を追加してください。）

補足（トラブルシューティング）
-----------------------------
- DuckDB 関連のエラー
  - executemany に空リストを渡すとエラーとなる箇所に配慮した実装になっていますが、DuckDB バージョンに依存する挙動が出る場合があります。最新の duckdb を使用してください。
- OpenAI SDK 互換性
  - OpenAI の SDK はバージョン差で例外クラスや属性が変わることがあります。API 呼び出しの例外処理は多少の互換性を考慮していますが、SDK 更新時には動作確認を行ってください。
- RSS 取得の SSRF 対策
  - news_collector はリダイレクト先ホストの判定や private IP 判定を行います。社内プロキシなどを使う環境ではホスト名解決が失敗し、拒否される可能性があります。検証を行ってください。

以上が本コードベースの概要と基本的な使い方です。細かな API（関数引数や返り値）については各モジュールの docstring を参照してください。必要であれば README を拡張して具体的な例（.env.example テンプレート、運用フロー、cron / Airflow ジョブの設定例 等）を追加します。どの情報を深掘りしますか？