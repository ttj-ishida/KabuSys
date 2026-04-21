README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究基盤の小規模フレームワークです。本リポジトリは以下の主要機能を提供します。

- 実行コンポーネント（ExecutionEngine）による発注処理とリスク管理
- 監視コンポーネント（MonitoringEngine）によるプロセス・システム状態・注文の継続監視と Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制約等）の純粋関数群
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量解析ユーティリティ
- ニュース NLP / レジーム判定（OpenAI API を利用したセンチメント評価）
- 各種 CLI ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

主な特徴
--------
- 環境別分離:
  - KABUSYS_ENV により development / paper_trading / live を切り替え
  - paper_trading モードは発注をモック化し、DB も data/paper_trading.db に分離
- 監視と安全装置:
  - 定期ポーリングでシステム状態、滞留注文、ドローダウン等を監視
  - 重大リスク発生時に data/kill.flag を作成して ExecutionEngine を安全停止
- ロギング:
  - 統一的な logging 設定（コンソール stdout + 日次ローテーションファイル logs/<app>.log）
- DuckDB / SQLite をデータ層に利用（DuckDB はファクター計算や AI バッチ処理用）
- OpenAI を用いたニュースセンチメントと市場レジーム判定モジュール（API キー必要）
- 純粋関数ベースのポートフォリオ構築ロジック（テストしやすい実装）

準備（セットアップ）
-------------------
1. Python 環境（3.9+ 推奨）を用意します。

2. 必要パッケージをインストールします。最低限必要なライブラリ例:
   - duckdb
   - psutil
   - openai
   - pyyaml（設定検証で YAML 検査を行う場合に必要）

   例:
   pip install duckdb psutil openai pyyaml

   注: 標準ライブラリの sqlite3 は不要な追加インストールは不要です。

3. プロジェクトルートに .env を用意します。対話式ウィザードで作成できます:
   python -m kabusys.config_setup

   ウィザードで設定される主な環境変数:
   - JQUANTS_REFRESH_TOKEN （必須）
   - KABU_API_PASSWORD （必須）
   - KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH （監視 DB、デフォルト: data/monitoring.db）
   - KABUSYS_ENV （development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等

   .env の自動読み込み:
   - OS 環境変数 > .env.local (上書き) > .env（初期ロード）
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. ログ用ディレクトリ:
   デフォルトは logs/。権限や配置を確認してください（setup_logging が自動作成を試みます）。

基本的な使い方
--------------

- 設定検証
  .env や config/*.yaml を起動前にチェックできます。
  python -m kabusys.validate_config
  --strict を付けると警告も失敗として exit(1) します。

- 実行エンジン（ExecutionEngine）起動
  - 本番・ペーパートレード切り替えは KABUSYS_ENV による
  - ペーパートレード時は MockBrokerClient が使われ、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離されます。

  起動:
  python -m kabusys.run_execution

  実行時のポイント:
  - 起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を使用します。
  - data/stop_requested.flag が存在すると起動・継続を停止します。
  - Settings.kill_flag_path（デフォルト data/kill.flag）による Kill Switch の挙動に注意。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除します（本番では推奨しません）。

- 監視ループ（MonitoringEngine）起動
  python -m kabusys.run_monitoring

  実行時のポイント:
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（1 以上の整数）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（環境に依らず同一パス）。
  - データベース接続: SQLite（監視ログ）と DuckDB（分析データ）を使用。
  - 監視が検出したリスクに基づいて kill.flag を書き込み、必要に応じて通知を送信します（AlertManager 実装に依存）。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプションで --db PATH を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を使うこともできます。

設定（Settings）について
-----------------------
設定は kabusys.config.Settings クラスで環境変数をラップしています。主な項目:

- データベース
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用）

- API キー等（必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- AI / LLM
  - OPENAI_API_KEY（news_nlp / regime_detector で使用）

- 監視閾値等
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

.env の読み込み挙動:
- 自動ロードはプロジェクトルート（.git または pyproject.toml を探索して決定）から行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定します。

主要ディレクトリ構成
--------------------
（src/kabusys 以下の主要ファイル・モジュールを抜粋）

- run_monitoring.py
  - MonitoringEngine の起動スクリプト（MONITOR_POLL_INTERVAL でポーリング間隔変更可）
- run_execution.py
  - ExecutionEngine の起動スクリプト（KABUSYS_ENV により paper_trading を分離）
- config.py
  - Settings クラス、.env 自動読み込みロジック、検証ユーティリティ
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前チェック CLI
- utils/
  - logging_setup.py — ロギング設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化 API
  - system_monitor.py — CPU/メモリ/Disk/データ鮮度/プロセス監視
  - trade_monitor.py — （注文ログ等の監視）※実装ファイルあり
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込み・評価
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py — 通知（LINE 等）管理（実装に依存）
- execution/
  - execution_engine.py — ExecutionEngine 本体（発注セッション管理）
  - broker_factory.py — ブローカークライアント生成（Mock/実装切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
- portfolio/
  - portfolio_builder.py — 候補選定、等重/スコア重み
  - position_sizing.py — 株数計算、利用可能資金スケーリング、lot 単位丸め
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value の計算（DuckDB 経由）
  - feature_exploration.py — forward returns, IC 計算 等
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py — ETF MA とマクロニュースでレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

データ・ログ
-----------
- デフォルト DB / ファイルパス:
  - data/kabusys.duckdb (DuckDB)
  - data/monitoring.db (監視ログ SQLite)
  - data/paper_trading.db (ペーパートレード用 SQLite)
  - data/execution.pid (ExecutionEngine PID)
  - data/kill.flag (Kill Switch フラグ)
  - data/stop_requested.flag (手動停止要求フラグ)
- ログ:
  - logs/<app>.log（日次ローテーション、デフォルト 30 日分保持）

注意点 / 運用上のヒント
---------------------
- 本番運用時は KABUSYS_ENV=live とし、.env の機密値を厳格に管理してください（.env を Git にコミットしないでください）。
- Kill Switch（data/kill.flag）は本番で誤って自動クリアされないよう KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。
- Monitoring は Settings.sqlite_path（監視 DB）を本番・開発共通で参照します。monitoring データの分離が必要な場合はパス設定を調整してください。
- OpenAI API を使う機能は API コスト・レート制限を考慮して運用してください。API キーは OPENAI_API_KEY に設定します。
- DuckDB を大量データで使う場合、ファイルパスや権限・バックアップ戦略を検討してください。

コマンド一覧（抜粋）
------------------
- .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視ループ起動:
  python -m kabusys.run_monitoring
  （MONITOR_POLL_INTERVAL 環境変数で秒を指定可）

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  --db PATH で DB 指定可能

ライセンス / バージョン
----------------------
パッケージバージョンは kabusys.__version__ = "0.1.0"。ライセンス情報はリポジトリのトップレベル（LICENSE 等）を参照してください。

さらに詳しい情報
----------------
各モジュールの docstring に設計意図や注意点が記載されています。特に以下のファイルを参照すると実装詳細が分かります。
- src/kabusys/monitoring/*
- src/kabusys/execution/*
- src/kabusys/research/factor_research.py
- src/kabusys/ai/news_nlp.py, src/kabusys/ai/regime_detector.py

問題報告・拡張
--------------
不具合・要望があれば Issue を作成してください。拡張（新しいブローカ実装、通知先追加、研究モジュール追加 等）はモジュールの責務ごとに分離されているため比較的簡単に追加可能です。