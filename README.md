# KabuSys — README (日本語)

概要
----
KabuSys は日本株の自動売買・リサーチ・監視のためのモジュール群です。  
主な機能は戦略に基づくポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ（DuckDB ベースのファクター計算）、および OpenAI を用いたニュース NLP / レジーム判定です。  
設計方針としては「テストしやすい純粋関数」「DB と発注系の明確な分離」「ルックアヘッドバイアス対策」「フェイルセーフ（API失敗時は安全なフォールバック）」を重視しています。

主な特徴
--------
- ポートフォリオ構築
  - 候補選定、等分配 / スコア加重配分、リスクベースのポジションサイズ算出
  - セクターキャップ、レジームに応じた資金乗数
- 発注エンジン（Execution）
  - Live / Paper trading 切替（paper_trading 時は MockBrokerClient を使用）
  - 発注履歴や取引ログを SQLite に永続化
- 監視（Monitoring）
  - システム稼働状況（CPU/MEM/DISK/プロセス）とデータ鮮度の監視
  - 注文・約定・リスクイベントの監視と Kill Switch（停止フラグ）発動
  - アラート送信（LINE 等、設定がある場合）
- 研究（Research）
  - DuckDB 上で Momentum / Volatility / Value ファクターや将来リターン、IC などを計算
- AI モジュール
  - ニュースを OpenAI（gpt-4o-mini）でスコア化して ai_scores に書き込み
  - マクロニュース + ma200 乖離を組み合わせた市場レジーム判定
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

前提・必要環境
--------------
- Python 3.10+（typing の | 記法などを使用）
- 標準ライブラリ: sqlite3, logging, threading, etc.
- 推奨外部ライブラリ（機能に応じて必要）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の構文チェック用、任意）

インストール（例）
-----------------
1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール（最低限）:
   - pip install duckdb psutil openai

   YAML 検証を行う場合:
   - pip install pyyaml

（プロジェクトに requirements.txt がない場合は上記を参照してインストールしてください）

初期設定
--------
- .env の作成:
  - 対話式ウィザードで .env を生成できます:
    - python -m kabusys.config_setup
  - 主要な環境変数（例）:
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - OPENAI_API_KEY: OpenAI を利用する場合
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
    - LOG_LEVEL（DEBUG/INFO/…）
    - KILL_FLAG_CLEAR_ON_START（0/1）
    - PAPER_FILL_MODE（paper_trading 用: instant | partial | never | reject）

- 自動 .env 読み込み:
  - Settings モジュールはプロジェクトルート（.git または pyproject.toml を探索）から .env を自動読み込みします。
  - 無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設定検証
-------
- .env や config/*.yaml の検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

主要コマンド / 使い方
--------------------

- 実行エンジン起動（ExecutionEngine）:
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存します:
    - paper_trading: MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
    - live: 実際に発注が行われます（設定の確認を厳重に行ってください）
  - 停止方法:
    - エンジンは data/stop_requested.flag の存在を検出すると停止します（または Kill Switch が data/kill.flag を書き込みます）。
    - 起動時に stop flag が既に存在する場合は起動を中止します。

- 監視ループ起動（SystemMonitor の簡易起動）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は Settings.sqlite_path（monitoring DB）を使用します（環境にかかわらず本番 sqlite_path を参照）

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数での指定も可）

- 設定ウィザード:
  - python -m kabusys.config_setup

- その他ユーティリティ:
  - ai.score_news / ai.score_regime 等の関数は DuckDB 接続と日付を渡してプログラム内から呼び出します。
  - OpenAI を利用する機能は OPENAI_API_KEY を必要とします。API エラー時はフェイルセーフの挙動（0.0 など）で継続する設計です。

重要なファイル/フラグ
-------------------
- data/stop_requested.flag
  - 実行中の run_execution/run_monitoring が停止ループの検出対象とするフラグファイル
- data/kill.flag
  - KillSwitch により作成され、ExecutionEngine に停止要求を通知
- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db

注意事項 / 運用メモ
------------------
- 本番運用（KABUSYS_ENV=live）の場合は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG の扱いを慎重に設定してください。
- KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険（Kill Switch を自動でクリアしてしまうため）。
- .env は Git にコミットしないでください（config_setup のヘッダにも同様の注意喚起があります）。
- ログ設定:
  - logs/<app_name>.log に日次ローテーションで出力（デフォルト logs ディレクトリ、30日保管）
  - コンソール出力は stdout を使用します
- DuckDB / SQLite のスキーマはコード中の初期化関数（monitoring_db.init_monitoring_db 等）で自動作成・マイグレーションされます。
- OpenAI API 呼び出しはリトライやバックオフを取り入れていますが、料金やレート制限に注意してください。

ディレクトリ構成
----------------
（抜粋: src/kabusys ツリー）
- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - execution/                — 発注関連（broker, engine, order_manager 等）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルの要約です。実際のコードベースにはさらに多くのモジュールが含まれます。）

簡単な例: 実運用の流れ
-------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定を検証（python -m kabusys.validate_config）
3. （必要なら）データベース / ログディレクトリを作成
4. 監視を起動（python -m kabusys.run_monitoring）
5. 実行エンジンを起動（python -m kabusys.run_execution）
6. 監視が異常を検出すると data/kill.flag を作成 → ExecutionEngine が停止

サンプル .env（最小）
-------------------
例:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献ルールを記載してください）

補足
----
- コード内ドキュメント（docstring）は意図や設計上の注意点を多く含んでいます。実装や運用にあたっては docstring を参照してください。
- DuckDB / SQLite のテーブルスキーマや挙動は各モジュール（monitoring_db, ai.news_nlp, research.*）にコメントで詳述されています。

質問や README に追加してほしい内容があれば教えてください。