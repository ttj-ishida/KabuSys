# KabuSys

日本株自動売買システムの軽量なモジュール群。ポートフォリオ構築、発注エンジン、監視、AI によるニュースセンチメントなどの機能を含みます。本 README はコードベース（src/kabusys 以下）を元にした利用ガイドです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤を構成するライブラリ兼実行スクリプト群です。主な責務は次のとおりです。

- 取引ロジック（オーダー管理、発注エンジン、リコンシリエーション）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 監視（システム稼働、注文滞留、リスク・ドローダウン監視、アラート）
- 研究 / ファクター計算（DuckDB 上の時系列データ処理）
- AI 連携（OpenAI を使ったニュースセンチメント評価・レジーム判定）
- 運用用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード等）

設計方針として、DuckDB/SQLite をデータ層に使い、外部発注 API との分離（paper_trading 用 DB 分離）や、LLM 呼び出しに対するフェイルセーフ処理が組み込まれています。

---

## 主な機能一覧

- Execution
  - 発注フロー（OrderManager、ExecutionEngine、BrokerClientFactory）
  - 再起動時のリコンシリエーション（Reconciler）
  - Risk Manager（ポジション・ドローダウン等の制御）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス存在確認
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・保有上限監視（kill flag 連携）
  - AlertManager: LINE によるプッシュ通知（クールダウン機能あり）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定（スコア順）、等金額・スコア加重、リスクベース割付、単元丸め
  - セクター集中制限、レジーム乗数
- Research
  - ファクター（Momentum/Volatility/Value）計算
  - 将来リターンの計算、IC（Information Coefficient）等の統計ユーティリティ
- AI
  - news_nlp: raw_news -> OpenAI で銘柄ごとのセンチメントスコア算出（ai_scores へ書き込み）
  - regime_detector: ETF ma200 とマクロニュースを合成して日次レジーム判定

---

## セットアップ手順

前提: Python 3.9+（型ヒントに基づく）、git clone でプロジェクトを入手し、プロジェクトルートで操作します。

1. 仮想環境を作成・有効化（推奨）
   - venv の例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # Linux/macOS
     .venv\Scripts\activate      # Windows
     ```

2. 依存パッケージのインストール
   - 必要パッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit (ダッシュボード利用時)
   - pip 例:
     ```
     pip install duckdb psutil openai requests streamlit
     ```

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みは .git または pyproject.toml が存在するルートで行われます）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須・代表的な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 SQLite、デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、空なら送信スキップ）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

   - 簡易 `.env` 例:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

4. データディレクトリ作成
   ```
   mkdir -p data
   ```

---

## 使い方（実行例）

以下は主要な起動・ツールの利用方法です。

1. 監視ループ起動（Monitoring）
   - 簡易実行:
     ```
     python -m kabusys.run_monitoring
     ```
   - 概要:
     - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。1 秒未満や 0 のような値は無効扱いでデフォルトにフォールバックします。
     - 監視は KABUSYS_ENV にかかわらず監視用の本番 sqlite_path を使用します（SQLite に system_status, trade_logs, positions, risk_logs, dashboard テーブルを初期化します）。
     - 停止方法: プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して停止します。

2. ExecutionEngine 起動（発注エンジン）
   - 実行:
     ```
     python -m kabusys.run_execution
     ```
   - 概要:
     - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い paper_trading 用 DB（`PAPER_TRADING_SQLITE_PATH`、デフォルト data/paper_trading.db） に完全分離して記録します。
     - 起動時に `data/stop_requested.flag` が存在すれば起動しません。実行中に同フラグが作成されると Engine に停止命令を送り安全に終了します。
     - 実行中、`data/execution.pid` に PID を書き込みます（stale PID の検出と削除機能あり）。

3. Paper Trading 検証レポート生成
   - 実行:
     ```
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     ```
   - 概要:
     - デフォルト DB: `data/paper_trading.db`。`--db` で上書き可。
     - 稼働率 / 注文成功率 / 送信率 / レイテンシ(P95) 等を算出し、PASS/FAIL を出力します。

4. Streamlit 監視ダッシュボード
   - 実行:
     ```
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
     ```
   - 概要:
     - monitoring DB を読み取り専用で開き、Overview / Positions / Orders / System タブで可視化します。

5. AI 系（ニューススコア・レジーム判定）
   - news_nlp.score_news / regime_detector.score_regime 等の関数は DuckDB 接続と対象日を受け取り、OpenAI API を呼び出して ai_scores / market_regime テーブルを書き込みます。
   - 必要: OPENAI_API_KEY（関数引数で渡すことも可）。API 呼び出しは冗長なリトライや JSON バリデーションを含む実装です。

---

## 重要な挙動・運用メモ

- .env 自動読み込み:
  - プロジェクトルートは `src/kabusys/config.py` の実装により .git または pyproject.toml を基準に探索されます。見つかった場合 `.env` と `.env.local` が自動で読み込まれます。OS 環境変数は上書きされません（ただし `.env.local` は override=True のため `.env` の値を上書きします）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- MONITOR の挙動:
  - run_monitoring は監視ログに関係する DB（sqlite_path）を初期化します（init_monitoring_db は冪等）。monitoring は常に指定の sqlite_path（本番用）を使用します。
- Execution の DB 分離:
  - KABUSYS_ENV が `paper_trading` の場合、発注処理は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
- 停止・Kill
  - 運用上の強制停止フロー:
    - `data/stop_requested.flag` を作成すると run_monitoring / run_execution が検知して停止します（両スクリプトとも使用）。
    - kill_switch（監視内）は条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送るために利用されます。kill flag は明示的にクリアする API（KillSwitch.clear）が備わっています。
- プロセス優先度:
  - run_monitoring / run_execution 起動時に set_process_priority("high") を呼び出します。psutil による実装で OS による差分処理あり（権限不足等で無効化される場合は警告ログ）。

---

## 環境変数（代表的・補足）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
- PID_FILE_PATH, KILL_FLAG_PATH（監視・実行時に Settings から読み込まれます）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

詳細は src/kabusys/config.py を参照してください（値検証・デフォルトが実装されています）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要構成です。実際のファイルはコード参照。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py       — SQLite ベースの永続化層（system_status 等）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - ... (発注関連)
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
  - utils/
    - process_priority.py

プロジェクトルートには data/ ディレクトリ（DB ファイルやフラグファイル）が置かれる想定です。

---

## 開発・運用上の注意点

- DB マイグレーション: monitoring_db.init_monitoring_db はシンプルなマイグレーション処理を含みますが、より複雑なスキーマ変更は適切な手順で行ってください。
- LLM 呼び出し: OpenAI API 呼び出しはリトライ・バリデーションを備えていますが、コストやレート制限に注意してください。テスト時は API 呼び出し部分をモックすることを推奨します（コード中に差し替え用のコメントあり）。
- 権限: set_process_priority / cpu_affinity の呼び出しは権限不足で失敗する場合があります（警告ログ）。その場合もプロセスは継続します。
- ログ: 各モジュールは logging を使用しています。運用では LOG_LEVEL 環境変数やログ出力設定を行うことを検討してください。

---

## 参考（主なエントリポイント）

- 監視ループ: python -m kabusys.run_monitoring
- 発注エンジン: python -m kabusys.run_execution
- Paper report: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- Streamlit ダッシュボード: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードのコメントと実装に基づいてまとめています。利用・運用にあたっては src/ 以下の各モジュールを参照して詳細な動作・パラメータを確認してください。必要があればセットアップ手順や運用手順をさらに詳しく追記できます。