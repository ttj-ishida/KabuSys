# KabuSys — 日本株自動売買システム（README）

KabuSys は日本株のデータパイプライン、ファクター・リサーチ、ニュースセンチメント（LLM）や市場レジーム判定、監査ログ（発注〜約定のトレーサビリティ）などを含む自動売買プラットフォームのライブラリ群です。本 README はこのコードベースの概要、機能、導入・実行方法、ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要 API / 実行例）
- 環境変数（.env）例
- ディレクトリ構成

---

プロジェクト概要
- 日本株向けの研究・データ基盤と自動売買に必要な共通コンポーネントを提供します。
- 主な関心領域：
  - J-Quants API を用いたデータ ETL（株価日足・財務・JPX カレンダー）
  - ニュース収集と LLM を使ったニュースセンチメント（銘柄別 ai_score）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索
  - 監査ログ（signal / order_request / executions テーブル）によるトレーサビリティ
  - データ品質チェック（欠損・重複・スパイク・日付不整合）

主な機能一覧
- データ ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（DuckDB 保存）
  - J-Quants API クライアント（認証自動更新、ページネーション、レート制御、リトライ）
- ニュース収集:
  - RSS フィード取得・正規化・SSRF 対策・raw_news への冪等保存
- ニュース NLP:
  - gpt-4o-mini を用いた銘柄別センチメント（score_news）
  - レスポンス検証・バッチ処理・クリップ（±1.0）
- 市場レジーム判定:
  - ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM を合成して daily market_regime に保存（score_regime）
- 研究（research）:
  - calc_momentum, calc_value, calc_volatility
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- データ品質チェック:
  - 欠損・スパイク・重複・日付不整合の検出と QualityIssue レポート
- 監査ログ（audit）:
  - signal_events, order_requests, executions の DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理:
  - .env の自動読み込み（プロジェクトルート検出）と Settings オブジェクト（kabusys.config.settings）

セットアップ手順（ローカル開発向け）
1. Python と仮想環境
   - 推奨: Python 3.9+
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 最低限必要なライブラリ（例）
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそちらを使用してください）

3. パッケージを開発モードでインストール（任意）
   - プロジェクトルートで:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数で指定します。
   - 自動読み込みは既定で有効（kabusys.config が .env / .env.local をプロジェクトルートからロード）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（主要 API / 実行例）
- 前提: DuckDB 接続を渡して実行するスタイルです。settings を使ってデフォルトの DB パスを取得できます。

1) ETL（日次パイプラインを実行）
- 例: 日次 ETL を実行して DuckDB に保存する
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- 設計ポイント:
  - run_daily_etl は calendar → prices → financials → 品質チェック の順に処理します。
  - 各ステップで例外が発生しても他ステップは継続され、result.errors に記録します。

2) ニュースセンチメント（銘柄別 ai_scores 生成）
- 例: score_news を呼び出す
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"written: {n_written}")

- 注意:
  - OpenAI API キーは api_key 引数、または環境変数 OPENAI_API_KEY を使用します。
  - チャンク処理、リトライ、レスポンスバリデーション済み。

3) 市場レジーム判定
- 例: score_regime
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

- 出力:
  - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）

4) 監査ログ DB の初期化
- 例: 監査用 DuckDB を作ってスキーマを初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って order リクエスト／約定のログを保存できます

5) 研究系関数の使用例
- calc_momentum, calc_volatility, calc_value:
  - from kabusys.research.factor_research import calc_momentum
    res = calc_momentum(conn, date(2026,3,20))
    # res は dict のリスト（date, code, mom_1m, ...）

環境変数（.env）例
- 必須（settings で _require されるもの）
  - JQUANTS_REFRESH_TOKEN="..."    # J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD="..."       # kabuステーション API パスワード
  - SLACK_BOT_TOKEN="..."         # Slack 通知用 Bot Token
  - SLACK_CHANNEL_ID="..."        # Slack 通知用 Channel ID

- 任意・デフォルトあり
  - KABUSYS_ENV="development"     # 有効値: development / paper_trading / live
  - LOG_LEVEL="INFO"
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env ロードを無効化
  - DUCKDB_PATH="data/kabusys.duckdb"
  - SQLITE_PATH="data/monitoring.db"
  - KABU_API_BASE_URL="http://localhost:18080/kabusapi"  # kabu API のベース URL
  - OPENAI_API_KEY (LLM 呼出しで直接参照されることあり)

- .env のパース挙動
  - コメント行、export キーワード対応、単一/二重クォートとエスケープに対応
  - .env.local が .env より優先して上書きされる（OS 環境変数は保護）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数／設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュース NLP（score_news, calc_news_window 等）
    - regime_detector.py          # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント + DuckDB 保存
    - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
    - etl.py                      # ETLResult の再公開
    - news_collector.py           # RSS ニュース収集（SSRF 対策等）
    - calendar_management.py      # 市場カレンダー管理（is_trading_day 等）
    - quality.py                  # データ品質チェック
    - stats.py                    # zscore_normalize 等
    - audit.py                    # 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py          # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py      # calc_forward_returns / calc_ic / factor_summary / rank

主要テーブル（コード中で参照される想定テーブル）
- raw_prices / raw_financials / market_calendar / raw_news / news_symbols
- ai_scores / market_regime
- audit 用: signal_events / order_requests / executions

設計上の注意点（抜粋）
- Look-ahead bias を防ぐため、各モジュールは target_date を外部から受け取り、内部で date.today() を直接参照しない設計を心がけています。
- API 呼び出しにはリトライ・指数バックオフ・レート制御が実装されています（J-Quants / OpenAI）。
- DuckDB への保存は冪等化（ON CONFLICT、DELETE→INSERT 等）を意識しています。
- RSS の取得は SSRF、XML 攻撃、巨大レスポンス対策が施されています。
- テストや CI のために .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能です。

トラブルシューティング（簡易）
- .env が読み込まれない:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に探します。自動ロードを無効化していないか確認してください。
- OpenAI 呼び出しで失敗:
  - OPENAI_API_KEY を指定するか、各関数の api_key 引数にキーを渡してください。API の一時的失敗は内部でリトライしますが、キー未設定は ValueError になります。
- J-Quants API エラー:
  - JQUANTS_REFRESH_TOKEN が有効か確認し、get_id_token の呼び出しが成功するか確認してください。

以上がこのコードベースの README（日本語）です。必要であれば、セクションを詳細化したドキュメント（API リファレンス、スキーマ定義、運用手順、Docker compose 例など）を追加で作成できます。どの部分を優先して詳しくしたいか指示してください。