# KabuSys

KabuSys は日本株向けの自動売買システム（実装サンプル）です。本リポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築・サイズ計算、リサーチ（ファクター計算）および AI を用いたニュース解析などの主要コンポーネントを含みます。

---

## 概要

- 設計方針
  - 本番（live） / ペーパートレード（paper_trading） / 開発（development）を切り替え可能な設定層を提供。
  - SQLite（監視ログ / ペーパートレード用）と DuckDB（時系列価格・財務データ等）を使用。
  - ExecutionEngine と MonitoringEngine を別プロセスで動かす想定（pid / kill flag による連携）。
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価・レジーム判定機能を搭載。
  - フェイルセーフ設計（API 失敗時のフォールバック・冪等操作・リトライ等）。

---

## 主な機能一覧

- Execution
  - 注文作成、送信、状態同期（Reconciler）
  - リスク管理（RiskManager）や注文管理（OrderManager / OrderRepository）
  - Paper trading mode（MockBrokerClient、専用 SQLite へ記録）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存判定、データ鮮度チェック
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション上限監視、ダッシュボード更新
  - KillSwitch: 危険時に flag（data/kill.flag）を置いて ExecutionEngine を停止
  - AlertManager: LINE Push によるアラート送信（クールダウンあり）
  - Streamlit ダッシュボード（監視状況可視化）
- Portfolio construction
  - 候補選別、等金額・スコア重み配分、セクターキャップ、ポジションサイズ計算（lot 単位処理、aggregate cap）
- Research
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン、IC 計算、統計サマリー
- AI
  - ニュース NLP（銘柄ごとのセンチメントを OpenAI で評価して ai_scores に書き込み）
  - 市場レジーム判定（ETF MA + マクロニュースセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定で稼働率、成功率、レイテンシ等を集計）

---

## 事前準備（セットアップ手順）

1. リポジトリをクローンし、プロジェクトルートに移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - プロジェクトの requirements.txt がある場合はそれを使用してください。ない場合の主要依存例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   ```
   pip install duckdb psutil requests openai streamlit
   ```

4. data ディレクトリを作成
   ```
   mkdir -p data
   ```

5. 環境変数の設定
   - .env をプロジェクトルートに置くと自動で読み込まれます（OS 環境変数優先、.env.local は上書き）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数（例）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能使用時に必要）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）
     - PAPER_FILL_MODE（instant|partial|never|reject, デフォルト: instant）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
   - 例 (.env)
     ```
     KABUSYS_ENV=paper_trading
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     OPENAI_API_KEY=sk-...
     ```

6. 初回 DB 初期化
   - run_execution / run_monitoring 起動時に監視用テーブルは自動で作成されます（init_monitoring_db により冪等で実行）。

---

## 使い方

- 実行エンジン（ExecutionEngine）を起動
  - 通常:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード（環境変数を設定する例）
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 補足: 起動時にプロセス優先度を "high" に設定します（set_process_priority を呼ぶ）。paper_trading では MockBrokerClient を使い、専用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。

- 監視（MonitoringEngine）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を見る想定）。

- Streamlit ダッシュボード（監視表示）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を read-only で開いてダッシュボードを表示します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パスは `data/paper_trading.db`。`--db` で指定可能。

- AI 機能（ニューススコア / レジーム判定）
  - ニュースのスコアリング関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも `OPENAI_API_KEY` を環境変数か引数で指定する必要あり。

- 開発者向けユーティリティ
  - 研究モジュール（kabusys.research）にはファクター計算や IC 計算が含まれており、DuckDB 接続を渡して利用します。

---

## 重要な動作・設定の注意点

- .env の自動読み込み
  - プロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索して `.env` / `.env.local` を読み込みます。OS 環境変数は保護されます。
- DB マイグレーション
  - monitoring DB 初期化時、必要に応じてカラム追加（例: peak_value, latency_ms）を行います（冪等）。
- Kill Switch
  - RiskMonitor 等で危険判定が出ると `data/kill.flag` が書かれ、Execution 側で検出して安全に停止します。flag は `KillSwitch.clear()` により削除可能。
- プロセス優先度と CPU affinity
  - 起動時に set_process_priority("high") を呼び出します。権限不足や未対応 OS の場合は警告を出してスキップします。
- Paper trading 分離
  - KABUSYS_ENV=paper_trading の場合、実際のブローカー API を使わず MockBroker を用いる設計（DB も paper_trading 専用に分離）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数/設定の読み込みと Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- src/kabusys/execution/
  - execution_engine.py (※実装ファイルは存在) — 実行エンジン（起動/セッション管理）
  - order_manager.py — 注文作成/送信の高レベル API
  - order_repository.py — 注文の永続化（SQLite）
  - reconciler.py — 起動時の注文・ポジション再同期ロジック
  - risk_manager.py — 実行時のリスク判定
  - broker_api.py / broker_factory.py — ブローカー抽象・生成
- src/kabusys/monitoring/
  - monitoring_db.py — 監視用 SQLite テーブル定義と簡易アクセス層（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留 / 約定異常チェック
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込み
  - alert_manager.py — LINE Push
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit による監視画面
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数算出・上限や aggregate cap 処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- src/kabusys/research/
  - factor_research.py — モメンタム/バリュー/ボラティリティ計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計
- src/kabusys/ai/
  - news_nlp.py — ニュースの LLM スコアリング、ai_scores 書き込み
  - regime_detector.py — マクロ + ETF MA によるレジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- data/
  - data/kabusys.duckdb（デフォルト）
  - data/monitoring.db（監視 DB、デフォルト）
  - data/paper_trading.db（paper_trading 用 DB、デフォルト）
  - data/execution.pid, data/kill.flag（PID / kill フラグ）

---

## 開発・デバッグ TIPS

- ローカルで Paper Trading を試す場合は `KABUSYS_ENV=paper_trading` を設定し、`PAPER_TRADING_SQLITE_PATH` を確認してください。実ブローカーに影響を与えません。
- DuckDB 接続は SQL を直接実行できるため、研究用途でのデータ抽出やクエリ確認に便利です。
- OpenAI を利用する機能は外部 API に依存するため、テスト時は該当呼び出し関数をモックすることを推奨します（コード内でモック可能なヘルパが用意されています）。
- Monitoring のログ・テーブルは init_monitoring_db で自動生成されます。既存 DB へカラム追加のマイグレーションも含まれます。

---

## おわりに

この README はコード構成と主要な利用方法の概要を示しています。実運用や継続的な拡張（ブローカー接続、注文処理の堅牢化、マスタデータ管理、監視アラートの改善など）を行う際は、それぞれのモジュールにある docstring と注釈を参照してください。質問や追加ドキュメントの要望があれば教えてください。