KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。  
本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理の実行
- 監視（Monitoring）: システム稼働状況・注文/リスク状況のポーリングとアラート
- ポートフォリオ構築ユーティリティ: 候補選定・重み付け・株数計算・セクター制限
- リサーチ / ファクター計算: Momentum/Volatility/Value 等の因子計算と探索
- AI モジュール: ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）
- ユーティリティ: 環境設定ウィザード、設定検証、Paper Trading 検証レポート等

主な特徴
--------
- 実運用を意識した設計（.env ベースの設定、監視用 DB、kill switch）
- Paper Trading 環境の明確な分離（専用 SQLite を使用）
- DuckDB を使った分析 / リサーチワークフロー
- OpenAI を用いたニュースセンチメント / レジーム判定（オプション）
- ログは stdout と日次ローテートファイルに出力（logs/*.log）

前提 / 必要パッケージ
--------------------
- Python 3.9+
- 必要（推奨）ライブラリ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config ファイルの構文チェックを行う場合）
- 標準ライブラリ: sqlite3, logging, argparse など

インストール例（仮想環境）
-----------------------
1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
2. 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

注意: requirements.txt は本リポジトリに含まれていないため、用途に応じてパッケージを追加してください。

設定（.env）
------------
プロジェクトルートに .env を置くことで環境変数を自動ロードします（.env.local があれば上書き）。  
自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能利用時に必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（0/1、デフォルト: 0。本番では 0 推奨）
- PAPER_FILL_MODE（paper_trading の注文約定挙動: instant/partial/never/reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）

.env 作成支援
--------------
対話式ウィザードで .env を作成する:
- python -m kabusys.config_setup

設定検証
--------
起動前に設定チェックを実行:
- python -m kabusys.validate_config
オプション --strict を付けると警告もエラー扱いになります。

起動・使い方
------------

1. 監視ループ（Monitoring）
   - 目的: システム状態（CPU/MEM/DISK）や注文状況、リスクを定期的にチェックしログ・アラート・kill switch を評価する。
   - 起動:
     - python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
     - 監視 DB は settings.sqlite_path（環境にかかわらず本番 sqlite_path を使用）。
     - 終了は data/stop_requested.flag ファイルを作成することでループが検知して終了します（または Ctrl+C）。

2. 実行エンジン（ExecutionEngine）
   - 目的: 発注処理・オーダー管理・リスク管理を担当するエンジンを起動する。
   - 起動:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録します。
     - 実行中は data/execution.pid に PID が書かれます。data/stop_requested.flag の存在で停止をトリガーします。
     - Execution 側の停止命令（外部トリガー）は kill.flag（Settings.kill_flag_path）を使います（KillSwitch により書き込まれる）.

3. Paper Trading 検証レポート
   - 目的: ペーパートレード履歴から稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL を判定
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 日付指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

4. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY）。
   - 提供関数:
     - kabusys.ai.score_news(conn, target_date, api_key=None)  — raw_news を読み ai_scores に書き込む
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime を計算して書き込む
   - 実行時は DuckDB 接続を渡して関数を呼び出します。API 呼び出しは内部でリトライやフェイルセーフを備えています。

停止 / Kill フラグ
------------------
- data/stop_requested.flag: run_monitoring/run_execution のループを止めるための外部フラグ（手動で作成）。
- data/kill.flag: KillSwitch が条件を満たしたときに書き込むファイル。ExecutionEngine 側はこれを検出して安全に停止します。
- KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では危険なためデフォルトは 0）。

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging() で統一的に設定されます。
- stdout（StreamHandler）と 日次ローテートファイル（logs/<app_name>.log）に出力します。
- ログ出力先ディレクトリが作成できない場合はコンソールのみで継続します。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 配下の主要ファイル / ディレクトリ構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite ベースの永続化層
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — 注文監視（ファイルに含まれる設計と組み合わせ）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （アラート送信等。コード中に参照あり）
  - execution/
    - execution_engine.py     — 実行エンジン（EngineConfig / run_session 等）
    - broker_factory.py       — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - tools/
    - paper_verification_report.py

設計上の注意点 / 運用メモ
-----------------------
- .env は決してリポジトリにコミットしないでください（config_setup に警告あり）。
- KABUSYS_ENV が live の場合は特に注意が必要（validate_config で警告が出ます）。
- Paper Trading は production DB と完全に分離する設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 等の外部 API 呼び出しはフェイルセーフ（タイムアウト・5xx 等は既定のフォールバックやリトライ）を備えていますが、API キー/課金等に注意してください。
- ログディレクトリ作成やプロセス優先度設定は OS 権限に依存します。アクセス拒否時は警告が出て処理は続行します。

よく使うコマンド例
-----------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視開始:
  - python -m kabusys.run_monitoring
- 実行エンジン開始:
  - python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ / 貢献
-----------------
設計や実装に関する改善提案、バグ報告、機能追加は Issue / PR でお願いします。README の補足や不足する運用手順があれば反映します。

以上で README の概要です。必要があれば「サンプル .env のテンプレート」や「各 CLI の詳細なオプション一覧」を追記します。どの情報を優先で追加しますか？