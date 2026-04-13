KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした Python パッケージ群です。
このリポジトリには以下の主要機能が実装されています（データ処理、ファクター計算、ポートフォリオ構築、発注・リコンシリエーション、監視・アラート、AI を用いたニュース解析など）。

主な設計方針
- DuckDB（履歴価格・財務データ等）と SQLite（監視ログ・発注ログ等）を組み合わせて使用
- 本番 / ペーパー (paper_trading) / 開発 (development) を環境変数で切り替え
- OpenAI（gpt-4o-mini）を利用したニュースセンチメントや市場レジーム検出機能を提供
- モジュールは可能な限り純粋関数・副作用の分離を意識して実装

機能一覧
---------
- execution
  - ExecutionEngine（発注/セッション実行、RiskManager、OrderManager、Reconciler）
  - ブローカーフェイク（paper_trading 時）と実ブローカーの切り替え
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス・データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、kill.flag の生成
  - AlertManager: LINE push による通知（クールダウン付き）
  - MonitoringEngine: 上の Monitor を束ねるポーリングループ
  - Streamlit ダッシュボード（簡易 UI）
- portfolio
  - 銘柄選定・重み付け（等金額・スコア重み）
  - セクターキャップ適用、レジーム乗数、ポジションサイズ計算（単元株丸め等）
- research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ
- ai
  - news_nlp: raw_news を LLM でスコアリングして ai_scores に書き込む
  - regime_detector: ETF マクロ指標＋LLM を使って日次レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成スクリプト

セットアップ手順
----------------

1. Python 環境準備（推奨: 仮想環境）
   - Python 3.10+ 推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 代表的な必要パッケージ（手動インストール例）:
     - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートの .env 自動読み込み
   - config.Settings モジュールはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 主要ディレクトリ・ファイル（実行前に作成される場合あり）
   - data/kabusys.duckdb （DuckDB、デフォルト: data/kabusys.duckdb）
   - data/monitoring.db （監視用 SQLite、デフォルト: data/monitoring.db）
   - data/paper_trading.db （paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
   - data/execution.pid, data/kill.flag（PID / kill flag）

重要な環境変数（代表）
---------------------
下記は config.Settings から参照する主なキー、デフォルトや説明を併記します。

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - デフォルト: development
  - paper_trading のときはブローカーが Mock に切替え、DB は data/paper_trading.db を使用

- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用トークン（必須）

- KABU_API_PASSWORD
  - kabuステーション API 用パスワード（必須）

- OPENAI_API_KEY
  - OpenAI 呼び出しに必要（ai.news_nlp, ai.regime_detector 等）

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - AlertManager（LINE通知）で使用。いずれか空の場合は通知は送られずログのみ

- SQLITE_PATH
  - 監視 DB のパス、デフォルト: data/monitoring.db

- DUCKDB_PATH
  - DuckDB のパス、デフォルト: data/kabusys.duckdb

- PAPER_TRADING_SQLITE_PATH
  - paper_trading 環境用 SQLite、デフォルト: data/paper_trading.db

- PAPER_FILL_MODE
  - paper_trading 時の mock fill 挙動: instant | partial | never | reject（デフォルト: instant）

- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔(秒)。デフォルト 60。1 未満や無効値は無視されデフォルトを使用

- PID_FILE_PATH / KILL_FLAG_PATH
  - PID ファイル・kill flag のパス（デフォルト: data/execution.pid / data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を削除する挙動が有効になる場合があります

使い方
------

実行系（ExecutionEngine）
- 本番 / ペーパーに応じて DB 切り替えやブローカー選択を行う起動スクリプト:
  - python -m kabusys.run_execution
  - 起動時にプロセス優先度（high）へ変更を試みます（psutil が必要、権限によっては警告が出ます）
  - paper_trading の場合は Settings.env により mock ブローカーを利用し、data/paper_trading.db にアクセスします

監視系（Monitoring）
- 単体の監視ループを起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔 (秒) を上書き可能
  - 監視は Settings にかかわらず（監視データは）本番用 sqlite_path を使用する実装になっています

Streamlit ダッシュボード
- 監視 DB を読んで簡易ダッシュボードを表示:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは読み取り専用で起動（DB が見つからない場合はエラー表示）

Paper Trading 検証レポート
- ペーパー口座の SQLite を読み、指標を集計してテキストレポートを出力:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI 関連
- news_nlp.score_news(target_date) / regime_detector.score_regime(target_date) などの関数は、OpenAI API キー (OPENAI_API_KEY または api_key 引数) が必要
- API 呼び出しはリトライやフェイルセーフを備えていますが、API キー未設定時は ValueError を出します

その他ユーティリティ
- process_priority.set_process_priority(level) など、プロセス優先度や CPU affinity の調整ユーティリティが utils にあります
- 各種モジュールはユニットテストを容易にするため内部関数の差し替えが容易な実装になっています（例: _call_openai_api をモック）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主なファイル・ディレクトリです（抜粋）。

- src/kabusys/
  - __init__.py              -- パッケージメタ情報
  - config.py                -- 環境変数 / 設定読み込み
  - run_execution.py         -- ExecutionEngine 起動スクリプト
  - run_monitoring.py       -- SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  -- Paper Trading レポート生成
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py     -- 市場レジーム判定（ETF MA + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py      -- SQLite テーブル初期化・CRUD ラッパー
    - system_monitor.py     -- CPU/メモリ/ディスク・データ鮮度・PID チェック
    - trade_monitor.py      -- 注文滞留・約定異常検出
    - risk_monitor.py       -- ドローダウン・ポジション制限監視
    - kill_switch.py        -- kill.flag の生成/チェック
    - alert_manager.py      -- LINE 通知（クールダウン）
    - monitoring_engine.py  -- 各 Monitor を束ねた実行エンジン
    - streamlit_dashboard.py-- streamlit ダッシュボード
  - portfolio/
    - __init__.py
    - portfolio_builder.py  -- 銘柄選定・重み付け
    - position_sizing.py    -- 発注株数算出（単元丸め等）
    - risk_adjustment.py    -- セクターキャップ、レジーム乗数
  - research/
    - __init__.py
    - factor_research.py    -- momentum / volatility / value ファクター計算
    - feature_exploration.py-- 将来リターン・IC 計算、統計サマリ
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 execution 系モジュールは発注ロジック、ブローカー抽象等)
  - utils/
    - __init__.py
    - process_priority.py    -- プロセス優先度 / CPU affinity ユーティリティ

注意事項 / トラブルシューティング
--------------------------------
- OpenAI 関連
  - OPENAI_API_KEY が設定されていないと ai.score_news / score_regime は ValueError を投げます。
  - API 呼び出しにはレート制限や一時エラー対策（指数バックオフ）が組み込まれていますが、API コストに注意してください。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等でテーブル作成と簡単なカラム追加を行います。既存 DB に対する互換性保守のため小規模な ALTER が実装されています。

- 権限 / プロセス優先度
  - set_process_priority は psutil を使って優先度を変更します。Linux 等では負の nice 値を設定するため権限（root）が必要になる場合があります。権限不足時は警告ログが出てスキップされます。

- Paper Trading
  - KABUSYS_ENV=paper_trading のときは本番 DB とは分離し data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）を使用します。テスト検証に便利です。

今後の拡張 / 開発メモ
--------------------
- 単元株情報（lot_size）を銘柄マスタ化し銘柄毎に対応する
- position sizing のコスト見積りにより精緻な手数料/スリッページモデルを導入
- AI 部分のモデル切替やロギング強化、推論キャッシュなどの最適化

貢献
----
バグ報告、改善提案、プルリクエスト歓迎します。開発フローに沿って issue を立ててください。

ライセンス
--------
リポジトリ内の LICENSE を参照してください（ここでは明示していません）。

以上。必要であれば各コマンドや設定ファイルの具体例（.env.example）を追記します。