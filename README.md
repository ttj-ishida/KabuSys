# KabuSys

日本株向け自動売買システムの一部を実装した Python コードベースの README です。  
このドキュメントはリポジトリ内のコード（src/kabusys 以下）をもとに、プロジェクト概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・検証・監視のためのコンポーネント群です。  
主な機能は以下の通りです。

- 注文の作成・送信・状態管理（Execution コンポーネント）
- 監視（システム状態・注文滞留・リスク監視）とアラート送信（LINE）
- Paper Trading モード（本番 DB と分離して動作するモックブローカー）
- DuckDB を使ったファクター計算・リサーチ（ファクター計算、将来リターン、IC 等）
- ニュース記事の NLP による銘柄センチメント算出（OpenAI API 経由）
- 市場レジーム判定（MA + マクロセンチメントの合成）
- Paper Trading 用の検証レポート生成ツール
- Streamlit による監視ダッシュボード

設計上のポイント：
- 環境変数 / .env による設定管理（自動読み込み機能あり）
- Paper Trading（`KABUSYS_ENV=paper_trading`）時は専用 SQLite（data/paper_trading.db）を使用して本番データと分離
- DB は SQLite（監視ログ）および DuckDB（時系列ファクター等）を利用
- OpenAI API 呼び出しはリトライやレスポンス検証等の耐障害性を持たせている

---

## 主な機能一覧（ファイル / モジュール別）

- 実行 / 起動
  - src/kabusys/run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV により Paper/Live 切替）
  - src/kabusys/run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）
- 監視（monitoring）
  - monitoring_db.py — 監視用 SQLite スキーマ / 永続化 API
  - system_monitor.py — CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag による ExecutionEngine 停止シグナル操作
  - alert_manager.py — LINE へのプッシュ通知（クールダウン管理あり）
  - monitoring_engine.py — 複数モニターを束ねポーリングするエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- 実行（execution）
  - order_manager.py, reconciler.py, など：発注・同期・復旧ロジック
- ポートフォリオ構築（portfolio）
  - portfolio_builder.py — 候補選定、等重/スコア重み計算
  - position_sizing.py — 発注株数決定（単元丸め、リスク制限、aggregate cap）
  - risk_adjustment.py — セクターキャップ、レジーム乗数
- 研究 / ファクター（research）
  - factor_research.py — モメンタム / ボラティリティ / バリューの計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
- AI（ai）
  - news_nlp.py — ニュースセンチメント算出（OpenAI）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロセンチメント）
- ユーティリティ
  - config.py — 環境変数 / .env 自動読み込み・Settings
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - tools/paper_verification_report.py — Paper Trading 結果の検証レポート出力

---

## セットアップ手順

前提
- Python 3.10 以降（typing の | 記法や future annotations を使用しているため）
- Git クライアント

1. リポジトリをクローンする
   - git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 以下は主要な依存例（プロジェクトに requirements.txt がない場合の目安）:
     - pip install duckdb psutil openai requests streamlit

   実際の要件はプロジェクト側で管理されている想定なので、requirements.txt があればそれを使用してください:
   - pip install -r requirements.txt

4. 環境変数設定 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主な環境変数（最低限の例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...  (任意)
     - LINE_USER_ID=...               (任意)
     - PAPER_FILL_MODE=instant|partial|never|reject  (paper_trading 時の振る舞い)
     - MONITOR_POLL_INTERVAL=60  (run_monitoring のポーリング間隔秒数)
   - .env の書式はシェル形式に準拠（export 対応、コメント行許容、クォート・エスケープ対応）。

5. データディレクトリ作成
   - 必要に応じて `data/` ディレクトリを作成し、SQLite / DuckDB のファイルを配置します。
   - Paper Trading 用 DB はデフォルト `data/paper_trading.db`、監視 DB は `data/monitoring.db`、DuckDB は `data/kabusys.duckdb`。

---

## 使い方（代表的なコマンド）

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - または（デフォルト development）: python -m kabusys.run_execution
  - 実行時はプロセス優先度を高く設定する処理が最初に走ります。
  - paper_trading モードでは MockBrokerClient を用い、Paper DB（PAPER_TRADING_SQLITE_PATH）に記録され本番 DB と分離されます。

- SystemMonitor をポーリング起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）。
  - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境にかかわらず本番監視 DB を使用する設計になっている点に注意）。

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視 DB を読み取り専用で開く）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーは環境変数 `OPENAI_API_KEY` を設定するか、関数引数で渡します。
  - モジュール API（プログラム内で使用）:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime

- モジュールをテスト的に一回だけ実行する（MonitoringEngine 用）
  - MonitoringEngine を組み立て run_once() を呼ぶことで単発実行可能（ユニットテスト用の設計が施されています）。

---

## 重要な設定項目（Settings より抜粋）

Settings クラスにより環境変数を参照します。主なキー:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合は必須)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラートを送る場合)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- PAPER_FILL_MODE (instant / partial / never / reject。paper_trading の注文約定挙動)
- PID_FILE_PATH (デフォルト data/execution.pid)
- KILL_FLAG_PATH (デフォルト data/kill.flag)
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

設定の自動ロードは、プロジェクトルート（.git または pyproject.toml がある階層）を基準に `.env` / `.env.local` を読み込みます。OS 環境変数が優先されます。

---

## 動作上の注意点 / 補足

- Paper Trading と本番データは分離されています。`KABUSYS_ENV=paper_trading` 時は paper DB（PAPER_TRADING_SQLITE_PATH）を利用します。
- run_monitoring は監視 DB（Settings.sqlite_path）を使用します。監視は環境にかかわらず本番の sqlite_path を参照する実装になっています（設計上の要件）。
- OpenAI 呼び出しは JSON mode を利用し、応答の検証・クリッピング・リトライが実装されています。API キーとネットワークの可用性が必要です。
- process_priority 設定（utils/process_priority.py）は Windows / POSIX の差分を吸収しますが、権限不足などで設定に失敗した場合は警告ログを出してスキップします。
- monitoring_db.init_monitoring_db はテーブル作成および一部マイグレーション（カラム追加）を行い、冪等に設計されています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / .env の読み込みと Settings
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py            — プロセス優先度 / CPU affinity
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - ... (ブローカ API 等のモジュール)
  - monitoring/
    - monitoring_db.py               — SQLite スキーマ / API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
    - __init__.py
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py

その他、data ディレクトリ（SQLite / DuckDB の DB ファイル配置想定）や設定ファイル（.env）をプロジェクトルートに置いて利用します。

---

## FAQ / トラブルシューティング

- Q: run_monitoring のポーリング間隔を変更したい
  - A: 環境変数 `MONITOR_POLL_INTERVAL` を秒数で設定してください（例: export MONITOR_POLL_INTERVAL=30）。不正値や 0 以下はデフォルト 60 秒にフォールバックします。

- Q: Paper Trading の DB を変えたい
  - A: 環境変数 `PAPER_TRADING_SQLITE_PATH` を設定してください。

- Q: OpenAI の API キーがないとどうなる？
  - A: AI 機能（news_nlp, regime_detector）は API キーが必要です。未設定の場合は ValueError を投げる実装箇所があります。AI を使わない限り他機能は動作します（ただし regime 判定やニューススコアが空になります）。

- Q: LINE 通知が送れない
  - A: `LINE_CHANNEL_ACCESS_TOKEN` と `LINE_USER_ID` を設定してください。設定が空の場合は送信は行われずログに警告が出ます。

---

この README はコードの現状をベースに作成しています。実行環境や追加の運用手順（systemd ユニット作成、監視アラート運用手順、バックアップなど）は運用方針に応じて追記してください。