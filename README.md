README
======

概要
----
KabuSys は日本株の自動売買および研究用ツール群を提供するプロジェクトです。  
このリポジトリには、注文実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI を用いたセンチメント評価）など、実運用・ペーパートレード・研究のための主要コンポーネントが含まれます。

主な特徴
--------
- ExecutionEngine：実際の発注（kabuステーション API）またはペーパートレード用の MockBroker を使った発注処理。
- Monitoring：CPU/メモリ/ディスク・プロセス生存確認・注文ログなどをポーリングして SQLite に記録。Kill Switch によるエンジン停止。
- Portfolio construction：候補選定、重み計算、ポジションサイジング、セクターキャップやレジームによる調整等の純粋関数実装。
- Research：DuckDB を用いたファクター計算（Momentum/Value/Volatility 等）および特徴量解析ユーティリティ（IC 計算等）。
- AI モジュール：OpenAI（gpt-4o-mini 想定）を使ったニュースセンチメント評価（ai_scores / market_regime 登録）。
- ユーティリティ：.env 対話式ウィザード（config_setup）、設定検証ツール（validate_config）、Paper Trading 検証レポート（tools/paper_verification_report）等。
- ロギング：統一された logging セットアップ（標準出力 + 日次ローテートファイル）。

必要条件（想定）
----------------
- Python 3.9+
- パッケージ（主な例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合）
- ネットワークアクセス（kabuステーション API / OpenAI を使う場合）
- SQLite（標準ライブラリで十分）

セットアップ手順
----------------
1. リポジトリをクローンし仮想環境を作成：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）：
   - pip install duckdb psutil openai PyYAML
   - 実運用では requirements.txt / Poetry 等で依存管理してください。

3. 初期設定（.env）を作成：
   - 対話式ウィザードを使う（推奨）：
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で .env を作成。
   - 重要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 環境選択:
     - KABUSYS_ENV=development | paper_trading | live
       - paper_trading: ペーパートレード用の MockBroker を使用（data/paper_trading.db に記録）
       - live: 実運用（kabu API 有効）

4. 設定検証（起動前チェック）：
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

5. データ・ログ用ディレクトリの確認：
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb  (環境変数: DUCKDB_PATH)
     - SQLite (monitoring): data/monitoring.db (環境変数: SQLITE_PATH)
     - Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
     - ログディレクトリ: logs/ (環境変数: LOG_DIR)
     - PID / Kill flag 等: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要に応じて親ディレクトリを作成してください（logging_setup は自動作成を試みます）。

使い方（主要コマンド）
--------------------

- 環境ウィザード（.env の生成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告を FAIL とする）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパーどちらも .env の KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
    - 起動時に data/stop_requested.flag があると起動をせず終了します。
    - 実行中、同フラグが作成されるとエンジンが停止します。
    - PID ファイルは data/execution.pid（Settings.pid_file_path で変更可）に書き込まれます。

- Monitoring を起動（ポーリング監視ループ）:
  - python -m kabusys.run_monitoring
  - オプション（環境変数）:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を参照します（監視 DB は共通に記録）。
  - 停止は data/stop_requested.flag を作成する、もしくは Ctrl+C。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パス指定:
    - --db PATH
    - 環境変数 PAPER_TRADING_SQLITE_PATH が優先

- AI（ニュース NLP / レジーム判定）
  - ニューススコアリング（ai_scores 書き込み）： kabusys.ai.news_nlp.score_news をスクリプトから呼ぶ
    - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定
  - レジーム判定（market_regime 書き込み）： kabusys.ai.regime_detector.score_regime
    - 同様に OPENAI_API_KEY を設定
  - CLI エントリは組まれていないため、必要に応じて小さなラッパースクリプトを作成してください。

重要な運用挙動
----------------
- Kill Switch / 停止フラグ:
  - KillSwitch はリスク条件（ドローダウンやポジション上限）に応じて data/kill.flag を書き込みます。ExecutionEngine は起動時・実行中にこのフラグをチェックして停止します。
  - run_* スクリプトは data/stop_requested.flag を使用して外部からの停止要求（監視やデプロイツールから）を受け付けます。
  - Settings で KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- DB 分離（本番 vs ペーパー）:
  - ExecutionEngine は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（既定: data/paper_trading.db）へ記録して本番 DB と完全分離します。Monitoring は環境に依らず本番 sqlite_path を使用する設計上の注意点があります（設定で変更可）。

- ロギング:
  - 共通の setup_logging() を使い、コンソール出力と日次ローテートファイル出力を行います。ログディレクトリは LOG_DIR 環境変数で変更可能。失敗時は標準出力のみ出力されます。

ディレクトリ構成（抜粋）
------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／Settings 管理（自動 .env ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・簡易永続化 API
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（存在）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 複数モニタを束ねる（ポーリング）
    - alert_manager.py       — 通知管理（LINE など、存在）
  - execution/
    - execution_engine.py    — 実行エンジン（EngineConfig, run_session 等）
    - broker_factory.py      — ブローカークライアント生成（実口座 / Mock）
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
    - news_nlp.py            — ニュース NLP（OpenAI でスコア生成）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py    — psutil を使った優先度/affinity 設定

設計上の注意点
---------------
- ルックアヘッド防止:
  - AI / レジーム / リサーチ系モジュールは date や時刻の扱いでルックアヘッドバイアスを防ぐ設計になっています（内部で date.today() を参照しない・クエリに排他条件を使う等）。
- フェイルセーフ:
  - OpenAI API 呼び出しや外部リソース故障時はリトライやフォールバック（スコア 0.0 等）を行い、処理がシステム全体を停止させないようになっています。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は既存 DB に対する簡易マイグレーション（カラム追加等）を行います。

開発・運用のヒント
------------------
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。
- ローカル開発では KABUSYS_ENV=development を使用してください（発注しない安全モード）。
- Paper Trading を使うときは PAPER_FILL_MODE（instant/partial/never/reject）で約定挙動を調整できます。
- Logging の詳細を上げるには LOG_LEVEL=DEBUG を .env に設定します。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス表記はリポジトリのルートにある LICENSE 等を参照してください（本リポジトリに含まれる場合）。

付録：よく使うサンプルコマンド
------------------------------
- .env を対話式で作る:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート（過去期間）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上を参考に、まずは .env を整えて validate_config -> run_monitoring（監視） -> run_execution（エンジン） の順で試してみてください。必要があれば README を拡張して具体的なデプロイ手順や systemd / supervisor 用のユニット例などを追加できます。