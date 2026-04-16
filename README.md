KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／検証／監視を目的とした Python ベースのプロジェクトです。
主要コンポーネントは実行エンジン（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築・サイズ計算、リサーチ（ファクター算出）、
およびニュース（LLM）を用いたセンチメント評価です。設計は本番/ペーパートレードの分離、DB永続化（SQLite / DuckDB）、
フェイルセーフ（ロールバック・リトライ・フラグファイル）を重視しています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / paper_trading を区別し、paper_trading 時は MockBrokerClient を利用して専用 SQLite（data/paper_trading.db）に記録
  - 起動時に Reconciler による自動復旧・リコンシリエーションを実行
  - プロセス優先度を設定し PID ファイル管理、停止フラグ検出で安全に停止

- MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor
  - CPU / メモリ / ディスク / プロセス生存チェック、価格データ鮮度チェック
  - 注文滞留、約定異常価格の検出
  - ドローダウン・ポジション上限の監視と kill.flag による自動停止トリガー
  - 監視ログは SQLite（デフォルト data/monitoring.db）に永続化
  - streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）

- Portfolio モジュール
  - 候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）：リスクベース・等分配方式、単元株丸め、aggregate cap 対応
  - セクターキャップ適用・レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- Research モジュール
  - ファクター算出（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）計算、特徴量統計サマリ

- AI 関連
  - ニュースを LLM（OpenAI）で評価して ai_scores に書き込む news_nlp.score_news
  - マクロニュース + ETF MA を使った市場レジーム判定 regime_detector.score_regime
  - OpenAI API（gpt-4o-mini 等）を利用。API キーは環境変数または引数で与える

- ツール
  - paper_trading の検証レポート生成ツール（kabusys.tools.paper_verification_report）

セットアップ
-----------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   (例)
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

2. 必要パッケージをインストールします（プロジェクトに requirements.txt があればそれを利用してください）。
   代表的な依存:
   - psutil
   - duckdb
   - openai
   - requests
   - streamlit
   例:
   pip install psutil duckdb openai requests streamlit

3. 環境変数の設定
   - プロジェクトルートの .env / .env.local が自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
   - 任意（デフォルトがあるもの）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | ... （デフォルト: INFO）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - PAPER_FILL_MODE: instant | partial | never | reject （ペーパー約定挙動、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - SQLITE_PATH: data/monitoring.db（監視ログ DB）
     - DUCKDB_PATH: data/kabusys.duckdb（リサーチ用時系列 DB）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（監視・停止に使うパス）

   サンプル .env（最小）
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development

4. データディレクトリの作成（必要に応じて）
   mkdir -p data

使い方
------
実行エンジン（本番 / ペーパー）
- run_execution.py を直接実行:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB（デフォルト data/paper_trading.db）へ記録し MockBrokerClient を使用します。
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - 停止は data/stop_requested.flag を作成することで安全に行えます。

監視ループ（SystemMonitor 単体）
- run_monitoring.py を実行:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用し、KABUSYS_ENV に依らず本番 DB パスを参照します。
  - 停止は data/stop_requested.flag を作成することで行います。

監視ダッシュボード（Streamlit）
- streamlit を使って起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB の読み取りは読み取り専用 URI を使います。MonitoringEngine が監視データを書き込んでいることを確認してください。

Paper Trading 検証レポート
- 以下でレポートを標準出力に表示:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで paper_trading DB を指定できます（デフォルト: data/paper_trading.db）

AI（ニューススコア / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - api_key を None にすると環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に OPENAI_API_KEY が必要（または引数で指定）。

停止・Kill フラグ
- ExecutionEngine の停止リクエスト:
  - KillSwitch はリスク条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促します（ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START 設定を参照してクリアすることができます）。
  - 明示的に停止したい場合は data/stop_requested.flag を作成してください（run_execution/run_monitoring はこれを検知して停止します）。

設定（Settings の主要項目）
- Settings クラスで環境変数をラップしています。主なプロパティ:
  - env: KABUSYS_ENV（development | paper_trading | live）
  - sqlite_path: SQLITE_PATH（デフォルト data/monitoring.db）
  - duckdb_path: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - paper_sqlite_path: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
  - paper_fill_mode: PAPER_FILL_MODE（instant|partial|never|reject）
  - pid_file_path / kill_flag_path / CPU/MEM/DISK 閾値 等

開発・テスト向け
- .env / .env.local が自動ロードされます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 一部の外部 API 呼び出し（OpenAI 等）はユニットテストでモックされるよう設計されています（内部の _call_openai_api 等をパッチする）。

ディレクトリ構成
----------------
（省略せず主要ファイルを列挙）

src/
  kabusys/
    __init__.py                # パッケージ定義
    config.py                  # 環境変数 / Settings
    run_execution.py           # ExecutionEngine 起動スクリプト
    run_monitoring.py          # SystemMonitor 単体ポーリングスクリプト

    ai/
      __init__.py
      news_nlp.py              # ニュース NLP スコアリング（OpenAI）
      regime_detector.py       # 市場レジーム判定（ETF MA + マクロセンチメント）

    monitoring/
      __init__.py
      monitoring_db.py         # SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      system_monitor.py        # システム状態・データ鮮度監視
      trade_monitor.py         # 注文滞留 / 約定異常監視
      risk_monitor.py          # ドローダウン / ポジション上限チェック
      kill_switch.py           # kill.flag 制御
      alert_manager.py         # LINE 通知
      monitoring_engine.py     # 複数 Monitor を束ねるエンジン
      streamlit_dashboard.py   # Streamlit ダッシュボード

    execution/
      order_manager.py         # 発注フロー制御
      order_repository.py      # Orders DB アクセス（SQLite）
      reconciler.py            # 起動時リコンシリエーション
      broker_factory.py        # ブローカークライアント生成（Mock 実装含む）
      ...                      # 他ブローカー/API 関連

    portfolio/
      portfolio_builder.py     # 候補選定・重み計算
      position_sizing.py       # 株数決定・リスク制限
      risk_adjustment.py       # セクターキャップ・レジーム乗数
      __init__.py

    research/
      factor_research.py       # ファクター計算 (momentum, volatility, value)
      feature_exploration.py   # 将来リターン, IC, 統計サマリ
      __init__.py

    tools/
      __init__.py
      paper_verification_report.py  # Paper Trading 検証レポート生成

    utils/
      __init__.py
      process_priority.py      # プロセス優先度 / CPU affinity ユーティリティ

注意事項・運用メモ
-----------------
- DB マイグレーション:
  monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に不足カラムがあれば簡易マイグレーションを行います。
- Process 優先度:
  run_execution/run_monitoring は起動時に set_process_priority("high") を呼びます（psutil による設定。権限に依存）。
- Paper Trading:
  ペーパートレード実行時は完全に別 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- OpenAI API:
  API 呼び出しはリトライやフェイルセーフ（失敗時はスコア 0.0、または処理スキップ）を備えていますが、API キーの取り扱いには注意してください。
- Alerts:
  AlertManager は LINE Messaging API を利用します。channel_access_token / user_id が未設定の場合は送信せずログに出力します。
- 停止管理:
  デーモン的に運用する場合は data/stop_requested.flag を作成して安全に停止するワークフローを用意してください。

ライセンス・貢献
----------------
- 本 README ではライセンス情報は含めていません。実際のリポジトリに LICENSE ファイルを追加してください。
- バグ・改善提案は Issue / Pull Request でお願いします。

以上が KabuSys の概要・セットアップ・使い方の簡易ドキュメントです。必要であれば各モジュールの API リファレンス（関数引数や戻り値の詳細）、運用手順（systemd ユニットの例、ログローテーション、バックアップ方針）などを追記します。どの情報を詳細化しましょうか？