# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買システム向けユーティリティ群・コアロジックの集まりです。
トレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、
およびニュース NLP / レジーム判定などのコンポーネントを含みます。

以下はリポジトリに含まれる主要機能と使い方のまとめです。

---

## プロジェクト概要

- 自動売買の実行エンジン（ExecutionEngine）とそれを支える OrderManager / Reconciler / RiskManager 等
- 稼働監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送信（LINE）
- Paper Trading モード（本番 DB と分離された SQLite を使用）
- ポートフォリオ構築ロジック（候補選定、重み付け、ポジションサイズ計算、セクター上限）
- リサーチ用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI を用いたニュースセンチメント（OpenAI）と市場レジーム判定
- Streamlit ベースの監視ダッシュボードと検証レポート生成ツール

---

## 機能一覧

- Execution
  - 注文生成 / 発注管理 / 状態同期（Reconciler による起動時復旧）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し、専用 SQLite に記録
  - リスク制御（最大ポジション比率、利用率、ドローダウンなど）

- Monitoring
  - システムリソース監視（CPU / メモリ / ディスク）とプロセス存在チェック
  - 注文滞留（stale orders）、約定異常（price anomaly）監視
  - ダッシュボード集計（dashboard テーブル）とリスクログ保存
  - LINE へのアラート通知（AlertManager）
  - Kill Switch（特定条件で停止フラグを書き込み ExecutionEngine を止める）

- Portfolio
  - 候補選定（スコア降順）
  - 等ウェイト / スコア加重 / リスクベースでの株数計算
  - セクターキャップ適用、レジーム乗数

- Research
  - Momentum / Volatility / Value 等ファクター計算（DuckDB 上の prices_daily / raw_financials を使用）
  - 将来リターン、IC 計算、統計サマリー

- AI
  - ニュースセンチメント（OpenAI）を使った ai_scores の作成（news_nlp）
  - マクロニュースと ETF MA200 を用いた市場レジーム判定（regime_detector）

- Tools
  - Paper Trading 検証レポート生成ツール（paper_verification_report）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）

---

## セットアップ手順（開発 / 実行前の準備）

1. 要件（代表例）
   - Python 3.10+
   - 必要パッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - SQLite は標準ライブラリで利用可能

   仮想環境を作成して pip でインストールしてください（requirements.txt がない場合は上のパッケージを個別にインストールします）。
   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil requests openai streamlit
   ```

2. プロジェクトルートに .env を置く（自動で読み込まれます）
   - Settings クラスは .env と .env.local を自動読み込みします（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必須環境変数（利用する機能により必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY
   - その他（任意／デフォルトがあるもの）:
     - KABUSYS_ENV = development | paper_trading | live （デフォルト: development）
     - PAPER_FILL_MODE = instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト: data/paper_trading.db）
     - SQLITE_PATH（監視 DB（monitoring）デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知用）
     - LOG_LEVEL（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）

   例 (.env):
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   PAPER_FILL_MODE=instant
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

3. データディレクトリを作成
   ```
   mkdir -p data
   ```

4. DB 初期化
   - Monitoring 用のテーブルはスクリプト実行時に自動で初期化されます（init_monitoring_db）。
   - DuckDB / prices_daily / raw_financials 等のテーブルはリサーチ機能を使う場合、適切なスキーマで事前に用意してください。

---

## 使い方（主要スクリプト）

- 監視ループを起動（Monitoring）
  - デフォルトでは production sqlite_path（Settings.sqlite_path）を使用します（run_monitoring の注記）。
  - 簡易実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数でポーリング間隔を上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 停止方法:
    - Ctrl+C（KeyboardInterrupt）
    - またはプロジェクトルートの data/stop_requested.flag を作成するとループ終了します。

- 実行エンジンを起動（ExecutionEngine）
  - 本番 / Paper Trading 切替:
    - Paper Trading:
      ```
      KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      ```
      → MockBrokerClient を使用し data/paper_trading.db を使います（本番 DB と分離）。
    - 本番:
      ```
      KABUSYS_ENV=live python -m kabusys.run_execution
      ```
  - 停止:
    - run_execution は data/stop_requested.flag の存在を監視しており、存在すればエンジンを停止します。
    - 実行時は data/execution.pid に PID を書きます。

- Paper Trading 検証レポート
  - 期間を指定してレポートを生成:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスを指定:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```
  - 実行時は PAPER_TRADING_SQLITE_PATH 環境変数も使えます。

- Streamlit 監視ダッシュボード
  - 起動例（既定の monitoring DB を参照）:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine がダッシュボード情報を更新します。

- AI / レジーム判定・ニューススコアリング（プログラム経由で利用）
  - OpenAI API キー（OPENAI_API_KEY）が必須。関数:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 例: DuckDB 接続を渡して呼び出します（スクリプトやバッチ処理内で利用）。

---

## 運用上の注意 / ヒント

- MONITOR_POLL_INTERVAL は 0 以下の値が与えられるとデフォルト（60秒）にフォールバックします。
- run_monitoring は Settings.env に関係なく「本番の sqlite_path」を使用して監視データを記録します（監視は常に本番 DB を参照する設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 専用 DB を使用します（本番 DB と分離）。
- プロセス優先度の設定（High）を試みますが、権限不足等で失敗した場合は警告になり実行は継続します。
- kill.flag / stop_requested.flag:
  - KillSwitch はリスク条件に応じて Settings.kill_flag_path（デフォルト data/kill.flag）を書き込み、外部から実行停止を促します。
  - stop_requested.flag（デフォルト data/stop_requested.flag）を作成すると run_monitoring / run_execution は安全に終了します。
- OpenAI を使う機能は API エラー時にフェイルセーフ（0.0 等）で続行する箇所が多く、例外は過度に投げない設計です。ただし API キーが未設定だと ValueError を投げる関数があります。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / Settings の読み取り・管理（.env 自動読み込み）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（Paper Trading モード対応）

  - ai/
    - news_nlp.py — raw_news を OpenAI でスコアリングし ai_scores に書き込む処理
    - regime_detector.py — ETF MA200 とマクロニュース（LLM）で市場レジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py — monitoring 用 SQLite テーブル初期化と永続化 API（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウンやポジション数上限チェック
    - alert_manager.py — LINE 通知ラッパー
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各監視を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード

  - execution/
    - order_manager.py — Order State Machine の外向き API
    - reconciler.py — 起動時の照合・自動復旧
    - （その他：broker_factory, execution_engine, order_repository 等は実装想定）

  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数算出・丸め・集約キャップ処理
    - risk_adjustment.py — セクターキャップ / レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
    - __init__.py

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ
    - __init__.py

- data/
  - monitoring.db（デフォルト、監視 DB）
  - kabusys.duckdb（DuckDB ファイル）
  - paper_trading.db（Paper Trading 用 DB）
  - kill.flag / stop_requested.flag / execution.pid（ランタイムで使用）

---

## 開発者向けメモ

- Settings クラスはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env をロードします。テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を使ったリサーチ関数（research/*.py）は prices_daily / raw_financials / raw_news 等のテーブルを前提としています（データ準備が必要）。
- ログレベルは環境変数 LOG_LEVEL で制御可能です（DEBUG/INFO/...）。
- OpenAI API との呼び出しは内部でリトライ・バックオフやレスポンス検証を行う設計です。テスト時は _call_openai_api をモックすることを推奨します。

---

## よくあるトラブルと対処

- OpenAI API KEY がない／空： AI 関数は ValueError を投げます。OPENAI_API_KEY を設定してください。
- monitoring DB が見つからない： streamlit ダッシュボードなどは MonitoringEngine を先に起動して DB を作成・更新してください。あるいは手動で data ディレクトリとファイルを準備してください。
- プロセス優先度の設定失敗： 権限がない場合は警告が出ますが処理自体は継続します。
- stop/kill フラグの取り扱い： kill.flag は KillSwitch が書き込みます。開発・デバッグ時は data/kill.flag を削除してから再起動してください。

---

必要であれば README に具体的な .env.example、requirements.txt、運用チェックリスト（デプロイ手順、systemd ユニット例など）を追加できます。どの情報を追記しますか？