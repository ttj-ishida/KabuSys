KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした Python ベースのプロジェクトです。  
主な設計方針は「モジュール化」「フェイルセーフ」「ルックアヘッドバイアス防止」で、発注処理・監視・ポートフォリオ構築・ファクター計算・AI ベースのニュース解析などの機能を含みます。

主な機能一覧
-------------
- Execution（発注エンジン）
  - 実口座・ペーパートレードを切り替えて起動可能（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine による発注制御・リスク管理
- Monitoring（監視）
  - システム状態（CPU/メモリ/ディスク）・プロセス監視
  - 注文ログ / リスクログ / ダッシュボード永続化（SQLite）
  - Kill Switch による停止フラグ発行
  - AlertManager 経由の外部通知（LINE 等、設定がある場合）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額・スコア重み配分、ポジションサイズ計算、セクター制限、レジーム乗数
- Research（研究用モジュール）
  - ファクター計算（Momentum / Value / Volatility）
  - 特徴量探索（forward returns, IC, summary）
  - DuckDB を用いた分析向け設計
- AI（OpenAI 利用）
  - ニュース NLP（news_nlp.score_news）: 記事を LLM でスコア化して ai_scores に保存
  - レジーム判定（regime_detector.score_regime）: MA と LLM センチメントの組合せで市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（tools.paper_verification_report）
- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - 統一的なログ設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）

セットアップ手順
--------------
前提
- Python 3.10+（typing の | 記法などを使用）
- 仮想環境の作成（推奨）

依存ライブラリ（主要）
- duckdb
- psutil
- openai
- PyYAML（任意、validate_config の YAML 検証に使用）

例（pip）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)

2. インストール
   - pip install -r requirements.txt
   （requirements.txt がない場合）
   - pip install duckdb psutil openai pyyaml

初期設定（.env の作成）
1. 対話式で .env を作る（推奨）
   - python -m kabusys.config_setup
   - プロンプトに従い必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力
2. 設定検証
   - python -m kabusys.validate_config
   - 厳密チェック（警告も FAIL）
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL（DEBUG/INFO/WARNING/...）
- LOG_DIR（ログ保存先、デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか 1/0）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）

使い方（主要スクリプト）
-----------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - メモ:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録する（本番 DB と分離）
    - 起動時に data/stop_requested.flag が立っていると起動せず終了する
    - 実行中の停止は data/stop_requested.flag を作成することで制御（Kill Switch など）

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒、デフォルト 60）
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path（data/monitoring.db の想定）を使用します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

ログ
----
- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- デフォルト出力先:
  - コンソール (stdout)
  - ファイル: logs/<app_name>.log（日次ローテーション、30日保持）
- LOG_DIR で出力先を指定可能

プロセス制御 / Kill Switch / フラグ
---------------------------------
- 停止要求ファイル:
  - data/stop_requested.flag — run_execution / run_monitoring の手動停止フラグ（存在チェック）
  - data/kill.flag — KillSwitch が書き込む停止フラグ（Execution 側で検出して停止）
- PID ファイル:
  - data/execution.pid（Execution 起動時の PID）
- 起動オプション:
  - KILL_FLAG_CLEAR_ON_START=1 によって起動時に kill.flag を自動クリアできる（本番では 0 推奨）

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数・.env 自動ロード / Settings
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 起動前設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート
- ai/
  - __init__.py
  - news_nlp.py               — ニュース NLP スコアリング
  - regime_detector.py        — 市場レジーム判定
- monitoring/
  - monitoring_db.py          — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py         — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py          — （注文周りの監視: stale/異常約定 等）
  - risk_monitor.py           — ドローダウン・ポジション上限監視
  - monitoring_engine.py      — 各 Monitor を束ねるエンジン
  - kill_switch.py            — kill.flag 書込ロジック
  - alert_manager.py          — 外部通知ラッパー（LINE 等）
- execution/
  - execution_engine.py       — 実行セッションロジック
  - order_manager.py
  - order_repository.py
  - risk_manager.py
  - reconciler.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py        — Momentum/Value/Volatility 計算（DuckDB）
  - feature_exploration.py    — forward returns / IC / summary
- utils/
  - logging_setup.py          — 共通ログ設定
  - process_priority.py       — プロセス優先度・CPU affinity
- monitoring_db、各種モジュールの実装がそれぞれ存在

注意事項 / 運用メモ
------------------
- .env は絶対にソース管理にコミットしないこと（config_setup のヘッダに注意書きあり）。
- 本番（KABUSYS_ENV=live）では LINE 関連や kill flag の設定を十分に確認すること（validate_config がチェックを支援）。
- AI 機能を使う場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フェイルセーフ実装が入っていますが、料金・遅延に注意してください。
- Monitoring はデフォルトで production sqlite_path を使用します（環境に依存しないため、監視 DB は別管理してください）。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を利用）。

貢献 / 開発
-----------
- コードはモジュール単位でテストを追加してください（特に AI 呼び出し・DB 書き込みまわりはモック推奨）。
- 新しい設定を追加したら config_setup.py / validate_config.py を更新して対話・検証に反映してください。

---

この README はリポジトリ内のドキュメント生成用に手早くまとめたものです。運用手順やデプロイ手順は実環境に合わせて追記してください。必要であれば各モジュール（ExecutionEngine、MonitoringEngine、AI パイプライン等）の詳細な設計ドキュメントも作成できます。必要な箇所を指示してください。