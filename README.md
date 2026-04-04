KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買基盤のコアライブラリです。  
主に以下を提供します。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB ベースの ETL パイプラインと品質チェック
- ニュース収集 & LLM を用いたニュース NLP（銘柄センチメント算出）
- 市場レジーム判定（ETF とマクロセンチメントの合成）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 監査ログ（シグナル → 発注 → 約定のトレースを行うスキーマ初期化）

目的は「バックテストや研究で使える高品質なデータ基盤」と「実運用での監査性・冪等性」を両立することです。

主な機能一覧
-------------
- データ取得 / 保存
  - J-Quants から株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを取得
  - DuckDB にデータを冪等保存（ON CONFLICT DO UPDATE）
  - rate limit / retry / token refresh 対応

- ETL パイプライン
  - run_daily_etl: カレンダー→株価→財務→品質チェックまでの一括処理
  - 部分実行（run_prices_etl / run_financials_etl / run_calendar_etl）

- データ品質チェック
  - 欠損（OHLC） / スパイク（前日比） / 重複 / 日付不整合（未来日・非営業日）検出
  - QualityIssue オブジェクトで結果を集約

- ニュース収集・NLP
  - RSS フィード収集（SSRF対策、トラッキングパラメータ除去、前処理）
  - OpenAI を用いた銘柄センチメントスコア算出（batch / JSON mode）
  - LLM 呼び出しのリトライ・検証ロジック

- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成
  - market_regime テーブルへ冪等書き込み

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー計算（prices_daily / raw_financials 参照）
  - 将来リターン計算・IC（Spearman）・ファクター統計 summarizer
  - zscore_normalize 等の統計ユーティリティ

- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL とインデックス、初期化ユーティリティ
  - init_audit_db で監査用 DuckDB を初期化

セットアップ手順
--------------
前提
- Python 3.10+（typing | match 機能や型ヒントに依存するため推奨）
- DuckDB, OpenAI client など以下のライブラリが必要です（適宜 requirements を用意してください）

推奨依存例
- duckdb
- openai
- defusedxml

インストール例（開発・ソースからの利用）
1. リポジトリをチェックアウトして仮想環境を作る:
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください。）

3. パッケージをローカルインストール:
   - pip install -e .

環境変数
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン（ETL / jquants_client が使用）
  - KABU_API_PASSWORD : kabu ステーション API のパスワード（発注関連で使用）
- 推奨 / オプション
  - OPENAI_API_KEY : OpenAI 呼び出し時の API キー（news_nlp / regime_detector で使用）。関数引数で明示渡しも可能。
  - KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（オプション）
  - DUCKDB_PATH : デフォルト data/kabusys.duckdb
  - SQLITE_PATH : 監視用 sqlite path
  - LOG_LEVEL : ログレベル（DEBUG, INFO, ...）
  - KABUSYS_ENV : development / paper_trading / live
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env/.env.local を置くと自動で読み込まれます。
  - テスト等で自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要 API と実行例）
-------------------------

1) DuckDB 接続と日次 ETL 実行
- Python REPL / スクリプト内で:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- run_daily_etl は ETLResult を返し、品質チェックや取得数・エラーを含みます。

2) OpenAI を用いたニューススコア算出（銘柄センチメント）
- API キーは環境変数 OPENAI_API_KEY か関数引数 api_key で指定可能。

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込み銘柄数: {written}")

3) 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

4) リサーチ / ファクター計算
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

5) 監査ログ（audit）スキーマ初期化 / 監査DB作成
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # init_audit_db はテーブル / インデックスを作成して接続を返す

6) 直接 J-Quants API を呼ぶ（必要に応じて）
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を利用
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))

注意点 / 運用上のヒント
- LLM 呼び出しや外部 API 呼び出しは失敗時にフェイルセーフで継続する設計です（多くはスコアを 0 にフォールバック）。
- データベースは DuckDB を前提。パスは環境変数 DUCKDB_PATH で変更可能。
- run_daily_etl の target_date は内部で date.today() に頼らない実装（ルックアヘッドバイアス対策）です。バックテスト用途にも安全に使えます。
- news_collector は SSRF 対策・受信サイズ制限・XML 脆弱性対策（defusedxml）を実装しています。
- OpenAI 呼び出しはモデル gpt-4o-mini を想定しており、JSON モードでレスポンス整形を期待します。API レートや失敗時のリトライを内部で行います。

ディレクトリ構成（要約）
---------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                — ニュース NLP（銘柄スコア算出）
  - regime_detector.py         — 市場レジーム判定
- research/
  - __init__.py
  - factor_research.py         — モメンタム / ボラティリティ / バリュー算出
  - feature_exploration.py     — 将来リターン / IC / 統計サマリー
- data/
  - __init__.py
  - calendar_management.py     — マーケットカレンダー管理
  - etl.py                     — ETL インターフェース（ETLResult 再エクスポート）
  - pipeline.py                — 日次 ETL パイプライン
  - stats.py                   — 統計ユーティリティ（zscore_normalize）
  - quality.py                 — データ品質チェック
  - audit.py                   — 監査ログ DDL / 初期化
  - jquants_client.py          — J-Quants API クライアント（取得・保存）
  - news_collector.py          — RSS ニュース収集
- research/
  (上記参照)

ライセンス・貢献
--------------
- 本 README ではライセンス情報は省略しています。実運用で配布する場合は適切な LICENSE ファイルを追加してください。
- バグ報告や機能拡張は PR を歓迎します。外部 API キーやシークレットは絶対にコミットしないでください。

最後に
------
この README はコードベースに含まれるモジュールの仕様と典型的な使用方法をまとめたものです。より詳細な設計や API の挙動は各モジュール（jquants_client.py, news_nlp.py, pipeline.py など）の docstring を参照してください。必要であれば README にサンプルスクリプトや CI/CD / バッチ実行例（systemd / cron / Airflow）を追加できます。