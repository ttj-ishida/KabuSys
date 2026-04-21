# KabuSys

日本株向け自動売買システムのライブラリ兼実行スクリプト群です。  
本リポジトリはシグナル生成・ポートフォリオ構築・発注エンジン・監視・AI支援（ニュースセンチメント／レジーム判定）などを含むモジュール群を提供します。

---

## 概要

- コア機能は純粋関数（ポートフォリオ構築・ポジションサイジング等）と、実行用コンポーネント（ExecutionEngine、OrderManager、BrokerClient）で構成されています。
- 監視機能は SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine により定期ポーリングで動作し、必要に応じて kill.flag を書き込んで ExecutionEngine を安全に停止します。
- Paper Trading（ペーパートレード）モードでは実際の発注を行わず MockBrokerClient を使い、発注ログ等は本番 DB と分離して `data/paper_trading.db` に保存します。
- ニュースの NLP（OpenAI）を用いたセンチメントスコアリングや、ETF ベースのレジーム検出モジュールを備えます（OpenAI API キーが必要）。

---

## 主な機能一覧

- 実行・発注関連
  - ExecutionEngine / OrderManager / OrderRepository / RiskManager / Reconciler（発注管理・再整合）
  - Paper Trading と Live の切替（環境変数 `KABUSYS_ENV`）
- 監視
  - SystemMonitor: CPU / メモリ / ディスク / プロセスの監視、データ鮮度チェック
  - TradeMonitor: 発注ログの整合性・滞留注文・約定異常検出（コード内に実装あり）
  - RiskMonitor: ドローダウン監視・ポジション上限監視、ダッシュボード更新
  - KillSwitch / MonitoringEngine: 条件に応じた停止フラグ（data/kill.flag）生成・通知
- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、セクター制限、レジーム乗数、株数算出（単元株丸め等）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
  - 市場レジーム判定（kabusys.ai.regime_detector）
- ユーティリティ
  - 環境変数のウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ロギング設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）

---

## 動作要件（推奨）

- Python 3.10+
- 必要な外部パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML 検査を行う場合）
- SQLite（標準ライブラリ sqlite3 を使用）
- （任意）LINE 通知を使う場合はネットワーク環境

requirements.txt はプロジェクトに含めていないため、環境に合わせてインストールしてください。例:

pip install duckdb psutil openai PyYAML

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンし、仮想環境を作成・有効化する:

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. 必要なパッケージをインストール:

   pip install duckdb psutil openai PyYAML

3. .env の初期作成（対話式ウィザード）:

   python -m kabusys.config_setup

   ウィザードに従って `JQUANTS_REFRESH_TOKEN`、`KABU_API_PASSWORD` など必須値を設定してください。
   生成された `.env` は Git にコミットしないでください。

4. 設定の検証:

   python -m kabusys.validate_config
   # 警告も失敗とする厳格モード
   python -m kabusys.validate_config --strict

5. DB / ディレクトリの初期化は起動スクリプトが自動で行います（logs ディレクトリや data ディレクトリを自動作成します）。必要に応じて `DUCKDB_PATH` / `SQLITE_PATH` を .env で変更してください。

---

## 環境変数（代表的なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: execution 環境
  - development（デフォルト） / paper_trading / live
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用。デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 本番での Kill Flag 自動クリア（0/1。0 推奨）

.env 自動ロード:
- プロジェクトルート（.git / pyproject.toml を探索）から `.env` と `.env.local` を自動読み込みします。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 実行方法（主要スクリプト）

- 実行エンジン（ExecutionEngine）起動:

  python -m kabusys.run_execution

  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に独立して記録されます。
  - 実行中の PID は `data/execution.pid` に書き込まれます。
  - 停止指示は `data/stop_requested.flag` を作成すると検知して安全停止します。
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると kill.flag を自動でクリアします（本番では 0 を推奨）。

- 監視モード起動:

  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  - デフォルトは 60 秒間隔。
  - 監視は本番（settings.env に関わらず）で設定された本番 sqlite_path を使用して永続化します。
  - `data/stop_requested.flag` が存在すると監視ループを終了します。

- 設定ウィザード:

  python -m kabusys.config_setup

- 設定検証:

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを上書きする場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

## ライブラリ（プログラム的に使う）

- 簡単な例:

  - AI ニューススコアリング（プログラムから呼ぶ場合）:

    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")

  - レジーム判定:

    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")

  - ポートフォリオ関数（純粋関数、テストしやすい）:

    from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

    candidates = select_candidates(buy_signals, max_positions=10)
    weights = calc_score_weights(candidates)
    sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)

- 設定読み込み:
  - `from kabusys.config import settings` を使って各種設定にアクセスできます（Settings クラス）。
  - Settings は .env / 環境変数から値を取得し、妥当性チェックを行います。

---

## ファイル / ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py  (ソース中に存在)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py  (ソース中に存在)
  - execution/                — 発注周りの実装（Engine・OrderManager 等）
  - utils/
    - logging_setup.py
    - process_priority.py

- data/                       — 実行時に生成される（デフォルト）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kill.flag
  - stop_requested.flag
  - execution.pid

- logs/                       — ログファイル（デフォルト）

（上記は主要なファイルのみ抜粋しています。各モジュールの詳細はソースをご参照ください。）

---

## 運用上の注意・トラブルシューティング

- KABUSYS_ENV を `live` に設定する際は特に注意してください。validate_config で追加警告が出ます。
- 本番時は `KILL_FLAG_CLEAR_ON_START=0` を推奨します。誤って kill.flag を削除してしまうと意図しない稼働再開につながります。
- OpenAI を使う機能は API 利用料が発生します。API キーと利用ポリシーに注意してください。API 失敗時は多くの処理がフェイルセーフ（0 やスキップ）になりますが、運用方針を明確にしてください。
- ログディレクトリ作成やファイルハンドラの作成が失敗した場合、標準出力に警告が出てコンソールログのみで継続します。
- run_execution / run_monitoring はプロセス優先度を高く設定しようとします（OS 権限により失敗する場合があります）。その場合はログに警告が出ますが処理自体は継続します。
- SQLite / DuckDB のファイルパスはデフォルトで `data/` 下に作られます。適切なバックアップ・パーミッションを確保してください。

---

## 開発向けヒント

- 多くの関数は外部副作用を持たない純粋関数（ポートフォリオ / リサーチ部分）で設計されているため、ユニットテストを書きやすくなっています。
- AI モジュールの外部呼び出しはラッパー関数を通して行うため、テスト時は該当関数をモック（patch）してテスト可能です（ソース内にそのための注釈があります）。
- `.env.local` は開発者固有のオーバーライドに使えます（自動ロード時に上書きされます）。

---

必要であれば、README に動作例（実際の .env サンプル、より細かい CLI オプション、各モジュールの API 例）を追加します。どの情報を追加したいか教えてください。