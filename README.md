KabuSys — 日本株自動売買システム (README)
======================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・AI 支援判定・監査ログ機能を備えた自動売買システムのコアライブラリです。  
主に以下を提供します：

- J-Quants からのデータ ETL（株価、財務、マーケットカレンダー）
- ニュースの収集と LLM（OpenAI）によるニュースセンチメント評価
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース）を格納する DuckDB 初期化ユーティリティ
- 環境変数 / .env 自動読み込みと設定管理

主要機能（抜粋）
----------------
- データ ETL（kabusys.data.pipeline.run_daily_etl）
- ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
- 市場レジームスコアリング（kabusys.ai.regime_detector.score_regime）
- ファクター計算（kabusys.research.calc_momentum / calc_value / calc_volatility）
- 統計ユーティリティ（zscore 正規化等）
- 市場カレンダー管理（営業日判定・更新ジョブ）
- データ品質チェック群（kabusys.data.quality.run_all_checks）
- 監査スキーマ作成 / 監査 DB 初期化（kabusys.data.audit.init_audit_db）

セットアップ
-----------

前提
- Python 3.10 以上（PEP 604 の union 型表記（|）や型ヒントに依存）
- ネットワーク接続（J-Quants / OpenAI / RSS フィード）

必須 Python パッケージ例
- duckdb
- openai
- defusedxml

インストール（ローカル開発）
- リポジトリルートで仮想環境を作って依存を入れてください。例:
  python -m venv .venv
  source .venv/bin/activate
  pip install -U pip
  pip install duckdb openai defusedxml

（プロジェクトに setup.cfg/pyproject がある場合は）開発インストール:
  pip install -e .

環境変数 / .env
- プロジェクトはルートにある .env / .env.local を自動で読み込みます（CWD ではなくパッケージ位置からプロジェクトルートを探索）。
- 自動読み込みを無効化したいときは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL      : kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
- DUCKDB_PATH            : DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV            : environment (development / paper_trading / live)（デフォルト development）
- LOG_LEVEL              : ログレベル (DEBUG/INFO/...)
- OPENAI_API_KEY         : OpenAI API キー（AI モジュール使用時に参照）

.env.example（参考）
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  KABUSYS_ENV=development
  LOG_LEVEL=INFO
  OPENAI_API_KEY=sk-...

使い方（主要ユースケース）
-------------------------

1) DuckDB 接続を作る
- 例:
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

2) 日次 ETL を実行する
- ETL は market calendar, prices, financials を差分フェッチし品質チェックを行います。
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

3) ニュースセンチメントをスコア化する
- score_news は raw_news / news_symbols が存在する DuckDB を前提に動作します。
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026,3,20), api_key="your_openai_key")
  print(f"scored {count} symbols")

4) 市場レジーム判定
- ETF 1321 の MA とマクロニュースを合成して market_regime テーブルへ記録します。
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key="your_openai_key")

5) 監査用 DB 初期化
- 監査テーブル群を作成して DuckDB 接続を返します。
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # または ":memory:" を渡してインメモリ DB を作成可能

6) ファクタ／リサーチ関数の利用例
- モメンタム計算:
  from kabusys.research.factor_research import calc_momentum
  res = calc_momentum(conn, date(2026,3,20))

注意点 / 設計上のポイント
-----------------------
- Look-ahead bias の防止:
  - 日付判定や API 呼び出しでは datetime.today() / date.today() を直接用いないよう設計されています（関数引数で target_date を渡す方式）。
- 冪等性:
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を使い冪等に保存します。
- フェイルセーフ:
  - LLM/API 呼び出しなど外部依存はリトライやフォールバック（例: マクロセンチメント失敗時は 0.0）を導入しています。
- テスト性:
  - OpenAI 呼び出しなどは内部でラップされており、ユニットテスト時はモック差し替えが容易です（例: kabusys.ai.news_nlp._call_openai_api を patch）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                        — 環境変数 / .env 自動読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py                     — ニュースセンチメント（LLM 呼び出し、バッチ処理）
  - regime_detector.py              — 市場レジーム判定（MA + マクロセンチメント合成）
- data/
  - __init__.py
  - calendar_management.py          — マーケットカレンダー管理、営業日判定
  - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
  - etl.py                          — ETLResult の公開
  - stats.py                         — zscore_normalize 等統計ユーティリティ
  - quality.py                       — データ品質チェック群
  - audit.py                         — 監査ログスキーマ定義・初期化
  - jquants_client.py                — J-Quants API クライアント & DuckDB 保存
  - news_collector.py                — RSS 収集、前処理、raw_news 保存
- research/
  - __init__.py
  - factor_research.py               — momentum/value/volatility 等
  - feature_exploration.py           — forward returns / IC / summary / rank

ロギングと動作モード
------------------
- KABUSYS_ENV により動作モードを切り替えられます（development / paper_trading / live）。
- LOG_LEVEL 環境変数でログ出力レベルを制御します。

依存関係（主なもの）
-------------------
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

ライセンス・貢献
----------------
この README はコードベースの説明を目的としたもので、実際の配布リポジトリに付属する LICENSE や CONTRIBUTING 指針に従ってください。

その他メモ
---------
- テストを行う際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動読み込みを無効化し、テスト用環境を明示的に構築することを推奨します。
- OpenAI 呼び出しはコストとレート制限があるため、開発時はモックを利用してください（_call_openai_api の patch が想定されています）。

必要なら、README を README.md 形式で整形（マークダウンの細部調整、コードサンプル追記、.env.example ファイルの出力など）して提供します。追加で含めたい内容（例: コマンドラインツール、CI ワークフロー、例データロード手順など）があれば教えてください。