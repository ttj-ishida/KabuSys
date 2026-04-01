KabuSys — 日本株自動売買プラットフォーム（README）
概要
KabuSys は日本株を対象にしたデータプラットフォーム／自動売買のライブラリ群です。  
主な目的は以下の通りです：
- J-Quants API からのデータ取得（株価、財務、JPX カレンダー）
- ETL（差分取得・保存・品質チェック）パイプライン
- ニュースの収集・NLP（LLM）によるニュースセンチメント評価
- 市場レジーム判定（MA とマクロニュースの複合評価）
- 監査ログ（発注→約定までのトレーサビリティ）とデータ品質チェック
- 研究用のファクター計算・特徴量分析ユーティリティ

主要機能一覧
- data.jquants_client
  - J-Quants API からのデータ取得（daily quotes / financials / market calendar / listed info）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - レート制限、リトライ、401 リフレッシュ処理を備えた HTTP クライアント
- data.pipeline / ETL
  - 日次差分 ETL（市場カレンダー → 株価 → 財務）と品質チェック実行（quality）
  - ETL 実行結果を ETLResult で返却
- data.quality
  - 欠損検査・スパイク検出・重複チェック・日付整合性チェック
- data.news_collector
  - RSS フィード収集、前処理、raw_news への冪等保存（SSRF / XML 攻撃対策あり）
- ai.news_nlp
  - 銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores に保存
- ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離＋マクロニュースの LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定・保存
- data.calendar_management
  - market_calendar を使った営業日判定・next/prev/get_trading_days、calendar_update_job
- data.audit
  - 監査テーブル（signal_events / order_requests / executions）定義と初期化ユーティリティ
- research
  - ファクター（momentum/volatility/value）計算、将来リターン計算、IC（スピアマン）や統計サマリー、Z-score 正規化ユーティリティ

セットアップ手順（開発環境向け）
前提
- Python 3.9+（typing の Union | 代替表記を考慮）
- DuckDB、openai SDK、defusedxml などの依存パッケージが必要です。

推奨インストール（例）
1) 仮想環境作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2) 必要パッケージをインストール（プロジェクトに requirements.txt がない場合は下記を目安に）
   pip install duckdb openai defusedxml

3) 環境変数 / .env の準備
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます。
   読み込み優先順位: OS 環境変数 > .env.local > .env
   自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（またはよく使う）環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- OPENAI_API_KEY        : OpenAI を使う機能実行時に必要（score_news / score_regime を直接呼ぶ場合は引数で渡すことも可）
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT / KABUSYS_ENV / LOG_LEVEL など（監視・運用設定）

使い方（主な API と実行例）
以下はライブラリをインポートしてプログラム内から使う最小例です。

1) DuckDB 接続
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")

2) ETL（日次パイプライン）を実行
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())

3) ニューススコアリング（OpenAI API キーを環境変数に設定済みの場合）
   from datetime import date
   from kabusys.ai.news_nlp import score_news
   written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores に書き込み
   print(f"written: {written}")

   または明示的に API キーを渡す:
   score_news(conn, date(2026,3,20), api_key="sk-...")

4) 市場レジーム判定
   from kabusys.ai.regime_detector import score_regime
   score_regime(conn, target_date=date(2026,3,20))  # market_regime に書き込み

5) 監査ログの初期化（監査用 DB 作成）
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成して初期化

6) 研究用関数（例: モメンタム計算）
   from kabusys.research.factor_research import calc_momentum
   records = calc_momentum(conn, target_date=date(2026,3,20))
   # zscore 正規化
   from kabusys.data.stats import zscore_normalize
   normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

自動 .env 読み込みの挙動
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を起点に .env と .env.local を自動で読み込みます。
- 上書き順序: OS 環境変数（最優先） > .env.local > .env
- テスト等で自動ロードを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
src/
  kabusys/
    __init__.py               -- パッケージ定義、__version__ 等
    config.py                 -- 環境変数 / 設定読み込みロジック（Settings）
    ai/
      __init__.py
      news_nlp.py             -- ニュースの LLM スコアリング（score_news）
      regime_detector.py      -- 市場レジーム判定（score_regime）
    data/
      __init__.py
      jquants_client.py       -- J-Quants API クライアント（fetch/save 系）
      pipeline.py             -- ETL パイプライン / run_daily_etl
      etl.py                  -- ETLResult の再エクスポート
      quality.py              -- データ品質チェック
      news_collector.py       -- RSS 収集、前処理
      calendar_management.py  -- 市場カレンダー管理 / 営業日判定
      stats.py                -- Z スコア等の統計ユーティリティ
      audit.py                -- 監査ログ定義・初期化
    research/
      __init__.py
      factor_research.py      -- momentum/value/volatility 等のファクター計算
      feature_exploration.py  -- 将来リターン、IC、統計サマリー
    ai/                       -- （上で示した ai モジュール）
    research/                 -- （上で示した research モジュール）
    その他: strategy, execution, monitoring パッケージ名は __all__ に含まれますが、今回の抜粋には未表示のモジュールが想定されます。

運用上の注意点
- Look-ahead バイアス対策: モジュールの多くは内部で date.today() 等を直接参照せず、明示的な target_date を受け取る設計です。バックテストや再現性のために target_date を明示してください。
- OpenAI の呼び出しは API 失敗時にフォールバック（0.0）する設計ですが、API キー管理・コストに注意してください。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、実装側で空チェックを行っています。
- news_collector では SSRF 対策・XML の安全パース（defusedxml）・サイズ制限等の防御を行っています。RSS ソースの選定は運用者の責任でお願いします。

開発／寄稿
- 新規機能追加やバグ修正の際は、既存の設計方針（冪等性、Look-ahead バイアス回避、フェイルセーフの継続処理）に沿うよう注意してください。
- テスト時は環境変数読み込みを無効にするか、必要な環境変数をモックしてください（KABUSYS_DISABLE_AUTO_ENV_LOAD を利用）。

問い合わせ
この README はコードベースの抜粋に基づき作成しています。実際の実行にはプロジェクトルートの pyproject.toml / requirements.txt / 実行スクリプト等を参照してください。必要であれば README に含めるサンプル .env.example や具体的な CLI 実行方法の追加を行います — 希望があれば教えてください。