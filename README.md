KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買および関連ツール群をまとめた Python パッケージです。  
主な目的は以下です。

- 戦略に基づく銘柄選定・ポジションサイズ計算（Portfolio construction）
- 発注エンジン（ExecutionEngine）とリスク管理
- 監視（Monitoring）: システム状態・注文状況・リスクの定期チェックとアラート
- 研究・ファクター計算（DuckDB を用いたオフライン分析）
- AI を用いたニュースセンチメント評価 / 市場レジーム判定（OpenAI）
- ペーパートレード検証レポート生成

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードの切り替え（KABUSYS_ENV）
  - Paper trading 時は MockBrokerClient を使用し DB を分離（data/paper_trading.db）
  - プロセス優先度設定・PID 管理・停止フラグ監視
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視ログは SQLite（監視用 DB）へ記録
- 設定管理
  - .env 自動読み込み（.env, .env.local、環境変数が優先）
  - 対話式セットアップウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
- 研究 / リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算など
  - DuckDB 接続を前提としたオフライン分析
- AI モジュール
  - news_nlp: ニュース記事を集約して OpenAI でセンチメント評価（ai_scores に格納）
  - regime_detector: ETF 等の MA とマクロニュースを組み合わせて市場レジーム判定
- ユーティリティ
  - logging_setup: stdout + 日次ローテートファイル出力
  - process_priority: プロセス優先度 / CPU affinity 設定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを出力

セットアップ手順
----------------
前提: Python 3.9+（実際の要件は pyproject.toml / packaging に依存）。

1. リポジトリをクローン / 配布パッケージを展開

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は以下を最低限導入）
     - pip install duckdb psutil openai
     - 解析用に PyYAML があれば設定ファイル検証が有効化されます: pip install pyyaml

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（例）
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - 注意: .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード（警告を FAIL 扱い）:
     - python -m kabusys.validate_config --strict

6. データディレクトリ等の作成（自動で作られる場合もありますが確認を推奨）
   - mkdir -p data logs

実行方法（主要なコマンド）
-------------------------
- ExecutionEngine（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - 実行時に KABUSYS_ENV=paper_trading とすると MockBrokerClient を使い data/paper_trading.db を使用します。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は監視用 SQLite DB（Settings.sqlite_path、デフォルト data/monitoring.db）へ記録します。
    - 監視は KABUSYS_ENV にかかわらず production の sqlite_path を使用します（監視ログは環境に依存しません）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

停止・フラグ管理
----------------
- 停止フラグ（run_execution/run_monitoring が監視する）
  - data/stop_requested.flag を配置すると、long-running スクリプトが安全に停止します。
- Kill Switch（ExecutionEngine 停止）
  - data/kill.flag を書き込むと ExecutionEngine に停止シグナルが送られます（KillSwitch / kill_switch.py が生成）。
  - Settings.kill_flag_clear_on_start=1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨。

主要な環境変数
--------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

重要/推奨:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring に影響）
- PAPER_FILL_MODE — ペーパートレードでの約定挙動（instant|partial|never|reject）

ログ
----
- ログはデフォルトで stdout と logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション、30日保管）へ出力されます。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。

ディレクトリ構成（主なファイル/モジュール）
-------------------------------------
以下はパッケージ内の主要モジュールと役割の一覧（src/kabusys 以下）:

- __init__.py
  - パッケージ定義（__version__ 等）

- config.py
  - 環境変数と Settings クラス（自動 .env 読み込みのロジック含む）

- config_setup.py
  - 対話式 .env 作成ウィザード

- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度、DB 接続、スレッド起動、停止フラグ監視）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で制御）

- execution/（Execution 関連サブパッケージ）
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager など
  - 発注・オーダー管理・リスク管理の実装（詳細は該当ファイル参照）

- monitoring/
  - monitoring_db.py — SQLite スキーマ & 永続化 API（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス健全性チェック
  - trade_monitor.py — 注文滞留・約定異常検出（実装参照）
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — フラグファイル生成ロジック
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - alert_manager.py — (アラート通知管理、LINE など)（存在する場合）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算・リスク制限・単元丸め
  - risk_adjustment.py — セクター上限・レジーム乗数
  - __init__.py — 主要関数のエクスポート

- research/
  - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - __init__.py — 研究用 API エクスポート

- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し、レスポンス検証、ai_scores 書き込み）
  - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定（OpenAI を利用）
  - __init__.py — ai API エクスポート（score_news 等）

- tools/
  - paper_verification_report.py — ペーパートレード DB を解析して検証レポートを生成

- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定

注意事項・トラブルシューティング
--------------------------------
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml がある場所）を基に .env/.env.local を読み込みます。
  - テストなどで自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視 DB:
  - monitoring の初期化（テーブル作成）は接続時に自動実行されます（init_monitoring_db）。
- OpenAI:
  - news_nlp / regime_detector は OPENAI_API_KEY が必要です。未設定の場合は ValueError が上がります（明示的に捕捉し適切に対処してください）。
- 権限:
  - process_priority の設定は OS と権限に依存します。AccessDenied 等が出た場合は警告を出してスキップします。
- ログディレクトリ作成失敗時でもコンソールログは出力されます（ファイル出力のみ無効化）。

貢献 / 開発
-----------
- 新しい機能追加やバグ修正は該当モジュールに対するユニットテストを追加してください。
- DB スキーマ変更は monitoring_db.init_monitoring_db のマイグレーションコードを更新してください（既存 DB への互換性考慮）。
- LLM 呼び出し箇所はテスト用に _call_openai_api をパッチ可能に設計してあります（ユニットテストでモック化してください）。

ライセンス
---------
プロジェクト配布時に別途記載（このリポジトリ内の LICENSE を参照）。

付録: よく使うコマンド（一覧）
-----------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。システムの詳細実装や API 仕様は各モジュール内の docstring / コメントを参照してください。