KabuSys — 日本株自動売買 / 研究プラットフォーム
=================================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買補助ライブラリです。  
主に次を目的としたモジュール群を提供します。

- J-Quants からの株価・財務・カレンダー ETL（差分取得・保存・品質チェック）
- ニュース収集と LLM を使ったニュースセンチメント（銘柄別 / マクロ）
- 市場レジーム判定（ETF MA と マクロセンチメントの合成）
- ファクター計算・特徴量探索（モメンタム / ボラティリティ / バリュー 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計方針により、バックテスト等でのルックアヘッドバイアスを避ける実装や、
外部 API 呼び出しに対するフェイルセーフ／リトライ処理が組み込まれています。

主な機能一覧
-------------
- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）：レートリミット管理、トークン自動リフレッシュ、ページネーション対応
- ニュース処理
  - RSS 収集（kabusys.data.news_collector）：SSRF 対策、トラッキングパラメータ除去、前処理
  - ニュース NLP（kabusys.ai.news_nlp）：銘柄別センチメント取得・ai_scores への書き込み
- 市場レジーム
  - kabusys.ai.regime_detector.score_regime：ETF(1321) MA とマクロセンチメントを合成して日次レジーム判定
- リサーチ
  - ファクター計算（kabusys.research.factor_research）：momentum/value/volatility 等
  - 特徴量探索（kabusys.research.feature_exploration）：将来リターン計算、IC、統計サマリー
  - zscore_normalize（kabusys.data.stats）
- データ品質
  - kabusys.data.quality：欠損・スパイク・重複・日付不整合チェック。QualityIssue オブジェクトを返す
- 監査ログ
  - init_audit_schema / init_audit_db（kabusys.data.audit）：監査テーブルとインデックスを冪等で作成

セットアップ手順
----------------

前提
- Python 3.10+ を推奨（型ヒントに union 型等を使用）
- DuckDB、OpenAI SDK、defusedxml などが必要

インストール（開発環境）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクト用 requirements.txt や poetry / pyproject.toml があればそちらに従ってください）
4. パッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数 / .env
- ランタイムに必要な環境変数（主なもの）:
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
  - SLACK_CHANNEL_ID: Slack 通知チャンネル ID（必須）
  - OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp / regime_detector で必要）
  - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite DB（例: data/monitoring.db）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

自動 .env ロード
- パッケージはパッケージソース位置からプロジェクトルートを探索し、プロジェクトルート/.env と .env.local を自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（抜粋）
-------------

基本的な Python インタラクティブ例（ETL 実行）

1) DuckDB 接続を作成して日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- run_daily_etl は市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェックの順に処理し、ETLResult を返します。

2) ニュースセンチメントの実行（OpenAI API キーが必要）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")  # api_key を明示可能
  print(f"wrote {n_written} scores")

3) 市場レジーム判定（1321 の MA とマクロセンチメントの合成）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

4) 監査ログ DB 初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブルが作成されます

注意点 / トラブルシューティング
- OPENAI_API_KEY が未設定の場合、news_nlp.score_news や regime_detector.score_regime は ValueError を投げます（api_key を引数で渡すか環境変数で設定してください）。
- J-Quants API 呼び出しは内部でレートリミット・リトライ・トークン自動更新を行いますが、ID トークンやリフレッシュトークンが正しくないと取得に失敗します。
- ETL は各ステップで例外を捕捉して処理を継続する設計です。結果は ETLResult で確認してください（errors / quality_issues）。
- news_collector は RSS 取得時に SSRF 対策やレスポンスサイズ上限を設けています。外部 RSS の仕様により一部フィードが取得できない場合があります。
- DuckDB executemany に関して空リストを投げるとエラーになるバージョンを考慮した実装がなされています。

ディレクトリ構成（重要モジュール）
--------------------------------

src/kabusys/
- __init__.py
  - パッケージ定義、バージョン
- config.py
  - 環境変数読み込み、settings オブジェクト（J-Quants / OpenAI / DB パス等）
- ai/
  - __init__.py
  - news_nlp.py         : 銘柄別ニュースセンチメント取得（score_news）
  - regime_detector.py  : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   : J-Quants API クライアント（fetch/save 関数）
  - pipeline.py         : ETL パイプライン（run_daily_etl 等）
  - calendar_management.py : マーケットカレンダー管理・営業日ロジック
  - news_collector.py   : RSS フィード取得・前処理・raw_news 保存
  - quality.py          : データ品質チェック
  - stats.py            : 汎用統計関数（zscore_normalize）
  - audit.py            : 監査ログ（スキーマ初期化）
  - etl.py              : ETL の公開型再エクスポート（ETLResult）
- research/
  - __init__.py
  - factor_research.py  : momentum / value / volatility 計算
  - feature_exploration.py : 将来リターン / IC / summary / rank
- research/__init__.py exports useful functions

（その他のユーティリティやモジュールは同階層に配置）

追加情報（設計のポイント）
-------------------------
- ルックアヘッドバイアス防止: 多くのモジュールが date 引数を受け取り、内部で datetime.today()/date.today() を直接参照しない実装です。バックテスト用途に配慮しています。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）故障時は個別処理をスキップしたりデフォルト値で継続する設計（例: マクロセンチメントが取得できなければ 0.0 にフォールバック）。
- 冪等性: J-Quants からの保存は ON CONFLICT DO UPDATE で冪等に保存されます。監査ログの order_request_id は冪等キーとして扱います。
- テスト容易性: OpenAI など API 呼び出し箇所は内部で差し替え可能に実装されており、単体テストでモックしやすくなっています。

貢献 / 開発
-----------
- 既存のコードに合わせた単体テストの追加、ドキュメントの改善、ETL のエラーハンドリング強化など歓迎します。
- プルリクエストの際は、関連する単体テスト（モックを使った外部 API のスタブ化）を添えてください。

以上が README の要点です。必要であれば README をプロジェクト用にさらに整形（CI / テスト実行方法、requirements.txt 例、具体的な .env.example ファイルのテンプレート等）しますので、希望があれば教えてください。