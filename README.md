# KabuSys

日本株向け自動売買システムのコードベースです。戦略・ポートフォリオ構築・発注エンジン・監視・リサーチ・AI（ニュースNLP / レジーム判定）などを含むモジュール群を収録しています。

この README は開発者向けに、プロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するライブラリ兼起動スクリプト群です。主なコンポーネントは以下の通りです。

- ExecutionEngine（発注エンジン） — ブローカークライアントを通じて注文を発行・管理。ペーパートレードモードをサポート。
- Monitoring（監視） — システム状態、注文・約定ログ、リスク（ドローダウン・ポジション数）を監視し、Kill Switch による強制停止やアラートを発行。
- Portfolio / Strategy utilities — 候補選定、重み計算、ポジションサイズ決定、セクター制約などの純粋関数群。
- Research（ファクター計算・特徴量探索） — DuckDB の市場データを用いたファクター計算・IC 解析等。
- AI（ニュースNLP / レジーム判定） — OpenAI を用いたニュースセンチメント評価とレジーム判定（OpenAI API は任意）。
- Tools — Paper Trading 検証レポート生成ツール等。
- ユーティリティ — ロギング設定、プロセス優先度設定、設定読み込みウィザード・検証等。

データ永続化は分析用に DuckDB、監視/注文履歴用に SQLite を利用します。

---

## 機能一覧

- 起動スクリプト
  - run_execution: 発注エンジンを起動。KABUSYS_ENV により paper_trading（Mock）/ live の挙動を切替。
  - run_monitoring: SystemMonitor をポーリングして監視ログを記録（MONITOR_POLL_INTERVAL 環境変数で間隔設定）。
- 設定管理
  - config_setup: .env を対話式に生成・更新するウィザード。
  - validate_config: .env や config/*.yaml の設定チェック CLI。
  - Settings クラスにより環境変数をアプリ側で参照。
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor：各種監視チェックと MonitoringDB への永続化。
  - KillSwitch：条件達成時に data/kill.flag を書き込み Execution を停止させる仕組み。
  - MonitoringEngine：複数 Monitor を束ねたポーリング実行。
- 発注関連
  - BrokerClientFactory：環境に応じたブローカークライアント（実取引 or Mock）を作成。
  - ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager：発注・リスク管理の実装。
- ポートフォリオ構築
  - 候補選定、等分配・スコア加重、リスク調整（セクター上限）、ポジションサイズ計算（lot 単位丸め・aggregate cap）
- リサーチ
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 将来リターン計算、IC 計算、ファクターの統計サマリー
- AI
  - news_nlp.score_news: raw_news を OpenAI に送り銘柄別センチメントを ai_scores に格納
  - regime_detector.score_regime: ETF MA とマクロニュースセンチメントを合成して市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポートを生成（稼働率・成功率・レイテンシ等）

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主要な依存パッケージ（機能に応じて任意）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config で YAML 検証を行う場合）

（requirements.txt はプロジェクトに応じて用意してください。例: pip install duckdb psutil openai pyyaml）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil
   - OpenAI を使う場合: pip install openai
   - validate_config の YAML 検証を有効にする場合: pip install pyyaml
4. 必要なディレクトリを作成（.env ウィザードが作るが手動でも）
   - mkdir -p data logs
5. 環境変数（.env）設定
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合: OPENAI_API_KEY
   - KABUSYS_ENV: development | paper_trading | live
   - DUCKDB_PATH, SQLITE_PATH などはデフォルトあり
6. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

注意:
- paper_trading モードでは発注は MockBrokerClient により data/paper_trading.db に記録され、本番 DB（monitoring.db 等）とは分離されます。
- .env は絶対にリポジトリにコミットしないでください。

---

## 使い方（代表的なコマンド）

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し data/paper_trading.db に記録されます。
  - 起動時、data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に停止したい場合は data/stop_requested.flag を作成するとエンジンに停止シグナルを送れます（スクリプトはフラグ検知で停止します）。

- Monitoring 起動（継続ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用して monitoring DB を更新します（環境に関わらず）。
  - 停止は data/stop_requested.flag を作成（または Ctrl+C）で行います。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- プログラム的に利用
  - ライブラリ関数はパッケージとしてインポートして利用可能です。例:
    - from kabusys.research import calc_momentum
    - from kabusys.ai import score_news
    - from kabusys.portfolio import calc_position_sizes

---

## 重要な環境変数（一部）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (デフォルト: logs)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔、秒。デフォルト 60)

---

## 停止・Kill Switch の挙動

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py はこのファイルの存在を監視しており、存在すれば起動を停止または実行中に終了処理を行います。
- data/kill.flag
  - KillSwitch により書き込まれることで ExecutionEngine 停止のトリガーになります（リスク閾値到達時など）。
  - KillSwitch は既にフラグがある場合は再書き込みを行わず冪等動作になります。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では推奨しません）。

---

## ログ

- ロギングは kabusys.utils.logging_setup.setup_logging を通じて初期化されます。
- 出力先:
  - コンソール（stdout）
  - ファイル（logs/<app_name>.log、日次ローテーション、30日保持）
- ログレベルは引数・環境変数 LOG_LEVEL で制御します。

---

## ディレクトリ構成（概観）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み取り / Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計
    - __init__.py
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄センチメント
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（テーブル初期化・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文系監視（約定・滞留チェック）※長大なファイルあり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート通知機構（LINE 等、実装に依存）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（セッション起動・注文処理）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注関連
  - data/ — （実行時に生成される可能性のあるディレクトリ）
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag, stop_requested.flag, execution.pid などのフラグ / PID ファイル

---

## 開発上の注意点 / ベストプラクティス

- .env ファイルは決してリポジトリにコミットしないでください（config_setup のヘッダーにも注意書きあり）。
- 本番（live）モードに切り替える前に validate_config で警告・必須設定を確認してください。
- OpenAI を使う機能は外部 API に依存し、失敗時はフェイルセーフ（スコア 0.0 など）で継続する設計ですが、API キーの漏えいに注意してください。
- paper_trading モードは本番 DB と分離されるためテスト時は paper_trading を推奨します。
- ログや DB のパスは環境変数で変更可能です（DUCKDB_PATH, SQLITE_PATH など）。

---

必要であれば、README に以下を追加できます：
- 具体的な .env のサンプル（機密情報はマスク）
- docker-compose / systemd ユニットのサンプル（本番運用）
- よくあるトラブルシューティング（ログ出力先・権限問題・psutil の権限エラー等）

追加してほしい項目があれば教えてください。