# KabuSys

日本株自動売買システムの一部（ライブラリ＋起動スクリプト群）。

このリポジトリは以下の主要コンポーネントを含みます：取引実行エンジン、監視（Monitoring）サブシステム、ポートフォリオ構築ロジック、リサーチ用ファクター計算、AI（ニュース NLP / レジーム判定）連携ユーティリティ、各種ユーティリティ（ログ設定、プロセス優先度など）。

バージョン: 0.1.0

---

## 概要

- ExecutionEngine: ブローカーへの注文送信、オーダー管理、リスク管理、照合（reconciler）などを担う実行エンジン。
- Monitoring: システム状態、注文ログ、リスク（ドローダウン/保有上限）を定期チェックしアラートや Kill Switch を発動する。
- Portfolio: 銘柄選定・重み付け・ポジションサイズ計算などの純粋関数群（DB 参照なし）。
- Research: DuckDB を用いたファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）。
- AI: OpenAI を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）。
- Tools: Paper Trading の検証レポート生成などのユーティリティスクリプト。
- Config: .env のウィザード生成、設定検証 CLI、Settings 抽象化（環境変数の収集・検証）。

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine を起動（KABUSYS_ENV によって paper_trading モードの挙動あり）
  - python -m kabusys.run_monitoring: SystemMonitor のポーリングループを起動
- 設定管理 / 検証
  - python -m kabusys.config_setup: .env を対話式に生成/更新するウィザード
  - python -m kabusys.validate_config: .env や config/*.yaml の事前検証
- Paper Trading 検証
  - python -m kabusys.tools.paper_verification_report: ペーパートレード DB から検証レポートを生成
- AI 機能（OpenAI）
  - kabusys.ai.score_news: ニュース記事を LLM でスコア化して DuckDB の ai_scores に書き込み
  - kabusys.ai.regime_detector.score_regime: マクロセンチメント＋ETF MA によるレジーム判定
- 監視（Monitoring）
  - system / trade / risk の各モニタ、MonitoringEngine による周期実行
  - kill.flag 書き込みによる ExecutionEngine 停止指示（KillSwitch）
- ログ設定ユーティリティ
  - 共通の logging 設定（コンソール + 日次ローテーションファイル）

---

## 前提 / 必要パッケージ

最低限の推奨パッケージ（一例）:
- Python 3.8+
- duckdb
- psutil
- openai
- (任意) PyYAML — validate_config が YAML ファイルの構文チェックをする場合に必要

requirements.txt が無い場合は手動でインストールしてください。例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／展開し、プロジェクトルートへ移動
2. Python 仮想環境を作成して有効化（推奨）
3. 必要パッケージをインストール（上記参照）
4. .env ファイルを作成
   - 対話式ウィザード推奨:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に手動作成
5. 設定を検証:
   ```
   python -m kabusys.validate_config
   ```
   問題がある場合はメッセージに従って修正してください。

重要な環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（default: development）: development | paper_trading | live
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, default: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（default: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時に kill flag を自動クリアするか, "0"/"1"）

自動 .env 読み込み
- プロジェクトルートに .env または .env.local があれば自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（主要スクリプト）

起動例（プロジェクトルートで実行）:

- Execution（本番 / ペーパートレード）
  - 本番（KABUSYS_ENV=live を .env に設定）:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレード（.env で KABUSYS_ENV=paper_trading）:
    - MockBrokerClient が使用され、data/paper_trading.db に記録され、本番 DB と分離されます。

- Monitoring
  - ポーリング間隔は環境変数で上書き可能（秒単位）。デフォルト 60 秒。
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を参照します（KABUSYS_ENV に依存しない）。

- 設定ウィザード / 検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

停止 / Kill
- run_execution / run_monitoring はプロジェクトの data/stop_requested.flag ファイルをチェックして終了します（run_monitoring と run_execution で同じ flag を参照）。
  - 停止要求を出すには data/stop_requested.flag を作成します。
- ExecutionEngine を外部から強制停止させたい場合、KillSwitch により data/kill.flag が書き込まれます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされますが、本番では 0 を推奨します。

ログ
- ログはコンソール（stdout）と日次ローテートされたファイルに出力されます。
- デフォルトログディレクトリ: logs/
- 主なログファイル例: logs/execution.log, logs/monitoring.log

OpenAI（AI 機能）利用
- OpenAI を使う機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。
- API 呼び出しはリトライ・バックオフの仕組みを備えていますが、API キー・料金・レート制限には注意してください。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル／パッケージと役割の一覧（src/kabusys 配下）。実際のリポジトリでは src/kabusys 以下に配置されています。

- kabusys/
  - __init__.py                 — パッケージ定義（__version__）
  - config.py                   — Settings クラス、.env 自動ロード、環境変数検証ユーティリティ
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py               — ニュースを LLM でスコア化し ai_scores に書き込む
    - regime_detector.py        — マクロ＋MA による市場レジーム判定
  - monitoring/
    - monitoring_db.py          — SQLite 監視 DB の初期化＋永続化層
    - system_monitor.py         — システム状態・データ鮮度監視
    - trade_monitor.py          — (注文ログ等の) 取引監視（ファイル内実装あり）
    - risk_monitor.py           — ドローダウン / ポジション上限監視
    - kill_switch.py            — kill.flag の生成・評価
    - monitoring_engine.py      — 各 Monitor を束ねる
    - alert_manager.py          — 通知（LINE 等）を行う抽象（実装参照）
  - execution/                  — 実行エンジン関連（BrokerFactory / ExecutionEngine / OrderManager 等）
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み付け関数
    - position_sizing.py        — ポジションサイズ計算
    - risk_adjustment.py        — セクターキャップ・レジーム乗数等
  - research/
    - factor_research.py        — momentum/value/volatility 等の計算（DuckDB）
    - feature_exploration.py    — forward returns, IC 計算 等
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py          — 共通のログ設定
    - process_priority.py       — プロセス優先度 / CPU affinity 設定

（実際のファイル一覧はリポジトリを参照してください。ここは主要モジュールの要約です）

---

## 注意点 / 運用メモ

- 環境（KABUSYS_ENV）:
  - development: 開発用（発注なしなどの挙動がある想定）
  - paper_trading: MockBroker を使用しペーパートレード DB に記録（本番 DB と完全分離）
  - live: 本番（実際に発注されます） — 設定ミス、LINE 通知設定などを特に注意
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と簡単なマイグレーション（カラム追加）を行います。
- ログ / ファイル作成:
  - ログディレクトリや data/ ディレクトリの作成権限に注意。logging_setup はディレクトリ作成失敗時にファイル出力をスキップしてコンソールのみで継続します。
- セキュリティ:
  - .env は絶対にリポジトリにコミットしないでください。
- テスト・開発:
  - validate_config の --strict モードで警告も失敗扱いにできます。CI やデプロイ前のチェックに便利です。

---

## よく使うコマンドまとめ

- .env の作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```
- 監視 (Monitoring) 起動（MONITOR_POLL_INTERVAL で間隔を指定可）
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に追記したい実際の .env.example や requirements.txt、簡単な起動手順スクリプトがあれば、それを基により具体的な手順やサンプルを追加できます。必要であればテンプレート .env を生成しますか？