# KabuSys

日本株自動売買システムのコアライブラリ群と実行ユーティリティ群です。  
本リポジトリにはトレード実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースNLU / レジーム判定）などのコンポーネントが含まれます。

※ 本 README はソースコードを元に作成しています。実運用前に必ず `python -m kabusys.validate_config` 等で設定検証を行ってください。

---

## プロジェクト概要

- 目的: 日本株自動売買の実行基盤と運用監視、バックテスト／リサーチ補助ツールを提供する。
- 設計方針:
  - 環境変数（.env）ベースの設定管理
  - 本番/ペーパー（分離された DB）を明確に分ける
  - DuckDB を分析/リサーチ用に利用、SQLite を監視・注文履歴用に利用
  - OpenAI API を用いたニュースセンチメント／レジーム判定をオプションで提供
  - フェイルセーフ寄りの挙動（API失敗時はフォールバック等）

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine の起動（`KABUSYS_ENV=paper_trading` で MockBrokerClient を利用）
- 監視・アラート
  - run_monitoring.py: SystemMonitor を定期ポーリング
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager 等
- 環境設定
  - config_setup.py: 対話式で .env を作成・更新
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
- ポートフォリオ構築
  - portfolio: 候補選定、重み計算、位置サイズ（株数）算出、リスク調整
- リサーチ
  - research: ファクター計算（モメンタム、ボラティリティ、バリュー）、特徴量探索（IC 等）
  - DuckDB を用いた価格・財務データ参照
- AI（オプション）
  - ai.news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores 書き込み）
  - ai.regime_detector: マクロ記事 + ETF MA 乖離で市場レジーム判定（market_regime 書き込み）
- 運用ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## 前提 / 必要環境

- Python 3.10 以上（`X | Y` 型ヒントを使用しているため）
- 外部ライブラリ（主に pip インストール）
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（`validate_config` 実行時に YAML 検証を行う場合。なくても警告のみ）
- SQLite（標準ライブラリの sqlite3 を使用）
- ネットワーク接続（kabuステーション API / OpenAI 利用時）

例（仮のインストールコマンド）:
```
python -m pip install duckdb psutil openai pyyaml
```

---

## 環境変数（主なもの）

必須（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用上よく使う / 重要:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: MockBrokerClient を使用し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で必須
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（0/1、本番では 0 推奨）

設定は `.env` に保存できます。自動ロードはプロジェクトルートに `.env` / `.env.local` があれば実行時に読み込まれます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - python -m pip install -r requirements.txt
   - （requirements.txt が無い場合は上記の主要パッケージを個別にインストール）

3. 初期設定（対話式ウィザード）
   - python -m kabusys.config_setup
     - .env を対話式で作成／更新します（J-Quants / Kabu API の秘密情報等を設定）

4. 設定検証（任意だが必須推奨）
   - python -m kabusys.validate_config
   - 問題があるとエラー・警告が出ます。--strict をつけると警告も FAIL 扱いになります。

5. DB 初期化
   - 実行スクリプトは起動時に必要なテーブルを（冪等に）作成します。特別な初期化手順は不要です。

---

## 使い方（主要コマンド）

- 実行エンジンを起動（デーモン化/管理は外部プロセス監視に任せる）
  - python -m kabusys.run_execution
  - 動作: Process 優先度を上げ、適切な SQLite/ DuckDB に接続して ExecutionEngine を起動します。
  - 注意: data/stop_requested.flag があると起動しない／停止させます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60 秒）。
  - 監視は Settings.env にかかわらず本番 sqlite_path を使用します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで PAPER_TRADING_SQLITE_PATH を指定できます（優先）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- AI 機能（スコアリング等）を手動実行（スクリプト内関数を直接呼ぶ場合）
  - OpenAI API キーが必要です（OPENAI_API_KEY または引数で渡す）。
  - 例: Python REPL から duckdb 接続を作成して kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
  - 注意: AI 呼び出しは API エラーに対してリトライ等の保護がありますが、API キーの管理には注意してください。

停止方法:
- 実行中の run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を作成すると安全に停止する仕組みがあります。
- KillSwitch（監視からの自動停止指示）は data/kill.flag を書き込みます（起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされますが、本番では 0 推奨）。

---

## 注意点 / 運用メモ

- paper_trading モードでは本番 DB と分離して動作します（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring は監視用 DB に対して本番 sqlite_path を使用する設計です（監視は実運用を想定）。
- AI 機能を有効にする場合は OpenAI の利用料金に注意してください。
- process priority や cpu affinity の設定は psutil を利用して行います。権限不足や未対応 OS の場合は警告が出てスキップされます。
- DuckDB に期待するテーブル（prices_daily / raw_financials / raw_news 等）が存在することを確認してください。validate_config は config YAML の存在を警告しますが、DuckDB 内データの有無は運用者が準備する必要があります。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / Settings クラス、自動 .env ロードロジック
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ・モジュール:
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI 経由）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
- monitoring/
  - monitoring_db.py — SQLite による監視ログの永続化層
  - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / プロセス監視
  - trade_monitor.py — 滞留注文・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — kill.flag 書き込みロジック
  - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
  - alert_manager.py — （アラート送信ロジック：未完或いは実装場所）
- execution/  (発注系: broker, order_manager, engine 等。起動は run_execution)
  - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py など
- portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 株数決定・スケーリング・lot 単位処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value 等のファクター計算
  - feature_exploration.py — forward returns / IC / summary 等
- monitoring/（上記）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（実際のプロジェクトではさらに細かいファイルが存在します。上記は README 作成時に提示された主要ソースを抜粋した一覧です。）

---

## よくある質問

Q: `.env` を自動で読み込ませたくない  
A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト用途など）。

Q: 監視ループの間隔を変更したい  
A: `MONITOR_POLL_INTERVAL`（秒）を環境変数で設定できます。無効（0以下や非数）な値はデフォルト 60 秒にフォールバックします。

Q: Paper Trading と本番 DB は分離されていますか？  
A: はい。`KABUSYS_ENV=paper_trading` のとき run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。監視は本番 sqlite_path を参照する設計なので注意してください。

---

何か追加で README に含めたい情報（例: systemd ユニット例、Docker/Docker Compose、サンプル .env.example、テストの実行方法など）があれば教えてください。必要に応じて追記します。