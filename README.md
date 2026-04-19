# KabuSys

日本株向け自動売買システムのコードベース説明書 (README)。  
この README はプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うシステムです。  
主な目的は以下です。

- シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）
- 実行中のシステム・注文・リスク監視（Monitoring）
- DuckDB を用いたリサーチ・ファクター計算
- OpenAI を利用したニュース NLP によるセンチメントスコアリング（任意）
- ペーパートレード用の分離された DB と検証ツール

設計方針として、テスト容易性とフェイルセーフ（API失敗時の継続）、環境依存の最小化が考慮されています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して発注処理を実行（本番 / ペーパートレード切替対応）
  - BrokerClientFactory によるブローカークライアントの抽象化
  - リスク管理（RiskManager）、注文管理（OrderManager）等のコンポーネント
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期ポーリング監視
  - MonitoringDB（SQLite）への永続化（system_status, trade_logs, risk_logs, positions, dashboard）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止）
  - AlertManager を通した通知（LINE 等の設定あり）
- Portfolio Construction
  - 候補選定、スコア重み付け、等金額配分、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - DuckDB を使ったファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量探索・IC 計算・統計サマリー
- AI / NLP
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブルへ書込）
  - regime_detector: ETF 等の指標とマクロニュースを合成して日次レジーム判定（market_regime テーブルへ）
- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
  - ログ設定・プロセス優先度ユーティリティ

---

## 必須 / 推奨環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（デフォルトあり／説明参照）:
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の専用 SQLite（デフォルト: `data/paper_trading.db`）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） デフォルト: `INFO`
- OPENAI_API_KEY — OpenAI を使う場合に必要（news_nlp / regime_detector）

その他:
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- PAPER_FILL_MODE — ペーパートレードの約定モード（`instant` / `partial` / `never` / `reject`、デフォルト: `instant`）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）（run_monitoring で使用、デフォルト: 60）

.env はプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順

1. リポジトリをクローン / 展開し、Python 仮想環境を作成・有効化する:
   - python >= 3.10 推奨
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）:
   - pip install -r requirements.txt
   - 主要依存例: duckdb, psutil, openai, PyYAML（設定検証時に任意）

   ※ requirements.txt が無い場合は個別に:
   - pip install duckdb psutil openai pyyaml

3. 初期 .env を作成:
   - 対話式で作る: python -m kabusys.config_setup
   - 作成後: python -m kabusys.validate_config で検証

4. 必要ディレクトリ作成（ログ / データ）:
   - mkdir -p data logs

5. DB 初期化:
   - 多くのスクリプトは起動時に必要テーブルを自動作成します（例: init_monitoring_db）。

---

## 使い方

基本的にはパッケージをモジュール実行します。プロジェクトルートで実行してください。

- ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution
  - 起動時に pid ファイル (data/execution.pid デフォルト) を利用します。
  - ペーパートレード: KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録します。

- Monitoring を起動（常駐ポーリング）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔(秒)を変更可能（例: MONITOR_POLL_INTERVAL=30）

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱いにできます

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH で代替可）

- AI/Regime 関連（ライブラリ関数として利用）:
  - ニューススコア付与: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを CLI から直接起動するラッパーは提供されていないため、スクリプト内で呼ぶか簡易ラッパーを作成してください。
  - API キーは OPENAI_API_KEY 環境変数、もしくは関数引数で指定できます。

- 停止手段:
  - 実行中のループはキーボード割込 (Ctrl+C) で停止します。
  - 外部から停止させる場合はプロジェクトルートの data/stop_requested.flag を作成すると run_execution / run_monitoring が検知して安全終了します。
  - Kill Switch は data/kill.flag を書き込むと ExecutionEngine を停止させます（監視・リスク条件により自動生成されることがあります）。

- ログ:
  - logs/<app_name>.log に日次ローテーションでログを出力（logs ディレクトリを作成しておくこと）。
  - setup_logging() が各起動スクリプトで呼ばれます。

---

## 環境固有の挙動（注意点）

- Monitoring の起動スクリプト（run_monitoring.py）は、KABUSYS_ENV にかかわらず「本番の sqlite_path（Settings.sqlite_path）」を使用して監視ログを書きます。モニタリング DB を別にしたい場合は設定でパスを変更してください。
- run_execution.py は KABUSYS_ENV=paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH を使用して本番 DB と完全に分離します。
- PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant / partial / never / reject）。
- OpenAI 系は外部 API なので、API キー設定と呼び出し回数/コストに注意してください。失敗時はフェイルセーフ（0.0 等）で続行する実装がされていますが、API 利用制限は運用設計が必要です。

---

## 主要ファイル・ディレクトリ構成

プロジェクトの主要モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — レジーム判定（OpenAI + ETF 指標）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層 + MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py       — (trade に関する監視: スタレ/約定異常等)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信のラッパ）
  - execution/
    - execution_engine.py    — ExecutionEngine / EngineConfig
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py            — prices / raw_financials などの取得ユーティリティ（DuckDB）
  - utils/
    - logging_setup.py       — 共通ロギング設定
    - process_priority.py    — 優先度 / CPU affinity 設定
  - monitoring/、execution/ 以下に DB/コンポーネントが配置

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに細かい実装・補助モジュールがあります）

---

## よく使うコマンド例

- .env 作成（対話）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

## 運用上の注意 / 推奨

- 本番（KABUSYS_ENV=live）では .env を厳密に管理し、Git にコミットしないでください（config_setup でも注意書きを出しています）。
- Kill Switch（KILL_FLAG）や stop flag（stop_requested.flag）などの外部フラグを使った停止/再開ワークフローを運用ルールとして定義してください。KILL_FLAG_CLEAR_ON_START は本番では `0` 推奨です。
- ログ・DB のバックアップ・ローテーションを含む運用設計を行ってください（logs/ は 30 日分ローテーション）。
- OpenAI API 利用はコスト管理とリトライ/バックオフの調整が必要です（既にコード内にリトライロジックあり）。

---

README は以上です。必要であれば次の内容の追記が可能です:
- 各設定項目のサンプル .env（テンプレート）
- systemd / supervisor 用のサービスユニット例
- 開発用のユニットテスト実行方法や CI 設定例

どの情報を追加しますか？