README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ基盤です。本リポジトリには、発注エンジン（ExecutionEngine）、監視システム（Monitoring）、ファクター計算 / リサーチ、ポートフォリオ構築ロジック、AI ベースのニュースセンチメント評価などの主要コンポーネントが含まれます。  
設計方針の要点は次のとおりです。

- 環境変数ベースの設定（.env をサポート、自動読み込みあり）
- 本番データは DuckDB / SQLite に永続化
- paper_trading モードを用いた完全分離のペーパートレード運用
- OpenAI を使ったニュース NLP／レジーム判定（API キー必須）
- モジュールは純粋関数／DB 層分離を意識して実装

主な機能
--------
- ExecutionEngine:
  - 本番 / ペーパートレード両対応（KABUSYS_ENV）
  - ブローカー抽象化（Mock ブローカーを paper_trading 用に使用）
  - OrderManager / Reconciler / RiskManager 等を組み合わせて注文管理
- Monitoring:
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存確認）
  - TradeMonitor（滞留注文や約定異常などの検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（リスク条件到達時に data/kill.flag を書き込む）
  - MonitoringEngine：各モニタを束ねてポーリング・アラート送信
  - 監視ログを永続化する monitoring.db（SQLite）
- Portfolio モジュール:
  - 銘柄選定、重み計算（等金額・スコア加重）
  - セクター制約、レジーム乗数
  - ポジションサイズ計算（単元丸め・集約キャップ）
- Research:
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン、IC 計算、統計サマリー
  - DuckDB を利用した高速な分析
- AI モジュール:
  - news_nlp: ニュースを LLM（gpt-4o-mini）でセンチメント評価して ai_scores に保存
  - regime_detector: ETF（1321）MA 等とマクロニュースで市場レジームを判定
- ツール:
  - 設定ウィザード: python -m kabusys.config_setup（.env 作成補助）
  - 設定検証: python -m kabusys.validate_config（起動前チェック）
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------

前提
- Python 3.9+（プロジェクトの Python バージョンに合わせてください）
- system パッケージ: psutil（プロセス優先度 / CPU affinity）、duckdb、openai（AI 機能）、PyYAML（設定検証用、任意）など

1. リポジトリをチェックアウト
   - この README は src/kabusys のコードベースを前提としています。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/Mac) または .venv\Scripts\activate (Windows)

3. 必要パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
     （ない場合は以下を目安にインストール）
   - pip install duckdb psutil openai

   - PyYAML（config 検証を精密にする場合）:
     - pip install pyyaml

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考にしてください）
   - 重要: .env は絶対に Git にコミットしないこと

5. 設定の検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

主な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 運用 / 動作制御:
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）、デフォルト: development
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト: INFO
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 使用時）
- DB パス:
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 用）
- Paper Trading 固有:
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）
- モニタ関連:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START — 本番で Kill Switch 自動クリア（0 推奨）

使い方（起動例）
----------------

1. 設定確認
   - python -m kabusys.validate_config

2. .env の作成（まだなら）
   - python -m kabusys.config_setup

3. 監視プロセスを起動
   - MONITOR_POLL_INTERVAL を変更したい場合:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は Settings に従い sqlite_path（monitoring.db）を使ってログ保存します。

4. Execution（実際の注文処理）を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合:
     - MockBrokerClient が使用され、data/paper_trading.db に記録されます（本番 DB と分離）
   - 実行中は data/execution.pid が生成され、data/stop_requested.flag / data/kill.flag で停止制御を行います。

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

運用上の注意
- .env を Git に絶対に含めないでください（機密情報を含みます）。
- 本番（KABUSYS_ENV=live）では LINE 通知設定や Kill Switch の挙動を十分確認してください。
- OpenAI を利用する機能は API キーと料金が必要です。API 呼び出しの上限・エラー処理は慎重に運用してください。
- MONITOR_POLL_INTERVAL やログ出力設定でプロセス負荷を管理してください。
- run_execution は停止フラグ（data/stop_requested.flag）や kill.flag を監視して安全に停止します。

監視 DB（SQLite）スキーマ（主要テーブル）
- system_status: CPU/メモリ/ディスク/プロセス状態の時系列ログ
- trade_logs: 発注イベントログ（event_type, client_order_id, code, qty, price, latency_ms 等）
- positions: 現在のポジション（code 主キー）
- risk_logs: リスクイベント（ドローダウン・ポジション上限等）
- dashboard: 集計（portfolio_value / cash / drawdown_pct / open_order_count / position_count / peak_value）

主なコマンド一覧
- python -m kabusys.config_setup            — .env 作成ウィザード
- python -m kabusys.validate_config         — 設定の静的検証
- python -m kabusys.run_monitoring          — 監視ループを起動
- python -m kabusys.run_execution           — ExecutionEngine を起動
- python -m kabusys.tools.paper_verification_report — ペーパートレード検証レポート出力
- 各モジュールはライブラリとしても import して利用可能（例: kabusys.research.calc_momentum）

ディレクトリ構成（主要部分）
- src/kabusys/
  - __init__.py
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - config.py              — 環境変数・Settings 管理（自動 .env ロード機能含む）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参考実装がある前提)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

付録: よく使う設定例
- ローカル開発（ペーパートレード）
  - KABUSYS_ENV=paper_trading
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  - PAPER_FILL_MODE=instant
  - OPENAI_API_KEY=（未設定でも AI 機能を省けば可）

- 本番（注意深く設定）
  - KABUSYS_ENV=live
  - LOG_LEVEL=INFO
  - KILL_FLAG_CLEAR_ON_START=0
  - 必須: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD
  - 推奨: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を設定してアラート受信

サポート / 開発メモ
- ロギング: kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出して統一
- プロセス優先度: utils.process_priority.set_process_priority("high") を起動直後に実行
- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等にテーブル・カラムを追加します
- テスト: 各純粋関数（portfolio / research / position sizing 等）は DB 参照が限定的なのでユニットテストが作りやすい

以上が本コードベースの概要・セットアップ・使い方のまとめです。具体的な拡張や運用ルールについては各モジュールの docstring を参照してください。必要であれば運用手順書やデプロイ手順（systemd / container サポート など）のテンプレートも作成できます。必要な場合は教えてください。