KabuSys — 日本株自動売買システム (README)
概要
- KabuSys は日本株向けのデータプラットフォームと研究/戦略基盤、および AI を利用したニュースセンチメント・市場レジーム判定を含む自動売買（執行は外部ブローカー連携想定）用のライブラリ群です。
- 主に以下を提供します:
  - J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
  - ニュース収集・前処理・LLM による銘柄別センチメント算出
  - 市場レジーム判定（ETF MA + マクロニュースの LLM 評価の合成）
  - 研究用ファクター計算・特徴量探索ユーティリティ
  - データ品質チェック、監査ログ（監査テーブルの初期化・管理）
  - 環境設定管理（.env の自動読み込み、Settings オブジェクト）

主な機能一覧
- data.jquants_client
  - J-Quants からのデータ取得（株価日足 / 財務 / 上場情報 / マーケットカレンダー）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レート制御・リトライ・トークン自動リフレッシュ
- data.pipeline / ETLResult
  - 差分 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - run_daily_etl による日次一括処理
- data.news_collector
  - RSS 取得・前処理・記事の正規化・raw_news への保存（SSRF や XML 攻撃対策あり）
- data.quality
  - 欠損、重複、スパイク、日付不整合などの品質チェック並列集計
- data.audit
  - シグナル→発注→約定の監査テーブル定義／初期化（冪等、UTCタイムスタンプ）
- data.calendar_management
  - JPX カレンダーの管理と営業日判定ユーティリティ（next_trading_day 等）
- data.stats
  - zscore_normalize などの汎用統計ユーティリティ
- research
  - factor_research: Momentum / Volatility / Value 等のファクター算出
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー等
- ai
  - news_nlp.score_news: ニュースを LLM で銘柄別センチメントに変換して ai_scores に保存
  - regime_detector.score_regime: ETF の MA とマクロニュース LLM を合成して market_regime に保存
- config
  - .env 自動読み込み（プロジェクトルートの .env, .env.local）と Settings オブジェクト経由の設定取得

セットアップ手順
前提
- Python 3.10 以上（Union 型（A | B）などの記法を使用）
- system に duckdb、openai クライアント、defusedxml 等がインストール可能であること

1) 仮想環境作成（例）
- python -m venv .venv
- source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2) パッケージのインストール
- 必要な依存を requirements.txt にまとめている場合は pip install -r requirements.txt
- 直接主要パッケージを入れる例:
  - pip install duckdb openai defusedxml

(プロジェクト配布パッケージがある場合)
- pip install -e .

3) 環境変数 / .env の準備
- プロジェクトルート（.git または pyproject.toml がある階層）に .env を作成すると自動読み込みされます（.env.local は .env の上書き）。
- 自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

推奨される主要環境変数（例）
- JQUANTS_REFRESH_TOKEN=...    # 必須（J-Quants リフレッシュトークン）
- KABU_API_PASSWORD=...       # 必須（kabuステーション API パスワード）
- SLACK_BOT_TOKEN=...         # 必須（Slack 通知用）
- SLACK_CHANNEL_ID=...        # 必須（Slack 通知先）
- OPENAI_API_KEY=...          # OpenAI を使う機能で必要（score_news / score_regime）。引数でも指定可
- DUCKDB_PATH=data/kabusys.duckdb   # デフォルト
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...

例 .env（簡易）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

4) ディレクトリとデータディレクトリの作成
- settings.duckdb_path の親ディレクトリを作成しておく（多くの初期化関数は親ディレクトリを作るが環境に依存するため確認推奨）。

使い方（主要 API サンプル）
- 共通: settings を使った設定取得
  from kabusys.config import settings
  print(settings.duckdb_path)

- DuckDB 接続を準備
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次パイプライン）の実行
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（AI）スコアリング
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # api_key 引数を使うか、環境変数 OPENAI_API_KEY を設定する
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（AI）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは OPENAI_API_KEY or api_key 引数

- 監査 DB の初期化（監査専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings
  audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" を使うことも可

- カレンダー更新ジョブ（単体）
  from kabusys.data.calendar_management import calendar_update_job
  from datetime import date
  saved = calendar_update_job(conn, lookahead_days=90)

注意点 / トラブルシューティング
- API キーが未設定だと score_news / score_regime 等は ValueError を送出します。OPENAI_API_KEY を .env に設定するか、関数引数で渡してください。
- J-Quants 関連は rate limit（120 req/min）やトークンの有効期限に注意。jquants_client は自動でリフレッシュと遅延制御を行いますが、ID トークン取得や接続エラーはログを参照してください。
- DuckDB の executemany による空リスト渡し（バージョン依存）に注意。ライブラリ内では空リスト回避のためチェック済みですが、独自コードの場合は注意してください。
- ニュース取得: RSS の取得は SSRF/プライベートアドレス検査・最大受信サイズ制限など安全対策が入っています。独自 RSS を追加する際は URL の妥当性に注意してください。
- ログレベルや環境は Settings で制御できます（KABUSYS_ENV, LOG_LEVEL）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数読み込み・Settings
  - ai/
    - __init__.py                 -- score_news のエクスポート
    - news_nlp.py                 -- ニュース NLP / score_news
    - regime_detector.py          -- 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント & 保存関数
    - pipeline.py                 -- ETL パイプライン run_daily_etl 等
    - etl.py                      -- ETLResult の公開
    - news_collector.py           -- RSS 取得 / 前処理 / raw_news 保存
    - quality.py                  -- データ品質チェック
    - stats.py                    -- zscore_normalize 等
    - calendar_management.py      -- 市場カレンダー管理・営業日ユーティリティ
    - audit.py                    -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py          -- モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py      -- 将来リターン, IC, summary, rank
  - research/ ...                 -- 研究系ユーティリティ群

開発・テスト
- .env 自動読み込みはプロジェクトルート（.git ある階層など）を探索します。テストで自動読み込みを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API 呼び出し部分はモジュール内部でラップされており、ユニットテスト時は該当関数を patch してモック可能です（コード内にテスト用差し替えポイントが記載されています）。

ライセンス / コントリビュート
- この README にはライセンス情報は含めていません。配布パッケージに含まれる LICENSE を参照してください。
- プロジェクトに貢献する場合はコードスタイル・テスト・ドキュメントに沿って PR を送ってください。

補足
- README の記載は提供されたコードベースの内容に基づき作成しています。実際の運用時は、接続先 API の仕様変更・モデル名変更（OpenAI）や DuckDB バージョン差異による挙動差に注意してください。

必要であれば、以下を追加で作成できます:
- .env.example のテンプレート
- よくあるエラーとログメッセージ一覧（トラブルシュート集）
- 実運用でのデプロイ手順（systemd / supervisor / cron 例）
- より詳細な API リファレンス（関数別ドキュメント）