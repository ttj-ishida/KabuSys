# KabuSys

日本株向け自動売買システムのコアライブラリ群（プロトタイプ実装）。  
このリポジトリは、発注エンジン、監視（モニタリング）、ポートフォリオ構築、研究・ファクター計算、AI（ニュースのセンチメント評価）などの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 日次／リアルタイムにおける売買実行（ExecutionEngine）
- システム稼働状況・注文状態・リスク監視（Monitoring）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- DuckDB を用いたファクター計算やリサーチ処理
- OpenAI を用いたニュース NLP（センチメント評価）と市場レジーム判定
- 設定ウィザード・検証ツール・ペーパートレード検証レポート生成

設計方針の一部：
- 環境変数（.env）により挙動を切り替え（development / paper_trading / live）
- Paper Trading は本番 DB と分離して専用 SQLite を使用
- DuckDB を分析用 DB として採用
- OpenAI 呼び出しはフェイルセーフ（リトライ・フォールバックあり）

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading DB に記録
  - プロセス優先度設定・PIDファイル管理・停止フラグ検知
- 監視（run_monitoring / MonitoringEngine）
  - CPU・メモリ・ディスク・データ鮮度・Execution プロセスの死活監視
  - トレードログ監視、リスク監視（ドローダウン・保有数上限）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み、Execution を停止）
- 設定関連
  - 対話式ウィザードで .env を生成（config_setup）
  - 設定検証 CLI（validate_config）
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額／スコア重み、リスクベース配分
  - セクターキャップ適用、レジーム乗数計算、単元株丸め、aggregate cap のスケーリング
- Research（ファクター計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI モジュール
  - ニュースから銘柄ごとのセンチメントを OpenAI によって算出し ai_scores に書き込み
  - マクロニュース + ETF ma200 を使った市場レジーム判定（score_regime）
  - API のリトライ・レスポンス検証を含む実装
- ユーティリティ
  - ロギング設定（setup_logging）
  - プロセス優先度 / CPU affinity 設定（process_priority）
  - Monitoring DB（SQLite）ラッパー（monitoring_db）
- 運用ツール
  - paper_trading の検証レポート生成スクリプト（tools/paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. Python 環境準備（推奨: 3.10+）
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合はそれを使用してください。無ければ主な依存例：
     - pip install duckdb psutil openai
     - optional: PyYAML（validate_config の YAML 検証用）
   - （例）
     - pip install duckdb psutil openai PyYAML

3. リポジトリルートでデータディレクトリを作成
   - mkdir -p data logs

4. .env の作成
   - 対話式ウィザードで作成（推奨）
     - python -m kabusys.config_setup
   - または .env を手動作成（.env.example を参考に）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数（デフォルト値）
     - KABUSYS_ENV: development | paper_trading | live  (default: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - PAPER_FILL_MODE: instant | partial | never | reject (paper_trading 用)

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱い

6. DB 初期化は各起動スクリプトが自動で行います（monitoring は init_monitoring_db を呼ぶ）。

---

## 使い方（起動 & ツール）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使う
    - 起動時に data/execution.pid を書く（PID 管理）
    - data/stop_requested.flag があると起動を行わない／停止をトリガー

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き可能:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は常に（環境にかかわらず）本番 sqlite_path を使用して monitoring DB にログを残す

- .env の対話式設定
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - --db /path/to/paper_trading.db
  - 環境変数: PAPER_TRADING_SQLITE_PATH を利用可能

- AI モジュール（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - 市場レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - 注意: OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定

- ログ
  - デフォルト出力先: 標準出力と logs/<app_name>.log（日次ローテート）
  - ログディレクトリ: 環境変数 LOG_DIR で変更可能

- Kill Switch / Stop フロー
  - デフォルトの停止フラグファイル: data/kill.flag（Settings.kill_flag_path）
  - 監視スクリプトは data/stop_requested.flag を参照して自身の終了や Execution の停止を行う
  - KillSwitch はリスク条件を満たすと data/kill.flag を書き込む（冪等）

---

## 主要ファイル・ディレクトリ構成

（パッケージルート: src/kabusys）

- run_execution.py
  - ExecutionEngine の起動スクリプト。プロセス優先度設定、DB接続、BrokerFactory 経由でのブローカークライアント生成、スレッドでのエンジン実行、停止フラグ監視。

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト。MONITOR_POLL_INTERVAL により間隔変更可。

- config.py
  - Settings クラス：.env / 環境変数の読み込み、必須チェック、各種パスやフラグの getter。

- config_setup.py
  - .env を対話的に作るウィザード。

- validate_config.py
  - 起動前の設定検証 CLI（環境変数・YAML ファイル存在・パス等をチェック）。

- monitoring/
  - monitoring_db.py : SQLite のスキーマ初期化・簡易ラッパー（MonitoringDB）
  - system_monitor.py   : CPU/メモリ/ディスク/データ鮮度・プロセス監視（SystemMonitor）
  - trade_monitor.py    : （注文や約定に関する監視ロジック）
  - risk_monitor.py     : ドローダウン / ポジション上限監視（RiskMonitor）
  - kill_switch.py      : kill.flag の管理
  - monitoring_engine.py: 各モニタを束ねて定期実行（MonitoringEngine）
  - alert_manager.py    : （アラート送信管理: LINE 等）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
  - （発注や注文管理、リスク管理の実装）

- portfolio/
  - portfolio_builder.py      : 候補選定・等重/スコア重み
  - position_sizing.py        : 株数計算、aggregate cap のスケール
  - risk_adjustment.py        : セクター制限、レジーム乗数

- research/
  - factor_research.py : Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py : 将来リターン、IC、統計サマリー

- ai/
  - news_nlp.py        : ニュースを OpenAI で評価して ai_scores に書き込むロジック
  - regime_detector.py : マクロ＋ETF を合成して market_regime を作る

- tools/
  - paper_verification_report.py : Paper Trading の検証レポート生成スクリプト

- utils/
  - logging_setup.py     : ログの初期化（stdout + 日次ローテート）
  - process_priority.py  : プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 注意点 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では .env を特に慎重に管理してください。validate_config は live 時に追加警告を行います。
- Paper Trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API 呼び出しはコスト・レート制限に注意。環境変数 OPENAI_API_KEY を必ず管理してください。
- logging_setup はログディレクトリの作成に失敗した場合、ファイル出力をスキップして stdout のみで動作します。
- process_priority の設定は OS に依存し、一部権限の制約で失敗することがあります（警告ログが出ます）。

---

必要に応じて README のチュートリアル（起動例、環境変数テンプレート、運用手順）を追加できます。追加して欲しい事項（例: systemd サービス定義例、Docker イメージ化手順、詳細な設定例など）があれば教えてください。