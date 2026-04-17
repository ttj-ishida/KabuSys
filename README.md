# KabuSys

KabuSys は日本株自動売買システムの一部をまとめたリポジトリです。取引エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）や AI を用いたニュースセンチメント評価などのコンポーネントを含みます。

以下はこのコードベースの README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方
  - ExecutionEngine の起動
  - Monitoring の起動
  - Streamlit ダッシュボード
  - Paper Trading 検証レポート
  - AI モジュール（ニュース / レジーム判定）
  - テスト用ユーティリティ（MonitoringEngine の単発実行等）
- 環境変数一覧（重要なもの）
- 停止／フラグファイル
- ディレクトリ構成

---

プロジェクト概要
- 日本株の自動売買運用を想定した内部モジュール群。
- 主な責務:
  - ExecutionEngine：発注の管理、リスク管理、再起動時のリコンシリエーション
  - Monitoring：システム状態・注文異常・リスク指標のポーリング監視とログ保存
  - Portfolio：銘柄選定／配分／ポジションサイズ計算の純粋関数群
  - Research：DuckDB を用いたファクター計算・特徴量解析
  - AI：ニュースの NLP によるセンチメント評価、レジーム判定（OpenAI を使用）
  - Tools：レポート生成や補助スクリプト（例: paper_verification_report、streamlit dashboard）

主な機能一覧
- システム監視（CPU / メモリ / ディスク / プロセス存在チェック / データ鮮度）
- 注文監視（滞留注文、約定異常価格検出）
- リスク監視（ドローダウンアラート、ポジション上限アラート）と kill-switch（停止フラグ生成）
- LINE を使ったアラート通知（AlertManager）
- ExecutionEngine 起動スクリプト（本番 / ペーパートレードの分離）
- Paper Trading 検証レポート生成スクリプト
- Streamlit による監視ダッシュボード表示
- DuckDB ベースのファクター計算（Momentum / Volatility / Value 等）
- OpenAI を利用したニュースセンチメント評価・市場レジーム判定（gpt-4o-mini を想定）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出・セクターキャップ）

セットアップ手順（ローカル開発向け）
1. Python バージョン
   - Python 3.10 以上を推奨（コード中で | 型注釈などを使用）。

2. 仮想環境作成（推奨）
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

3. 必要なパッケージのインストール
   - 最低限の依存:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - インストール例:
     ```
     pip install -U pip
     pip install duckdb psutil openai requests streamlit
     ```
   - sqlite3 は標準ライブラリで提供されます。

4. 環境変数の設定
   - ルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数は後述します。`.env.example` を参考にしてください（リポジトリに例ファイルがある想定）。

5. データディレクトリ
   - デフォルトでは `data/` 下に DB や PID / flag ファイルを置きます。必要に応じてディレクトリを作成してください。
     ```
     mkdir -p data
     ```

使い方

- 実行前の注意
  - 実行時にプロセス優先度設定（psutil による nice / Windows の優先度変更）を試みます。権限が不足する場合は警告が出ますが処理は継続します。
  - OpenAI を使う機能（ニュース NLP / レジーム判定）は `OPENAI_API_KEY` を設定する必要があります。

1) ExecutionEngine の起動
- スクリプト: `src/kabusys/run_execution.py`
- 実行（パッケージモード推奨）:
  ```
  python -m kabusys.run_execution
  ```
- 挙動:
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い paper_trading 用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と完全分離します。
  - 起動時に `data/execution.pid` に PID を書く設計（Settings.pid_file_path で変更可能）。
  - 停止は `data/stop_requested.flag` を作成することで行えます（Monitoring 側もこのフラグを参照）。

2) Monitoring の起動
- スクリプト: `src/kabusys/run_monitoring.py`
- 実行:
  ```
  python -m kabusys.run_monitoring
  ```
- オプション / 環境変数:
  - `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き（デフォルト 60）。
- 挙動:
  - 監視ループは常に本番の `sqlite_path` を使用して監視ログを記録します（KABUSYS_ENV に依存しない）。
  - 停止は `data/stop_requested.flag` により行います（存在を検知するとループ終了）。

3) Streamlit ダッシュボード
- ファイル: `src/kabusys/monitoring/streamlit_dashboard.py`
- 起動例:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- 説明:
  - 監視用 SQLite DB を読み取り専用で開き、ダッシュボードとして表示します。
  - DB が存在しない場合はエラー表示（MonitoringEngine を先に起動してください）。

4) Paper Trading 検証レポート
- スクリプト: `src/kabusys/tools/paper_verification_report.py`
- 実行例:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
- 概要:
  - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し PASS/FAIL を判定します。
  - デフォルト DB: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` 環境変数で上書き可）。

5) AI 関連
- ニュース NLP（センチメント）
  - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - 要: OpenAI API キー（引数 or 環境変数 `OPENAI_API_KEY`）
  - raw_news / news_symbols / ai_scores テーブルを使用してスコアを ai_scores に書き込みます。
- レジーム判定
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - ETF（1321）の MA200 とマクロニュースセンチメントを組み合わせて `market_regime` テーブルへ書き込みます。

6) ライブラリ / ユーティリティの利用
- Portfolio（銘柄選定・重み・ポジションサイズ）: `kabusys.portfolio` の関数群をインポートして利用可能。
- Research（ファクター / IC / 統計要約）: `kabusys.research` の関数群を利用可能。

環境変数（主要）
- KABUSYS_ENV: 起動環境。許容値: development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading モードでの約定挙動（instant / partial / never / reject）
- PID_FILE_PATH: execution.pid のパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（値を "1" に）

停止／フラグファイル
- data/stop_requested.flag:
  - run_monitoring / run_execution がこのファイルの存在を検知すると安全に終了処理を行います。
- data/kill.flag:
  - KillSwitch（監視側）によって書き込まれると ExecutionEngine 側が外部停止を受けるためのフラグです。
  - KillSwitch はドローダウンやポジション上限違反などの重大シグナルでフラグを作成します。
- data/execution.pid:
  - ExecutionEngine の PID を格納するファイル。SystemMonitor はこの PID ファイルを見てプロセス存在を検査します。

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定の読み込みと Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト（本番 / paper_trading 分離）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — paper trading の検証レポート生成 CLI
  - execution/
    - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, broker_factory.py, ... — 発注・ブローカー関連
  - monitoring/
    - monitoring_db.py — SQLite によるログ永続化
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — 停止フラグ生成ロジック
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック（純粋関数）
  - research/
    - factor_research.py — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメント取得（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + ETF MA200）
  - data/ (実行時に作成される)
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading）
    - kabusys.duckdb（DuckDB）
    - execution.pid, stop_requested.flag, kill.flag

運用上の注意
- 本リポジトリには実際のブローカー接続や金銭の移動を伴う部分が含まれます。paper_trading モードが提供されていますが、実運用前に十分なテストを行ってください。
- OpenAI の呼び出しや外部 API 呼び出しにはレート制限やエラーがあるため、モジュール内でバックオフやリトライ処理が組み込まれていますが、API キーや課金・レートに注意してください。
- プロセス優先度や CPU affinity の変更は OS 権限が必要になる場合があります。権限不足時は警告が出ますが動作は続行します。
- DB マイグレーションは monitoring_db.init_monitoring_db() が冪等に行う設計ですが、バックアップを取った上で運用してください。

補足（開発者向け）
- Settings クラスは自動で .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止できます。
- Unit テスト／モック: OpenAI 呼び出し部分は内部で独立した関数（_call_openai_api 等）に切り出してあり、テスト時に patch して挙動を差し替えやすくなっています。
- DuckDB 接続を受け取って処理を行う設計なので、testing 用にメモリ内 DuckDB を渡してユニットテストを構成できます。

---

問題や質問、追加ドキュメントの要望があれば教えてください。README を実行例や .env.example（機密情報を含めないサンプル）で拡張することもできます。