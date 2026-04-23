# KabuSys

日本株向け自動売買システム（簡易版）  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・研究ツール・AI ニュース解析などを含む自動売買コンポーネント群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 市場データ（DuckDB の prices_daily 等）からファクターを算出し、シグナルを生成する（research/*）。
- 候補選定・重み付け・株数決定などのポートフォリオ構築ロジック（portfolio/*）。
- ExecutionEngine を通じた発注・注文管理・リスク制御（execution/*）。
- システム稼働監視・注文ログ収集・リスク監視と Kill Switch（monitoring/*）。
- OpenAI を用いたニュースセンチメント解析および市場レジーム判定（ai/*）。
- ペーパートレードの検証レポートや対話式設定ウィザード等のツール群（tools/*、config_setup.py、validate_config.py）。

設計方針の一部:
- DuckDB/SQLite をローカル DB として利用（分析用と監視用を分離）。
- Paper Trading（テスト発注）と Live（実口座）を環境変数で切替可能。
- 外部 API（kabuステーション / J-Quants / OpenAI）は設定で有効にする。失敗時は安全にフォールバックする実装。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注ループ、リスク管理、注文リコンシリエーション）
  - Paper Trading モード（MockBrokerClient／専用 SQLite に記録）
- Monitoring
  - SystemMonitor（CPU/メモリ/Disk、データ鮮度、プロセス生存チェック）
  - TradeMonitor / RiskMonitor（滞留注文、約定異常、ドローダウン監視）
  - KillSwitch（閾値トリガで停止フラグを生成）
  - Monitoring DB（SQLite に監視ログ、trade_logs、risk_logs、dashboard を永続化）
- Research / Portfolio
  - ファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC（Information Coefficient）/統計サマリー等
  - 候補選定、等重・スコア重み、リスク調整、ポジションサイズ計算
- AI
  - ニュースの LLM ベースセンチメント解析（OpenAI）
  - レジーム（bull/neutral/bear）判定（ETF MA200 + マクロセンチメント）
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）
  - 共通ログ設定、プロセス優先度設定ユーティリティ

---

## 要求環境 / 依存パッケージ

- Python 3.10+
- 推奨パッケージ（pip でインストールしてください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合）
- OS: Linux / macOS / Windows（process priority のサポートに差異あり）

requirements.txt は含まれていないため、プロジェクトに合わせて必要パッケージをインストールしてください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

2. Python 環境を用意（venv など）

3. 必要パッケージをインストール
   - 例: pip install duckdb psutil openai PyYAML

4. .env の作成（対話式ウィザード推奨）
   - 実行:
     python -m kabusys.config_setup
   - 生成された .env を編集して必要な値（特に JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を設定してください。

5. 設定検証（任意・推奨）
   - 実行:
     python -m kabusys.validate_config
   - 問題があれば指示に従い .env や config/*.yaml を調整します。
   - --strict を付けると警告も失敗扱いになります。

6. DB 初期化
   - 監視用 SQLite（デフォルト: data/monitoring.db）は起動スクリプト内で必要に応じてテーブル作成（init_monitoring_db）されます。手動で作る必要は通常ありません。
   - Paper Trading の DB（PAPER_TRADING_SQLITE_PATH）を使用する場合は該当起動で同様に初期化されます。

注意:
- Monitoring（run_monitoring）は KABUSYS_ENV に関係なく本番 sqlite_path（SQLITE_PATH）を参照して監視データを書き込みます。
- Paper Trading 時は Execution 起動で paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を用いて実行され、本番 DB と分離されます。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (LLM を使う機能で必要)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant|partial|never|reject, デフォルト instant)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト INFO)
- LOG_DIR (ログ出力ディレクトリ, デフォルト logs/)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか 0/1, デフォルト 0)

最小 .env（例）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-xxxx
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（立ち上げ / コマンド）

- 設定ウィザード（.env を作る）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  (失敗時は exit code != 0)

- 監視プロセス（SystemMonitor をポーリング）
  python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で変更可（秒、デフォルト 60）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成するとループが終わる

- 実行エンジン（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録
  - 実行中は data/execution.pid に PID を書く（設定によりパス変更可）
  - 停止は data/stop_requested.flag を作成するか、監視側から kill.flag が書かれると停止

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- 開発用: MonitoringEngine を単発実行（テスト）:
  - 組み合わせてインスタンスを作り run_once することで一回だけ監視処理を実行できます（ユニットテスト向け）。

停止フラグ／Kill Switch:
- Stop ループ: data/stop_requested.flag を作成すると run_monitoring.py / run_execution.py のループは終了します。
- KillSwitch（リスク超過時に監視が自動で書き込む）: data/kill.flag が作成されると ExecutionEngine の起動・継続に影響する場合があります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアされます（ただし本番では推奨されません）。

ログ:
- デフォルト logs/ ディレクトリに日次ローテートログが生成されます（各アプリ名ごと）。
- コンソール出力は stdout に出力されます。

---

## ディレクトリ構成（抜粋）

ここでは src/kabusys 以下の主なファイルと役割を列挙します。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数読み込み / Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前の設定検証 CLI
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py    — レジーム判定（ETF + マクロセンチメント）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル初期化＆永続化 API
    - system_monitor.py     — システム監視（CPU/メモリ/データ鮮度 等）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - trade_monitor.py      — （注文関連監視）※実装参照
    - monitoring_engine.py  — 各 Monitor の束ね・ポーリングループ
    - kill_switch.py        — kill.flag 管理
    - alert_manager.py      — （アラート送信、LINE 等）※実装参照
  - execution/
    - execution_engine.py   — ExecutionEngine 本体（run_session 等）
    - order_manager.py      — 注文管理
    - order_repository.py   — 注文永続化（SQLite 等）
    - reconciler.py         — 注文状態整合処理
    - broker_factory.py     — BrokerClient 作成（Mock / 実装）
    - risk_manager.py       — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 株数決定・資金配分ロジック
    - risk_adjustment.py    — セクター上限・レジーム乗数
  - research/
    - factor_research.py    — モメンタム/バリュー/ボラティリティ算出
    - feature_exploration.py— 将来リターン計算・IC・統計等
  - utils/
    - logging_setup.py      — 共通ロギング設定
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ

※実際のファイルツリーは src/kabusys 以下を参照してください。

---

## 開発メモ / 注意事項

- Paper Trading と Live は DB を分離していますが、Monitoring は常に SQLITE_PATH（本番監視 DB）を使う点に注意してください。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キーが必須です。テスト時は _call_openai_api をモックすることを想定しています。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- process_priority の設定は OS に依存し、権限不足の場合は警告が出てスキップされます。
- .env は機密情報を含むため Git にコミットしないでください。

---

## よく使うコマンドまとめ

- .env を作る（対話式）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視を起動
  python -m kabusys.run_monitoring

- 実行エンジンを起動
  python -m kabusys.run_execution

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に環境別の運用手順（開発 / ペーパートレード / 本番）やサンプル .env の詳細、起動時のユニットテスト/デバッグ方法を追記できます。どの内容を追加しますか？