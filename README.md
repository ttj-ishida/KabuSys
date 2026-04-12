# KabuSys

日本株自動売買システムのパイソン実装（コアモジュール群）の README。  
このリポジトリは注文発行・実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI 補助（ニュース NLP / レジーム判定）等の機能を提供します。

---

## プロジェクト概要

KabuSys は日本株自動売買のための内部ライブラリ群です。主な役割は次のとおりです。

- 注文作成・送信・状態同期（ExecutionEngine / OrderManager / Reconciler）
- リスク管理（RiskManager、RiskMonitor）
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine / AlertManager）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング）
- リサーチ（定量ファクター計算、将来リターン、IC 等）
- ニュース NLP を用いた銘柄センチメント（OpenAI API 経由）
- Paper Trading モード（本番 DB と分離された専用 SQLite）

設計方針として、可能なかぎり副作用を少なくして純粋関数や明確な永続層（SQLite / DuckDB）で処理を分離しています。ルックアヘッドバイアス防止（target_date 固定等）やフェイルセーフ（API失敗時はフォールバック）などの配慮が組み込まれています。

---

## 主な機能一覧

- Execution（発注・リスク管理・再同期）
  - OrderManager: 注文ライフサイクル（作成→送信→同期）
  - Reconciler: 起動時の自動リコンシリエーション（ブローカーと状態照合）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格監視
  - RiskMonitor: ドローダウン・ポジション数監視 → kill.flag による Execution 停止
  - AlertManager: LINE への通知（クールダウン管理）
  - Streamlit ダッシュボード（監視 UI）
- Portfolio（銘柄選定・重み付け・ポジションサイズ）
  - 等重・スコア重み、セクターキャップ、レジーム乗数、リスクベースのサイズ設計
- Research（DuckDB ベースのファクター / 解析）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン、IC、統計サマリー
- AI（OpenAI を用いた処理）
  - news_nlp.score_news(): ニュース記事を集約して LLM で銘柄別センチメントを算出→ai_scores に保存
  - regime_detector.score_regime(): ma200 乖離 + マクロニュースで市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading の検証レポート出力

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で `|` を使用しているため）
- SQLite / DuckDB をローカルで使用

例: 仮想環境作成とパッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 主要依存の例
pip install duckdb psutil openai requests streamlit
```

（requirements.txt があれば `pip install -r requirements.txt` を推奨）

必須ディレクトリ（存在しない場合は作成）
```bash
mkdir -p data
```

環境変数
- 自動で .env / .env.local をプロジェクトルートから読み込みます（CWD に依存せず __file__ 基点で検索）。無効化するには:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 重要な環境変数（代表）
  - KABUSYS_ENV: 起動環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - SQLITE_PATH: monitoring 用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag（デフォルト: data/kill.flag）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
  - PAPER_FILL_MODE: paper_trading の約定モード（"instant"|"partial"|"never"|"reject"、デフォルト: "instant"）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
  - LOG_LEVEL: ログレベル（"DEBUG","INFO","WARNING","ERROR","CRITICAL"、デフォルト INFO）

例 .env（最小）
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
```

DB 初期化
- 多くの起動スクリプトで init_monitoring_db が実行され、必要テーブル/マイグレーションを自動作成します。手動で用意する必要は通常ありません。

---

## 使い方（主要スクリプト・モジュール）

モジュールとして実行可能なスクリプトはパッケージ形式で呼び出せます（パスに src を含めるかパッケージとしてインストールしてください）。

1. 監視ループ起動（Monitoring）
```bash
# デフォルトで本番用の sqlite_path を使用（Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照）
python -m kabusys.run_monitoring
# またはスクリプト直実行
python src/kabusys/run_monitoring.py
```
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（デフォルト 60 秒）。
- 起動時にプロセス優先度を "high" に設定しようとします（psutil による）。

2. 実行エンジン起動（ExecutionEngine）
```bash
# 本番（デフォルト development では本番 DB を使用）
python -m kabusys.run_execution

# Paper Trading モード（実際のブローカー呼び出しをモックし、data/paper_trading.db を利用）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- paper_trading の場合、BrokerClientFactory が MockBrokerClient を使用し、Paper 用 SQLite に完全分離して記録します。
- 起動時に ExecutionEngine は pid ファイルを利用します（Settings.pid_file_path）。

3. Paper Trading 検証レポート
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# 別 DB を指定
python -m kabusys.tools.paper_verification_report --db /path/to/db.sqlite
```
- 稼働率、注文成功率、送信率、レイテンシ（P95）等を計算して標準出力にレポート表示します。

4. Streamlit ダッシュボード（監視 UI）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 監視 DB を読み取り専用で開いてダッシュボード表示します。

5. AI / レジーム判定・ニュース NLP
- ニュース NLP（銘柄別スコア）:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - api_key が None の場合 OPENAI_API_KEY を参照します。未設定だと ValueError。
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 実行には DuckDB 接続を渡す必要があります（duckdb.connect）。

※ OpenAI 呼び出しはリトライ・バックオフ・バリデーションを備えています。API キーを必ず設定してください。

6. ライブラリとしての利用（Portfolio / Research 等）
- ポートフォリオ構築 API:
  - kabusys.portfolio.select_candidates(...)
  - kabusys.portfolio.calc_equal_weights(...)
  - kabusys.portfolio.calc_score_weights(...)
  - kabusys.portfolio.calc_position_sizes(...)
  - kabusys.portfolio.apply_sector_cap(...)
  - kabusys.portfolio.calc_regime_multiplier(...)
- リサーチ API:
  - kabusys.research.calc_momentum(conn, date)
  - kabusys.research.calc_volatility(conn, date)
  - kabusys.research.calc_value(conn, date)
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)

---

## 重要な挙動メモ / 動作上の注意

- 環境分離
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用する実装になっています（run_monitoring.py の設計）。
  - Execution は KABUSYS_ENV=paper_trading の場合 Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- PID / kill.flag
  - ExecutionEngine は PID ファイルを作成・確認します。KillSwitch は kill.flag を作成すると ExecutionEngine 側に停止シグナルとなる設計です。
  - Settings.kill_flag_clear_on_start を有効にすると起動時に kill.flag を自動削除できます（設定に依存）。
- データ鮮度
  - SystemMonitor は DuckDB の prices_daily を参照してデータ鮮度を判定（デフォルト許容 3 日以下）。
- マイグレーション
  - init_monitoring_db はテーブルを作成するだけでなく、既存 DB に対してカラム追加（例: peak_value, latency_ms）を行います（冪等）。
- OpenAI 呼び出し
  - API レスポンスのバリデーションとクリッピングを実施します。429 / ネットワーク断 / 5xx は指数バックオフでリトライ。
  - テスト時は内部の _call_openai_api をモックできます（ユニットテストのための設計）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・パッケージ一覧（コードベースから抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 永続層（テーブル作成、読み書き）
    - system_monitor.py             — システム監視
    - trade_monitor.py              — 注文監視
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag 管理
    - alert_manager.py              — LINE push 通知
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py        — Streamlit ダッシュボード
  - execution/
    - (OrderManager, Reconciler, ExecutionEngine 等の実装ファイル群)
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
    - news_nlp.py                   — ニュース NLP（OpenAI 経由）
    - regime_detector.py            — レジーム判定
    - __init__.py
  - utils/
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

（実際のファイル構成はリポジトリを参照してください）

---

## よくある質問 / トラブルシューティング

- Q: .env が読み込まれない
  - A: プロジェクトルートの判定は config._find_project_root() によって行われ、.git または pyproject.toml を上位ディレクトリに探索します。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動ロードしてください。
- Q: OpenAI キーが無いときに AI 機能だけを無効にしたい
  - A: ai モジュールを呼ばないか、score_* の呼び出し時に api_key を渡さない場合は ValueError が送出されます。呼び出し側で捕捉してフェイルセーフにする設計が推奨されます。
- Q: Monitoring が本番 DB をいじってしまうのでは？
  - A: 設計上、Monitoring は監視対象として本番 monitoring DB（Settings.sqlite_path）を使用する想定です。Paper Trading と完全分離したい場合は監視側の DB 設定を適切に上書きしてください。

---

その他の詳細は各モジュールの docstring（コード内コメント）を参照してください。必要であれば、この README をベースにデプロイ手順や運用手順（systemd / Supervisor / コンテナ化）向けの追加ドキュメントを作成します。