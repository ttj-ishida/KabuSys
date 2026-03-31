KabuSys
======

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP による銘柄センチメント算出、マーケットレジーム判定、研究用ファクター計算、監査（トレーサビリティ）テーブルの初期化などを含みます。

主な目的
- J-Quants（日本市場データ）を DuckDB に差分取得・保存する ETL
- RSS ニュースの収集と OpenAI を使った銘柄センチメント算出（ai_score）
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull / neutral / bear）
- 研究用のファクター計算・特徴量探索ユーティリティ
- 発注・約定などを追跡する監査用スキーマの初期化

機能一覧
- 環境変数 / .env 自動読み込み（settings 経由で参照）
- J-Quants クライアント（fetch / save / rate limit / retry / token refresh）
- 日次 ETL パイプライン（prices / financials / market calendar）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- RSS ニュース収集（SSRF対策・サイズ上限・トラッキング除去）
- OpenAI を使ったニュース NLP（銘柄ごとのセンチメントスコア）
- マーケットレジーム判定（ETF MA200 と LLM マクロセンチメントの合成）
- 研究モジュール（momentum / volatility / value 等のファクター計算、forward returns、IC、統計サマリー）
- 監査ログスキーマ（signal_events / order_requests / executions）の初期化ユーティリティ

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 環境
   - Python 3.10 以上を推奨（型記法で | を使用）
   - 仮想環境作成（例）
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （パッケージ化されていれば）プロジェクトを editable インストール:
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートの .env（.env.local）を作成してください（.env.example を参照）。
   - 主な必須変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（ETL 用）
     - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 用）
     - KABU_API_PASSWORD     : kabu ステーション API パスワード（注文系）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : 通知用 Slack 設定
   - 自動 .env ロード:
     - 起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、OS 環境変数 > .env.local > .env の順で読み込みます。
     - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DuckDB（データベースファイル）のデフォルトパス
   - settings.duckdb_path のデフォルト: data/kabusys.duckdb
   - settings.sqlite_path のデフォルト: data/monitoring.db
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH を上書きしてください。

簡単な使い方（コード例）
- 共通：設定を参照する
  - from kabusys.config import settings
  - print(settings.duckdb_path, settings.env, settings.is_live)

- DuckDB 接続を作成して ETL を実行
  - import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメント（OpenAI を使用）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    # conn: DuckDB 接続（raw_news, news_symbols, ai_scores が存在すること）
    n = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {n} symbols")

  - API キーは OPENAI_API_KEY 環境変数を使うか、api_key 引数で渡せます。

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20))

- 監査 DB の初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # テーブルが作成されます（UTC タイムゾーン設定含む）

- 研究用ファクター計算例
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    records = calc_momentum(conn, target_date=date(2026,3,20))

注意点・運用上の想定
- Look-ahead bias 回避: モジュールの多くは内部で date.today() を直接参照しないように設計されています。必ず target_date を明示して呼び出してください。
- OpenAI 呼び出し: レスポンスのパース失敗や API エラーはフェイルセーフでデフォルト値（0.0 等）にフォールバックする設計ですが、API キーが未設定の場合は ValueError を出します。
- J-Quants API: レート制限（120 req/min）を守る実装になっています。get_id_token() による自動リフレッシュやページネーションに対応しています。
- ニュース収集: SSRF 対策（リダイレクト検査・プライベートアドレス拒否）、受信サイズ制限、XML の安全パース（defusedxml）を行っています。
- DuckDB の executemany は空リスト不可なバージョン差異を考慮した実装になっています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP / ai_scores 書き込み
    - regime_detector.py             -- マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API client / save_* 関数
    - pipeline.py                    -- ETL パイプライン / run_daily_etl 等
    - etl.py                         -- ETLResult の再エクスポート
    - news_collector.py              -- RSS 取得・前処理・保存
    - calendar_management.py         -- 市場カレンダー管理（is_trading_day 等）
    - quality.py                     -- データ品質チェック
    - stats.py                       -- zscore_normalize 等
    - audit.py                       -- 監査テーブル DDL / init_audit_db
  - research/
    - __init__.py
    - factor_research.py             -- momentum/value/volatility 等
    - feature_exploration.py         -- forward returns / IC / factor_summary / rank

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants 用リフレッシュトークン
- OPENAI_API_KEY (必須 for NLP): OpenAI API キー（news_nlp, regime_detector）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH, SQLITE_PATH: データベースパス
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

開発・テストのヒント
- 自動 .env ロードを無効にしたいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから settings をインポートしてください。
- AI 呼び出し部分（news_nlp._call_openai_api, regime_detector._call_openai_api）はテストで patch する想定の設計になっています（unittest.mock.patch）。
- DuckDB 接続は文字列パス（":memory:" も可）で初期化できます。監査 DB 初期化用ヘルパーが用意されています。

ライセンス / 貢献
- （ここにライセンス情報や貢献方法を追記してください。プロジェクトポリシーに従って README を更新するとよいです。）

以上。README に記載してほしい追加情報（CI/バッジ・さらに詳しい設定例・運用手順など）があれば教えてください。