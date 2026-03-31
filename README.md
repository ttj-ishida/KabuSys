KabuSys — 日本株自動売買プラットフォーム（README）
概要
KabuSys は日本株のデータパイプライン、特徴量計算、ニュース／マクロセンチメント解析、監査ログ、研究用ユーティリティを備えた自動売買システムのコアライブラリです。J-Quants API や OpenAI（gpt-4o-mini）を用いた ETL、ニュースNLP、レジーム判定、ファクター計算などを提供します。設計上、バックテストでのルックアヘッドバイアス防止、ETL の冪等性、API 呼び出しのリトライ・レート制御、データ品質チェックを重視しています。

主な機能一覧
- データ取得 / ETL
  - J-Quants API 経由で株価（日次 OHLCV）、財務（四半期）、JPX カレンダーを差分取得・保存
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl を提供
  - レートリミッタ、トークン自動更新、リトライ、ページネーション対応
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付整合性チェック（quality.run_all_checks）
- ニュース収集
  - RSS からのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去、サイズ制限など）
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に送りセンチメントを算出し ai_scores テーブルへ書き込み（ai.news_nlp.score_news）
  - バッチ処理、レスポンスバリデーション、スコアのクリッピング、リトライ
- 市場レジーム判定（マクロ + ETF）
  - ETF（1321）の200日MA乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.calc_*）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル作成・初期化（data.audit.init_audit_schema / init_audit_db）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings による環境変数ラッパー（config.settings）

必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要。引数で渡すことも可）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に必要（必須）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb（省略可）
- SQLITE_PATH: 監視用 SQLite パス（省略可）
- KABUSYS_ENV: development | paper_trading | live （デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

（自動 .env 読み込み）
- プロジェクトルートに .env / .env.local があれば起動時に自動ロードされます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順
1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境を作成して有効化してください（venv / conda 等）

2. 依存パッケージのインストール
   - requirements ファイルは付属しない想定のため、少なくとも以下をインストールしてください:
     - duckdb
     - openai
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml

3. ソースをプロジェクトに組み込む / 開発インストール
   - パッケージルートに移動し（pyproject.toml がある想定）、開発インストール:
     pip install -e .

4. 環境変数の設定
   - .env を作成（.env.example を参照する想定）。最小例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
   - プロジェクトルートに .env を置くと自動読み込みされます。

5. DB 用ディレクトリ作成
   - 例: mkdir -p data

使い方（主要な API と例）
- DuckDB 接続と ETL 実行（日次 ETL）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコアリング
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定しているか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込んだ銘柄数:", written)

- 市場レジーム判定（マクロセンチメント + MA）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 研究用ファクター計算
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は dict のリスト

- 監査DB 初期化（監査ログ専用 DB を作成）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring.duckdb")
  # これで signal_events / order_requests / executions が作成されます

注意点（設計・運用上のポイント）
- ルックアヘッドバイアス防止
  - 多くの関数は date.today() / datetime.today() を直接参照せず、明示的な target_date 引数に基づいて動作します。バックテストでの使用時は target_date を必ず明示してください。
- 冪等性
  - ETL と保存関数は ON CONFLICT DO UPDATE 等で冪等に設計されています（部分失敗時の保護を考慮）。
- API 安全性
  - J-Quants クライアントにはレート制御・リトライ・トークン自動更新があります。OpenAI 呼び出しはリトライ・JSON パースの堅牢化を行っています。
- セキュリティ
  - ニュースコレクタは SSRF 対策、受信サイズ制限、XML の安全パーサ（defusedxml）を使用しています。

ディレクトリ構成（主なファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL の公開型（ETLResult 再エクスポート）
    - news_collector.py          — RSS 収集と保存
    - calendar_management.py     — 市場カレンダー管理 / 営業日ロジック
    - quality.py                 — データ品質チェック（QualityIssue）
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログ（テーブル定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py         — momentum/value/volatility 等
    - feature_exploration.py     — forward returns, IC, rank, summary
  - monitoring/ (省略可の監視関連モジュールが想定される)
  - execution/ (発注等の実行ロジック、実装が追加される想定)
  - strategy/ (戦略生成ロジック、実装が追加される想定)

開発・テストに関するヒント
- 自動 .env ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しやネットワーク IO 部分はユニットテストでモックしやすい設計（内部関数をパッチして差し替え可能）。
- DuckDB の executemany は空リストを受け取れないバージョンがあるため、コード内で事前に空チェックを行っています。

ライセンス・貢献
- この README はコードベースを説明するためのドキュメントです。実運用前に各 API キーの管理、秘密情報の取り扱い、追加のログ・監視を必ず整備してください。貢献やバグ報告はリポジトリの ISSUE / PR フローに従ってください。

問い合わせ・補足
- README に含めてほしい具体的な運用手順（例: cron ジョブ, Airflow, GitHub Actions 連携）やサンプル .env.example を希望される場合は、その旨を教えてください。必要に応じて追記します。