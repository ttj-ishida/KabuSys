# KabuSys

日本株向け自動売買システムのリポジトリ（README）。このドキュメントはリポジトリ内の主要スクリプト／モジュールから自動的に把握できる情報をまとめたものです。

主な内容：
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- ディレクトリ構成（主要ファイルの説明）
- 主要環境変数一覧 / デフォルト値
- 運用メモ（Kill Switch / stop フラグ 等）

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュラーなシステムです。以下のサブ機能を持ち、運用環境（development / paper_trading / live）に応じて挙動を切り替えます。

- ExecutionEngine: 注文の生成・送信・リスク管理（本番 / ペーパートレード対応）
- Monitoring: システム状態・注文状況・リスク（ドローダウン・保有上限など）の定期監視とアラート、Kill Switch 機能
- Portfolio construction: 候補選定、重み計算、ポジションサイズ決定、セクター制限など
- Research: ファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量探索、IC 計算
- AI モジュール: ニュースのセンチメントスコアリング（OpenAI）、市場レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード / 検証 CLI、DB 初期化など
- ツール: Paper Trading 検証レポート生成スクリプト等

設計方針として、データベース（DuckDB / SQLite）や外部 API（kabuステーション、J-Quants、OpenAI）へのアクセスを明確に分離し、運用上の安全策（ペーパートレード DB の分離、Kill Switch、冪等な DB 書き込みなど）を多く取り入れています。

---

## 機能一覧（抜粋）

- 設定管理
  - .env 対話ウィザード（python -m kabusys.config_setup）
  - 設定検証ツール（python -m kabusys.validate_config）
- ロギング
  - stdout と日次ローテーションログ（logs/<app_name>.log）を統一的に設定
- 実行エンジン（Execution）
  - 本番（live） / ペーパー（paper_trading）モード切替
  - BrokerClientFactory による Broker クライアントの抽象化
  - リスク管理、オーダーマネージャ、リコンサイラ（再整合化）
- 監視（Monitoring）
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねる MonitoringEngine
  - Kill Switch（一定条件で data/kill.flag を書き込み Execution を停止）
  - run_monitoring スクリプト（ポーリングループ、MONITOR_POLL_INTERVAL で調整可能）
- ポートフォリオ構築
  - 候補選別、等金額/スコア加重、リスクベースのポジションサイズ決定
  - セクター上限適用、レジーム乗数
- リサーチ
  - DuckDB を用いたファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI（OpenAI）
  - ニュース NLP による銘柄別センチメント（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF MA200 を使った市場レジーム判定
  - レート制限や 5xx に対するリトライバックオフ実装
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定を出力

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンしてソースコード配置
   - この README は src/kabusys を想定しています（パッケージとして実行可能）。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必須:
     - duckdb
     - psutil
     - openai
   - オプション（YAML 検証等）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がない場合は上記を参考にインストールしてください）

4. .env を作成
   - 対話ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example をベースに手動で作成
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリ作成（必要に応じて）
   - data/ （デフォルトの DB / flag / pid ファイル格納場所）
   - logs/（ロギング出力先。起動時に自動作成されますが、権限等に注意）

---

## 主要な使い方（コマンド）

- ExecutionEngine を起動（常駐する実行エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
    - 実行中に data/stop_requested.flag を作成すると安全に停止します
    - 起動時に PID ファイル（data/execution.pid 等）を書きます

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60
  - 動作:
    - 本処理は MonitoringEngine のループを回し、system/trade/risk を定期チェックして DB に記録・アラート送信（AlertManager が設定されている場合）
    - stop 判定には data/stop_requested.flag を見ます（存在すればループ終了）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）

- AI モジュール（プログラム内呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡すと ai_scores テーブルを書き換えます
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ書き込み

---

## 主要環境変数（デフォルト含む）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト "development"
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...。デフォルト: INFO）
- LOG_DIR: ログディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH: ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch 用フラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、デフォルト 0。live では注意）

---

## 運用メモ / フラグ類

- stop_requested.flag
  - run_execution / run_monitoring は data/stop_requested.flag（コードは Projectルート下 data/stop_requested.flag を参照）を存在チェックして安全に終了します。運用時に手動で作成してプロセスを停止できます。
- kill.flag（Kill Switch）
  - Monitoring 側でリスク条件が満たされた場合、data/kill.flag に理由を書き込みます。ExecutionEngine は起動時 / 起動中にこのフラグを確認し、存在すれば停止/アラートの対象になります。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアされますが、本番では 0 を推奨します（安全装置の誤解除を防止）。
- PID ファイル
  - ExecutionEngine は起動時に PID ファイル（data/execution.pid など）を作成します。存在確認や stale PID の検出処理が組み込まれています。

---

## ディレクトリ構成（主要ファイル・モジュール説明）

（src/kabusys をプロジェクトルートのパッケージとする想定）

- kabusys/
  - __init__.py
    - パッケージメタ情報（__version__ 等）
  - config.py
    - 環境変数・設定の読み込みと Settings クラス（.env 自動読み込みロジック含む）
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モードでは MockBroker を使用して DB 分離）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔上書き可）
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    - 注文送信・リスク管理などの実装（詳細は各ファイルを参照）
  - monitoring/
    - monitoring_db.py: SQLite スキーマ定義と永続化 API（MonitoringDB クラス）
    - system_monitor.py: CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py: （trade の監視ロジック）
    - risk_monitor.py: ドローダウン・ポジション上限の判定とログ
    - monitoring_engine.py: 各 Monitor を束ねるループ・アラート管理
    - kill_switch.py: Kill Switch 実装（flag 書込）
    - alert_manager.py:（通知送信の抽象化）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数決定・リスク制限・単元丸め
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - research/
    - factor_research.py: ファクター計算（momentum / volatility / value）
    - feature_exploration.py: 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py: ニュースセンチメント（OpenAI）→ ai_scores への書き込み
    - regime_detector.py: ETF MA200 + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py: ペーパートレード DB 解析レポート出力
  - utils/
    - logging_setup.py: 共通のログ設定ユーティリティ
    - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

（上記に含まれない補助モジュールや DB スキーマ、strategy / data 関連の実装は各ディレクトリのファイルを参照してください）

---

## 開発・デバッグのヒント

- DuckDB を使って Research 用データを高速に扱えます。
- OpenAI を利用する処理（news_nlp / regime_detector）は API 失敗時のフォールバックを備えていますが、ローカルテスト時は API キー無しでスキップするか、テスト用のモックを使うと良いです（テスト時は内部の API コール関数を patch 可能）。
- ロギングは setup_logging を各スクリプト冒頭で呼んでいるので、ログ出力先やレベルは環境変数 LOG_DIR / LOG_LEVEL で調整可能です。
- run_monitoring の MONITOR_POLL_INTERVAL は秒数（1 秒以上）を設定してください。不正な値を与えるとデフォルト（60 秒）にフォールバックします。

---

## ライセンス / 注意点

- .env は機密情報を含むため決して Git にコミットしないでください（config_setup でも注意書きがあります）。
- 本リポジトリには本番で実際に注文を出す実装が含まれるため、live モードでの起動前に設定と通知（LINE 等）を十分に確認してください。
- 本 README はソースコード中のコメントおよび関数ドキュメントを元に要約しています。詳細は該当モジュールの docstring / コメントを参照してください。

---

必要があれば以下を追加できます：
- 具体的な依存関係一覧（requirements.txt）
- CI / テスト実行手順（pytest 等）
- デプロイ / systemd / Supervisor 向けのサービス定義例
- alert_manager（LINE 等）設定例

ほかに README に入れたい情報（例: 実運用でのチェックリスト、systemd サンプルなど）があれば教えてください。