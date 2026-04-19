# KabuSys

日本株向けの自動売買 / 研究フレームワーク（KabuSys）のリポジトリ向け README。  
このドキュメントはリポジトリ内の主要モジュール群と実行方法、環境設定の手順をまとめたものです。

注意: 実行前に必ず .env を適切に設定し、`python -m kabusys.validate_config` で設定検証してください。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムの基盤ライブラリです。主な機能は次の通りです。

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper/live 切替対応）
- 監視（Monitoring）: システム状態、注文状態、リスク監視、Kill Switch の運用
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算・リスク調整）
- リサーチ機能（ファクター計算・将来リターン・IC計算など）、DuckDB を用いた分析
- AI 補助（OpenAI を用いたニュースセンチメント、レジーム判定）
- ペーパートレード用の検証ツール（検証レポート生成）

設計方針として、ルックアヘッドバイアスを避ける設計、フェイルセーフ（API失敗やデータ欠損時は安全側にフォールバック）を重視しています。

---

## 主な機能一覧

- 実行系
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV に応じて paper_trading（MockBroker）/live を切り替え。stop フラグ検出で安全停止。
- 監視系
  - run_monitoring.py: SystemMonitor（CPU / メモリ / ディスク / プロセス監視）を定期実行し、監視ログを SQLite に保存。MONITOR_POLL_INTERVAL で間隔変更可。
  - MonitoringEngine: System / Trade / Risk モニタを束ね、アラート送信・KillSwitch 評価を行う。
  - KillSwitch: リスク条件（ドローダウン・ポジション上限等）に応じて data/kill.flag を書き込み Execution を停止させる。
- モジュール群
  - portfolio: 候補選定、等重・スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数。
  - research: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）、前方リターン・IC・統計サマリなど。
  - ai: OpenAI を呼ぶニュース NLP（news_nlp）、市場レジーム判定（regime_detector）。
  - monitoring: 監視 DB 層（monitoring_db）、各種モニタ実装（system_monitor, trade_monitor, risk_monitor）とアラート管理。
  - utils: ロギング設定、プロセス優先度 / CPU affinity 設定などのユーティリティ。
- ツール
  - config_setup.py: 対話式 .env 設定ウィザード（初期作成・更新）。
  - validate_config.py: .env や config/*.yaml の基本チェックを行う CLI。
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポートを生成。

---

## セットアップ手順

前提: Python 3.9+（コードの typing による型注釈等を想定）。環境に応じて仮想環境を作成してください。

1. リポジトリをクローン / 配置
   - 仮にプロジェクトルートに配置されている前提です（`.git` または `pyproject.toml` がルートとして検出されます）。

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - 追加（開発 / オプション）
     - pip install PyYAML

   ※ requirements.txt がない場合は上記を参考に。実行する機能により依存パッケージが異なります（AI 系は openai、YAML 検証は PyYAML 等）。

4. 環境変数 / .env の設定
   - 推奨: python -m kabusys.config_setup を実行して対話的に .env を作成。
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合は:
     - OPENAI_API_KEY
   - 主要な既定値（参考）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - KABUSYS_ENV: development | paper_trading | live
     - LOG_LEVEL: INFO

   .env の自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

5. 設定検証
   - python -m kabusys.validate_config
   - 必要なら --strict を付けて警告も fail として扱う。

---

## 使い方（実行例）

- .env の作成（推奨）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - エラーがあれば修正して再実行

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path（SQLITE_PATH 環境変数）を使用します（環境に依存せず監視 DB は本番 DB を参照）。

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が用いられ、Paper DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 系（ニューススコア / レジーム判定）はプログラム的に呼び出すか、適切な runner を用意して実行してください（OPENAI_API_KEY 必須）。

停止方法:
- 停止フラグ: run_monitoring / run_execution はプロジェクトの data/stop_requested.flag を検出すると安全停止します（`data/stop_requested.flag` を作成）。
- Kill Switch: KillSwitch が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込み ExecutionEngine に停止シグナルを発行します。

ログ:
- ログは stdout と logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリが作れない場合はコンソールのみ）。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用・挙動制御:
- KABUSYS_ENV — 実行環境（development | paper_trading | live） (default: development)
  - paper_trading: ブローカーは Mock、DBは PAPER_TRADING_SQLITE_PATH を使用
  - live: 実際に発注されます（注意して設定）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログファイルの出力先（デフォルト logs/）

DB 関連:
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（default: data/paper_trading.db）

監視 / 実行制御:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- PID_FILE_PATH — 実行エンジンの pid ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch が書き込むパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1"=クリア）

AI / 外部 API:
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp, ai.regime_detector など）
- PAPER_FILL_MODE — paper_trading 時の約定モード（instant|partial|never|reject）

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を指定すると .env の自動読み込みを無効化

（validate_config.py に一覧と一部チェックロジックがあります。詳細はその実装を参照してください）

---

## ディレクトリ構成（主なファイルと説明）

以下は src/kabusys 以下の主要ファイル／モジュールの一覧と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、__version__
  - config.py — 環境変数 / 設定管理（Settings クラス）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- src/kabusys/execution/  (Execution 系: broker, engine, order 管理)
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - （Execution の中核実装。ブローカー抽象化・リスク制御等）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite を用いた監視ログ永続化層（初期化・マイグレーション含む）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 発注 / 約定に関する監視（滞留注文・約定異常など）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイルを書いて実行停止を指示
  - monitoring_engine.py — 各 Monitor を束ね実行するエンジン
  - alert_manager.py — （アラート送信の抽象化、実装が含まれる想定）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み付け関数
  - position_sizing.py — 単元丸め・リスクベースの株数決定ロジック
  - risk_adjustment.py — セクター制限・レジーム乗数
  - __init__.py — API エクスポート

- src/kabusys/research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン、IC、統計サマリ等
  - __init__.py — 主要関数のエクスポート

- src/kabusys/ai/
  - news_nlp.py — ニュース記事を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロニュースを組み合わせ市場レジーム判定
  - __init__.py — API エクスポート

- src/kabusys/utils/
  - logging_setup.py — 共通ログ設定ユーティリティ（stdout + 日次ローテーションファイル）
  - process_priority.py — psutil を使ってプロセス優先度 / CPU affinity を設定
  - __init__.py

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - __init__.py

- data/ (実行時に生成・利用するファイル)
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（paper_trading 用）
  - kabusys.duckdb（DuckDB）
  - kill.flag / stop_requested.flag / execution.pid などのフラグ・PID ファイル

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では特に注意して環境変数（LINE 通知設定や kill flag の挙動）を確認してください。validate_config に本番向けのガードチェックがあります。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用します。環境に依らないため、監視 DB を別に分離したい場合はファイルパスを明示的に設定してください。
- AI 呼び出し（OpenAI）には API コストと稼働制約（レート制限等）があるため、適切なレート制御・リトライロジックが組み込まれていますが、設定や量に注意してください。
- データベースのマイグレーションは monitoring_db.init_monitoring_db で安全に行われますが、バックアップを推奨します。

---

## さらに詳しく（開発者向けメモ）

- 設計は「テスト可能性」「フェイルセーフ」「ルックアヘッドバイアス防止」を重視しています。各モジュールは副作用を最小化する純粋関数（portfolio, research 等）と外部副作用を扱う層（execution, monitoring）に分離されています。
- ロギングは setup_logging() で統一され、すべての起動スクリプトから呼ばれる想定です。
- プロセス優先度設定は utils.process_priority.set_process_priority を使用（Windows / POSIX の差分吸収）。
- DuckDB 用のクエリはパフォーマンスを考慮してウィンドウ関数や partition を多用しています。大規模データセットでの実行時は DuckDB の最適化設定を検討してください。

---

必要に応じて README を拡張します。特定の実行例（systemd ユニット、Dockerfile、CI 設定など）が必要であれば教えてください。