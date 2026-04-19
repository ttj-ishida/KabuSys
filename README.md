KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買/リサーチ/監視コンポーネント群を含む Python パッケージです。  
本 README はコードベース（src/kabusys）に基づく概要・機能・セットアップ・使い方・ディレクトリ構成を説明します。

プロジェクト概要
---------------
KabuSys は以下の役割を持つモジュールで構成されています。

- ExecutionEngine（発注エンジン）: 実際の発注あるいはペーパートレードを行う
- Monitoring（監視）: システム状態、注文状態、リスクを定期監視しアラートや Kill Switch を発動
- Portfolio / Strategy / Research: 銘柄選定、配分、ファクター計算、特徴量分析
- AI モジュール: ニュースの NLP スコアリングや市場レジーム判定（OpenAI 使用）
- ユーティリティ: ロギング設定、プロセス優先度設定、環境設定ウィザード/検証ツール 等
- Tools: ペーパートレード検証レポート等の CLI スクリプト

主要な設計方針
- 本番とペーパートレードの DB を分離（KABUSYS_ENV により切替）
- ルックアヘッドバイアス防止（date/time の扱いに注意）
- フェイルセーフ設計（API 失敗時はフォールバック動作）
- ロギングと日次ローテートで運用の可視性を確保

主な機能一覧
----------------
- 実行/発注
  - ExecutionEngine（run_execution.py をエントリポイントに起動）
  - BrokerClientFactory により本番ブローカー or MockBroker（ペーパートレード）を選択
  - リスクマネージャ（ポジション上限、利用率等）による発注制御
- 監視
  - SystemMonitor: CPU/Mem/Disk、Execution プロセス生存、データ鮮度を監視
  - TradeMonitor: 注文の滞留・約定異常などを検出
  - RiskMonitor: ドローダウン、ポジション上限を監視し dashboard を更新
  - MonitoringEngine: 上記をまとめてポーリング・アラート送信・Kill Switch 評価
- データ永続化
  - SQLite（monitoring.db / paper_trading.db）: 監視ログ・トレードログ・ポジション等
  - DuckDB（kabusys.duckdb）: 価格やファクター計算用の分析 DB
- リサーチ
  - ファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC 計算、統計サマリー
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重配分、リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数
- AI（OpenAI）
  - news_nlp: ニュースを LLM でセンチメント化し ai_scores に保存
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して日次レジーム判定
- CLI / ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

必要な環境変数（主なもの）
-------------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨/任意:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録
  - live: 本番動作（注意して設定）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパー用 DB）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: AI 機能を使う場合に必要
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

セットアップ手順
----------------
1. リポジトリをクローンして Python 環境を準備
   - Python 3.10+ を推奨
   - 仮想環境を作成して activate する

2. 依存ライブラリをインストール
   - 主要なライブラリ例:
     - duckdb
     - psutil
     - openai（AI 機能使用時）
     - PyYAML（validate_config の YAML 検証を行う場合）
   - 例: pip install -r requirements.txt （requirements.txt がある場合）

3. 環境変数設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参照）
   - 重要: .env は Git にコミットしないこと

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合は --strict を付ける

5. データディレクトリの作成（必要に応じて）
   - data/ logs/ などは起動時に自動作成されることが多いが、権限等で失敗する場合があるため手動で作ると安全

使い方（起動・操作）
-------------------

基本的な起動方法（モジュールとして実行）:

- 監視ループを起動（MONITOR_POLL_INTERVAL で間隔を指定可能）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔（秒）を上書き可能
  - 監視は常に settings.sqlite_path（監視 DB）を使用

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し PAPER_TRADING_SQLITE_PATH に出力
  - 起動時に data/stop_requested.flag が存在すると起動を中止
  - 実行中は PID ファイル（data/execution.pid）を作成

- Paper Trading 検証レポート（CSV ではなくターミナル出力）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH (PAPER_TRADING_SQLITE_PATH を上書き)

停止・Kill フラグ
- 手動でエンジンを停止したい場合はプロジェクトルートの data/stop_requested.flag を作成すると run_monitoring / run_execution のループを検知して安全に終了します。
- Kill Switch（監視が条件を満たすと）data/kill.flag を書き込み、ExecutionEngine にストップシグナルを送る仕組みがあります。KILL_FLAG_CLEAR_ON_START=1 を有効にすると起動時に自動クリアされますが、本番では推奨されません。

ログ
- 共通ロギングユーティリティを用いて stdout と日次ローテートログ（logs/<app_name>.log）へ出力します。
- LOG_DIR 環境変数でログ保存先を指定可能。デフォルトは logs/

AI 機能について
- OpenAI を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。
- API の呼び出しはリトライ・バックオフを行いフェイルセーフ設計がなされていますが、API キー・料金に注意してください。

開発時の注意点
- Settings は .env や環境変数から自動的に読み込みます（プロジェクトルートに .env/.env.local がある場合）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です（テスト等で使用）。
- validate_config により起動前に設定漏れや危険設定（live モード）を検出できます。
- DuckDB / SQLite のパスは Settings で指定され、デフォルトは data/ 以下です。バックアップやアクセス権に注意してください。

ディレクトリ構成（src/kabusys の主要ファイル）
----------------------------------------------
以下はパッケージ内の主要モジュールと簡単な説明です（省略表記あり）。

- __init__.py
  - パッケージ定義、バージョン

- config.py
  - Settings クラス（環境変数/.env 読み込み・検証）

- config_setup.py
  - .env 対話式ウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（スレッド起動、PID 管理、stop flag チェック）

- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL で制御）

- utils/
  - logging_setup.py — 共通のログ設定（stdout + 日次ファイルローテーション）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite のテーブル作成・読み書きラッパー
  - system_monitor.py — CPU/Mem/Disk・データ鮮度・プロセス検出
  - trade_monitor.py — （注文監視ロジック）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の書込判定
  - monitoring_engine.py — 複数監視を束ねるエンジン
  - alert_manager.py — （アラート送信管理：LINE 等に送る実装が想定される）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注・注文管理・リスク制御の実装群

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（単元株丸め・aggregate cap）
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン、IC、統計サマリー

- ai/
  - news_nlp.py — ニュースを LLM でスコア化して ai_scores テーブルへ保存
  - regime_detector.py — MA200 とマクロニュースを合成してレジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成 CLI

例: よく使うコマンド
--------------------
- .env を作る（対話式ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視プロセス起動
  - MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
- 実行エンジン起動（ペーパートレードで起動する例）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- ペーパートレードレポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足 / 運用ヒント
-----------------
- 本番環境（KABUSYS_ENV=live）では LINE 通知の設定や kill_flag の取り扱いを必ず確認してください。
- logs/ と data/ は運用ユーザーが書き込みできるように権限を整えておくこと。
- OpenAI を運用で使う場合はレート制限やコスト、API エラー時の挙動を事前に確認してください。
- DB スキーマ変更（マイグレーション）は monitoring_db.init_monitoring_db 内で一部自動対応していますが、慎重な運用が必要です。

ライセンス・貢献
----------------
- 本 README はコード内容に基づく説明です。実際のライセンスや貢献ガイドラインはリポジトリ内の LICENSE / CONTRIBUTING 等のファイルを参照してください。

この README で不明点があれば、どの部分（起動方法、設定項目、監視/実行の挙動、AI 周りなど）を詳しく知りたいか教えてください。必要に応じてサンプル .env、運用手順書（runbook）や systemd / supervisor による起動例も作成できます。