# KabuSys

日本株自動売買システムのコアライブラリ（モニタリング・実行エンジン・ポートフォリオ構築・リサーチ・AIユーティリティ等）。この README はリポジトリ内の主要モジュールに基づき、セットアップ方法・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な責務は次の通りです。

- 注文（Order）ライフサイクルの管理（作成 → 送信 → 同期 / リコンシリエーション）
- リスク管理（ドローダウン、ポジション上限などの監視）
- システム監視（CPU/メモリ/ディスク、Execution プロセス死活、データ鮮度）
- ポートフォリオ構築（候補選定、重み計算、ポジション決定）
- リサーチ（ファクター計算、将来リターン、IC 等）
- AI ユーティリティ（ニュースの NL 評価によるスコアリング、レジーム検出）
- 監視用ダッシュボード（Streamlit）やレポート生成ツール（Paper Trading 検証）

設計方針としては、DB（SQLite / DuckDB）と独立して純粋関数群を用いる箇所と、永続化層（MonitoringDB, OrderRepository）を分離してあります。また、本番環境 / paper_trading 環境を切り替えられるようになっており、paper_trading は本番 DB と完全に分離して動作します。

---

## 機能一覧

- ExecutionEngine 起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading のときは Mock ブローカー（paper_trading DB に記録）
  - プロセス優先度の設定、Reconciler による再起動時の自動復旧
- Monitoring（run_monitoring / MonitoringEngine）
  - SystemMonitor: プロセス死活、CPU/MEM/DISK、データ鮮度の監視
  - TradeMonitor: 注文滞留、約定価格の異常検出
  - RiskMonitor: ドローダウン、ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件達成時にフラグファイルを書き ExecutionEngine に停止を指示
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - SQLite に監視ログを永続化（monitoring_db）
  - Streamlit ダッシュボード（監視結果の可視化）
- Portfolio モジュール
  - 候補選定 (select_candidates)
  - 等金額 / スコア加重の重み計算
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター上限・レジーム乗数の適用
- Research モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）や統計サマリ
- AI モジュール
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に書込
  - regime_detector: ETF(ma200) とマクロニュースの LLM スコアを合成して market_regime を算出
  - 再試行・フェイルセーフ・レスポンスバリデーション等を実装
- ツール
  - paper_verification_report: paper_trading DB を解析して検証レポートを生成

---

## セットアップ手順（開発環境向け）

前提：
- Python 3.9 以上（コードは typing の近代機能を使用）
- SQLite（標準ライブラリ内）
- DuckDB（Python パッケージ）
- 外部 API（OpenAI）や LINE 通知を使う場合は API キー等が必要

例: 仮想環境の作成・依存パッケージのインストール

1. 仮想環境作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージをインストール（最小例）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   実際のプロジェクトでは pyproject.toml / requirements.txt があればそちらを使用してください。
   （パッケージ名はコードで使われているライブラリに基づく提案です）

3. プロジェクトをインストール（任意）
   ```
   pip install -e .
   ```
   （パッケージ化済みの場合）

4. データディレクトリ準備
   ```
   mkdir -p data
   ```
   デフォルトの DB パスは:
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db

5. 環境変数の設定
   - .env / .env.local をプロジェクトルートに配置するか、OS 環境で設定します。
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject。デフォルト: instant）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト: 60）

   例 .env（最低限の例）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方（主要コマンド・エントリポイント）

注意: 各スクリプトはパッケージとして実行可能です（python -m kabusys.<module>）。

1. 監視ループを起動（監視デーモン）
   ```
   python -m kabusys.run_monitoring
   ```
   - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔（秒）を上書き可能（例: 30）
     ```
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     ```
   - 監視は常に「本番」向けの sqlite_path を使用します（KABUSYS_ENV に依らず）。

2. 実行エンジンを起動（ExecutionEngine）
   ```
   python -m kabusys.run_execution
   ```
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と完全に分離されます。
   - 起動時にプロセス優先度を "high" に設定します（可能な限り）。

   例: Paper trading を使う
   ```
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```

3. Streamlit 監視ダッシュボード
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - DB は読み取り専用で開かれます。監視ループが monitoring.db を生成・更新します。
   - ブラウザで可視化（Overview, Positions, Orders, System）。

4. Paper Trading 検証レポートの生成
   ```
   python -m kabusys.tools.paper_verification_report
   ```
   - 期間指定:
     ```
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     ```
   - DB パス指定:
     ```
     python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
     ```
   - デフォルトの DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

5. AI スコアリング / レジーム判定（プログラムから呼び出す）
   - DuckDB 接続を作成して関数を呼びます（例は Python スクリプト内で実行）。
     ```python
     import duckdb
     from datetime import date
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     count = score_news(conn, date(2026, 4, 1), api_key="sk-...")
     print("scored:", count)
     ```
   - regime_detector の場合:
     ```python
     from kabusys.ai.regime_detector import score_regime
     score_regime(conn, date(2026,4,1), api_key="sk-...")
     ```

6. その他
   - 多くの内部モジュールは DuckDB / SQLite 接続を引数として受け取り純粋関数として利用できます（研究・検証用）。

---

## 主要設定の説明（抜粋）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - 挙動例: paper_trading では MockBroker を使用し DB を切り分ける

- MONITOR_POLL_INTERVAL
  - 監視ループ（run_monitoring）のポーリング間隔（秒）。デフォルト 60。

- PAPER_FILL_MODE
  - paper_trading 時のモック約定挙動
  - instant / partial / never / reject

- PAPER_TRADING_SQLITE_PATH
  - paper_trading 用 SQLite DB のパス（デフォルト: data/paper_trading.db）

- OPENAI_API_KEY
  - news_nlp / regime_detector で使用。未設定時は ValueError を投げる関数あり（使う場合は必須）。

- DUCKDB_PATH / SQLITE_PATH
  - DuckDB / monitoring SQLite のパス（デフォルト: data/kabusys.duckdb, data/monitoring.db）

- PID_FILE_PATH / KILL_FLAG_PATH
  - Execution のプロセス管理用ファイルパス（デフォルト: data/execution.pid, data/kill.flag）

- LOG_LEVEL
  - ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys の主要ファイルとディレクトリの概略です。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env の読み込みと Settings
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite 永続化層（init / MonitoringDB）
    - system_monitor.py        — CPU/メモリ/ディスク / データ鮮度 / PID チェック
    - trade_monitor.py         — 注文滞留 / 約定異常検出
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — フラグファイルによる停止指示
    - alert_manager.py         — LINE 通知
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py   — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - ... （ブローカー関連）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの LLM スコアリング
    - regime_detector.py     — 市場レジーム判定（マクロ + ma200）
  - data/
    - pipeline.py / stats.py  — DuckDB からのデータ取得や統計ユーティリティ（参照される想定）
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

（実際のリポジトリでファイル数がさらに多数存在する場合があります。上は主要コンポーネントの抜粋です。）

---

## 運用上の注意 / ベストプラクティス

- paper_trading を使う場合、本番 DB と分離されていることを必ず確認してください（PAPER_TRADING_SQLITE_PATH を明示）。
- OpenAI 等 API のキーは安全に管理し、リポジトリにハードコーディングしないでください。
- MONITOR_POLL_INTERVAL は 1 以上の整数であることを確認してください（不正値はデフォルトにフォールバックします）。
- Kill Switch はデフォルトで data/kill.flag を作成します。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START を使って自動クリアする運用も可能です。
- streamlit で DB を開く際は読み取り専用 URI を使う（dashboard は READ-ONLY を推奨）。

---

## よくある操作例（まとめ）

- 監視開始:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン（Paper）起動:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Streamlit ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースに含まれるドキュメントとソースを参照して作成しています。さらに具体的な運用手順、CI/CD、テスト、パッケージ化情報等が必要な場合は追記可能です。必要があればどの項目を詳しく補足するか教えてください。