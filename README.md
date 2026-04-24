README
======

概要
----
KabuSys は日本株向けの自動売買およびリサーチ基盤の小規模フレームワークです。本リポジトリには下記の主要機能が含まれます。
- 注文実行エンジン（ExecutionEngine） — 本番／ペーパートレード対応
- 監視（Monitoring） — システム健全性、注文状況、リスク監視と Kill Switch
- ポートフォリオ構築ロジック（選定・重み付け・ポジションサイジング）
- 研究／ファクター計算（DuckDB 利用）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- 環境設定ウィザード / 設定検証 / レポートツール

特徴
----
- 環境（KABUSYS_ENV）に応じた挙動切替（development / paper_trading / live）
- Paper Trading は本番 DB と分離して data/paper_trading.db に記録可能
- 監視は SQLite（monitoring.db）に状態を永続化。Kill Switch による安全停止
- DuckDB を分析用データベースとして利用（prices_daily / raw_financials 等を想定）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価やレジーム判定（API キー必須）
- ログは stdout と日次ローテーションファイル（logs/）に出力

セットアップ
----------
1. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - duckdb, psutil, openai, PyYAML（任意）、その他必要なライブラリを pip でインストール
     例:
       pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使ってください（本リポジトリの提供内容に依存）。

3. 環境変数 (.env) の準備
   - 対話式ウィザードで .env を作成する:
       python -m kabusys.config_setup
   - 主要な環境変数（例・必須）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - OPENAI_API_KEY — AI 機能を使う場合に必要
     - LOG_LEVEL — デフォルト: INFO
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1, デフォルト 0)

   - 実行前に必ず .env（機密情報を含むため）を Git にコミットしないでください。

4. データ / ログディレクトリ
   - デフォルトでは data/ や logs/ を利用します。起動時に自動作成されますが、権限などあらかじめ確認してください。

設定検証
--------
環境設定や config/*.yaml の検証を行うツールがあります。
- 簡易検証:
    python -m kabusys.validate_config
- 警告も失敗扱いにする（--strict）:
    python -m kabusys.validate_config --strict

使い方
------
主要な実行スクリプトとツール:

- Execution Engine を起動する
  - 本番（KABUSYS_ENV=live または環境に応じて）:
      python -m kabusys.run_execution
    - 起動フロー:
      1. ログ設定
      2. プロセス優先度を high に設定（set_process_priority）
      3. SQLite / DuckDB 接続（paper_trading の場合は paper 用 SQLite を使用）
      4. BrokerClient を生成し ExecutionEngine を起動（別スレッド）

    - 停止方法:
      - data/stop_requested.flag を作成すると起動しているスクリプトが検知してシャットダウンします。
      - Kill Switch: 監視コンポーネントが条件判定して data/kill.flag を書き込むと ExecutionEngine 側で停止シグナルとして利用されます。
    - PID ファイル:
      - data/execution.pid（デフォルト）に PID を書きます。

- Monitoring を起動する
    python -m kabusys.run_monitoring
  - 説明:
    - SystemMonitor / TradeMonitor / RiskMonitor 等を用いてポーリング監視を行うコンポーネントを起動します。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可能。デフォルト 60 秒。
    - Monitoring は設定されている sqlite_path（本番 DB）を常に使用して監査ログを記録します（環境にかかわらず本番監視 DB を使用する設計）。

- 環境設定ウィザード
    python -m kabusys.config_setup
  - .env を対話式に生成・更新します。

- Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定

- AI / 研究機能
  - ニュース NLP（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は OpenAI API キーが必要です（OPENAI_API_KEY）。
  - DuckDB 上のテーブル（prices_daily, raw_news, raw_financials など）から計算を行います。

環境変数の重要項目（抜粋）
-----------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — execution 動作モード（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — OpenAI 利用に必須（ai モジュール）
- MONITOR_POLL_INTERVAL — 監視ポーリング秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に data/kill.flag を自動クリアするか（"1" で有効）

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

サブパッケージ（主要）
- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - （発注処理や Broker 抽象化、注文管理ロジック）

- monitoring/
  - monitoring_db.py — SQLite による永続化 API
  - system_monitor.py — システム状態監視（CPU/メモリ/Disk、データ鮮度、プロセス監視）
  - trade_monitor.py — 注文遅延・異常監視（該当ファイルあり）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねるポーリングランナー
  - kill_switch.py — Kill Switch 実装（data/kill.flag 操作）
  - alert_manager.py — アラート送信（LINE 等を想定）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・アロケーション
  - risk_adjustment.py — セクター上限、レジーム乗数

- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ

- ai/
  - news_nlp.py — raw_news を LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール

- utils/
  - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイルローテート）
  - process_priority.py — プラットフォーム横断のプロセス優先度 / CPU affinity 設定

運用上の注意
------------
- 本番環境で KABUSYS_ENV=live を設定する場合は .env の内容（アクセストークン、LINE 通知設定など）を十分に確認してください。
- data/kill.flag および data/stop_requested.flag はプロセス間の停止制御に使われます。誤って削除・上書きしないように注意してください。
- Paper Trading は本番 DB と分離されますが、DuckDB の分析データ等は別途管理してください。
- OpenAI や外部 API への呼び出しは料金やレート制限が発生するため、運用方針を定めてください。

開発
----
- コードはモジュール単位に分割されており、ユニットテストを作成しやすい構造になっています（多くの関数が純粋関数または副作用を明示しています）。
- OpenAI 呼び出し部はテスト可能なように内部呼び出し関数を差し替えやすく設計されています（ユニットテスト時は patch でモック可能）。

ライセンス・貢献
----------------
- 本 README はリポジトリ内コードから生成されたドキュメントです。実際のライセンス/コントリビュート方法はリポジトリの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

補足: よく使うコマンド例
-----------------------
- .env を作成:
    python -m kabusys.config_setup
- 設定検証:
    python -m kabusys.validate_config
- Execution 起動:
    python -m kabusys.run_execution
- Monitoring 起動:
    python -m kabusys.run_monitoring
- Paper レポート生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

以上。README に追加してほしい具体項目（例: サンプル .env、依存バージョン、実行フローの図など）があれば教えてください。