KabuSys
======

日本株自動売買システム（ライブラリ / 実行スクリプト群）のリポジトリです。
本 README はコードベース（src/kabusys/...）に基づいて作成しています。

概要
----
KabuSys は日本株向けの自動売買フレームワークです。  
主な責務は以下の通りです。

- 戦略・ファクター計算（DuckDB を利用した履歴価格・財務データ解析）
- ポートフォリオ構築（銘柄選定・重み算出・ポジションサイジング）
- Execution（発注エンジン／ブローカークライアントを抽象化）
- 監視（プロセス・システム状態・注文・リスク監視）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定）
- ペーパートレード検証レポート生成

設計上のポイント
- DuckDB（分析用）と SQLite（監視・トレース用）を併用
- Paper Trading（KABUSYS_ENV=paper_trading）は本番発注を行わず、専用 SQLite に記録して本番 DB と分離
- .env を用いた環境変数管理（config_setup.py による対話式生成）
- ログは stdout と日次ローテートファイルに出力（logs/<app>.log）
- OpenAI（gpt-4o-mini 等）を用いるモジュールは API キーが必要（失敗時はフェイルセーフ）

主な機能一覧
----------------
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading で MockBroker を使用、data/paper_trading.db に記録
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は環境に関わらず本番 sqlite_path を使用（監視 DB を分離しない運用想定）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.news_nlp.score_news — ニュースを LLM でスコアリングして ai_scores テーブルへ保存
  - kabusys.ai.regime_detector.score_regime — マクロ + ma200 で市場レジームを判定して保存
- ポートフォリオ構築:
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - apply_sector_cap / calc_regime_multiplier（リスク調整）
- 監視:
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - KillSwitch によるフラグファイル（data/kill.flag）を書き込んで ExecutionEngine を停止する仕組み
- ユーティリティ:
  - ログ設定（kabusys.utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（kabusys.utils.process_priority）

セットアップ手順
----------------
以下は一般的なローカルセットアップ手順です。

1. Python 環境
   - 推奨: Python 3.10+（コードは型ヒント / モダンな構文を利用）
   - 仮想環境を作成・有効化（venv / pyenv 等を利用）

2. 必要パッケージのインストール
   - 必要な外部パッケージ（少なくとも）:
     - duckdb
     - psutil
     - openai（AI 機能を利用する場合）
     - PyYAML（validate_config の YAML 検証に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （パッケージ管理ファイル requirements.txt があればそれを利用してください）

3. ディレクトリ準備
   - data/ および logs/ は自動作成されることが多いですが、手動で作る場合:
     - mkdir -p data logs

4. 環境変数設定 (.env)
   - 対話式に .env を作る:
     - python -m kabusys.config_setup
   - もしくは直接 .env を作成（.env は Git にコミットしないでください）
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 便利な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading の DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LOG_LEVEL, LOG_DIR
     - MONITOR_POLL_INTERVAL（監視スクリプト用、秒）
     - PAPER_FILL_MODE（paper_trading の fill モード: instant | partial | never | reject）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラーとして扱います

使い方（実行例）
----------------
- 環境セット:
  - export $(cat .env | xargs)  # 環境に応じて読み込み方法は任意
  - あるいは個別に export KABUSYS_ENV=paper_trading 等

- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - paper_trading モード:
    - export KABUSYS_ENV=paper_trading
    - run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30

- 監視／実行停止方法:
  - run_execution / run_monitoring は data/stop_requested.flag の存在を見て終了します
  - システム側で KillSwitch がトリガーした場合は data/kill.flag が作成され、ExecutionEngine 起動時に検出できます
  - ExecutionEngine は起動時に pid ファイル（data/execution.pid 等）を扱います

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能）

- AI / レジーム判定:
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime は OpenAI API キーが必要です
  - 直接呼び出す際は OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、関数引数で渡します

設定ファイルと .env の自動読み込み
----------------
- config_setup.py で .env を対話的に生成できます
- config.py はプロジェクトルート（.git または pyproject.toml を基準）を自動検出して .env/.env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- validate_config.py は .env と config/*.yaml の整合性チェックを提供します（PyYAML がインストールされていれば YAML のパースチェックも行います）

重要な動作上の注意
----------------
- 監視（run_monitoring）は「環境にかかわらず」Settings.sqlite_path（本番の monitoring.db）を使用する設計です。運用時は監視 DB の扱いに注意してください。
- paper_trading モードは本番発注とデータベースを分離する意図で実装されていますが、運用前に validate_config で設定を確認してください。
- AI 機能は外部 API を使用するため API 利用制限や料金が発生します。API キーは安全に管理してください。
- ログディレクトリ作成に失敗するとファイル出力はスキップされ、コンソールのみの出力になります（warnings が出ます）。LOG_DIR 環境変数で出力先を変更できます。
- process priority / CPU affinity の設定は実行環境（OS）や権限に依存します。権限が不足すると警告が出てスキップされます。

ディレクトリ構成（主要ファイル）
----------------
（src/kabusys 配下の主なモジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env 作成ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート
    - ai/
      - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
      - regime_detector.py     — レジーム判定（ma200 + マクロセンチメント）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - monitoring/
      - monitoring_db.py       — SQLite テーブル初期化 / 永続層
      - system_monitor.py
      - trade_monitor.py       — （trade_monitor の実装がある想定）
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py       — （alert_manager の実装がある想定）
    - utils/
      - logging_setup.py
      - process_priority.py
    - execution/                — ExecutionEngine 周り（ブローカーファクトリ等）
    - data/                     — データパイプライン / stats（DuckDB 参照系）
    - research/                 — 解析用モジュール等

（注）上記には実装ファイルの一部を抜粋しています。実際のファイル一覧はリポジトリの src/kabusys 以下を参照してください。

サンプル .env（生成される内容の例）
----------------
下記は config_setup によって書き出される .env の主要項目です（秘密値は伏せてください）。

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

開発・運用に関する補足
----------------
- validate_config を起動前に必ず実行して、必須変数・パス・YAML 設定を確認することを推奨します。
- 本番環境（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN/LINE_USER_ID）や Kill Switch の設定に特に注意してください。
- DB スキーマのマイグレーションは monitoring_db.init_monitoring_db 内で簡易的に行われます（既存カラムがない場合は ALTER を実行）。

ライセンス・貢献
----------------
- このリポジトリのライセンス情報・コントリビュート方針はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

質問・トラブルシュート
----------------
- 依存パッケージの import エラー（例: duckdb、psutil、openai、yaml）は pip で該当パッケージをインストールしてください。
- ログファイルが作成されない場合は LOG_DIR 環境変数とデータディレクトリのパーミッションを確認してください。
- OpenAI API 呼び出しで頻繁に失敗する場合、API キー・レート制限・ネットワークを確認し、モジュールのログを参照してください。

以上がこのコードベースの概要・セットアップ・使い方・ディレクトリ説明です。必要であれば、特定モジュールの詳細なドキュメント（関数シグネチャ・返り値・サンプルコード）を別途作成します。どの部分を詳細化しましょうか？