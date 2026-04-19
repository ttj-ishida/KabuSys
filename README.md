# KabuSys

日本株自動売買システムのコアライブラリ群（README）。  
このドキュメントはリポジトリ内の主要スクリプト / モジュールの使い方、セットアップ手順、ディレクトリ構成を日本語でまとめたものです。

注意: 実行には外部パッケージ（duckdb, psutil, openai など）が必要です。requirements.txt がある場合はそれを利用してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買およびそれに付随する監視・リサーチ機能を提供するコードベースです。主な役割は次のとおりです。

- ExecutionEngine：発注ロジック・注文管理・リスク管理（paper_trading モードをサポート）
- Monitoring：システム稼働状況、注文/リスク監視、Kill Switch による自動停止
- Portfolio：銘柄選定、重み付け、ポジションサイズ計算
- Research：ファクター計算・特徴量探索（DuckDB を用いた時系列計算）
- AI：ニュースを LLM（OpenAI）で評価してスコア化する機能
- CLI ツール：.env ウィザード、設定検証、Paper Trading 検証レポート生成など

設計方針の一部：
- Paper Trading（ペーパートレード）時は本番 DB と分離して data/paper_trading.db を使用
- ルックアヘッドバイアスを避けるため、日付・時刻の扱いに注意
- OpenAI 関連処理は失敗してもフェイルセーフ（ゼロやスキップ）で継続

---

## 主な機能一覧

- 実行系
  - ExecutionEngine（発注、OrderManager、RiskManager、Reconciler）
  - BrokerClientFactory により実環境/モックを切替え（KABUSYS_ENV=paper_trading）
- 監視系
  - SystemMonitor：CPU/メモリ/ディスク/プロセスの監視、データ鮮度チェック
  - TradeMonitor：注文滞留・約定異常等の検出（実装ファイル参照）
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch：条件により data/kill.flag を書き込んで ExecutionEngine を停止
  - MonitoringEngine：上記を束ねて定周期ポーリング、アラート発行
- ポートフォリオ構築
  - 候補選定（score/order）・等重/スコア重み付け
  - セクターキャップ適用、レジームによる乗数調整
  - ポジションサイズ計算（ロット丸め、aggregate cap）
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（情報係数）や統計サマリー
- AI
  - news_nlp.score_news：raw_news をまとめて OpenAI に送り銘柄別センチメントを ai_scores に書込
  - regime_detector.score_regime：ETF MA とマクロ記事の LLM 出力を合成して市場レジーム判定
- ツール
  - config_setup.py：.env を対話的に作成/更新するウィザード
  - validate_config.py：環境変数・config/*.yaml 等の検証（--strict オプションあり）
  - tools/paper_verification_report.py：Paper Trading の性能指標を集計してレポート出力

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もし requirements.txt がない場合は少なくとも次を入れてください:
     - duckdb, psutil, openai, PyYAML（config YAML の検証に必要）, pandas 等は任意
     例:
       pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で .env を作成
   - 自動で .env をロードする（デフォルト）仕組みがあります。テストで自動ロードを無効化するには:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ等の初期準備
   - デフォルトの DB / パス（必要に応じて .env で上書き）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - ログディレクトリ: logs/ （LOG_DIR で変更可能）
   - data/ ディレクトリや logs/ は自動作成されますが、権限に注意してください。

---

## 環境変数（主なもの）

必須（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意・設定可能な代表例
- KABUSYS_ENV: execution モード（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、実際のブローカー呼び出しはモックとなり PAPER_TRADING_SQLITE_PATH に記録される
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- LOG_DIR: ログ格納ディレクトリ（デフォルト logs）
- OPENAI_API_KEY: OpenAI API を使う機能（news_nlp, regime_detector）で必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番 LINE 通知用
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60 秒

設定読み込みについて:
- .env と .env.local をプロジェクトルートから自動ロード（OS 環境変数が優先）
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要スクリプト）

全てのスクリプトはパッケージモードで実行できます（推奨）。

- 実行エンジン（Execution）
  - 起動:
    python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
    - 実行中に停止させるには data/stop_requested.flag を作成するとループ内で検知して停止します
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します
    - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）
- 監視（Monitoring）
  - 起動:
    python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視データを記録します
    - 停止は data/stop_requested.flag の存在を検知して終了
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を指定すると警告も失敗扱い（exit code 1）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

プログラム的に利用する関数例:
- ポートフォリオ生成:
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
- リサーチ:
  from kabusys.research import calc_momentum, calc_volatility, calc_value
- AI:
  from kabusys.ai import score_news  (実行には OpenAI API キーが必要)

ログ:
- デフォルトはコンソール + 日次ローテートファイル logs/<app_name>.log（30日保持）
- ログ設定は kabusys.utils.logging_setup.setup_logging を使って統一されます
- LOG_DIR 環境変数でログ保存先を変更可能

停止フラグ:
- run_execution / run_monitoring が監視する停止フラグ: data/stop_requested.flag
- KillSwitch が書き込む停止フラグ（ExecutionEngine を停止させるためのフラグ）: data/kill.flag
  - KillSwitch はリスク閾値（ドローダウン等）到達時に書き込みます

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・ディレクトリの構成（抜粋）です。実際のリポジトリに合わせて調整してください。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメントの LLM スコアリング
    - regime_detector.py     — レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成 + 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信の実装）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                    — 実行時に生成されることが多い（DB, flag, pid など）
  - logs/                    — ログファイル（デフォルト）

---

## 追加の注意点 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください（validate_config で警告が出ます）。
- .env ファイルは絶対に Git にコミットしないでください（config_setup.py の生成コメントあり）。
- OpenAI を利用する機能は API コストが発生します。API キーの管理、レート制限に注意してください。
- Paper Trading を使うときは PAPER_TRADING_SQLITE_PATH を確認して、本番 DB と完全に分離されていることを確認してください。
- ログディレクトリ・data ディレクトリの権限／容量管理を行ってください（DuckDB や SQLite はファイルサイズが大きくなる可能性があります）。
- psutil を利用する処理で権限不足の警告が出る場合は実行ユーザの権限を確認してください。process priority / cpu affinity は OS により動作が異なります。

---

もし README に追記したい詳細（例: 実際の設定例 .env、commands の systemd ユニット例、より詳しいアーキテクチャ図など）があれば教えてください。必要に応じて追加でセクションを作成します。