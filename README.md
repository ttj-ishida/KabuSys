KabuSys
=======

KabuSys は日本株向けのデータパイプライン／リサーチ／自動売買基盤のライブラリ群です。  
DuckDB をデータ層に用い、J-Quants からのデータ取得、RSS ニュース収集、LLM を用いたニュースセンチメント、ファクター計算、ETL ジョブ、監査ログ（トレーサビリティ）などを提供します。

主な目的
- J-Quants など外部データソースからの差分 ETL と品質チェック
- ニュース収集と LLM を用いた銘柄別センチメント付与
- 市場レジーム判定（ETF + マクロニュース）
- ファクター計算・特徴量探索（Research 用）
- 監査ログ（signal → order → execution のトレーサビリティ）
- DuckDB によるローカルデータ管理（バックテスト / 運用の両方で利用可能）

主な機能一覧
- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch_* / save_*）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news 保存、URL 正規化、SSRF 防御、サイズ制限）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ初期化・管理（audit schema の init, init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化 等）
- ai
  - ニュース NLP（gpt-4o-mini を使った銘柄別センチメント score_news）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成して regime 判定 score_regime）
  - テストしやすい API 呼び出しラッパ（_call_openai_api をモックして差し替え可能）
- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、rank 等
- config
  - .env / 環境変数自動読み込み、必要環境変数チェック（settings）

セットアップ（開発環境向け）
1. 必要な Python バージョン
   - Python 3.10 以上（typing の | 記法などを使用しているため）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージ（代表例）
   最低限必要なパッケージ例:
   - duckdb
   - openai
   - defusedxml

   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

4. 環境変数 / .env
   プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。  
   必須の環境変数（実行に必要）:
   - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
   - KABU_API_PASSWORD      — kabu ステーション API パスワード（将来の注文実装用）
   - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（通知を使う場合）
   - SLACK_CHANNEL_ID       — Slack チャンネル ID（通知を使う場合）
   - OPENAI_API_KEY         — OpenAI API キー（ai モジュールを利用する場合）

   任意の環境変数:
   - KABUSYS_ENV            — "development", "paper_trading", "live" のいずれか（デフォルト: development）
   - LOG_LEVEL              — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
   - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            — 監視用 sqlite（デフォルト: data/monitoring.db）

   サンプル .env（例）
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

使い方（典型的なワークフロー）
- DuckDB 接続を作って ETL を回す（日次バッチ）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())

- ニュースセンチメント（AI）を実行して ai_scores に書き込む
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB 初期化（監査専用 DB）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 返り値は DuckDB 接続

- ファクター計算 / Research
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))

テストやモックについて
- OpenAI などの外部 API 呼び出しは内部で _call_openai_api を経由しているため、unittest.mock.patch で差し替えやスタブを挿入してテストできます（kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api をモック）。

自動 .env ロードの挙動
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると、.env → .env.local の順に自動読み込みします。  
- OS 環境変数が優先され、.env.local は .env を上書きします。  
- テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                - パッケージ初期化（バージョン等）
  - config.py                  - 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py              - ニュース NLP（score_news）
    - regime_detector.py       - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        - J-Quants API クライアント（fetch/save）
    - pipeline.py              - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   - 市場カレンダー管理
    - news_collector.py        - RSS ニュース収集
    - quality.py               - データ品質チェック
    - stats.py                 - 統計ユーティリティ（zscore_normalize）
    - etl.py                   - ETLResult 再エクスポート
    - audit.py                 - 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py       - ファクター計算（momentum/value/volatility）
    - feature_exploration.py   - 将来リターン / IC / summary / rank

設計上の注意点
- Look-ahead bias を避ける設計が各所に組み込まれており、target_date 引数を明示することで過去時点のみのデータを参照するようにしています（datetime.today() を直接参照しない実装方針）。
- ETL は冪等性（ON CONFLICT DO UPDATE）を重視しており、部分失敗時に既存データを不必要に消さない設計です。
- OpenAI / J-Quants などの外部 API 呼び出しはリトライやバックオフ、フェイルセーフ（失敗時は中立スコア等）を組み込んでいます。

よくある実行例のまとめ
- ETL（夜間バッチ）: run_daily_etl を cron や Airflow から呼ぶ
- ニュース収集: news_collector.fetch_rss を定期実行して raw_news に保存（DB 保存ロジックは本モジュールに実装）
- AI スコアリング: score_news, score_regime を ETL 後に呼ぶ
- Research: DuckDB に読み込んだデータを用いて kabusys.research.* をローカルで実行

サポート / 拡張
- OpenAI モデルやバッチサイズ、ニュースウィンドウ等は各モジュールの定数で定義されています。運用ポリシーに合わせて調整可能です。
- 注文執行部分（kabu ステーション等）や Slack 通知は設定や別モジュールで接続実装を追加できます。

（以上）