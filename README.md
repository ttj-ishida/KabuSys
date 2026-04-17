# KabuSys

KabuSys は日本株向けの自動売買 / リサーチ / 監視ユーティリティ群をまとめたパッケージです。ポートフォリオ構築・ポジションサイジング・監視エンジン・ExecutionEngine の起動スクリプト、Paper Trading 検証ツールや LLM を使ったニュースセンチメント評価などを含みます。

以下はリポジトリ内の主要機能、セットアップ方法、使い方、ディレクトリ構成の説明です。

注意: 本 README はソースコードの docstring / 実装に基づいて作成しています。

## プロジェクト概要
- 自動売買実行エンジン（ExecutionEngine）と監視システム（MonitoringEngine）を分離して提供。
- Paper Trading モード（本番 DB と分離）をサポートし、モックブローカーでの検証が可能。
- DuckDB を使ったリサーチ / ファクター計算モジュール（ファクター、ボラティリティ、バリュー等）。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（ai.news_nlp）と市場レジーム判定（ai.regime_detector）。
- 監視ログは SQLite（デフォルト data/monitoring.db）へ永続化。Streamlit ベースの監視ダッシュボードあり。
- kill.flag / stop_requested.flag 等のフラグファイルによるプロセス制御、LINE 通知経由のアラート機能を備える。

## 主な機能一覧
- ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - 環境変数 KABUSYS_ENV に応じて paper_trading（モック）/ live を切り替え
  - paper_trading 時は専用 SQLite（data/paper_trading.db）へ記録
  - プロセス優先度設定・PID 管理・停止フラグ対応
- MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor
  - システム資源・プロセス監視、注文滞留・約定異常検出、ドローダウン監視
  - kill.flag を書き込む KillSwitch と通知（AlertManager）
- Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
  - ポーリングループで定期的にモニタリングを実行（MONITOR_POLL_INTERVAL で間隔変更）
- Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
  - SQLite の監視 DB を読み取り、ポートフォリオ / ポジション / オーダー / システムを表示
- Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading DB から稼働率、注文成功率、レイテンシ等のレポート作成
- Portfolio モジュール
  - 候補選定、等配分 / スコア配分、セクターキャップ、レジーム乗数、ポジションサイジング等の純粋関数群
- Research モジュール
  - ファクター（momentum, volatility, value）計算、将来リターン、IC（ランク相関）計算、統計サマリ
- AI モジュール
  - news_nlp.score_news: raw_news を LLM で評価して ai_scores に書き込み
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースを合成してレジーム判定
- ユーティリティ
  - Settings（環境変数管理、自動 .env 読み込み）
  - process_priority（プロセス優先度 / CPU affinity 設定ユーティリティ）

## 前提 / 必要環境
- Python 3.10 以上（型注釈に | を使用しているため）
- 必要な主要ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- （任意）.env ファイルをプロジェクトルートに配置して環境変数を管理可能。
  - 自動読み込みはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

例（インストール）:
- requirements.txt が無い場合は手動で:
  pip install duckdb psutil requests openai streamlit

## 主要な環境変数（代表）
- KABUSYS_ENV: 起動環境。valid: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合に必須）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（Settings 参照）

Settings は src/kabusys/config.py に実装されており、自動でプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数を保護）。

## セットアップ手順（例）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install duckdb psutil requests openai streamlit

4. 環境変数設定（ウィザード推奨）:

   対話式ウィザードで `.env` を作成できます:
   ```cmd
   python -m kabusys.config_setup
   ```
   手動設定する場合は `.env.example` をコピーして `.env` を作成してください。
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動ロードされます。
   - 必須環境変数: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`
   - OpenAI を使う場合は `OPENAI_API_KEY` を設定

5. YAML 設定ファイルの生成:
   ```cmd
   python scripts/generate_config.py
   ```
   `config/` 配下に `system_config.yaml` など 6 ファイルが生成されます（既存ファイルはスキップ）。

6. 設定を検証:
   ```cmd
   python -m kabusys.validate_config
   ```
   必須環境変数の欠落・YAML ファイルの異常・`live` 環境特有の警告を検出します。

7. データディレクトリの作成:
   ```cmd
   mkdir -p data
   ```

### 実行環境（KABUSYS_ENV）の使い分け

| 値 | 用途 | 発注 |
|----|------|------|
| `development` | ローカル開発・単体テスト | なし |
| `paper_trading` | 仮想発注・動作検証 | MockBrokerClient を使用 |
| `live` | 本番稼働（実際に発注） | kabuステーション API |

> `live` に切り替える前に必ず `python -m kabusys.validate_config --strict` で設定を確認してください。

### 必須環境変数

| 変数名 | 説明 |
|--------|------|
| `JQUANTS_REFRESH_TOKEN` | J-Quants API リフレッシュトークン |
| `KABU_API_PASSWORD` | kabuステーション API パスワード |
| `KABUSYS_ENV` | 実行環境（development / paper_trading / live） |

その他の変数とデフォルト値は `.env.example` を参照してください。

---

## 使い方（実行例）
※ すべてプロジェクトルートで実行することを想定

- 監視ループを起動
  - MONITOR_POLL_INTERVAL を変更して起動間隔を設定可能（秒）
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  run_monitoring は Settings.sqlite_path（デフォルト data/monitoring.db）へ接続し、duckdb も開きます。監視は常に本番 sqlite_path を使用（環境に依らず）。

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - Paper Trading モード:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - Paper Trading 時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）に書き込み、本番 DB と完全分離されます。

  実行中は data/execution.pid（デフォルト）に PID を書きます。停止は data/stop_requested.flag を作成するか、KillSwitch により data/kill.flag が書かれると停止処理が走ります。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開いて表示します（監視ループが先に起動していることが望ましい）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を手動指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（スコアリング・レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で渡す）
  - news_nlp.score_news / regime_detector.score_regime をスクリプトやバッチで呼び出して ai_scores / market_regime テーブルに書き込み

## プロセス制御 / フラグファイル
- 停止フラグ（run_monitoring / run_execution が監視するもの）
  - data/stop_requested.flag: 監視ループやエンジンに即時停止指示を与える（存在を検知してループを終了）
- Kill Switch（自動停止判定）
  - KillSwitch は条件（ドローダウン超過 / ポジション上限など）を満たすと data/kill.flag に理由を書き込み、ExecutionEngine に停止指示を送る
  - Settings.kill_flag_clear_on_start が 1 なら起動時に kill.flag をクリアするように設定可能
- PID ファイル
  - data/execution.pid（デフォルト）: ExecutionEngine 側が書き込む PID。SystemMonitor はこの PID の存否をチェックしてプロセス停止検出や stale PID 削除を行う。

## 開発向け情報 / 備考
- Settings（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索基準）から自動読み込み。OS 環境変数を保護。
  - 環境が不正な値の時は ValueError を投げる（KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL など）。
- DB スキーマ
  - 監視用 SQLite（monitoring_db.py）に system_status, trade_logs, positions, risk_logs, dashboard のテーブルを作成。マイグレーションも一部コード内で実施（カラム追加等）。
- ロギング / 優先度
  - 起動スクリプトは最初に set_process_priority("high") を試みます（psutil の権限に依存）。
- テスト / モック
  - Paper Trading 用に BrokerClientFactory がモックブローカーを作成するため、本番 API 呼び出しを伴わない検証が可能。
- LLM 呼び出しの堅牢化
  - news_nlp と regime_detector は OpenAI 呼び出しにリトライ・バックオフやレスポンス検証を実装。API 失敗時はフェイルセーフ（スコア 0 等）で継続する設計。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要なファイル・モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                      — Settings / .env 自動読み込み
  - run_monitoring.py              — Monitoring ポーリングスクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + LLM）
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 execution 関連のモジュール: broker_factory, execution_engine, order_repository, ...)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py
  - data/ (runtime)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading モード時)
    - kabusys.duckdb (DuckDB データベースファイル)
    - execution.pid
    - stop_requested.flag
    - kill.flag

（実際のリポジトリの全ファイルは上記以外にも存在します。上は主要なコンポーネントの一覧です。）

## よくある操作例まとめ
- 監視をデフォルト間隔で起動:
  - python -m kabusys.run_monitoring
- 監視間隔を 30 秒に変更:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ExecutionEngine（Paper Trading）起動:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 停止（手動）:
  - touch data/stop_requested.flag
- ダッシュボード表示:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

何か特定のセットアップ（例: Docker 化、CI 設定、requirements.txt 作成、テスト実行例）や個別モジュールの詳しいドキュメントが必要であれば教えてください。README をそれに合わせて拡張します。