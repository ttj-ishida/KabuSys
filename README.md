# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）→ ETL → 品質チェック → 特徴量算出 → AIによるニュース・レジーム判定 → 監査ログまで、取引システムのバックエンドを構成する機能群を提供します。

## プロジェクト概要
KabuSys は日本株のデータプラットフォームとリサーチ／シグナル生成に必要なユーティリティ群をまとめた Python パッケージです。主な設計方針は次の通りです。

- Look-ahead bias（未来情報の参照）を防止する設計
- ETL・保存処理は冪等（idempotent）に実装（ON CONFLICT / DELETE→INSERT 等）
- 外部 API 呼び出しは再試行・バックオフ・レート制御を備える
- ニュース収集は SSRF 対策や XML 攻撃対策を実装
- DuckDB をデータレイクとして利用する想定

## 主な機能一覧
- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー、上場銘柄情報
  - レート制限、トークン自動リフレッシュ、リトライ/バックオフを実装
- ETL パイプライン
  - run_daily_etl：市場カレンダー・株価・財務データの差分取得、保存、品質チェック
  - 個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック
  - 欠損データ、重複、スパイク（急変）、日付不整合（未来日／非営業日）検出
- ニュース収集
  - RSS フィード収集、前処理、raw_news への冪等保存、news_symbols で銘柄紐付け
  - SSRF 対策、受信サイズ制限、XML の安全パーサ（defusedxml）
- AI モジュール
  - news_nlp.score_news：銘柄別ニュースセンチメントを OpenAI (gpt-4o-mini) により算出して ai_scores に保存
  - regime_detector.score_regime：ETF（1321）200日移動平均乖離とマクロニュース（LLM）を合成して市場レジーム判定（bull/neutral/bear）
  - OpenAI 呼び出しは再試行やフォールバック（失敗時 0.0）を備える
- 研究・ファクター計算
  - calc_momentum / calc_value / calc_volatility などのファクター算出
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions テーブルの初期化機能（init_audit_schema / init_audit_db）
  - 発注の冪等性とトレーサビリティをサポート
- ユーティリティ
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - データベース初期化・スキーマ用関数群

## セットアップ手順

前提：
- Python 3.9+ を想定（型ヒントに union 型などを使用しているため）
- DuckDB, openai, defusedxml などを利用します。

1. リポジトリをクローン、またはパッケージソースを配置

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. パッケージをインストール（開発モード）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.git または pyproject.toml を基準にルートを探索）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用）。
   - 必要な環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI を使う場合に指定（AI モジュールで使用）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: {development, paper_trading, live}（デフォルト: development）
     - LOG_LEVEL: {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）

   例 (.env):
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG

## 使い方（簡単なコード例）

- DuckDB 接続を作成して日次 ETL を実行する例:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを算出する（OpenAI API キーが必要）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値: 書き込んだ銘柄数

- 市場レジームをスコアリングする（OpenAI API キーが必要）:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算 / 研究ユーティリティ

  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  forward = calc_forward_returns(conn, date(2026, 3, 20))
  ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")

- 監査ログ DB を初期化する:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます

- カレンダー関連ユーティリティ:

  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  is_trade = is_trading_day(conn, date(2026, 3, 20))
  nxt = next_trading_day(conn, date(2026, 3, 20))

注意:
- AI モジュール（news_nlp / regime_detector）は OpenAI の API キーを environment または引数で渡す必要があります。
- 各関数は look-ahead bias を避けるよう設計されており、内部で現在時刻を参照しません（target_date を明示してください）。

## 設計上の重要ポイント / 実装ノート
- 自動環境読み込み: config モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- 冪等性: DB への保存は基本的に ON CONFLICT DO UPDATE や DELETE→INSERT を用いて冪等に実装されています。
- リトライ / バックオフ: J-Quants / OpenAI 呼び出しは再試行と指数バックオフを備え、429 やネットワークエラーを想定した実装があります。
- セキュリティ: ニュース収集では SSRF 対策、XML 脆弱性対策、受信サイズ制限を実装。
- DuckDB をデータレイクとして使用する想定（ファイルパスは settings.duckdb_path 参照）。

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py                         -- 環境設定・自動 .env ロード
- ai/
  - __init__.py
  - news_nlp.py                     -- ニュースセンチメント算出（OpenAI）
  - regime_detector.py              -- ETF MA200 とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py               -- J-Quants API クライアント（取得＋DuckDB 保存）
  - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
  - etl.py                          -- ETLResult の再エクスポート
  - calendar_management.py          -- マーケットカレンダー管理（営業日判定等）
  - news_collector.py               -- RSS 収集・前処理
  - quality.py                      -- データ品質チェック
  - stats.py                        -- 汎用統計関数（zscore_normalize）
  - audit.py                        -- 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py              -- calc_momentum / calc_value / calc_volatility
  - feature_exploration.py          -- calc_forward_returns / calc_ic / factor_summary / rank
- monitoring/                        -- （存在が想定されるが抜粋コードには詳細なし）
- strategy/                          -- （戦略・シグナル生成。抜粋コードには詳細なし）
- execution/                         -- （発注・ブローカー連携。抜粋コードには詳細なし）

（README にはサブモジュールの主要関数を列挙しました。実際のリポジトリでは他にもモジュールが含まれることがあります。）

## 追加情報 / トラブルシューティング
- 自動 .env 読み込みが動作しない場合:
  - プロジェクトルートの判定は __file__ の親ディレクトリを .git または pyproject.toml で探索します。配布パッケージや別パスで実行する場合は環境変数を直接設定してください。
- OpenAI 呼び出しで JSON parsing エラーが起きた場合:
  - モジュールはフォールバック（default 0.0）で継続する設計ですが、ログを確認してプロンプトや API レスポンスを調査してください。
- DuckDB executemany の空リスト制約:
  - 一部関数は DuckDB 互換性のため executemany に空リストを渡さないガードを入れています。直接 SQL を流用する場合は注意してください。

---

ご要望があれば、以下の追加を作成できます:
- example .env.example のテンプレート
- SQL スキーマ定義（初期化スクリプト）
- 実行用の簡易 CLI / systemd / Airflow 用のジョブ例
- 詳細な API リファレンス（各関数のパラメータ・返り値の例）

必要なものがあれば教えてください。