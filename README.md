KabuSys — 日本株自動売買プラットフォーム（README）
概要
- KabuSys は日本株向けのデータ基盤・リサーチ・AI スコアリング・監査ログ・ETL を含む自動売買補助ライブラリ群です。
- 主な目的は「J-Quants 等のデータ取得 → DuckDB に永続化 → ファクター計算やニュース/NLP 評価 → 戦略・発注ロギング」のワークフローを安全かつ冪等に実行することです。

主な機能
- データ取得 / ETL
  - J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存（冪等）
  - run_daily_etl による日次 ETL パイプライン（カレンダー → 価格 → 財務 → 品質チェック）
  - レート制御・リトライ・トークン自動リフレッシュ対応（jquants_client）
- データ品質管理
  - 欠損、重複、スパイク、日付不整合検出（quality モジュール）
- ニュース収集 / NLP
  - RSS からニュースを収集して raw_news に保存（news_collector）
  - OpenAI（gpt-4o-mini）を用いた銘柄別・マクロセンチメントのスコアリング（news_nlp, regime_detector）
  - SSRF対策やサイズ制限、トラッキングパラメータ除去などの安全設計
  - API エラー時はフェイルセーフ（スコア=0、もしくはスキップ）で継続
- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（情報係数）、統計サマリ、Zスコア正規化
- 監査（Audit / トレーサビリティ）
  - signal_events / order_requests / executions を含む監査用スキーマ定義と初期化ユーティリティ（data.audit）
  - init_audit_db による監査用 DuckDB の初期化（UTC タイムゾーン設定）
- 設定管理
  - .env / 環境変数から設定を自動読み込み（config モジュール）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

セットアップ手順（開発環境向け）
1. ソースをチェックアウト
   - レポジトリのルート（pyproject.toml/.git がある場所）で作業してください。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージのインストール（ローカル開発モード）
   - python -m pip install -e . 
   - （必要な外部依存は pyproject.toml / requirements 文件に記載されている前提です）

4. 環境変数 / .env ファイル
   - プロジェクトルートに .env（および .env.local）を置くと自動で読み込まれます（config._find_project_root による）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（jquants_client が内部で使用）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack のチャンネル ID
   - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）を使う場合に必要
   - オプション・設定:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動 .env 読み込みを抑制
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
   - 例（.env）
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development

使い方（主要な API/例）
- DuckDB 接続を作る
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL の実行
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  # ETLResult オブジェクト。result.to_dict() で内容確認可能。

- ニューススコアリング（銘柄別 AI スコア）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026,3,20), api_key="あなたのOpenAIキー")
  # 戻り値は書き込んだ銘柄数（整数）

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20), api_key="あなたのOpenAIキー")
  # market_regime テーブルへ書き込む

- 監査 DB 初期化（監査専用 DB を作りたい場合）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit に対してアプリは監査レコードを書き込みます

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は [{ "date":..., "code": "...", "mom_1m": ...}, ...]

注意・設計上のポイント
- ルックアヘッドバイアス対策: 多くのモジュールで date.today()/datetime.today() を内部で用いず、呼び出し側が target_date を渡す設計です。バックテストや再現性に配慮してください。
- フェイルセーフ: OpenAI や外部 API の失敗は原則例外直投げではなく、フォールバック（スコア0やスキップ）して処理継続する箇所が多くあります。ログを必ず確認してください。
- ニュース収集: SSRF 対策、gzip サイズ上限、トラッキングパラメータ除去など堅牢化を行っています。RSS のパース失敗はログに出して空スキップします。
- ETL の冪等性: 保存処理は ON CONFLICT DO UPDATE を使い、再実行で上書きされる仕様です（ページネーション間のトークン共有や backfill に対応）。
- OpenAI 呼び出し: テストしやすくするため _call_openai_api をモック可能にしています。API キーは引数で明示的に渡せます。

主要ディレクトリ構成（src/kabusys）
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス（自動 .env 読み込み、必須 key チェック）
- ai/
  - __init__.py
  - news_nlp.py            # 銘柄別ニュースセンチメント評価、score_news 関数
  - regime_detector.py     # マクロ + ETF ma200 で市場レジーム判定、score_regime 関数
- data/
  - __init__.py
  - calendar_management.py # JPX カレンダー取得・営業日判定ユーティリティ
  - etl.py                 # ETLResult の再エクスポート
  - pipeline.py            # run_daily_etl, run_prices_etl 等（ETL パイプライン本体）
  - stats.py               # zscore_normalize 等の統計ユーティリティ
  - quality.py             # データ品質チェック群
  - audit.py               # 監査ログテーブル DDL と初期化ユーティリティ
  - jquants_client.py      # J-Quants API クライアント（取得・保存・リトライ・rate limit）
  - news_collector.py      # RSS 取得・前処理・raw_news 保存
- research/
  - __init__.py            # 研究系ユーティリティの公開（factor_research 等）
  - factor_research.py     # Momentum/Value/Volatility の計算
  - feature_exploration.py # forward returns / IC / summary 等

参考 API（抜粋）
- data.pipeline.run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
  - 日次 ETL を実行して ETLResult を返す
- data.jquants_client.fetch_daily_quotes(id_token=None, date_from=None, date_to=None)
  - J-Quants から生データを取得（ページネーション対応）
- data.jquants_client.save_daily_quotes(conn, records)
  - DuckDB の raw_prices に保存（冪等）
- ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースを集約して OpenAI に投げ、ai_scores に書き込む
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ma200乖離 + LLM マクロセンチメントから market_regime を算出して書き込む

テスト・開発メモ
- OpenAI 呼び出しや外部 HTTP を含む箇所は _call_openai_api や _urlopen 等を patch/mock してユニットテストを行いやすく設計しています。
- 自動 .env ロードはプロジェクトルートの存在を探して行うため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定しておくと環境汚染を防げます。

ライセンス・貢献
- （リポジトリの LICENSE を参照してください。）
- バグ報告や改善提案は Issue/PR で歓迎します。外部 API キーや秘密情報は絶対に公開しないでください。

以上。README の補足・追記やサンプルスクリプト（CLI ラッパー等）が必要であれば教えてください。