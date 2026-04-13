KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォーム（研究・シグナル生成・発注・監視・検証ツール群）です。  
主な設計方針は「再現性・フェイルセーフ・環境分離」で、production/paper_trading/development を環境切替でき、監視・アラート・自動リコンシリエーション機能を備えています。

主な機能
--------
- Execution（発注）エンジン
  - OrderManager / ExecutionEngine による注文生成・送信・状態遷移管理
  - BrokerClientFactory により本番ブローカーと Mock（paper_trading）を切替可能
  - 起動時のリコンシリエーション（Reconciler）で再起動後の同期を自動化
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク・プロセス・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）作成
  - AlertManager：LINE へのプッシュ通知（クールダウン付き）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等分/スコア加重配分、リスク調整（セクター上限・レジーム乗数）、株数算出（単元丸め／aggregate cap）
- Research（リサーチ）
  - ファクター計算（Momentum / Volatility / Value）
  - forward returns / IC（Information Coefficient）計算、統計サマリ
  - DuckDB を用いた高速集計
- AI（LLM）連携
  - news_nlp: OpenAI を使ったニュースセンチメント付与（銘柄ごと）
  - regime_detector: ma200 とマクロニュースで市場レジーム判定（bull/neutral/bear）
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・P95レイテンシ等）

動作要件
--------
- Python 3.10+
- 必須パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリ）
- ネットワーク接続（ブローカー API / OpenAI / LINE を利用する場合）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <リポジトリURL>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があればそれを使う）
4. データディレクトリ作成
   - mkdir -p data
5. 環境変数設定
   - .env（プロジェクトルート）あるいは環境変数で設定できます。
   - 自動読み込みはデフォルトで有効（.env / .env.local をプロジェクトルートから読み込む）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
6. 重要な環境変数（代表）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能利用時に必須）
   - KABUSYS_ENV （development | paper_trading | live 、デフォルト: development）
   - PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject、デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
   - SQLITE_PATH（monitoring DB、デフォルト: data/monitoring.db）
   - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知用）
   - PID_FILE_PATH / KILL_FLAG_PATH（監視・停止フラグのファイルパス）
   - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒。デフォルト 60。0以下は無効）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

初期 DB 作成
- run_execution / run_monitoring の起動時に、必要な monitoring SQLite テーブルは init_monitoring_db() により自動作成（冪等）されます。

使い方（主要コマンド）
--------------------

- Execution（発注エンジン）を起動
  - 通常（production/live）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - Paper Trading（ブローカーは Mock、DBは data/paper_trading.db に保存）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 補足: 起動時にプロセス優先度が "high" に設定されます（set_process_priority）。

- Monitoring（ポーリング監視）を起動
  - MONITOR_POLL_INTERVAL による間隔上書き（秒、デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は monitoring DB（settings.sqlite_path）へ記録します。KABUSYS_ENV に関係なく本番 sqlite_path を使用します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくは --db で DB パスを指定

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定しない場合は PAPER_TRADING_SQLITE_PATH 環境変数 or data/paper_trading.db を使用

- AI（ニューススコア付与）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡し、OPENAI_API_KEY（あるいは api_key 引数）を設定して実行します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ書き込みます。API キー必須（未設定時は ValueError）。

API / ライブラリ利用例
- DuckDB を開いて research モジュールを直接呼ぶ例（Python REPL）:
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.research import calc_momentum
  - calc_momentum(conn, datetime.date(2026, 4, 1))

監視・停止（KillSwitch / flag）
- KillSwitch は RiskMonitor 等の判定結果に応じて settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine はこのフラグファイルの存在を確認して安全停止を行うことが前提です。
- Execution 起動時にフラグをクリアしたい場合:
  - 環境変数 settings.kill_flag_clear_on_start を利用（Settings.kill_flag_clear_on_start が "1" の場合）または手動で削除。

トラブルシューティング（よくある注意点）
- OPENAI_API_KEY が無いと LLM 関連機能は動作しません（例外または 0.0 フォールバックがあります）。
- MONITOR_POLL_INTERVAL に不正な値を設定するとデフォルト (60s) にフォールバックします。
- process priority / cpu affinity の変更はプラットフォーム依存で権限不足になる場合があります（警告ログのみで続行）。
- DuckDB / SQLite ファイルのパスは Settings で上書き可能（環境変数 DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。

ディレクトリ構成（抜粋）
-----------------------
- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定管理（.env の自動ロード機能含む）
  - run_execution.py                 — 発注エンジン起動スクリプト
  - run_monitoring.py                — 監視ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成 CLI
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - broker_factory.py
    - ...（発注関連実装）
  - monitoring/
    - monitoring_db.py               — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
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
    - pipeline.py / stats.py (DuckDB 関連ユーティリティ) — （実装に依存）
  - utils/
    - process_priority.py

開発・寄稿
----------
- コードはモジュールごとに純粋関数（副作用最小）設計を目指しています。ユニットテスト・モックを用いた検証が行いやすい構造です。
- 新機能追加やバグ修正は PR でお願いします。テストと簡単な説明（変更点の意図）を添えてください。

ライセンス
---------
- プロジェクトに付属の LICENSE を参照してください（リポジトリに存在する前提）。

補足
----
- README に記載のコマンドはプロジェクトルートを作業ディレクトリとして実行する想定です。
- 詳細な設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）はコード内コメントで参照されています。必要に応じてそれらのドキュメントを参照してください。