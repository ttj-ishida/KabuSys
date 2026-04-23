# KabuSys

日本株自動売買システム（ライブラリ＋実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・研究支援・AIによるニュース解析などを含む日本株向け自動売買システムのコア部分を提供します。設計は「本番とペーパートレードの分離」「フェイルセーフ」「ログ／監視の一貫運用」を重視しています。

主な特徴、セットアップ、使い方、ディレクトリ構成を以下にまとめます。

---

## プロジェクト概要

- システム構成要素
  - 発注実行エンジン（ExecutionEngine）
  - 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
  - ポートフォリオ構築（候補選定、重み付け、株数算出、セクター制約など）
  - 研究用モジュール（ファクター計算、特徴量解析、IC算出など）
  - AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
  - ユーティリティ（環境設定ウィザード、設定検証、ログ設定、プロセス優先度）
  - 各種永続層：SQLite（監視・発注ログ等）、DuckDB（時系列・分析用）
- 運用面の配慮
  - 本番とペーパートレードの DB を分離（KABUSYS_ENV による切替）
  - Kill Switch（フラグファイルで ExecutionEngine を停止）
  - 日次ローテーションのログ出力（logs/<app>.log）
  - .env による設定管理、対話式ウィザードあり

---

## 機能一覧

- 環境管理
  - .env 自動ロード（プロジェクトルート検出）
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

- 実行と監視
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用してペーパートレード用 DB に記録
    - 停止フラグ（data/stop_requested.flag / data/kill.flag）により安全に停止
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
    - SystemMonitor を定期ポーリングして system_status 等を記録
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き（秒、デフォルト 60）

- 監視とアラート
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度を監視
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新・リスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB: SQLite を使った監視ログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）

- 発注・リスク管理（概要）
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine（エンジン本体）
  - RiskConfig に基づく制限（最大ポジション比率、利用率、レート制限、サーキットブレーカー等）

- ポートフォリオ構築
  - 候補選定（スコア降順、上位 N）
  - 重み付け（等金額 / スコア加重）
  - セクターキャップ適用
  - ポジションサイズ計算（リスクベース、等配分、単元株丸め、aggregate cap）

- 研究（Research）
  - ファクター計算（Momentum, Volatility, Value など）
  - 将来リターンの計算、IC（Spearman）計算、統計サマリー

- AI（OpenAI）
  - ニュース NLP（news_nlp.score_news）で銘柄別センチメントを ai_scores に保存
  - レジーム検出（regime_detector.score_regime）で市場レジームを daily に判定
  - OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で指定

- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発 / 実行環境）

1. システム要件（目安）
   - Python 3.10+
   - SQLite（標準ライブラリ）
   - 必要パッケージ（主なもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検査を使う場合）
   - 例: pip install duckdb psutil openai pyyaml

2. リポジトリの取得
   - git clone <repo-url>
   - プロジェクトルートに移動（pyproject.toml や .git が存在するディレクトリ）

3. .env の作成
   - 対話式ウィザード（推奨）:
     - python -m kabusys.config_setup
     - 画面の指示に従って必須鍵（J-Quants, kabuステーションパスワード 等）を入力
   - あるいは .env を手動で作成（.env.example を参照）

   主要な環境変数（一部）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development | paper_trading | live）
   - OPENAI_API_KEY（AI 機能を使用する場合）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（DEBUG/INFO/...）
   - PAPER_FILL_MODE（paper_trading 時のフィルモード: instant|partial|never|reject）

4. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict

5. ログディレクトリ
   - デフォルトのログ保存先は logs/。必要に応じて LOG_DIR 環境変数で変更。
   - 起動時にログディレクトリが作成されます（作成失敗時はコンソールのみ出力）。

---

## 使い方（主要コマンド）

- 実行エンジン起動（本番 / ペーパー）
  - デフォルト: KABUSYS_ENV により本番/ペーパーを切替
  - 起動:
    - python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると run_execution は検出して安全に停止します
    - 実行中のエンジンは data/execution.pid に PID を書きます
  - ペーパートレード時の DB は PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db を使用

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    - MONITOR_POLL_INTERVAL 環境変数（秒）で指定（例: export MONITOR_POLL_INTERVAL=30）
    - 1 秒以上の整数でなければデフォルト 60 秒にフォールバック
  - 停止:
    - data/stop_requested.flag を作成すると run_monitoring は終了します
    - Monitoring は Settings に依らず本番 sqlite_path を使用して監視ログを書きます

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱い

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスの指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定して使用
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を引数に取り、DB に結果を永続化します

---

## 運用上の注意

- Kill Switch / Stop flags
  - KillSwitch は risk 判定などで data/kill.flag を書き込み、本番 ExecutionEngine に停止シグナルを送ります（冪等）。
  - run_monitoring / run_execution はプロジェクト内の stop_requested.flag（data/stop_requested.flag）を監視して安全にシャットダウンします。

- 本番データの保護
  - .env は絶対に Git にコミットしないこと（config_setup も README にその旨を記載）
  - KABUSYS_ENV=live 設定時は LINE 通知や Kill Switch 等の設定を慎重に確認すること

- DuckDB / SQLite
  - DuckDB は分析用テーブル（prices_daily, raw_financials 等）を想定
  - SQLite は監視・トレードログの永続化に使用
  - 両者のパスは .env で指定可能（デフォルトは data/ 以下）

- 権限・優先度
  - 起動時にプロセス優先度を high に設定する処理が入っています（psutil による処理）。権限がないと警告が出ますが実行は継続します。

---

## ディレクトリ構成（抜粋）

プロジェクトルート（例）:
- .env (生成/保管は自己責任で)
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (ペーパートレード DB)
  - kill.flag / stop_requested.flag / execution.pid
- logs/
  - execution.log
  - monitoring.log
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (実装想定)
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
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
    - data/
      - pipeline.py (prices データ取得等を想定)
      - stats.py
    - tools/
      - paper_verification_report.py

（上記は本リポジトリで使われている主要ファイル／モジュールの概観です。実際のファイル数や細かい実装はリポジトリの内容に依存します。）

---

## よくある質問 / トラブルシュート

- Q: .env の自動読み込みが行われない
  - A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定していると自動読み込みを無効化します。プロジェクトルートが検出できない場合（.git や pyproject.toml が見つからない）もスキップされます。

- Q: OpenAI を使った処理で失敗するとどうなる？
  - A: AI 関連処理はフェイルセーフ設計です。API 失敗時はデフォルト値（例: macro_sentiment=0.0）やスキップ動作で継続します。ログに警告が出ます。

- Q: モジュールのテスト実行や個別関数確認は？
  - A: 多くのモジュールは関数ベースで純粋関数（副作用が少ない）で実装されています。duckdb 接続や sqlite 接続をモック/テスト DB で与えることでユニットテストが容易です。

---

この README はコードベースの概要と基本的な運用フローをまとめたものです。詳細な API や内部設計（Engine の起動フロー、OrderRepository の契約、DB スキーマ詳細、アラート配信設定など）は各モジュールの docstring を参照してください。必要であれば各モジュール向けの詳細ドキュメント（使用例・設計メモ）も作成できます。