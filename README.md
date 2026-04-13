# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買（バックテスト／ペーパートレード／本番運用）を目的としたモジュール群を含みます。ポートフォリオ構築、ポジションサイズ計算、発注／再同期ロジック、監視基盤、AI を使ったニュース NLP やレジーム判定などを備えています。

## 主要コンポーネント（概要）
- 実行系
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じて paper_trading 用のモックブローカーを使用。
  - reconciler / order_manager / order_repository: 起動時リコンシリエーション、発注状態管理。
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングを行う起動スクリプト。
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager: システム状態、注文滞留、リスク（ドローダウン等）を監視し、必要に応じて kill.flag を作成、LINE 通知を行う。
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）。
  - monitoring_db: SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）。
- ポートフォリオ構築
  - portfolio: 候補選定、等金額／スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数。
- リサーチ
  - research: ファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量探索、IC 計算。
- AI
  - ai.news_nlp: OpenAI を用いたニュースセンチメント解析（ai_scores への書き込み）。
  - ai.regime_detector: ETF MA とマクロニュースを組み合わせた市場レジーム判定。
- ユーティリティ
  - config.Settings: 環境変数／.env 読み込みと検証。
  - utils.process_priority: プロセス優先度／CPU affinity 設定。

## 主な機能一覧
- 実行エンジン起動（本番 / ペーパートレード分離）
- 発注ライフサイクル管理、二相永続化によるクラッシュ耐性
- 起動時のリコンシリエーション（未確定注文・ポジション差分の自動修正）
- 監視（CPU/メモリ/ディスク、プロセス生存、データ鮮度、注文滞留、約定異常、ドローダウン）
- Kill Switch（条件に達したら flag ファイルを書き、ExecutionEngine 停止を促す）
- LINE によるアラート送信（cooldown 管理）
- Streamlit ベースの監視ダッシュボード（読み取り専用）
- ペーパートレード検証レポート出力ツール
- DuckDB を用いたファクター計算／リサーチツール
- OpenAI を用いたニュース評価 / レジーム判定（API のリトライ・バリデーション・スコアクリップ等を実装）

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンしてプロジェクトルートへ移動
2. Python 環境を作成（例）
   - python3 -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール（プロジェクトに requirements.txt がある想定）
   - pip install -r requirements.txt
   - 主要依存（抜粋）: duckdb, psutil, requests, openai, streamlit
4. データディレクトリを作成
   - mkdir -p data
5. 環境変数設定
   - 本プロジェクトは .env / .env.local をプロジェクトルートから自動読み込みします（.git または pyproject.toml を基準）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨／オプション
     - OPENAI_API_KEY — AI 機能を使う場合に必須
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定モード: instant|partial|never|reject（デフォルト: instant）
     - SQLITE_PATH（監視DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB, デフォルト: data/paper_trading.db）
     - DUCKDB_PATH（DuckDB パス, デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH（ExecutionEngine 用 PID ファイルのパス, デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（Kill Switch flag, デフォルト: data/kill.flag）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、run_monitoring 用。デフォルト 60）

6. DB 初期化
   - run_monitoring や run_execution 起動時に自動で monitoring DB のスキーマを作成 / マイグレーションします（init_monitoring_db を使用）。手動での初期化は通常不要です。

## 使い方（主なコマンド例）

- 監視ループを起動（デフォルト 60 秒間隔、MONITOR_POLL_INTERVAL で変更可）
  - python -m kabusys.run_monitoring
  - 例（30 秒間隔）:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（本番 / ペーパー自動切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

  注意: paper_trading の場合、settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。

- Streamlit 監視ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB を使う:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュール（プログラムから呼び出す例）
  - ニューススコア算出:
    - from datetime import date
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  - レジームスコア算出:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")

- ライブラリ関数の利用例（ポートフォリオ構築）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - candidates = select_candidates(buy_signals)
  - weights = calc_equal_weights(candidates)
  - sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)

## 重要な設計・運用上の注意
- .env ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して .env/.env.local を読み込みます。OS 環境変数は .env の上書きから保護されます。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化します（テスト等で便利）。
- KABUSYS_ENV:
  - "development", "paper_trading", "live" のいずれかを指定します。不正な値は例外になります。
- Paper Trading:
  - paper_trading モードではモックブローカーを利用し、発注履歴は paper_sqlite_path（デフォルト data/paper_trading.db）に保存され本番 DB と完全に分離されます。
- OpenAI の使用:
  - OPENAI_API_KEY が必要です。API 呼出しはコストとレート制限があるため注意してください。news_nlp / regime_detector は応答の検証・リトライ・クリップを行い、障害時はフェイルセーフ（デフォルト値）で継続する設計です。
- Kill Switch:
  - RiskMonitor などが条件を満たすと data/kill.flag を作成し、ExecutionEngine に停止を促します。ExecutionEngine 起動時にこのフラグをクリアする設定があります（Settings.kill_flag_clear_on_start）。
- プロセス優先度:
  - run_monitoring / run_execution の起動時に set_process_priority("high") を呼び出します。権限やプラットフォームによっては無視されることがあります。

## ディレクトリ構成（主要ファイル）
（プロジェクト内の src/kabusys 以下の主要モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (他: broker_factory, execution_engine, order_repository など)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (DuckDB/パイプライン関連; prices_daily / raw_financials 等を扱うコード)

（注）上記は本コードベースで提供される主要モジュールを示した抜粋です。

## モニタリング DB スキーマ（監視用 SQLite）
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (single-row id=1, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

## 開発者向け補足
- DuckDB を使って価格データや財務データを効率的に集計・計算します（research / ai モジュール）。
- テストを書く際は Settings の自動 .env ロードを無効化したり、ai モジュールの API コール部分をモックすることを推奨します（コード中にも patch 用のコメントあり）。
- ロギングは基本 INFO レベルで起動スクリプトで設定しています。LOG_LEVEL 環境変数で細かく制御可能です。

---

問題や追加で README に載せたい情報（例: インストール手順の詳細、CI 設定、実際の ExecutionEngine の構成やパラメータ）などがあれば教えてください。必要に応じてサンプル .env.example を作成します。