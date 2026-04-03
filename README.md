プロジェクト名: KabuSys — 日本株自動売買システム

プロジェクト概要
- KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買の基盤ライブラリです。
- 主な役割はデータ収集（J-Quants / RSS 等）、データ品質チェック、ファクター計算、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注〜約定のトレーサビリティ）などを提供することです。
- 設計上の特徴：
  - Look-ahead bias を避ける設計（関数内で date.today()／datetime.today() を直接参照しない等）
  - DuckDB をデータ格納に利用し、冪等保存（ON CONFLICT）やトランザクション制御を想定
  - OpenAI（gpt-4o-mini）を用いた JSON モードによるスコアリング（リトライ・フォールバック実装）
  - セキュリティ考慮（RSS の SSRF 対策、defusedxml など）

主な機能一覧
- データ取得 / ETL
  - J-Quants 連携: 株価日足（OHLCV）、財務データ、JPX カレンダー（jquants_client）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）：data.pipeline.run_daily_etl 等
- データ品質管理
  - 欠損・スパイク・重複・日付不整合検出（data.quality）
- ニュース収集 / NLP
  - RSS 取得・前処理・raw_news 登録（data.news_collector）
  - 銘柄別ニュースセンチメントスコア（ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF 1321 の MA200 とマクロニュースセンチメントを合成（ai.regime_detector.score_regime）
- リサーチ / ファクター処理
  - Momentum / Value / Volatility 等のファクター計算（research.factor_research）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ（research.feature_exploration）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions のスキーマ定義と初期化（data.audit）
- ユーティリティ
  - 設定管理（環境変数自動ロード / settings）（config）
  - 汎用統計ユーティリティ（data.stats）

セットアップ手順（概要）
1. Python バージョン
   - Python 3.10 以上を推奨（PEP 604 の型記法（|）等を使用）。

2. 必要パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外の依存を pip でインストール）
   例:
     pip install duckdb openai defusedxml

   - 必要に応じてその他のユーティリティ（logging 等は標準ライブラリ）

3. リポジトリ配置
   - パッケージは src/kabusys 配下に実装されています。開発時はプロジェクトルートに移動してインストール（editable）してください。
     例:
       pip install -e .

4. 環境変数 / .env
   - アプリ設定は環境変数またはルートの .env / .env.local から自動ロードされます（config モジュール）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（任意）
     - DUCKDB_PATH           : デフォルト data/kabusys.duckdb
     - SQLITE_PATH           : 監視用途の SQLite（デフォルト data/monitoring.db）
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL             : DEBUG/INFO/...
   - 自動ロードを無効化する場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. ディレクトリ/ファイルパーミッション
   - DuckDB ファイルやログ・pid/flag などの書き込み先（デフォルト data/ 配下）に書き込み権限が必要です。

使い方（よく使う例）
- DuckDB 接続を開く（簡易例）
  - Python スクリプト内で:
    from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（単発）
  - 例（Python ワンライナー）:
    python -c "import duckdb, datetime; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect('data/kabusys.duckdb'); print(run_daily_etl(conn, datetime.date(2026,3,20)).to_dict())"

- ニューススコアリング（ai.news_nlp.score_news）
  - 例:
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime, os
    conn = duckdb.connect('data/kabusys.duckdb')
    # OPENAI_API_KEY は環境変数か api_key 引数で渡す
    n_written = score_news(conn, datetime.date(2026,3,20))
    print("書き込み銘柄数:", n_written)

- 市場レジーム判定（ai.regime_detector.score_regime）
  - 例:
    from kabusys.ai.regime_detector import score_regime
    import duckdb, datetime
    conn = duckdb.connect('data/kabusys.duckdb')
    score_regime(conn, datetime.date(2026,3,20))

- 監査ログ DB の初期化
  - データベースファイルを作成して監査スキーマを初期化:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db('data/audit.duckdb')

- 設定（Settings）利用例
  - from kabusys.config import settings
    print(settings.env, settings.log_level, settings.duckdb_path)

注意点 / 運用上のポイント
- OpenAI API 呼び出しは料金が発生します。テスト環境では API コールをモックしてください（モジュール内で _call_openai_api を差し替えることを想定）。
- ETL / API 呼び出しにはリトライやレート制御が実装されていますが、運用時は API レート制限やコストを確認してください。
- データ品質チェック（data.quality）は ETL 後に実行して問題をログ・結果で確認できます。重大な品質問題は ETLResult.has_quality_errors で検出可能です。
- news_collector は SSRF 対策や読み込みサイズ制限を行っていますが、外部 RSS 取得時のネットワーク信頼性に注意してください。
- 本ライブラリは本番の発注 API（broker 等）とは分離しており、監査ログは約定の受信等と組み合わせることで運用可能です。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                : パッケージのエントリ（version 等）
  - config.py                  : 環境変数 / 設定管理（.env 自動ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py              : ニュース NLP スコアリング（score_news）
    - regime_detector.py      : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント（取得・保存関数）
    - pipeline.py              : ETL パイプライン（run_daily_etl 等）
    - etl.py                   : ETLResult 再エクスポート
    - news_collector.py        : RSS 収集・前処理・保存
    - audit.py                 : 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
    - calendar_management.py   : 市場カレンダー管理（is_trading_day 等）
    - quality.py               : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                 : 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py       : モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py   : 将来リターン、IC、統計サマリ等
  - ai/regime_detector.py      : （上記）ETL で算出する市場レジームロジック

開発・テストのヒント
- OpenAI や J-Quants など外部 API はモック化してユニットテストを作成してください（各モジュールに _call_openai_api 等の差し替えフックあり）。
- config._find_project_root は .git または pyproject.toml を探索して .env 自動読み込みを行います。CI で固定設定を使う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して手動で環境変数を注入してください。

ライセンス・貢献
- 本 README にはライセンス情報は含まれていません。実プロジェクトでは LICENSE を追加してください。
- 貢献する際はコード規約・テスト・ドキュメントを揃えて Pull Request を作成してください。

以上。必要であれば README.md の具体的な例（.env.example のテンプレート、requirements.txt、より詳細な実行スクリプト例など）を追記しますか？