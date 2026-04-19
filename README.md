# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、自動売買エンジン、監視・リスク管理、ポートフォリオ構築、リサーチ、AI を用いたニュース解析などを含む統合システムのコードベースです。本 README はプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主要な責務は以下の通りです。

- ExecutionEngine：発注ロジック・注文管理・リスク管理の実行（本番/ペーパートレード両対応）
- Monitoring：システム状態・注文状態・リスク指標を定期的に監視し、必要に応じてアラートや Kill Switch を発動
- Portfolio Construction：候補選定、重み付け、ポジションサイジング、セクター制約などの純粋関数群
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI（OpenAI）モジュール：ニュースの NLP によるセンチメント評価や市場レジーム判定
- ユーティリティ：設定読み込み、ログ設定、プロセス優先度設定など

設計方針として、データベース（DuckDB / SQLite）や環境変数を利用して設定を分離し、ペーパートレードは本番 DB と分離して安全にテスト可能です。

---

## 主な機能一覧

- 環境設定ウィザード（.env 自動生成・更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の事前チェック）
  - python -m kabusys.validate_config
- ExecutionEngine の起動（本番 / paper_trading 切替対応）
  - python -m kabusys.run_execution
- SystemMonitor（CPU / memory / disk / データ鮮度 / プロセス監視）
  - python -m kabusys.run_monitoring
- MonitoringEngine：System / Trade / Risk モニタを組み合わせたポーリングとアラート
- KillSwitch：条件に応じた停止フラグ（data/kill.flag）出力
- RiskMonitor：ドローダウン検出、ポジション上限監視とログ記録
- Portfolio モジュール：
  - 銘柄選定（select_candidates）
  - 等ウェイト・スコア重み付け（calc_equal_weights、calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用・レジーム乗数（apply_sector_cap、calc_regime_multiplier）
- Research モジュール：モメンタム、バリュー、ボラティリティの計算・IC 計算など（DuckDB 前提）
- AI モジュール：
  - news_nlp.score_news：OpenAI を使ったニュースセンチメント集計・ai_scores 書き込み
  - regime_detector.score_regime：ETF（1321）MA とマクロニュースを組合せた市場レジーム判定
- ツール：
  - Paper Trading 検証レポート出力（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

以下は一般的なローカルセットアップ手順です。プロダクション環境では運用要件に応じて調整してください。

1. Python（推奨 3.10+）をインストール

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 必要パッケージをインストール
   必要な主な依存：
   - duckdb
   - psutil
   - openai
   - PyYAML（config/*.yaml の検証を行う場合）
   （requirements.txt がある場合はそれを利用してください）
   例:
   - pip install duckdb psutil openai pyyaml

4. .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   ウィザードで J-Quants / kabu API / OpenAI のキー等を設定します。.env は絶対にリポジトリへコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   必須環境変数や config/*.yaml の存在 / 基本的な注意点を確認できます。--strict を指定すると警告も失敗扱いになります。

6. ディレクトリの作成（必要に応じて）
   - data/（SQLite や PID・フラグファイル用）
   - logs/（ログ）
   ただし多くのコードは起動時にディレクトリを作成します。

7. データベース初期化
   - 実行スクリプト（run_monitoring/run_execution）が初回起動時に監視用テーブル等を自動作成します。

---

## 主要な環境変数とデフォルト

（.env ウィザードはこれらを設定します。主要項目のみ抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN（任意、アラート通知）
- LINE_USER_ID（任意、アラート送信先）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60; run_monitoring で利用）

注意:
- run_monitoring は「監視用 DB（SQLITE_PATH）」に常に本番 sqlite_path を使います（環境に依らず）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使用し発注は MockBrokerClient によるシミュレーションで本番 DB と分離されます。

---

## 使い方（実行例）

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine の起動（フォアグラウンド）
  - python -m kabusys.run_execution
  - ペーパートレードを選ぶには .env で KABUSYS_ENV=paper_trading を設定

- SystemMonitor の起動（監視ループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔(秒)を上書き可能（例: 30秒）
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

- 停止方法
  - 実行ループ（run_execution/run_monitoring）はプロジェクトルートの data/stop_requested.flag が存在するとループを終了します（停止フラグ）。
  - KillSwitch（リスク条件により）を発動させると data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。
  - run_execution は内部で data/execution.pid を使用します（PID ファイル）。

---

## ログとファイル配置

- ログ: デフォルト logs/ ディレクトリに日次ローテートで保存（logs/<app_name>.log）
  - set up via kabusys.utils.logging_setup.setup_logging
- データ:
  - DuckDB: data/kabusys.duckdb（デフォルト）
  - SQLite (monitoring): data/monitoring.db（デフォルト）
  - Paper trading SQLite: data/paper_trading.db（ペーパートレード時）
- PID / フラグ:
  - data/execution.pid（ExecutionEngine の PID）
  - data/kill.flag（KillSwitch が発行する停止フラグ）
  - data/stop_requested.flag（人為的にスクリプト停止を要求するフラグ）

---

## 開発者向けメモ / 注意点

- AI 機能（news_nlp, regime_detector）は OpenAI API を利用します。OPENAI_API_KEY をセットしてください。API 失敗時はフェイルセーフとして代替動作（0.0 のスコア等）する設計です。
- monitoring_db.init_monitoring_db は冪等でテーブル作成と簡単なマイグレーション処理を行います。
- config._find_project_root() は .git または pyproject.toml を辿ってプロジェクトルートを検出し、.env の自動読み込みに利用します。テスト時など自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- process_priority と CPU affinity は psutil を利用してクロスプラットフォーム対応を試みますが、権限や OS により設定に失敗する可能性があります（例外は警告ログに抑止）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - Settings クラス（環境変数読み込み・検証）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - execution_engine.py (エンジン本体: 起動/セッション管理)
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py

- monitoring/
  - monitoring_db.py (SQLite 永続化層)
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
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

- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py
  - process_priority.py
  - その他ユーティリティ

その他トップレベル:
- config/（設定用 YAML テンプレート等）
- data/（DB・PID・フラグを配置するデフォルトディレクトリ）
- logs/（ログ出力先）

（実際のファイルは src/kabusys/ 以下を参照してください）

---

## よくある質問（FAQ）

Q: 本番環境で誤ってペーパートレード DB を使わないようにできますか？
A: KABUSYS_ENV を適切に設定してください。run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 SQLite を使用します。validate_config は本番モード（live）での注意喚起も行います。

Q: OpenAI の呼び出しに失敗した場合どうなる？
A: AI モジュールはリトライやフォールバック（0.0のスコア、失敗時はスキップ）を実装しており、システムは継続します。ログに警告を出力します。

Q: 監視間隔を変更したい
A: run_monitoring は環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（デフォルト 60 秒）。不正な値はデフォルトにフォールバックします。

---

## 貢献 / 開発の流れ

- まず issue を立て、設計・仕様を合意の上で PR を送ってください。
- 単体テスト・統合テストを追加し、主要機能の回帰を防いでください。
- 機密情報（.env、APIキー等）は決してコミットしないでください。

---

README は以上です。追加で各モジュールの API ドキュメント（関数仕様、引数の詳細、戻り値、例）をまとめた Developer Guide を作成することも推奨します。必要であれば自動生成用の Sphinx/pydoctor 設定案や、運用手順書（デプロイ・監視・バックアップ）も作成します。どれが必要か教えてください。