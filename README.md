# KabuSys

日本株自動売買システムの軽量実装（ライブラリ兼実行スクリプト群）。

以下はこのリポジトリの主要コンポーネント・使い方・セットアップ手順の概要です。

---

## プロジェクト概要

KabuSys は、シグナル → 発注 → モニタリング → リスク制御 の一連の自動売買ワークフローを想定したモジュール群です。  
主な機能は以下の通り：

- 発注エンジン（ExecutionEngine）と OrderManager / Reconciler による発注・再同期
- 監視システム（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送信（LINE）
- Paper Trading 用の隔離された DB / Mock ブローカ動作
- DuckDB を用いたリサーチ・ファクター計算（momentum/volatility/value 等）
- ニュースを用いた AI スコアリング（OpenAI）と市場レジーム判定
- Streamlit ベースの監視ダッシュボード
- 検証レポート生成ツール（Paper Trading 用）

設計方針として、本番 DB と Paper Trading DB を分離し、監視・ログ周りは SQLite に永続化します。OpenAI 呼び出しはリトライ・フェイルセーフが入っています。

---

## 主な機能一覧

- Execution
  - 発注処理、リスク管理、発注リコンシリエーション
  - Paper Trading モード（KABUSYS_ENV=paper_trading）で MockBroker を利用し DB を分離
- Monitoring
  - CPU / メモリ / ディスク / プロセス存在チェック
  - 注文滞留検出、約定価格異常検出
  - ドローダウン・ポジション上限の監視と kill.flag による強制停止
  - LINE への通知（冷却時間管理あり）
  - Streamlit ダッシュボード表示
- Research
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の統計ツール
- AI
  - ニュースのセンチメントを OpenAI (gpt-4o-mini 等) で評価し ai_scores へ格納
  - マクロニュース × ETF MA200 を組み合わせた市場レジーム判定
- Tools
  - Paper Trading の検証レポート生成スクリプト

---

## 要件（想定）

- Python 3.9+（型注釈・モダンライブラリ使用を想定）
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリで対応）

実プロジェクトで使用するバージョンは pyproject.toml 等で管理してください。

---

## セットアップ手順

1. リポジトリをチェックアウトして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   ※ requirements.txt がない場合は上記の主要ライブラリを個別にインストールしてください。

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 最低限設定すべき環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: Monitoring SQLite DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に必要
   - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant | partial | never | reject）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

   例 (.env):
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

6. 初回起動時は Monitoring 用のテーブルは自動で作成されます（init_monitoring_db が実行されます）。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（通常の運用 or paper_trading 切替）
  - KABUSYS_ENV=paper_trading を指定すると Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し Mock ブローカー動作になります。
  - 実行:
    - python -m kabusys.run_execution
  - 停止方法:
    - run_execution は data/stop_requested.flag の存在を監視します。外部からこのファイルを作成すると安全に停止します。
    - また、KillSwitch（監視側）で data/kill.flag が書かれると処理停止を促します。

- Monitoring を起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を使ってログを記録します（KABUSYS_ENV に関わらず）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db` で SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開きます（MonitoringEngine を先に起動してログを蓄積してください）。

---

## 重要なファイル / フラグ

- data/execution.pid: ExecutionEngine が PID を書きます。SystemMonitor はこれを見てプロセスの存在を確認します。
- data/stop_requested.flag: run_execution / run_monitoring がこのファイルの存在を見て安全に停止します。
- data/kill.flag: KillSwitch が書き込むフラグ。ExecutionEngine の起動時設定（Settings.kill_flag_clear_on_start）で開始時にクリアできます。
- monitoring DB（デフォルト: data/monitoring.db）: system_status / trade_logs / positions / risk_logs / dashboard などを保持します。
- paper_trading DB（デフォルト: data/paper_trading.db）: Paper Trading モード専用のログ保存先（本番と完全分離）。

---

## 設定詳細（主な Settings）

- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: MockBroker を利用、DB は PAPER_TRADING_SQLITE_PATH を使用
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒）
- OPENAI_API_KEY: news_nlp / regime_detector の API 呼び出しで使用
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

設定は .env/.env.local または環境変数から読み込まれます。プロジェクトルートの検出は .git または pyproject.toml を基準に行います。

---

## 開発メモ / 注意点

- MonitoringEngine の run は例外をキャッチしてループを継続する設計です。個々のモニターは失敗しても他を阻害しないようになっています。
- AI 周り（news_nlp, regime_detector）は OpenAI 呼び出しの失敗時にフェイルセーフ（スコア 0.0 等）で継続します。
- DuckDB を利用する分析関数は SQL を主体とした実装で、prices_daily や raw_financials テーブルを参照します。
- process_priority の設定（set_process_priority("high")）が起動時に行われます。OS によって権限や挙動が異なります（設定に失敗した場合は警告でスキップされます）。
- テスト目的で `.env` の自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / Settings
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py         — （実装箇所はコードベースに依存）
  - broker_factory.py
  - broker_api.py
- monitoring/
  - monitoring_db.py
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
- ai/
  - news_nlp.py
  - regime_detector.py
- research/
  - factor_research.py
  - feature_exploration.py
- data/                          — 実行時に利用する data ディレクトリ (DB, pid, flags など)
- utils/
  - process_priority.py

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## よくある運用フロー（例）

1. .env を設定し、data ディレクトリを作成
2. DuckDB に prices_daily / raw_financials / raw_news 等のデータを投入（別途 ETL 実行）
3. Monitoring を常時稼働（python -m kabusys.run_monitoring）
4. Execution を起動（python -m kabusys.run_execution）
5. 必要に応じて AI スコアリングや regime 判定を cron 等で実行
6. Streamlit ダッシュボードで監視状況を可視化
7. Paper Trading の検証は paper_trading 環境で実行し、tools のレポートで評価

---

README に記載のない詳細や、実装に関する質問（各モジュールの挙動やテーブルスキーマの詳細、テスト用のモックの使い方等）があれば教えてください。必要に応じて README を拡張します。