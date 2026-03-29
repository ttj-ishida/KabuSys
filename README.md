KabuSys
=======

日本株向けの自動売買 / データ基盤ユーティリティ群です。  
このリポジトリはデータ ETL、ニュース NLP（LLM）、市場レジーム判定、リサーチ用ファクター計算、監査ログなどのモジュール群を提供します。  
主に DuckDB をローカル DB として用い、J-Quants API / RSS / OpenAI（gpt-4o-mini）など外部サービスと連携します。

主な目的
- J-Quants からの株価・財務・カレンダーの差分 ETL
- RSS によるニュース収集と LLM（OpenAI）を用いた銘柄センチメント算出
- ETF を使った市場レジーム（bull/neutral/bear）判定
- 研究向けファクター生成・統計ユーティリティ
- 発注・約定などのフローを追跡する監査ログスキーマ（DuckDB）

機能一覧
- kabusys.config: 環境変数 / .env 自動ロード、アプリ設定取得
- kabusys.data:
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - ニュース収集（RSS -> raw_news）と前処理（SSRF 対策・サイズ制限）
  - マーケットカレンダー管理（営業日判定・next/prev_trading_day 等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化 等）
- kabusys.ai:
  - news_nlp.score_news: ニュースをまとめて LLM に投げ、銘柄ごとの ai_score を ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA 乖離 + マクロ記事 LLM 評価を合成して market_regime に保存
- kabusys.research:
  - ファクター計算（momentum / volatility / value）と特徴量探索ユーティリティ（forward returns, IC, summary）

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて追加パッケージをインストールしてください）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を作成すると、kabusys.config が自動読み込みします（CWD 依存ではなくパッケージ位置からプロジェクトルートを探索）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨の .env（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development / paper_trading / live
- LOG_LEVEL=INFO

使い方（簡易サンプル）
- 基本的な DB 接続（DuckDB）と ETL 実行例
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("<path/to/kabusys.duckdb>"))  # settings.duckdb_path を参照しても良い
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY に設定）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化（監査専用 DB を作る場合）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

重要な挙動・注意点
- Look-ahead bias 対策: モジュールの多くは target_date を明示的に受け取り、datetime.today()/date.today() を内部で直接参照しない設計になっています。バッチ処理やバックテストで再現性を保つため、target_date を明示してください。
- OpenAI 呼び出し: gpt-4o-mini（JSON mode）を利用する想定です。API レスポンスのパース失敗や API 障害はフェイルセーフ（0 値で継続）になるよう実装されていますが、API キーの設定が必要です。
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml の存在場所）を基準に .env/.env.local を読み込みます。既存の OS 環境変数は保護されます。
- J-Quants API: rate limit（120 req/min）に合わせたレートリミッタ、リトライ・トークン自動リフレッシュ等の機構を内蔵しています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                       : .env / 環境設定管理
  - ai/
    - __init__.py                    : score_news を公開
    - news_nlp.py                    : ニュース NLP（score_news）
    - regime_detector.py             : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              : J-Quants API クライアント（fetch/save）
    - pipeline.py                    : ETL パイプライン（run_daily_etl 等）
    - etl.py                         : ETLResult 再エクスポート
    - news_collector.py              : RSS 収集・正規化
    - calendar_management.py         : 市場カレンダー管理
    - quality.py                     : データ品質チェック
    - stats.py                       : 統計ユーティリティ（zscore_normalize）
    - audit.py                       : 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             : ファクター計算（momentum/value/volatility）
    - feature_exploration.py         : 将来リターン / IC / summary 等

開発上のヒント
- テスト／CI 用に .env の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。
- OpenAI 呼び出しや HTTP クライアント等は関数単位で差し替え（モック）しやすい実装です（ユニットテスト時にモック可能）。
- DuckDB 側のテーブル（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar など）は ETL / save 関数で想定されるスキーマが必要です。監査ログは kabusys.data.audit.init_audit_schema / init_audit_db で作成できます。

ライセンス / コントリビュート
- （ここでは省略）実際のリポジトリでは LICENSE ファイルや Contributing ガイドを追加してください。

問題報告・質問
- バグや使い方については Issue を立ててください。API キーやシークレットは公開しないでください。

以上がプロジェクトの概要・導入・利用方法の簡易 README です。必要であればセットアップの詳細コマンドや .env.example の完全テンプレート、よくあるトラブルシューティング（OpenAI レート制限・J-Quants 認証失敗・DuckDB パーミッション等）を追記します。どの情報が欲しいか教えてください。