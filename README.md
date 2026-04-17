README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。価格データや財務データを DuckDB で分析し、シグナル生成・ポートフォリオ構築・発注実行・監視・アラートを行うためのモジュール群を提供します。設計方針として本番とペーパー（模擬売買）を明確に分離し、監視・Kill Switch、ログ永続化（SQLite）や外部LLM（OpenAI）によるニュース解析などを備えています。

主な特徴
--------
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 発注実行エンジン（実ブローカー／Mock ブローカーを環境で切替）
- 監視サブシステム（システム状態、注文滞留、リスク監視、Kill Switch）
- DuckDB を用いたファクター計算・リサーチ（モメンタム、ボラティリティ、バリューなど）
- ニュースNLP（OpenAI を用いたセンチメントスコアリング）
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザード（.env 作成）と設定検証 CLI

前提 / 依存関係
---------------
推奨手順で仮想環境を利用してください。主要な Python パッケージ（抜粋）:
- python >= 3.9
- duckdb
- psutil
- openai
- requests
- PyYAML （config 検証で YAML 検査を行う場合）
その他、パッケージはプロジェクトで管理してください（requirements.txt を用意する場合はそこからインストールします）。

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（例）:
   - pip install duckdb psutil openai requests PyYAML

3. .env を作成します（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   ウィザードは .env をプロジェクトルートに作成・更新します。必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   注意: .env は機密情報を含むため、絶対に Git にコミットしないでください。

4. 設定検証:
   - python -m kabusys.validate_config
   --strict オプションで警告も失敗扱いにできます。

5. データディレクトリと DB:
   - デフォルトでは data/kabusys.duckdb（DuckDB）、data/monitoring.db（SQLite）。
   - 必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を上書き。

使い方
------

環境変数のポイント
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録されます（本番 DB と分離）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env ファイルをロードしません（テスト等で使用）。
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト 60。無効値は無視されデフォルトにフォールバックします。
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant / partial / never / reject）
- KILL_FLAG_* / PID 関連:
  - デフォルトの kill.flag: data/kill.flag（Settings.kill_flag_path）
  - 起動時に kill_flag_clear_on_startを1にすると起動時に kill.flag を自動クリア（本番では推奨しない）

主要スクリプト / コマンド
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper_trading 専用 DB を使用し、MockBrokerClient で動作します。
  - 実行中の停止は data/stop_requested.flag（プロジェクトの data 配下）を作成すると検知して終了します。
  - 実行中は data/execution.pid に PID が書かれます。

- 監視ループ起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を指定可能（秒、デフォルト 60）
  - 監視は本番 sqlite_path を環境に関わらず使用します（monitoring 用 DB の永続化は共通）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB は --db オプションか環境変数 PAPER_TRADING_SQLITE_PATH、なければ data/paper_trading.db を使用

ライブラリ / API の使い方（一部）
- DuckDB 接続を使う研究関数:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb")
  - res = calc_momentum(conn, date(2026,4,1))
- ニュース NLP / レジーム判定（OpenAI が必要）:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="sk-...")
  - OpenAI API エラー時はフェイルセーフで継続する設計ですが、APIキーは必須（引数 or OPENAI_API_KEY 環境変数）
- 監視 API（プログラム埋め込み用）
  - MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, AlertManager 等を組み合わせてユニットテストやカスタム監視ループを構築できます。

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では LINE のトークン・ユーザー ID を設定しておくこと（アラート用）。
- .env に機密情報を保存する場合はアクセス制限・秘密管理に注意してください。
- Kill Switch（kill.flag）や stop flag（data/stop_requested.flag）の動作を理解した上で運用してください。KILL_FLAG_CLEAR_ON_START=1 は本番では推奨しません（Kill Switch が自動クリアされるため危険）。
- DuckDB / SQLite のファイルパスは .env で設定可能。バックアップや同時アクセスに注意してください。

ディレクトリ構成
----------------
（抜粋。src/kabusys をルートとする主要ファイル／パッケージの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings クラス（.env, .env.local のロード、KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート）
  - config_setup.py
    - .env を対話的に作成・更新するウィザード
  - validate_config.py
    - 起動前に env / config/*.yaml 等の妥当性を検証する CLI
  - run_execution.py
    - ExecutionEngine の起動スクリプト（paper_trading 時は MockBroker を使用）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度や CPU affinity の設定ユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定、等重／スコア重み計算
    - position_sizing.py — 株数（ロット）計算、資金配分、スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite 管理（初期化、CRUD ユーティリティ）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor の束ね
    - alert_manager.py — LINE 通知（push）ユーティリティ
    - kill_switch.py — Kill Switch（kill.flag）管理
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
    - 発注ロジック・ブローカラッパー（BrokerClientFactory で実ブローカー or Mock を生成）
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリューの計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - ai/
    - news_nlp.py — OpenAI を使ったニュースセンチメントのスコアリング
    - regime_detector.py — ma200 + マクロセンチメントを使った市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成スクリプト

補足（よくある質問）
-------------------
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に対する一部カラム追加（マイグレーション）を行います。
- ログレベル:
  - LOG_LEVEL 環境変数で設定可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- テスト:
  - 各モジュールは純粋関数とクラスに分かれており、ユニットテストが書きやすい設計です。外部 API 呼び出しはモック可能な設計（関数を patch して差し替え）になっています。

最小の .env の例
-----------------
（対話ウィザード使用を推奨します。機密情報は伏せる）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

問い合わせ / 変更履歴
--------------------
- バージョン: 0.1.0 (src/kabusys/__init__.py)
- 変更やバグ修正の提案はリポジトリの Issue / Pull Request を通してください。

以上。運用・カスタマイズにあたっては特に .env の管理と Kill Switch / stop flag の運用ルールを必ず確認してください。