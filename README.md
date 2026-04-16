# KabuSys

日本株向けの自動売買システム（ライブラリ/実行スクリプト群）。  
本リポジトリには、シグナル→ポートフォリオ構築→発注→監視までの主要コンポーネントと、Research / AI 支援（ニュース NLP・レジーム検出）・監視ダッシュボード等が含まれます。

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- 発注エンジン（ExecutionEngine）：ブローカークライアント経由で注文を発行・管理する
- 監視（Monitoring）：プロセス状態・データ鮮度・注文滞留・リスク等を定期チェックしログ/アラートを出す
- ポートフォリオ構築（Portfolio）：候補選定・重み付け・ポジションサイジングを行う関数群
- Research：DuckDB 上の時系列データからファクター計算・特徴量解析を行う
- AI（news_nlp / regime_detector）：OpenAI を用いたニュースセンチメントや市場レジーム判定
- ツール：Paper Trading の検証レポート生成や Streamlit ダッシュボードなど

設計方針として「本番 DB と paper_trading の分離」「ルックアヘッドバイアス防止」「フェイルセーフ（API 失敗時に続行）」等を重視しています。

---

## 主な機能一覧

- SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度を監視して SQLite にログ化
- TradeMonitor: 滞留注文・約定異常価格の検出とリスクログ化
- RiskMonitor / KillSwitch: ドローダウンやポジション上限でのアラート／kill.flag 発行
- MonitoringEngine: 上記モニタをまとめて周期実行、AlertManager 経由で LINE に通知
- ExecutionEngine 起動スクリプト: 本番/ペーパー切替、Broker クライアント生成、エンジン実行ループ
- Reconciler: 再起動時の注文・ポジション整合性チェック（自動リカバリ）
- Portfolio モジュール: 候補選定、等配分/スコア配分、リスク調整、ポジションサイジング
- Research モジュール: Momentum/Volatility/Value 等のファクター計算、将来リターン / IC / 統計要約
- AI モジュール: OpenAI を使ったニューススコアリング（ai_scores）・レジーム判定（market_regime）
- Streamlit ダッシュボード: SQLite を読み取り専用で可視化
- tools.paper_verification_report: Paper Trading 履歴から検証レポートを出力

---

## 必要要件（例）

- Python 3.10+
- pip パッケージ:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準の sqlite3 モジュールを使用）
- ネットワークアクセス（LINE / OpenAI を使う場合）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（このリポジトリに requirements.txt がない場合は上記パッケージを手動で用意してください）

---

## 環境変数（主要）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（デフォルト等）:

- KABUSYS_ENV: 起動環境。`development` | `paper_trading` | `live`（デフォルト: development）
  - `paper_trading` の場合、MockBroker を使用し DB は `data/paper_trading.db` を使用します（本番 DB と完全分離）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabu ステーション API パスワード
- OPENAI_API_KEY: OpenAI 利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）利用時
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 環境の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（`instant` | `partial` | `never` | `reject`、デフォルト `instant`）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag パス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト: 60）

注意:
- Settings クラスで検証を行っています。不正な値や未設定の必須変数は起動時に例外になります。

---

## セットアップ手順（開発用サンプル）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成（例は下記）
5. DuckDB / data ディレクトリなどを準備
6. DB 初期化は実行スクリプトが自動で行います（init_monitoring_db を使用）

例 .env（必要なもののみ抜粋）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

---

## 使い方（主な起動コマンド）

- Monitoring を起動（ポーリング監視）
  - モジュール実行:
    - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - data/stop_requested.flag を作るとループが検知して停止します（同ディレクトリの stop フラグ）
    - KeyboardInterrupt（Ctrl+C）でも停止します

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用 DB と MockBroker を使います
  - Execution 停止シグナル:
    - data/stop_requested.flag を作ると実行中のエンジンに停止要求を送ります
    - または KillSwitch が `data/kill.flag` を書き込むと起動しない/停止する設計です
  - PID:
    - 実行時に `data/execution.pid` を書きます（Settings.pid_file_path）

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を読み取り専用で開きます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/data/paper_trading.db
    - 省略時は環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト `data/paper_trading.db` を使用

- AI 関連（プログラム内呼び出し）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、OpenAI API キーを引数または環境変数から取得します

---

## 停止 / フラグ制御

- data/stop_requested.flag: 起動スクリプト（run_monitoring/run_execution）はこのファイルの存在を監視し、存在すればグレースフルに停止します（運用用の手動停止フラグ）。
- data/kill.flag: KillSwitch により書き込まれるファイル。ExecutionEngine の起動・継続を阻害する目的で使用。KillSwitch は条件（ドローダウン等）を満たした場合に理由をファイルに書き込みます。
- KillSwitch.clear() が起動時に kill.flag を削除する設定もあります（Settings.kill_flag_clear_on_start に基づく）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM ベースセンチメント評価・ai_scores 書き込み
  - regime_detector.py — マクロ + ETF MA200 でレジーム判定、market_regime 書き込み
- monitoring/
  - monitoring_db.py — SQLite スキーマ定義・CRUD（MonitoringDB）
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各監視ロジック
  - monitoring_engine.py — 監視の束ね実行
  - alert_manager.py — LINE への通知
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, ...（発注周り）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
- research/
  - factor_research.py, feature_exploration.py — DuckDB を使ったファクター計算・解析
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- utils/
  - process_priority.py — プラットフォーム横断のプロセス優先度 / CPU affinity 設定

data/（実行時に使用／生成）
- data/monitoring.db — 監視ログ（Settings.sqlite_path）
- data/paper_trading.db — paper_trading 用 SQLite（Settings.paper_sqlite_path）
- data/kabusys.duckdb — DuckDB（Settings.duckdb_path）
- data/execution.pid — ExecutionEngine の PID
- data/kill.flag, data/stop_requested.flag — フラグファイル

---

## 運用上の注意 / 補足

- paper_trading モードは本番データベースと完全に分離しているため、検証やバックテストに適しています。
- OpenAI / LINE API を使用する機能は外部サービス依存のため、API キーが無い場合はスキップまたは例外になる箇所があります（モジュール毎に挙動が異なる）。事前に環境変数を設定してください。
- process_priority.set_process_priority("high") を起動初期化で呼び出します。権限によっては設定に失敗することがある旨の警告が出ますが、動作継続します。
- DuckDB / SQLite のスキーママイグレーションは monitoring_db.init_monitoring_db で簡単なカラム追加を行いますが、大規模なマイグレーションは別途検討してください。
- Logging は各モジュールで行っています。動作確認時はログレベルを適宜変更してデバッグしてください（Settings.log_level を使用）。

---

## 開発・テスト

- モジュール単体の純粋関数（portfolio/*、research/*）は外部副作用が小さく単体テストが書きやすい設計です。
- API 呼び出し（OpenAI / ブローカー等）はモックしやすい設計（_call_openai_api の差し替え等）になっています。ユニットテストでは patch 等で外部呼び出しを置き換えてください。

---

README は以上です。必要があれば、セットアップ用の requirements.txt / .env.example のテンプレートや、主要コマンドの systemd / supervisor 用のサービス定義テンプレートも作成します。どちらを希望しますか？