# KabuSys — 日本株自動売買システム（README）

概要
- KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買パイプラインのコア実装です。
- DuckDB をバックエンドにして、J-Quants API からのデータ取り込み（OHLCV / 財務 / 市場カレンダー）、ニュース収集・NLP（OpenAI）、因子計算、ETL、監査ログ（発注・約定のトレーサビリティ）などを提供します。
- バックテストや本番運用を意識した設計（ルックアヘッドバイアス対策、冪等保存、堅牢なリトライやバリデーション）を重視しています。

主な機能一覧
- データ取得 / ETL
  - J-Quants クライアント（jquants_client）：日次株価、財務、マーケットカレンダー、上場銘柄情報の取得・保存（ページネーション・レート制御・トークン自動更新・冪等保存）
  - ETL パイプライン（data.pipeline）：差分取得、バックフィル、品質チェックの統合実行（run_daily_etl 等）
- データ品質チェック（data.quality）
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue として集約）
- ニュース収集 / NLP（data.news_collector、ai.news_nlp）
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI を使った銘柄ごとのニュース感情スコア生成（score_news）
- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成し日次で市場レジームを判定（bull/neutral/bear）
- リサーチ / 因子計算（research）
  - モメンタム、ボラティリティ、バリューなどの因子計算（prices_daily / raw_financials を参照）
  - 将来リターン、IC 計算、統計サマリーなどのユーティリティ
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の監査テーブルの定義と初期化（init_audit_schema / init_audit_db）
- 設定管理（config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と環境変数集約（Settings オブジェクト）

前提・依存
- Python 3.10+（型注釈の Union | などを利用）
- 主な Python パッケージ（最低限、開発時にインストールするもの）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリを多用（urllib, json, datetime, logging 等）

セットアップ手順（開発環境向けの例）
1. リポジトリをチェックアウト
   - git clone ... && cd <repo>

2. 仮想環境の作成（例：venv）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （パッケージはプロジェクトの requirements.txt / pyproject.toml に合わせて調整してください）

4. 開発インストール（任意）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに .env または .env.local を配置すると自動読み込みされます（config モジュールが .git または pyproject.toml を基準にプロジェクトルートを探索）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

重要な環境変数（設定項目）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（ai モジュールで利用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

（参考 .env の例）
# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（簡単なクイックスタート例）

- DuckDB 接続を作って日次 ETL を実行する
  例（Python REPL / スクリプト）:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- 監査用 DB を初期化する
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成して初期化

- ニューススコア作成（OpenAI 必須）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で渡す
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")

- 市場レジーム判定（OpenAI 必須）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))

- 因子計算 / リサーチ
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))

運用上の注意
- AI（OpenAI）呼び出しを行う機能（news_nlp, regime_detector）は API キーと通信コスト、レート制限に注意して運用してください。モック可能な設計（テストで差し替え）が施されています。
- J-Quants API はレート制限（120 req/min）やトークン制御があります。jquants_client は内部でレート制御・リトライ・トークンリフレッシュを行いますが、ID トークン・リフレッシュトークンの管理は適切に行ってください。
- ETL は部分失敗に強く設計されていますが、品質チェック結果（QualityIssue）を監視し、重大な問題が検出された場合は運用側で対応してください。
- DuckDB の executemany などはバージョン差分で挙動が変わる場合があるため、必要に応じて DuckDB のバージョンを固定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント（OpenAI）
    - regime_detector.py             — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + 保存関数
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL 結果クラス再公開
    - news_collector.py              — RSS ニュース収集
    - calendar_management.py         — マーケットカレンダー管理（営業日判定）
    - stats.py                       — 統計ユーティリティ（zscore 正規化）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Value/Volatility 等の因子計算
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー
  - ai, research, data 以下に更なる内部ユーティリティや公開関数群

開発・テスト
- モジュール内のネットワーク呼び出しや OpenAI 呼び出しはモックしやすく設計されています（ユニットテストの際は該当関数を patch してください）。
- .env 自動読み込みはプロジェクトルートの検出に依存します。CI・テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して明示的に環境変数を設定してください。

ライセンス・貢献
- 本 README には記載されていません。リポジトリの LICENSE を参照してください。
- バグ修正や機能追加は PR ベースで受け付けてください。大きな設計変更は事前に Issue で議論してください。

お問い合わせ
- 問題・提案は Issue を立ててください。コードの理解や利用方法についての質問があれば README を更新します。

以上です。必要であれば、README に実行スクリプト例（systemd ユニット / cron など）やより詳細な .env.example を追加できます。どの情報を追加したいか教えてください。