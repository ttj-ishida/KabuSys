KabuSys — 日本株自動売買 / データ基盤ライブラリ
================================

概要
----
KabuSys は日本株のデータ収集・品質管理・ファクター計算・AIベースのニュースセンチメント
および市場レジーム判定、監査ログ（発注→約定トレース）を含む内部ユーティリティ群を提供する
Python パッケージです。J-Quants API や RSS を用いた ETL、DuckDB を用いたデータ永続化、
OpenAI（gpt-4o-mini）を使ったニュース NLP/レジーム判定、研究用のファクター計算・統計解析
など、システム化された投資システムの基盤機能を実装しています。

主な機能
-------
- データ ETL（J-Quants からの株価日足 / 財務 / 市場カレンダー取得、差分更新・バックフィル）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- 市場カレンダー管理（営業日判定 / next/prev trading day / SQ 判定）
- ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去・前処理）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア算出、ai_scores へ保存）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成）
- 研究ユーティリティ（モメンタム / ボラティリティ / バリュー等のファクター計算、
  将来リターン計算、IC 計算、Z スコア正規化、統計サマリー）
- 監査ログ（signal_events / order_requests / executions テーブル、冪等性・トレーサビリティ）
- J-Quants API クライアント（レート制限・再試行・トークン自動リフレッシュ・DuckDB への冪等保存）
- 環境変数管理（.env 自動ロード / 必須キー検査 / 設定ラッパー）

セットアップ
-----------

1. リポジトリをチェックアウト（通常の Python パッケージ構成を想定）
   - この README は src/kabusys 配下のパッケージ用です。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - 必要に応じて他ライブラリ（テスト用: pytest など）を追加してください。
   - 開発インストール: pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（主な）環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=your_openai_api_key  # score_news / score_regime を呼ぶ際に必要
- KABU_API_PASSWORD=...               # kabuステーション API を使う場合
- SLACK_BOT_TOKEN=...                 # Slack 連携がある場合
- SLACK_CHANNEL_ID=...
任意 / デフォルトあり
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development  # development / paper_trading / live
- LOG_LEVEL=INFO

使い方（代表的な呼び出し例）
--------------------------

※ 以下は簡単な例です。実運用ではロギング設定・エラーハンドリング・スケジューリングを追加してください。

- DuckDB 接続を作って ETL を実行する（1日分）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントスコア（OpenAI 必須）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書込銘柄数:", n_written)

- 市場レジーム判定（OpenAI 必須）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- 研究用ファクター計算
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

運用上のポイント / テストのヒント
- OpenAI 呼び出しはモックしやすいように内部の _call_openai_api を patch できます。
  （例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）
- .env はプロジェクトルート（.git または pyproject.toml のある上位）から自動ロードされます。
  テストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- J-Quants クライアントはレート制限（120 req/min）・再試行を内部で行います。大量取得はバッチ化してください。
- DuckDB への executemany に関する互換性を考慮して空リストは渡さない実装になっています（ETL 内で対策済み）。

ディレクトリ構成（概要）
---------------------

src/kabusys/
- __init__.py
- config.py                 -- 環境変数 / 設定ラッパー（.env 自動ロード含む）
- ai/
  - __init__.py             -- score_news の公開
  - news_nlp.py             -- ニュース NLP（銘柄ごとセンチメント）
  - regime_detector.py      -- マクロ + MA200 で市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py       -- J-Quants API クライアント + 保存関数
  - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
  - etl.py                  -- ETLResult の公開
  - calendar_management.py  -- 市場カレンダー関連ユーティリティと更新ジョブ
  - quality.py              -- データ品質チェック群
  - news_collector.py       -- RSS 収集・前処理・保存（SSRF対策、トラッキング除去）
  - stats.py                -- zscore_normalize など統計ユーティリティ
  - audit.py                -- 監査ログ（DDL / init / init_audit_db）
- research/
  - __init__.py
  - factor_research.py      -- Momentum / Volatility / Value ファクター計算
  - feature_exploration.py  -- 将来リターン, IC, rank, factor_summary 等

補足・設計方針（抜粋）
--------------------
- ルックアヘッドバイアス回避: 内部で date.today()/datetime.today() を直接参照しない設計箇所が多く、
  target_date を明示して処理を行います。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時は部分的にフェイルセーフなデフォルト（例: macro_sentiment=0）で継続する箇所があるため、
  運用ではログを監視して再実行やアラートを行ってください。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE / INSERT … ON CONFLICT を使い、再実行での上書きを安全にしています。
- セキュリティ: news_collector では SSRF 防止、XML パースに defusedxml を使用、RSS サイズ上限の設定などを実施しています。

ライセンス / コントリビューション
---------------------------------
（このリポジトリのライセンス情報やコントリビューションポリシーがあればここに記載してください。）

最後に
------
この README はコードベースの主要機能・使い方・設定を素早く把握するための概要です。詳細な API 仕様や運用手順は各モジュールの docstring（src/kabusys 以下）を参照してください。質問や追加したい内容があれば教えてください。