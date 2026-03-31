KabuSys — 日本株自動売買プラットフォーム（README）
概要
本リポジトリは「KabuSys」プロジェクトのコアライブラリ群です。J-Quants / kabuステーション / OpenAI 等を使ったデータETL、ニュースNLP（LLM）による銘柄センチメント、ファクター研究、監査ログ／発注履歴管理など、日本株の自動売買プラットフォームに必要な基盤処理を提供します。設計上、バックテストや研究用途と本番運用（実注文）を分離できるように実装されています。

主な特徴（機能一覧）
- データ取得・ETL
  - J-Quants API 経由で日次株価（OHLCV）、財務指標、上場銘柄情報、JPXカレンダーを差分取得 → DuckDB に冪等保存
  - 差分・バックフィルロジック、ページネーション対応、レート制御・再試行ロジック実装
- データ品質管理
  - 欠損、スパイク、重複、日付不整合などの品質チェックを実行するモジュール
- ニュース収集
  - RSS フィード収集（SSRF対策、トラッキングパラメータ除去、前処理）→ raw_news / news_symbols へ保存
- ニュースNLP（LLM）
  - OpenAI（gpt-4o-mini 等）を使い、銘柄ごとのセンチメント（ai_scores）を生成
  - マクロニュースを用いた市場レジーム判定（regime_detector）
  - レート制限・リトライ・レスポンス検証を備えた堅牢な実装
- 研究（Research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリーの実装
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義、初期化ユーティリティ
  - 監査DB（DuckDB）初期化関数を提供
- ユーティリティ
  - 環境設定の自動読み込み（.env/.env.local）、設定ラッパー（kabusys.config.settings）
  - 汎用統計関数（zscore_normalize）など

セットアップ手順（開発環境向け）
前提
- Python 3.10+（typing | match 機能を想定）
- ネットワークアクセス（J-Quants / OpenAI / RSS 等）
- 必要パッケージ: duckdb, openai, defusedxml, など（下記参照）

1) リポジトリをクローン
  git clone <this-repo>
  cd <this-repo>

2) 仮想環境作成（任意）
  python -m venv .venv
  source .venv/bin/activate  # macOS/Linux
  .venv\Scripts\activate     # Windows

3) 依存パッケージをインストール
  （requirements.txt が無い場合は以下を例示）
  pip install duckdb openai defusedxml

  開発時は editable install:
  pip install -e .

4) 環境変数設定
  - プロジェクトルートに .env または .env.local を作成すると、自動で読み込まれます（デフォルト）。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 代表的な必須環境変数:
    - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL用）
    - KABU_API_PASSWORD     : kabuステーション API のパスワード（実注文連携時）
    - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
    - SLACK_CHANNEL_ID      : Slack チャネル ID
    - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 等）
  - オプション:
    - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
    - SQLITE_PATH (監視用: data/monitoring.db)
    - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - KABUSYS_ENV (development / paper_trading / live)
    - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

  例 (.env):
    JQUANTS_REFRESH_TOKEN=xxxx
    OPENAI_API_KEY=sk-...
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb

5) データベースの初期化（監査DBなど）
  Python REPL から:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
  これにより監査テーブル（signal_events / order_requests / executions）とインデックスが作成されます。

使い方（主要な利用例）
- 日次ETL を実行（ETL パイプライン）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメント（LLM）で ai_scores を生成
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  cnt = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote {cnt} scores")

  ※ OpenAI API キーは OPENAI_API_KEY 環境変数、または score_news の api_key 引数で渡せます。

- 市場レジーム判定（MA + マクロニュース）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))

- 監査DB初期化（コード例）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- ファクター計算（研究用途）
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

注意事項（運用上のポイント）
- 本ライブラリはデータ取得・API呼び出しを行います。APIキーやシークレットの管理・アクセス制御に注意してください。
- OpenAI 呼び出しには費用が発生します。テスト時はキーや呼び出し回数に注意してください。
- 実際の発注連携（kabuステーション）を有効化する前に、必ずペーパートレード／ステージングで検証してください（KABUSYS_ENV を paper_trading に設定）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行われます。テスト等で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

主なディレクトリ構成（概要）
- src/kabusys/
  - __init__.py                   : パッケージ初期化（バージョン等）
  - config.py                     : 環境変数読み込み・設定ラッパー（settings）
  - ai/
    - __init__.py                 : ai サブパッケージ公開
    - news_nlp.py                 : ニュース NLP（LLM）で銘柄ごとの ai_score を生成
    - regime_detector.py          : マクロ + ETF MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           : J-Quants HTTP クライアント（取得 / 保存関数）
    - pipeline.py                 : ETL パイプライン（run_daily_etl 等）
    - etl.py                      : ETLResult 再エクスポート
    - calendar_management.py      : マーケットカレンダー管理・営業日ユーティリティ
    - news_collector.py           : RSS ニュース収集と前処理
    - quality.py                  : データ品質チェック（欠損・スパイク・重複等）
    - stats.py                    : 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                    : 監査ログテーブル定義・初期化
  - research/
    - __init__.py                 : 研究系公開 API（factor, feature_exploration など）
    - factor_research.py          : momentum/value/volatility 等のファクター計算
    - feature_exploration.py      : 将来リターン計算、IC、統計サマリー
  - ai/, data/, research/ などの他モジュールは上記に準拠

開発・テスト
- 単体関数は外部API呼び出しを行うため、ユニットテスト時は API 呼び出し関数（OpenAI / urllib 等）をモックすることを推奨します（コード内に patch を想定した差替えポイントあり）。
- DuckDB はファイルベースですが ":memory:" を指定してインメモリ DB でテスト可能です。

ライセンス / 責任
- 本 README はコードベースの概要説明です。実際の商用利用または実資金での発注は自己責任で行ってください。API利用規約・法令順守を必ず確認してください。

フィードバック・寄稿
- バグ報告・改善提案は issue を通じてお願いします。設計思想（ルックアヘッドバイアスの排除、フェイルセーフの採用、冪等性の担保）はドキュメント中に述べた通りですので、それを尊重する変更を歓迎します。

以上。必要であれば、セットアップ用の requirements.txt や実行スクリプト（例: cli エントリポイント）、.env.example のテンプレートを追加する README 版を作成します。どの内容を優先しますか？