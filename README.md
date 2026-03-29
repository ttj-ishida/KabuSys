KabuSys — 日本株自動売買プラットフォーム (README)
概要
本リポジトリは「KabuSys」と呼ばれる日本株向けのデータプラットフォーム／自動売買基盤の一部実装です。主に以下を目的としています。
- J-Quants API を用いた市場データ（株価・財務・カレンダー等）の差分 ETL
- RSS ニュース収集および LLM（OpenAI）によるニュースセンチメント付与
- 市場レジーム判定（MA200 とマクロニュースの組合せ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化
- 研究用ファクター計算・特徴量解析ユーティリティ

主な機能一覧
- データ取得・保存
  - J-Quants からの株価日足 / 財務データ / 上場銘柄情報 / マーケットカレンダー取得（jquants_client）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 日次差分 ETL（run_daily_etl）でカレンダー・株価・財務を取得し品質チェックを実行（pipeline）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などの検出（data.quality）
- ニュース収集と NLP
  - RSS フィード収集（news_collector）・raw_news 保存
  - OpenAI を用いた銘柄別ニュースセンチメント（ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成（ai.regime_detector.score_regime）
- リサーチ／ファクター計算
  - モメンタム・ボラティリティ・バリュー等のファクター計算（research）
  - forward returns / IC / 統計サマリ（feature_exploration）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの DDL・初期化ユーティリティ（init_audit_schema / init_audit_db）
- コンフィグ管理
  - .env または環境変数から設定を読み込む自動ロード機能（config.Settings）

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   ここではソース配布に依存せず最小限の依存を示します。プロジェクトに requirements.txt があればそれを使ってください。
   pip install duckdb openai defusedxml

   （実運用では requests 等追加パッケージが必要になる可能性があります。）

4. 環境変数（.env）を用意
   プロジェクトルートの .env または .env.local に必要な環境変数を設定します。自動ロードはデフォルトで有効です。
   主要な環境変数（少なくとも以下を設定してください）:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack 通知先 Channel ID（必須）
   - OPENAI_API_KEY        : OpenAI API キー（AI 機能を使う場合）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite(監視) DB パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV           : 実行環境 ('development'|'paper_trading'|'live')（デフォルト development）
   - LOG_LEVEL             : ログレベル ('DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL')

   自動 .env ロードを無効にする場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境にセットしてください（テスト時等で便利）。

使い方（よく使う API 例）
- DuckDB 接続の作成（例）
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")  # ファイルがなければ作成されます

- 日次 ETL 実行
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを生成（AI 必須）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n_written} codes")

  ※ OPENAI_API_KEY を環境変数に入れておけば api_key を省略できます。

- 市場レジーム判定
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数からキー取得

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # スキーマ作成済みの DuckDB 接続が返る

- 研究用ファクター計算例
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # z-score 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

設定（Config）について
- 自動的にプロジェクトルート（.git または pyproject.toml を基準）から .env を読み込みます（.env → .env.local の順で上書き）。
- Settings クラス経由で環境設定にアクセス可能:
  from kabusys.config import settings
  settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live など

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                     (パッケージ初期化、バージョン)
  - config.py                        (.env / 環境変数管理)
  - ai/
    - __init__.py
    - news_nlp.py                    (ニュースの LLM スコアリング)
    - regime_detector.py             (市場レジーム判定ロジック)
  - data/
    - __init__.py
    - jquants_client.py              (J-Quants API クライアント + 保存ユーティリティ)
    - pipeline.py                    (ETL パイプライン: run_daily_etl 等)
    - etl.py                         (ETLResult 再エクスポート)
    - news_collector.py              (RSS 収集・前処理)
    - stats.py                       (z-score 正規化等)
    - quality.py                     (データ品質チェック)
    - calendar_management.py         (市場カレンダー管理)
    - audit.py                       (監査テーブル DDL / 初期化)
  - research/
    - __init__.py
    - factor_research.py             (モメンタム/バリュー/ボラティリティ)
    - feature_exploration.py         (forward returns, IC, summary, rank)
  - research/* other modules for factor exploration

設計・運用上の注意
- ルックアヘッドバイアス対策:
  - 多くの処理は datetime.today()/date.today() を内部で直接参照せず、target_date を明示的に受け取り過去データのみを参照するよう設計されています。バックテストや再現性確保に有利です。
- 冪等性:
  - J-Quants から取得したデータの DB 保存は基本的に UPSERT（ON CONFLICT DO UPDATE）で冪等となるよう実装されています。
- フェイルセーフ:
  - OpenAI API の失敗などは多くの箇所でフォールバック（例: macro_sentiment=0.0）し、全体処理を停止させない設計になっています。
- セキュリティ:
  - news_collector は SSRF 防止・gzip 大量解凍対策等を持ちます。外部から渡す URL には注意してください。
- 環境分離:
  - settings.env（development / paper_trading / live）により、本番と擬似環境の挙動を切り替えることを想定しています。

開発・テストのヒント
- 自動 .env ロードを無効化してユニットテスト内で環境変数を制御したい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しなど外部 API 呼び出しは各モジュール内の _call_openai_api や _urlopen をモックしやすい構造になっています。
- DuckDB を使ったテストでは ":memory:" を使うことでインメモリ DB を利用できます（init_audit_db 等は ":memory:" を受け付けます）。

ライセンス・貢献
- （リポジトリにライセンスファイルがある場合はそこに従ってください。ここには記載がありません）

以上が本コードベースの主要な説明になります。必要であれば、README に
- 具体的な .env のサンプル (.env.example)
- requirements.txt の想定内容
- CI／デプロイ手順
などの追記を行います。どの情報を追加しますか？