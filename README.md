# KabuSys

KabuSys は日本株の自動売買およびそれを支えるデータ処理・監視ツール群を含むプロジェクトです。取引エンジン、発注管理、監視/アラート、ポートフォリオ構築、ファクター研究、LLM を用いたニュースセンチメント評価などの機能を備えています。

---

## プロジェクト概要

- 言語: Python
- 目的: 日本株の自動売買運用に必要な実行系（ExecutionEngine）、監視系（MonitoringEngine）、リサーチ/ポートフォリオ構築、AI（ニュースNLP・レジーム判定）を提供する
- 永続化: SQLite（監視ログ / paper trading 用）および DuckDB（時系列・ファイナンスデータ）
- 設計方針:
  - 本番/ペーパートレードを分離（DB・挙動）
  - ルックアヘッドバイアス回避（日時参照に注意）
  - フェイルセーフ（APIエラー時は安全にフォールバック）

---

## 主な機能一覧

- Execution（起動スクリプト / 自動復旧）
  - 起動スクリプト: `kabusys.run_execution`
  - ブローカーファクトリにより本番または MockBroker を選択（`KABUSYS_ENV=paper_trading`）
  - リコンシリエーション（起動時の注文同期、ポジション差分検出）
  - 注文状態管理（OrderManager / OrderRepository）

- Monitoring（監視）
  - 起動スクリプト: `kabusys.run_monitoring`
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視（MonitoringEngine）
  - LINE によるアラート送信（AlertManager）
  - kill.flag による ExecutionEngine 停止指示（KillSwitch）
  - Streamlit ベースの監視ダッシュボード（`streamlit_dashboard.py`）

- Portfolio（銘柄選定・配分・株数決定）
  - 候補選定、等配分/スコア配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算

- Research（ファクター計算 / 特徴量解析）
  - モメンタム / ボラティリティ / バリューのファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー

- AI
  - ニュースの LLM ベースセンチメント評価（OpenAI を利用）
  - マクロニュースと ETF MA200 を組み合わせた市場レジーム判定

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - 環境変数自動読み込み（`.env`, `.env.local`）、`Settings` クラス

- Tools
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## セットアップ手順

1. Python 環境を準備（推奨: 3.10+）
2. 依存パッケージをインストール（プロジェクトに requirements.txt がある想定）
   - 例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - インストール例:
     ```bash
     pip install duckdb psutil requests openai streamlit
     ```
3. プロジェクトルートに `.env`（または `.env.local`）を作成して必要な環境変数を設定
   - 自動ロードはデフォルトで有効。無効化したい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
4. デフォルトのデータディレクトリを作成:
   ```bash
   mkdir -p data
   ```
5. 必要に応じて DuckDB/SQLite のファイルを用意（初回は起動スクリプトがテーブルを作成します）

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` の場合、paper 用 SQLite（デフォルト: data/paper_trading.db）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須・用途に応じて）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（`instant`|`partial`|`never`|`reject`、デフォルト: `instant`）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）

注意: `.env` の読み込みはプロジェクトルート（.git または pyproject.toml を探索）に依存します。

---

## 使い方（主なコマンド例）

- Monitoring を起動（デフォルトのポーリング間隔 60 秒、環境変数 `MONITOR_POLL_INTERVAL` で上書き可）:
  ```bash
  python -m kabusys.run_monitoring
  # 例: 30 秒間隔にする
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV で切替）:
  ```bash
  # 本番/開発
  python -m kabusys.run_execution

  # ペーパートレード
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Streamlit ダッシュボード（監視 DB を読み取り専用で開く）:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成:
  ```bash
  # デフォルト DB を参照
  python -m kabusys.tools.paper_verification_report

  # 期間指定・DB 指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI モジュールのプログラム利用例（Python API 呼び出し）:
  - ニューススコア算出:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="OPENAI_KEY")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="OPENAI_KEY")
    ```

---

## 注意・運用メモ

- Monitoring は KABUSYS_ENV に関係なく監視用の本番 sqlite_path を使います（run_monitoring 内の設計）。
- ExecutionEngine は paper_trading 時に DB を分離するため、ペーパーデータが本番に混ざりません。
- kill.flag（デフォルト: data/kill.flag）を作成すると ExecutionEngine 側で停止シグナルとして検出できます。
- プロセス優先度設定は起動直後に試みますが権限不足時は警告を出してスキップします。
- OpenAI API 呼び出しはリトライとバリデーション処理が実装されていますが、API キーと使用上のコストに注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / Settings
  - run_monitoring.py                 — 監視ポーリング起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py                — SQLite 監視テーブル定義 / DB API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (他、発注関連)
    - execution_engine.py (エンジン本体)
    - broker_factory.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

---

## 貢献・拡張案

- 銘柄別の lot_size 対応（stocks マスタの導入）
- レジーム判定の特徴量拡張（外部マクロデータ等）
- モジュール間テスト整備、CI の導入
- エラー監視・メトリクス（Prometheus 等）追加

---

README に書かれているコマンドは最小限の起動例です。実環境での運用時は必ず .env を整備し、API キーや各種パス・閾値を適切に設定した上で事前検証（ペーパートレード）を行ってください。