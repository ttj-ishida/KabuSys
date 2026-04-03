KabuSys — 日本株自動売買 / データ基盤ライブラリ
======================================

概要
----
KabuSys は日本株のデータ取得・品質管理・ファクター計算・AI（ニュース）スコアリング・市場レジーム判定・監査ログ管理などを含む、バックテスト・リサーチ・自動売買に使える共通ユーティリティ群です。本リポジトリは以下を目的としています。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ニュース収集と OpenAI を用いたニュースセンチメント（銘柄別／マクロ）
- 市場レジーム判定（ETF とマクロの組合せ）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル → 注文 → 約定のトレーサビリティ）
- DuckDB を用いた永続化、冪等保存の設計

特徴（機能一覧）
----------------
- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページング・レート制御・リトライ）
  - market_calendar / raw_prices / raw_financials 等への保存ユーティリティ
  - ニュース収集（RSS）と安全性対策（SSRF・XML攻撃対策）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - ETL 結果を表す ETLResult
- ai
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースを銘柄別に集約して OpenAI でセンチメントを付与し ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF(1321) の MA 乖離とマクロニュースセンチメントを合成して market_regime に保存
  - 両モジュールとも look-ahead バイアス回避の設計（target_date 指定、内部で date.today を参照しない）
- research
  - ファクター計算（calc_momentum、calc_volatility、calc_value）
  - 将来リターン計算、IC 計算、ファクター統計（calc_forward_returns、calc_ic、factor_summary 等）
  - zscore_normalize（data.stats）
- config
  - 環境変数管理（.env 自動読み込み、必須項目チェック、設定プロパティ）
- その他
  - DuckDB ベースの永続化、冪等性（ON CONFLICT）
  - ログレベル／環境判定（development / paper_trading / live）

セットアップ手順
----------------

1. リポジトリをクローンしてインストール（任意で仮想環境を利用）
   - pip で開発インストールが想定されます（setup.cfg / pyproject.toml がある前提）。
     例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -e .

2. 必要な Python パッケージ（代表例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外の依存関係は pyproject.toml / requirements に従ってください）

3. 環境変数 / .env
   - プロジェクトルートの .env/.env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings 参照）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
     - OPENAI_API_KEY : OpenAI を利用する場合に必要（ai.score_news / score_regime を呼ぶ場合）
   - 任意（デフォルト値あり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH : data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH : data/monitoring.db（監視用）
     - PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値等
   - .env 解析はシェル風の export KEY=val / 引用符 / コメントをサポートしています。
   - .env.example を参考に作成してください（リポジトリに用意がある想定）。

使い方（主要な API と実行例）
----------------------------

- 設定読み取り
  - from kabusys.config import settings
  - settings.jquants_refresh_token 等で取得できます。

- DuckDB 接続を作って ETL を実行する（例）
  - import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

  - run_daily_etl は market_calendar → prices → financials → 品質チェック を順に実行し ETLResult を返します。

- ニューススコアリング（銘柄別 AI スコア）
  - from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date=date(2026,3,20), api_key=None)
  - api_key を None にすると環境変数 OPENAI_API_KEY を参照します。
  - score_news は前日 15:00 JST ～ 当日 08:30 JST のウィンドウを対象に記事を集約します（calc_news_window を参照）。

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key=None)
  - ETF 1321 の MA200 乖離（70%）とマクロニュース LLM スコア（30%）を合成し market_regime テーブルに保存します。

- ファクター計算 / 研究用ユーティリティ
  - from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
    mom = calc_momentum(conn, date(2026,3,20))
    vol = calc_volatility(conn, date(2026,3,20))
    val = calc_value(conn, date(2026,3,20))
  - forward returns / IC / summary:
    from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

- 監査ログスキーマ初期化
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
  - または既存の DuckDB 接続へ init_audit_schema(conn, transactional=True) を呼ぶ。

設計上の注意点（重要）
--------------------
- Look-ahead バイアスに注意
  - ai.score_news, ai.regime_detector, ETL 等は target_date 引数を取り、内部で date.today() を参照しない（ルックアヘッドを避ける設計）。バックテストで使用する場合は target_date を明示してください。
- OpenAI 呼び出し
  - gpt-4o-mini を前提に JSON mode を利用しています。API エラー時の挙動はフェイルセーフ（多くの場合 0.0 やスキップ）にしていますが、レート制限等は適切に処理してください。
- DuckDB バージョン互換性
  - 一部実装（executemany の空リスト送信可否、配列バインドなど）は DuckDB のバージョン差異に依存する箇所があります。DuckDB 0.10 系を想定しています。
- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）を検出して .env/.env.local を自動読み込みします。テスト時に無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                  — 銘柄別ニューススコアリング
  - regime_detector.py           — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント + 保存ロジック
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETLResult エクスポート
  - stats.py                      — zscore_normalize 等汎用統計
  - calendar_management.py       — market_calendar 管理 / 営業日ロジック
  - news_collector.py            — RSS 収集・前処理・保存
  - quality.py                   — データ品質チェック
  - audit.py                     — 監査ログテーブル初期化
- research/
  - __init__.py
  - factor_research.py           — momentum/volatility/value 等
  - feature_exploration.py       — forward returns / IC / summary

補足（トラブルシュート）
-----------------------
- OpenAI のレスポンスパース失敗や API エラーはログに出力してスコアをフォールバック（多くは 0.0 またはスキップ）します。詳細はログ（LOG_LEVEL を DEBUG に設定）を確認してください。
- J-Quants API 呼び出しは内部でレート制限・リトライ・401 リフレッシュを行います。id_token の取得には JQUANTS_REFRESH_TOKEN が必要です。
- news_collector は SSRF / XML 攻撃対策（defusedxml、ホスト検証、リダイレクト検査）を実装しています。RSS が正しく取れない場合はログの警告を確認してください。

ライセンス・貢献
----------------
- 本 README ではライセンスや貢献ルールは記載していません。実践利用前にリポジトリの LICENSE や CONTRIBUTING を確認してください。

最後に
------
この README はコードベースの主要機能と使い方の概要をまとめたものです。関数の詳細な引数仕様や内部ロジックは各モジュールの docstring を参照してください。追加の使用例や CLI、ユニットテスト等を作成することで運用しやすくなります。必要があれば README にサンプルスクリプトや CLI の使い方を追記します。