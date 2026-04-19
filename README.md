KabuSys — README（日本語）
========================

概要
----
KabuSys は日本株向けの自動売買 / 研究用ライブラリ群です。  
このリポジトリには、発注エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、ファクター計算・研究、ニュースNLP / レジーム判定（OpenAI を利用）などの主要機能が含まれます。  
設計方針としては「本番・ペーパートレードの分離」「ルックアヘッドバイアスを避ける」「フェイルセーフ（APIエラー時の安全なフォールバック）」が重視されています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 実口座 / ペーパートレードを環境で切り替え可能（KABUSYS_ENV=paper_trading で MockBrokerClient を使用）
  - リスク管理（RiskManager）、注文管理（OrderManager）、Reconciler 等を備える
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして system_status, trade_logs, risk_logs, dashboard 等を SQLite に永続化
  - Kill Switch（条件を満たすと data/kill.flag を書き込む）による緊急停止機能
  - MONITOR_POLL_INTERVAL によるポーリング間隔変更（デフォルト 60 秒）
- Portfolio（ポートフォリオ構築）
  - 候補選び、重み付け（等金額 / スコア加重）、ポジションサイズ決定（リスクベース、単元丸め、集計制約）
  - セクター上限やレジームに応じた調整
- Research（研究 / ファクター計算）
  - Momentum / Volatility / Value などのファクター計算（DuckDB を使用して prices_daily / raw_financials を参照）
  - 将来リターンや IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI を利用した機能）
  - news_nlp: ニュース記事を LLM でセンチメント化して ai_scores に書き込む
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成して市場レジームを判定
- ツール
  - config_setup: .env 作成ウィザード（対話形式）
  - validate_config: 起動前の設定検証 CLI（.env および config/*.yaml の存在など）
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

前提 / 依存
------------
最低限の実行に必要な主要パッケージ（一部）：
- Python 3.9+（プロジェクトの使用環境に合わせてください）
- duckdb
- psutil
- openai（ニュースNLP / レジーム判定を使う場合）
- PyYAML（config の詳細検証を行う場合は任意で推奨）

（pip でインストールしてください。requirements.txt は本リポジトリに含まれていない想定のため、必要なパッケージを個別にインストールしてください。）

セットアップ手順
----------------
1. レポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証を使うなら pip install PyYAML）

4. .env の初期作成（対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークンや kabuAPI パスワードなどを入力します。
   - .env は自動作成されます（.env は絶対に Git にコミットしないでください）。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題があれば修正してください。--strict を付けると警告もエラー扱いになります。

6. データディレクトリ
   - デフォルトでは data/ 以下に SQLite やログ用ディレクトリが置かれます。必須ではないが、実行前に書き込み権限があるか確認してください。
   - 実行時（logging_setup）に logs/ を自動作成します。data/ も必要に応じて作成されます。

主な環境変数（抜粋）
-------------------
（config.py を参照。ここにないものもありますが、主要なものを列挙します）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API のリフレッシュトークン

- KABU_API_PASSWORD (必須)
  - kabuステーション API パスワード

- KABU_API_BASE_URL (任意)
  - デフォルト: http://localhost:18080/kabusapi

- KABUSYS_ENV (任意)
  - 有効値: development / paper_trading / live
  - paper_trading のとき Execution は MockBrokerClient を使い、paper_trading DB に記録します

- OPENAI_API_KEY
  - news_nlp や regime_detector を使う際に必要

- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb

- SQLITE_PATH
  - デフォルト: data/monitoring.db（Monitoring 用）

- PAPER_TRADING_SQLITE_PATH
  - デフォルト: data/paper_trading.db（ペーパートレード専用 DB）

- LOG_LEVEL
  - デフォルト: INFO

- LOG_DIR
  - デフォルト: logs/

- MONITOR_POLL_INTERVAL
  - 監視ループのポーリング間隔（秒）。run_monitoring で使用。デフォルト 60（かつ 1 未満の値は無効扱い）

- KILL_FLAG_CLEAR_ON_START
  - 本番での自動クリアは危険。0 を推奨。

使い方（よく使うコマンド）
-------------------------
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB に記録されます。
  - 停止信号: data/stop_requested.flag を作成すると起動中の run_execution は停止します（また KillSwitch は data/kill.flag を書き込みます）。

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能
  - 監視は本番 sqlite_path を常に使用します（環境に依らず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（未指定時は環境変数 PAPER_TRADING_SQLITE_PATH あるいは data/paper_trading.db を使用）

停止・Kill Switch
-----------------
- KillSwitch（kabusys.monitoring.kill_switch）は RiskMonitor の検出結果に基づき data/kill.flag を書き込みます。ExecutionEngine はこのフラグを確認して停止します。
- 手動で停止する場合はプロジェクトルートの data/stop_requested.flag を作成してください（run_monitoring.py / run_execution.py は起動中にこれをチェックして安全に停止します）。
- 本番運用時は KILL_FLAG_CLEAR_ON_START を 0 に設定することを推奨します（誤ってクリアされると緊急停止機能が無効化される場合があります）。

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
- デフォルト出力:
  - コンソール（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log（30日分保持）
- app_name は起動スクリプトごとに設定されます（例: "execution", "monitoring"）。

ディレクトリ構成（サマリ）
--------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み/検証・Settings クラス
- config_setup.py
  - .env の対話ウィザード
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（主要ファイル）
- ai/
  - news_nlp.py      — ニュースセンチメントスコアの取得と ai_scores 書込み（OpenAI 使用）
  - regime_detector.py — マクロセンチメント + MA200 で市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite のテーブル作成・読み書きラッパー
  - system_monitor.py — CPU/MEM/DISK/データ鮮度・実行プロセスの監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - trade_monitor.py — （trade 関連監視：コードベースに該当実装あり）
  - kill_switch.py — Kill Switch 実装（flag ファイル）
  - monitoring_engine.py — Monitor を束ねるエンジン
  - alert_manager.py — （アラート送信機能：LINE 等）
- execution/
  - execution_engine.py — 実行エンジン本体
  - broker_factory.py — ブローカークライアント選択（実際 or モック）
  - order_manager.py / order_repository.py / risk_manager.py / reconciler.py — 発注管理・リスク制御など
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数算出・集計調整
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度 / CPU Affinity の設定ヘルパー

注意事項 / 運用上のヒント
------------------------
- production（本番）運用の前には必ず python -m kabusys.validate_config を実行して設定を検証してください。
- OPENAI_API_KEY を使用する AI 機能は API 利用料・レートリミットがあるため、運用時は適切なエラーハンドリングとリトライ設定がされていますが利用コストに注意してください。
- run_monitoring は監視用 DB（SQLITE_PATH）に常に「本番」DBを使います。環境に依らず監視データが同じ DB に保存される点に注意してください。
- run_execution は KABUSYS_ENV=paper_trading のときに paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。本番 DB と完全分離されます。
- .env は秘密情報（APIトークン等）を含むため絶対に Git にコミットしないでください。

問題が発生したら
----------------
- ログ（logs/<app>.log）を確認
- python -m kabusys.validate_config で設定に問題がないか確認
- AI 機能利用時は OPENAI_API_KEY の設定と API エラーをログで確認
- SQLite / DuckDB のパス設定（環境変数）を確認

---

この README はコードベースの主要部分に基づく要約です。より詳細な仕様や設計文書（PortfolioConstruction.md 等）がある場合はそちらも参照してください。