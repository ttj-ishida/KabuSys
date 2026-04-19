KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）です。  
主要な機能として、売買シグナルからポートフォリオ構築・発注までの ExecutionEngine、システム稼働監視・アラート・Kill Switch、ペーパートレード検証やリサーチ用ファクター計算、LLM を使ったニュースセンチメント評価などを提供します。

主な特徴
--------
- Execution:
  - 本番（live）／ペーパートレード（paper_trading）／開発（development）を切替可能
  - paper_trading 時は MockBroker を使用し、発注ログを本番 DB と分離
  - リスク管理（ポジション上限、ドローダウン等）を組み込んだ ExecutionEngine
- Monitoring:
  - CPU / メモリ / ディスク、プロセス生存確認、データ鮮度監視
  - Kill Switch（条件を満たすと data/kill.flag を書き込み Execution を停止）
  - MonitoringEngine によるポーリングとアラート通知連携
- Portfolio construction:
  - 候補選定、等分配・スコア重み・リスク基準によるポジションサイズ計算
  - セクターキャップやレジーム乗数対応
- Research:
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI:
  - OpenAI API を用いたニュースのセンチメントスコアリングおよび市場レジーム判定
  - API 呼び出しのリトライ／検証ロジックを備えた堅牢な実装
- 運用支援:
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - ペーパートレード検証レポート生成ツール（kabusys.tools.paper_verification_report）
- ロギング:
  - 統一的なログ設定（コンソール + 日次ローテートファイル出力）

セットアップ
-----------
1. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 必要ライブラリをインストール
   - 必須（主要）パッケージの例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. プロジェクトルートに移動し、.env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env を作成してください（.env は絶対に Git にコミットしないこと）。

主な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 起動環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用: デフォルト data/paper_trading.db）
- ログ:
  - LOG_LEVEL（例: INFO）
  - LOG_DIR（デフォルト: logs/）
- その他:
  - OPENAI_API_KEY（AI 機能を使う場合に必要）
  - MONITOR_POLL_INTERVAL（監視ループのポーリング秒数、デフォルト 60）

設定検証
--------
.env や config/*.yaml の初期チェックには validate_config を使います:
- python -m kabusys.validate_config
- 警告も失敗扱いにする場合:
  - python -m kabusys.validate_config --strict

使い方（起動スクリプト）
-----------------------
- 実行エンジン（ExecutionEngine）起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して PAPER_TRADING_SQLITE_PATH に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid（既定）に PID を書く実装です。

- 監視ループ（SystemMonitor）起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に（KABUSYS_ENV にかかわらず）本番 sqlite_path を使用します。
  - 停止は data/stop_requested.flag を作成することで行います（監視プロセス自身がフラグを検出して終了）。

- 設定ウィザード:
  - python -m kabusys.config_setup

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代わりに直接指定可能）

- ライブラリ的な利用例（Python REPL / スクリプト内）:
  - リサーチ（DuckDB 接続を渡す）:
    from kabusys.research import calc_momentum
    result = calc_momentum(duckdb_conn, target_date)
  - AI ニューススコアリング:
    from kabusys.ai import score_news
    count = score_news(duckdb_conn, target_date, api_key="sk-...")

運用メモ / オペレーション
-------------------------
- Kill Switch:
  - KillSwitch は RiskMonitor 等の結果で条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。
- ログ:
  - logs/<app_name>.log に日次でローテーションされます（デフォルト 30 日保持）。
- DB マイグレーション:
  - init_monitoring_db() は冪等でテーブル作成・簡易マイグレーション（カラム追加）を行います。
- 停止/再起動:
  - 監視／実行スクリプトは stop フラグ（data/stop_requested.flag）をチェックして終了します。運用ツール等でフラグを削除して再起動してください。

ディレクトリ構成（主要ファイル）
--------------------------------
（プロジェクトの src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py                        — パッケージ定義（__version__ 等）
  - config.py                          — 環境変数 / 設定読み込みユーティリティ（.env 自動読み込み）
  - config_setup.py                    — .env 対話式ウィザード
  - validate_config.py                 — 設定検証 CLI
  - run_execution.py                   — ExecutionEngine 起動スクリプト
  - run_monitoring.py                  — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py     — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py             — 候補選定・重み計算
    - position_sizing.py               — 株数決定・資金配分（lot 単位調整・スケーリング）
    - risk_adjustment.py               — セクター上限・レジーム乗数
  - research/
    - factor_research.py               — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py           — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py                      — ニュースの LLM センチメント評価（ai_scores 書き込み）
    - regime_detector.py               — マクロ＋MA によるレジーム判定
  - monitoring/
    - monitoring_db.py                 — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py                — システム状態 / データ鮮度チェック
    - trade_monitor.py                 — 注文滞留／約定異常検知（実装参照）
    - risk_monitor.py                  — ドローダウン／ポジション上限監視
    - kill_switch.py                    — Kill Switch 書き込みロジック
    - monitoring_engine.py             — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py                 — アラート送信（LINE などの実装ポイント）
  - execution/
    - execution_engine.py              — 実行セッションの中核（EngineConfig 等）
    - broker_factory.py                 — BrokerClient の生成（本番／Mock）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - utils/
    - logging_setup.py                 — 共通ログ設定ユーティリティ
    - process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ

注意事項 / 開発者向け補足
------------------------
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env を自動でロードします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- Paper Trading 分離:
  - paper_trading 環境では発注・約定を専用 DB（デフォルト data/paper_trading.db）に記録し、本番 DB と完全分離します。
- LLM（OpenAI）利用:
  - API キーは OPENAI_API_KEY に設定してください。AI モジュールはリトライとレスポンス検証を行いますが、API 利用時のコストとレート制限に注意してください。
- テスト/モック:
  - API 呼び出しや時間依存処理は差替え可能な設計（例えば _call_openai_api を patch）でテストが書きやすくなっています。

ライセンス・貢献
----------------
（この README にはライセンス情報は含まれていません。配布する場合は LICENSE を追加してください）  

以上が主要な README 内容です。必要であれば、各モジュールの使い方例（API サンプル）や運用手順（systemd / Supervisor 用の unit サンプル、ログローテーション設定例）を追加で作成します。どの部分を優先して掘り下げますか？