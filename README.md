KabuSys — 日本株自動売買プラットフォーム
================================

概要
----
KabuSys は日本株のデータ取得（J-Quants）、ニュース収集・NLP（OpenAI）、リサーチ（ファクター計算）、ETL、監査ログ、マーケットカレンダー管理、ならびに自動売買のための補助機能を備えたライブラリ群です。本リポジトリはバックテスト／リサーチ用のデータ基盤と、実運用で必要となる監査・品質検査のユーティリティを提供します。

主な特徴（機能一覧）
------------------
- 環境設定管理
  - .env / .env.local 自動読み込み（パッケージ配置後も動作）
  - 必須設定の検証（settings オブジェクト）
- データプラットフォーム（DuckDB）
  - J-Quants からの差分 ETL（株価 / 財務 / 市場カレンダー）
  - ETL 実行結果を ETLResult として返却
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集
  - RSS 取得、URL 正規化、SSRF 対策、記事保存（raw_news）
- ニュース NLP（OpenAI）
  - 銘柄別ニュース集約 → LLM（gpt-4o-mini）でセンチメント評価 → ai_scores へ書き込み
  - レート制限・リトライ・レスポンス検証を実装
- 市場レジーム判定
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントの合成で日次レジーム判定（bull / neutral / bear）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルと初期化ユーティリティ
  - すべてのトレースに created_at を付与、冪等性を考慮
- J-Quants クライアント
  - id_token のリフレッシュ、ページネーション対応、固定間隔レートリミッタ、DuckDB への冪等保存関数
- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ 等）
  - 将来リターン / IC / 統計サマリ / Z スコア正規化

セットアップ手順
----------------

前提
- Python 3.9+（コードは型ヒントで 3.10+ を想定）
- ネットワーク接続（J-Quants / OpenAI / RSS）

開発環境への導入（例）
1. リポジトリをクローンし（省略）、プロジェクトルートでインストール:
   - python -m pip install -e .
     （編集可能インストール。requirements は適宜 pyproject / requirements.txt を参照）

2. 環境変数を用意:
   - プロジェクトルートに .env を作成してください。自動読み込みは
     - OS 環境変数 > .env.local > .env の優先順で行われます
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します

  必要な主要環境変数（例と説明）
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    - J-Quants API のリフレッシュトークン（get_id_token で使用）
  - KABU_API_PASSWORD=your_kabu_password
    - kabuステーション等で使う API パスワード
  - KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
  - OPENAI_API_KEY=your_openai_api_key
    - news_nlp / regime_detector が使用（関数引数でも渡せます）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID
    - Slack 通知用（必須）
  - DUCKDB_PATH (既定: data/kabusys.duckdb)
    - データベースファイルパス
  - SQLITE_PATH (既定: data/monitoring.db)
    - 監視用 sqlite ファイルパス
  - KABUSYS_ENV: development | paper_trading | live （既定: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（既定: INFO）

3. 必要ライブラリ（主要）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外は pyproject / requirements を参照してインストール）

基本的な初期化
- 監査ログ用 DuckDB を作成してスキーマ初期化:
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

使い方（簡単な利用例）
--------------------

共通: DuckDB 接続を用意
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL を実行する
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=date(2026,3,20))
- print(result.to_dict())

ETL は市場カレンダー → 株価 → 財務 → 品質チェックの順で処理します。ETLResult に各ステップの取得・保存件数、検出した品質問題とエラー情報が入ります。

2) ニュースセンチメント（ai_scores）を付与する
- from kabusys.ai.news_nlp import score_news
- n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key を渡さないと環境変数 OPENAI_API_KEY を参照

戻り値は書き込んだ銘柄数（int）。

3) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20), api_key=None)

market_regime テーブルへ判定結果を冪等的に書き込みます。

4) 監査スキーマ初期化（既存接続に対して）
- from kabusys.data.audit import init_audit_schema
- init_audit_schema(conn, transactional=True)

5) J-Quants の直接操作（必要に応じて）
- from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
- token = get_id_token()  # settings.jquants_refresh_token を使用
- records = fetch_daily_quotes(date_from=..., date_to=...)

ロギング／環境モード
- settings.env で KABUSYS_ENV を検証します（development / paper_trading / live）。
- settings.log_level で LOG_LEVEL を検証します。
- is_live / is_paper / is_dev プロパティで挙動分岐可能。

ディレクトリ構成（主要ファイル説明）
---------------------------------
src/kabusys/
- __init__.py
  - パッケージのバージョンと __all__ の定義
- config.py
  - .env 自動読み込み、Settings クラス（環境変数アクセスユーティリティ）
- ai/
  - __init__.py
  - news_nlp.py: ニュースの集約・OpenAI を使ったセンチメント付与処理
  - regime_detector.py: ETF MA200 とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得・保存関数）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 取得・前処理・raw_news 登録
  - calendar_management.py: 市場カレンダーの判定・更新ジョブ
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit.py: 監査ログスキーマ定義・初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ、ランク関数
- その他（strategy, execution, monitoring 等のパッケージ参照は __all__ に含まれる想定）

運用上の注意点
--------------
- Look-ahead バイアス回避
  - ライブラリ内の各処理は datetime.today() / date.today() を直接参照しないか、明示的な target_date を受け取る設計です。バックテストでは target_date を意図的に与えてください。
- OpenAI / J-Quants 呼び出し
  - ネットワークエラーや 5xx はリトライ処理がありますが、API キー未設定の場合は ValueError を送出します。テスト時は各 _call_openai_api をモックしてください。
- 自動 .env 読み込みについて
  - プロジェクトルートの検出は __file__ の親階層を上がって .git または pyproject.toml を基準に行います。CI やテストでこれを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany の制約
  - 一部の処理は DuckDB の executemany が空リストを受け取れないことを考慮しています（空チェックを行っています）。

トラブルシューティング
--------------------
- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。プロジェクトルートの検出が失敗すると自動ロードは行われません。
- OpenAI/ J-Quants API エラー
  - 環境変数の値とネットワーク（プロキシ等）を確認。ログにリトライ情報や警告が出力されます。

ライセンス / 貢献
-----------------
- 本 README ではライセンスは記載していません。実プロジェクトに合わせて LICENSE を追加してください。
- コントリビューションの際はコードスタイル、テスト、ドキュメントを合わせて提供してください。

以上がプロジェクトの簡易 README です。必要であれば、実行例の具体的なスクリプトや .env.example のテンプレート、よくあるエラーと対処法（FAQ）を追加で作成できます。どの部分を詳しく載せたいか教えてください。