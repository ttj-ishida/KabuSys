KabuSys — 日本株自動売買システム
================================

簡潔な紹介
----------
KabuSys は日本株向けの自動売買フレームワーク（分析・ポートフォリオ構築・発注・監視・AI 補助）です。
このリポジトリは、取引実行エンジン（ExecutionEngine）と監視サブシステム、ファクター計算／リサーチ用モジュール、AI を使ったニュースセンチメント評価などの主要コンポーネントを含みます。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - リスク管理（最大ポジション比率、資金利用率、ドローダウン等）
  - Order 管理・リコンシリエーション
- Monitoring（監視）
  - システム状態（CPU / メモリ / ディスク）・データ鮮度監視
  - 注文ログの監視（滞留注文、約定異常など）
  - リスク監視（ドローダウン、保有上限）
  - Kill Switch（条件を満たすと ExecutionEngine に停止シグナル）
  - 監視情報は SQLite に永続化
- Portfolio Construction（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重、ポジションサイズ算出（単元株丸め含む）
  - セクターキャップ、レジームによる乗数適用
- Research（研究用）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI（OpenAI を利用）
  - ニュースの NLP センチメント評価（ai_scores への格納）
  - 市場レジーム判定（ETF / マクロニュース合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト

セットアップ手順
----------------
1. Python 環境を用意
   - 推奨: Python 3.10+
   - 仮想環境を使うことを推奨します（venv, pyenv 等）

2. 依存パッケージをインストール
   - 必須ライブラリの例:
     - duckdb
     - psutil
     - openai
     - sqlite3（標準ライブラリ）
     - （オプション）PyYAML（config 検証で YAML の構文チェックをする場合）
   - 例:
     python -m pip install duckdb psutil openai pyyaml

   ※ requirements.txt がある場合はそれを使用してください（本リポジトリにない場合は上記パッケージを参照）。

3. .env を作成
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に直接作成
   - 主要な環境変数（必須 / デフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - PAPER_FILL_MODE — デフォルト: instant（有効値: instant|partial|never|reject）
     - OPENAI_API_KEY — AI 機能を使う場合に必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
     - KILL_FLAG_CLEAR_ON_START — デフォルト 0（本番では 0 を推奨）

4. 設定検証（起動前チェック）
   - 簡易チェック:
     python -m kabusys.validate_config
   - 警告も失敗扱いにする（CI 等）:
     python -m kabusys.validate_config --strict

使い方
------
- 監視プロセス起動
  - run_monitoring は SystemMonitor をポーリングして監視を行います。
  - 起動（デフォルトポーリング間隔 60 秒）:
    python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止:
    - プロセスを Ctrl+C（KeyboardInterrupt）
    - もしくはプロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。
  - 注意: run_monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用します（監視 DB として）。

- 実行エンジン起動
  - run_execution は ExecutionEngine を起動します。
  - 起動:
    python -m kabusys.run_execution
  - Paper Trading:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ※ paper_trading の場合、MockBrokerClient を使用し paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 停止:
    - stop flag（data/stop_requested.flag）で実行中のエンジン停止を指示
    - kill.flag（Settings.kill_flag_path）を書き込むと ExecutionEngine に対する停止シグナル（Kill Switch）として機能します
  - 実行中はプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid 等）を管理します。

- Paper Trading 検証レポート
  - data/paper_trading.db を参照して簡易レポートを生成:
    python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能
  - ニューススコアリング / レジーム判定は OPENAI_API_KEY が必要
  - ai モジュールは OpenAI API を呼び出すため、API Key の準備と料金に注意してください。

停止・Kill の仕組み
------------------
- stop_requested.flag
  - run_monitoring / run_execution のループはプロジェクトルート/data/stop_requested.flag を監視します。
  - このファイルを作成すると、次のポーリングサイクルで安全に終了します（Graceful shutdown）。
- kill.flag
  - KillSwitch が作動すると Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込み、ExecutionEngine 停止を促します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では危険なため注意）。

ログ
----
- ログはデフォルトで logs/ ディレクトリに出力されます（アプリごとに logs/<app_name>.log）。
- ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で指定可能。
- 既にログハンドラが設定されている場合は一旦クリアして再設定する仕様です（多重出力防止）。
- TimedRotatingFileHandler による日次ローテーション（30日保持）。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定管理（自動 .env ロード）
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_monitoring.py         — 監視ループ起動スクリプト
- run_execution.py          — 実行エンジン起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py      — レジーム判定（MA + マクロニュース）
- monitoring/
  - monitoring_db.py        — 監視用 SQLite の初期化・永続化 API
  - system_monitor.py       — システム状態 / データ鮮度監視
  - trade_monitor.py        — 注文ログ監視（滞留・レイテンシ等）
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — Kill Switch 書き込みロジック
  - monitoring_engine.py    — 各 Monitor をまとめて実行
  - alert_manager.py        — 通知管理（LINE 等、実装による）
- execution/
  - execution_engine.py     — ExecutionEngine 本体
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py        — ロギング設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py

（上記は主要ファイル。実際のツリーはプロジェクトルートの src/kabusys/ 以下を参照してください）

注意事項 / 運用上のヒント
------------------------
- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください（validate_config は警告も表示します）。
- kill.flag / stop flag の運用を間違えると意図せず停止するため、本番では自動クリア設定は無効（0）にしておくことを推奨します。
- Paper Trading は本番 DB と完全分離されていますが、パスを誤るとデータ混在する可能性があるため環境変数を明示して運用してください。
- AI（OpenAI）を利用する機能は外部 API 呼び出しおよびコストが発生します。レート制限やエラーに対するリトライ・フォールバックが組み込まれていますが、実運用時は API キー管理と利用量の監視をしてください。
- DuckDB は分析用途のデータ格納に使われます。データファイル（デフォルト data/kabusys.duckdb）をバックアップすることを推奨します。

開発 / テスト
--------------
- モジュールには多くの純粋関数（Portfolio / Research 等）があり、ユニットテストしやすい設計になっています。
- OpenAI クライアント呼び出しは個別関数（_call_openai_api 等）に分離されているため、テスト時には patch / mock が可能です。

サンプルコマンドまとめ
---------------------
- .env 作成（ウィザード）:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
- 監視起動:
  python -m kabusys.run_monitoring
- 実行エンジン起動:
  python -m kabusys.run_execution
- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
（この README にはライセンス情報は含まれていません。リポジトリの LICENSE ファイルを参照してください。）

補足
----
詳細な設計やアルゴリズムの説明（ポートフォリオ構築方針、StrategyModel、PortfolioConstruction 等）はリポジトリ内のドキュメント（例えば PortfolioConstruction.md や StrategyModel.md）を参照してください（存在する場合）。

以上。必要であれば、README に入れる具体的な .env のテンプレートやシステム図、デプロイ手順（systemd / Docker / supervisor など）を追加で作成します。どの形式がよいか指示ください。