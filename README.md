# KabuSys

日本株向け自動売買システムの軽量実装。シグナル処理→発注→監視／リスク管理／レポーティング／研究用ファクター計算・AI ベースのニュースセンチメント評価までを含むモジュール群を提供します。

主な設計方針：
- 本番 DB（SQLite / DuckDB）と paper trading を分離可能
- 各コンポーネントは純粋関数／軽量クラスでテストしやすい設計
- 外部 API 呼び出し（OpenAI 等）は明示的にキーを渡すか環境変数で設定
- ルックアヘッドバイアスに配慮した時刻／クエリ設計

---

## 機能一覧

- 実行（ExecutionEngine）
  - ブローカー抽象化（実口座 or MockBrokerClient for paper trading）
  - 注文管理（OrderManager）、リスク管理、リコンシリエーション（Reconciler）
  - PID ファイル管理・停止フラグ監視（data/execution.pid / data/stop_requested.flag）

- 監視（Monitoring）
  - システム（CPU/メモリ/ディスク）・プロセス・データ鮮度監視（SystemMonitor）
  - 注文滞留・約定異常の検出（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - KillSwitch による停止フラグ（data/kill.flag）書込み
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（read-only 接続）

- ポートフォリオ構築（Portfolio）
  - 候補選定、等配分・スコア加重配分、セクター制約、ポジションサイズ計算

- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算、ファクター統計サマリ

- AI モジュール
  - ニュースを LLM（OpenAI）で評価し ai_scores に書き込む（news_nlp）
  - マクロセンチメント + ETF MA200 を合成して市場レジーム判定（regime_detector）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発環境）

前提：Python 3.10+ を想定（typing 機能を使用）。適切な仮想環境を推奨します。

1. リポジトリをクローンし、仮想環境を作成／有効化
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要なパッケージをインストール
   （プロジェクトに requirements.txt は含まれていない想定のため、下記をインストールしてください）
   ```
   pip install duckdb psutil requests openai streamlit
   ```

3. データディレクトリを作成
   ```
   mkdir -p data
   ```

4. 環境変数（.env）を用意
   - 自動ロード: `src/kabusys/config.py` がプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると無効化）。
   - 必須／推奨変数の例（.env）:
     ```
     KABUSYS_ENV=development            # development | paper_trading | live
     OPENAI_API_KEY=<your-openai-key>   # AI 機能を使う場合必須
     JQUANTS_REFRESH_TOKEN=<token>      # （必要に応じて）
     KABU_API_PASSWORD=<password>       # kabu API を使う場合
     LINE_CHANNEL_ACCESS_TOKEN=         # LINE 通知を使う場合
     LINE_USER_ID=
     PAPER_FILL_MODE=instant            # instant | partial | never | reject
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     ```

5. DB 初期化
   - 実行 / 監視スクリプト起動時に `monitoring_db.init_monitoring_db` が自動でテーブルを作成します。特別な初期化コマンドは不要です。

注意:
- Settings 内の必須環境変数が未設定だと例外が発生します（例: JQUANTS_REFRESH_TOKEN を要求するプロパティにアクセスした場合）。必要な変数だけ設定してください。

---

## 使い方

基本的な起動例を示します。作業ディレクトリはプロジェクトルートであることを想定します。

1. ExecutionEngine（エンジン起動）
   - 本番 / 開発 / paper_trading は `KABUSYS_ENV` により切替。
   - paper_trading の場合、MockBrokerClient を使い DB は `data/paper_trading.db` に書き込まれ本番 DB と分離されます。
   ```
   # paper trading の例
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution
   ```
   - 実行中は `data/execution.pid` が利用され、`data/stop_requested.flag` が存在すると早期終了します。

2. Monitoring（監視ループ起動）
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルトは 60 秒。
   - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（設計上の注意）。
   ```
   export MONITOR_POLL_INTERVAL=30
   python -m kabusys.run_monitoring
   ```

   停止:
   - 監視・実行ループを外部から静かに止めたい場合はプロジェクトの `data/stop_requested.flag` を作成すると両方のループが検出して終了します。
   - KillSwitch（監視側）による強制停止は `data/kill.flag` に理由を書き込みます。`KillSwitch.evaluate()` が条件を満たすと書き込まれ、ExecutionEngine 側は起動時や監視でこれを検知して停止します。

3. Streamlit ダッシュボード（監視用）
   - 読み取り専用で SQLite に接続して監視情報を表示します。
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

4. Paper Trading 検証レポート
   - Paper Trading DB（デフォルト: data/paper_trading.db）から期間指定で検証レポートを生成します。
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```

5. AI 機能（ニューススコア付与 / レジーム判定）
   - OpenAI API キーが必要です（環境変数または関数引数で渡す）。
   - 例（Python 内呼び出し）:
     ```py
     from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, date(2026, 4, 10), api_key="sk-...")
     ```

---

## 主要ファイルとディレクトリ構成

（抜粋・概要）

- src/kabusys/
  - __init__.py — バージョン等
  - config.py — 環境変数／.env のロードと Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト

- src/kabusys/execution/
  - execution_engine.py (省略) — 実際のエンジン起動ロジック（ファイルはコードベースに存在）
  - order_manager.py — 注文の作成 / 同期など外向き API
  - order_repository.py — SQLite を利用した注文永続化
  - reconciler.py — 起動時の注文・ポジション再同期
  - broker_factory.py, broker_api.py — ブローカー抽象、Mock 実装等

- src/kabusys/monitoring/
  - monitoring_db.py — 監視用 SQLite テーブル定義 / CRUD ユーティリティ
  - system_monitor.py — CPU/メモリ/Disk・データ鮮度・PID チェック
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の書き込み・管理
  - alert_manager.py — LINE への通知送信
  - monitoring_engine.py — 複数モニターの束ねとループ
  - streamlit_dashboard.py — 監視 Dashboard（streamlit）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクター制約・レジーム乗数
  - position_sizing.py — 発注株数計算

- src/kabusys/research/
  - factor_research.py — ファクター (momentum/value/volatility)
  - feature_exploration.py — 将来リターン・IC・統計

- src/kabusys/ai/
  - news_nlp.py — raw_news を LLM で評価し ai_scores に書き込み
  - regime_detector.py — マクロ + MA200 を合成して daily market regime 判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート出力ツール

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - (データファイル、デフォルト)
  - monitoring.db (SQLite) — 監視ログ（Settings.sqlite_path）
  - paper_trading.db (SQLite) — paper trading 用 DB（Settings.paper_sqlite_path）
  - kabusys.duckdb — 価格等集計用（Settings.duckdb_path）
  - execution.pid — 実行中 PID（生成される）
  - stop_requested.flag — 外部停止フラグ（両ループで検出）
  - kill.flag — KillSwitch の停止理由書き込み用

---

## 環境変数（主要）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - run_execution は paper_trading の場合、MockBrokerClient と専用 DB を使用します。
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。デフォルト 60。
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI を使う機能で使用
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 各 API の認証情報
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

注意: Settings クラスは一部プロパティで未設定時に ValueError を投げます（必須変数は _require() でチェック）。

---

## 運用上の注意 / トラブルシューティング

- 監視（Monitoring）は常に Settings.sqlite_path（production 想定）を使う設計です。paper_trading と監視 DB を分離したい場合は環境変数や設定でパスを調整してください。
- stop_requested.flag と kill.flag の違い:
  - stop_requested.flag: 両 run スクリプトのループを止めるための一般的なフラグ（存在を検出して終了）。
  - kill.flag: KillSwitch が作成する「緊急停止指令（理由付き）」で ExecutionEngine 側の停止トリガーになる。kill.flag は明示的に削除するまで残ります（KillSwitch.clear() で削除可）。
- データベースのマイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存 DB に列が無ければ ALTER TABLE で追加します（例: peak_value, latency_ms）。
- OpenAI 使用時:
  - API 呼び出しはリトライやフォールバックを実装していますが、API キーやネットワーク問題には注意してください。テスト時は _call_openai_api をモック可能です。
- プロセス優先度:
  - run_* 起動時に set_process_priority("high") を呼び出します。権限不足により失敗する場合は警告を出してスキップします。
- ログ:
  - スクリプトは基本的に logging.basicConfig(level=logging.INFO) を使います。詳細デバッグが必要な場合は LOG_LEVEL=DEBUG に設定してください。

---

## 開発／拡張のヒント

- 各モジュールは比較的独立しています。unit test を書く場合は DB 接続や OpenAI クライアントをモックすれば良い設計です。
- portfolio や research の関数群は pure function を意識して書かれているため単体テストが容易です。
- news_nlp や regime_detector の OpenAI 呼び出しは `_call_openai_api` を patch することでテスト時に外部依存を切り離せます。

---

必要であれば、README に含めるサンプル .env、systemd サービスファイル例、Dockerfile／docker-compose の雛形、また各モジュールの詳細な API ドキュメントを追加で作成します。どれを優先しますか？