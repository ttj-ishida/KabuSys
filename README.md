# KabuSys

日本株自動売買システムのサブセット実装リポジトリ（ドキュメント用・学習用）。  
本リポジトリには、実行エンジンの起動スクリプト、監視コンポーネント、ポートフォリオ構築・ポジションサイジング関数、リサーチ用ファクター計算、AI を用いたニュース NLP / レジーム判定、各種ユーティリティや CLI ツールが含まれます。

以下はこのコードベースの README です。

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件 / 依存関係
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数一覧（主要）
- 停止・Kill スイッチ
- ディレクトリ構成（主要ファイル説明）

プロジェクト概要
- 目的：日本株向けの自動売買システムのコアロジック群（発注エンジン、監視、リサーチ、ポートフォリオ構築、AI ベースのニュース解析）をモジュール化して実装。
- 設計思想：DB はファイルベース（SQLite / DuckDB）。AI 呼び出しは OpenAI クライアントをラップして使う。プロダクション・ペーパー環境を分離し安全性を保つ設計。

主な機能一覧
- Execution 起動スクリプト（run_execution.py）
  - 実際の発注ロジックを起動するためのラッパー。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に分離して記録。
  - スレッドで ExecutionEngine を実行し、stop flag を監視して安全停止。
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングし system_status / risk_logs / trade_logs / dashboard 等を更新。
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御可能（デフォルト 60 秒）。
- 監視コンポーネント（monitoring/*）
  - SystemMonitor: プロセス稼働状況、データ鮮度、CPU/メモリ/ディスク監視。
  - TradeMonitor: 注文の滞留チェック、約定価格の異常検知。
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ記録。
  - MonitoringDB: SQLite を用いた永続化層（テーブル初期化、マイグレーション含む）。
  - KillSwitch / AlertManager: リスク閾値到達時に kill.flag を書き ExecutionEngine を停止させる仕組み（アラート通知は LINE 等に接続可能）。
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等重・スコア重み計算、セクター上限適用、ポジションサイズ計算（単元丸め・利用可能資金キャップの調整）等の純粋関数群。
- リサーチ（research/*）
  - DuckDB を利用したファクター計算（モメンタム、ボラティリティ、バリュー等）と将来リターン / IC 計算機能。
- AI モジュール（ai/*）
  - news_nlp: raw_news を集約し OpenAI（gpt-4o-mini）でセンチメントを計算、ai_scores に書き込む。
  - regime_detector: ETF（1321）の MA200 とマクロニュースセンチメントを合成して market_regime を算出・保存。
- CLI ユーティリティ
  - config_setup.py: .env の対話式ウィザード（初期設定支援）。
  - validate_config.py: 環境変数・config/*.yaml の整合チェック。
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを出力。

必要条件 / 依存関係
- Python 3.10+（型ヒントに | を使用しているため）
- 必須（主に実行時）:
  - duckdb
  - psutil
  - openai
- 推奨 / オプション:
  - PyYAML（config/*.yaml の検証を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib, os 等

セットアップ手順（開発環境向け）
1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone <repo> && cd <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - pip install duckdb psutil openai
   - （PyYAML を入れる場合）pip install pyyaml

4. data ディレクトリを作成（DB / PID / flag 用）
   - mkdir -p data

5. 環境変数設定
   - 対話式で .env を作成する: python -m kabusys.config_setup
   - または .env を手動で作成（README 下の「環境変数一覧」を参照）

6. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict

使い方（主要コマンド例）
- ExecutionEngine を起動する
  - python -m kabusys.run_execution
    - KABUSYS_ENV が paper_trading の場合、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い、MockBrokerClient により発注のテストが可能。
    - 実行中は data/execution.pid に PID が書かれる想定（Settings.pid_file_path）。

- Monitoring を起動する
  - MONITOR_POLL_INTERVAL を指定して起動（秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルト間隔は 60 秒。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path（Settings.sqlite_path）を参照して監視ログを記録します。

- .env の対話式セットアップ
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）になります。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - DB パスはデフォルトで data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- AI 系処理（プログラム的に呼び出し）
  - OpenAI API キーを指定（環境変数 OPENAI_API_KEY か引数で渡す）
  - 例（ニュース NLP を直接呼ぶ場合）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")

環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 推奨 / 既定値あり:
  - KABUSYS_ENV — 実行環境（development / paper_trading / live） default=development
  - DUCKDB_PATH — DuckDB ファイルパス（default=data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（default=data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（default=data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...） default=INFO
  - OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知（任意）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
  - PAPER_FILL_MODE — ペーパートレードの fill モード（instant / partial / never / reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- その他:
  - PID_FILE_PATH, KILL_FLAG_PATH などは Settings クラスで default 値が設定されています。

サンプル .env（抜粋）
- .env は Git に含めないでください（機密情報を含みます）。
- 例:
  JQUANTS_REFRESH_TOKEN=your_jquants_token
  KABU_API_PASSWORD=your_kabu_password
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO

停止・Kill スイッチ
- run_execution / run_monitoring の両スクリプトはプロジェクトルートの data/stop_requested.flag を監視しており、存在するとメインループを安全に終了します。
- KillSwitch による自動停止は data/kill.flag を生成して ExecutionEngine に停止を指示します。kill.flag は明示的に削除しない限り残ります（KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で消される設定あり）。
- 手動停止の例:
  - 監視プロセスを止める (簡易): touch data/stop_requested.flag
  - ExecutionEngine に停止指示を出す（手動）: echo "reason" > data/kill.flag

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — Settings クラス、.env 自動読み込みロジック、環境変数検証ユーティリティ
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（PID / stop flag 管理）
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ（psutil）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義 / Migration / DB 操作ラッパー
    - system_monitor.py — CPU/メモリ/Disk/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留 / 価格異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の書き込み / クリア
    - monitoring_engine.py — 各モニタをまとめてポーリング（run / run_once）
    - alert_manager.py — （アラート送信の抽象、実装はプロジェクト次第）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（等重・スコア重み）
    - position_sizing.py — 株数計算（risk_based 等）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム／バリュー／ボラティリティの計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースを集約して OpenAI でセンチメント算出、ai_scores 書き込み
    - regime_detector.py — MA200 とマクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード DB から検証レポート生成

補足 / 注意事項
- DB（DuckDB / SQLite）はファイルベースです。バックアップ・永続化の運用は利用者側で管理してください。
- .env には機密情報が含まれるため絶対にリポジトリへコミットしないでください（config_setup の出力にも注意喚起があります）。
- AI モジュールは OpenAI API を利用します。API キー・レート制限・コスト管理に注意してください。エラー時はフェイルセーフとして処理をスキップする実装になっていますが、運用方針を検討してください。
- run_monitoring は監視用 DB（Settings.sqlite_path）を参照します。monitoring の性質上、本番 DB を利用する設計になっていますので扱いに注意してください（paper_trading 時の ExecutionEngine DB は分離されています）。

問題や拡張
- alert_manager の具体的な通知実装（LINE / Slack 等）はプロジェクトごとに実装する必要があります。
- 戦略 / 実行エンジンの詳細（ExecutionEngine, BrokerClientFactory 等）は本 README の対象コードに依存します。実運用時はブローカ接続や注文リスクロジックの更なる監査が必要です。

以上がこのコードベースの概要および使い方です。必要があればサンプル .env の完全版、systemd / supervisor 用のサービス例、または各モジュールの詳細ドキュメント（API / 入出力仕様）を追補します。どのドキュメントが欲しいか教えてください。