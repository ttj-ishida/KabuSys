# KabuSys

日本株向けの自動売買システム（ライブラリ兼コマンドスクリプト群）。  
このリポジトリは以下の主要機能を持ち、ローカル開発 / ペーパートレード / 本番（live）運用を意識した設計になっています。

- シグナル生成・ポートフォリオ構築（portfolio）
- 発注実行エンジン（execution）
- 監視・アラート・Kill Switch（monitoring）
- ファクター計算・リサーチ（research）
- ニュース NLP / レジーム判定（AI 統合）
- ユーティリティ（ログ設定・プロセス優先度等）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート）

以下は使い方、セットアップ手順、主要コンポーネントの説明です。

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動コマンド・オプション）
- 環境変数（主要）
- 運用ファイル / フラグ
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株を対象とした自動売買システム基盤です。  
データストレージに DuckDB（分析用）と SQLite（監視・注文ログ）を用い、kabuステーション API 等と統合して実運用を想定したコンポーネント群を提供します。AI（OpenAI）を用いたニュース分析や、監視エンジンによる Kill Switch など安全機構も組み込まれています。

---

## 機能一覧
- 環境設定ウィザード（kabusys.config_setup）: .env の対話的作成・更新
- 設定検証 CLI（kabusys.validate_config）: .env / config/*.yaml の事前チェック
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV により paper_trading モードで MockBroker を使用（paper DB に分離）
  - risk manager / order manager / reconciler 等を組み立てて Engine を起動
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor を定期実行（MONITOR_POLL_INTERVAL で間隔指定可）
  - 監視 DB は環境にかかわらず 本番 sqlite_path を使用（監視は本番 DB を見る設計）
- 監視サブシステム
  - SystemMonitor: CPU / メモリ / ディスク / プロセス / データ鮮度監視
  - TradeMonitor, RiskMonitor: 約定・滞留注文・ドローダウン等の監視（TradeMonitor は別ファイル）
  - MonitoringEngine: 各モニタを束ねてアラートや Kill Switch を評価
  - KillSwitch: 条件を満たしたら data/kill.flag を書き込み Execution を停止
- AI モジュール
  - news_nlp: ニュース記事を OpenAI でスコアリングし ai_scores に書き込み
  - regime_detector: マクロ記事 + ETF MA を合成して市場レジーム判定
- Research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - feature_exploration: 将来リターン計算・IC 計算・統計サマリ
- Portfolio
  - 候補選定・重み計算・ポジションサイズ決定・セクター制限等
- ツール
  - paper_verification_report: ペーパートレード検証レポート生成

---

## セットアップ手順（開発 / ローカル実行の例）

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ※ 本リポジトリでは以下が少なくとも必要:
     - duckdb, psutil, openai
     - PyYAML（config.yaml の検証を行う場合に任意）
   - requirements.txt がない場合は手動で:
     - pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - またはテンプレートをコピーして編集（.env.example があれば参考に）

5. 設定を検証
   - python -m kabusys.validate_config
   - 本番モード等で警告を厳格化するには:
     - python -m kabusys.validate_config --strict

6. 必要ディレクトリを作成（logs, data 等）
   - mkdir -p logs data

7. DB 初期化：起動スクリプトが初回に必要テーブルを作成します（init_monitoring_db を内部で呼出）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Execution Engine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db を利用（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動しない
    - 停止は data/stop_requested.flag を作成、または Kill Switch による data/kill.flag が作成される
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は常に Settings.sqlite_path（本番 sqlite）を参照します
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: env PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

実際のサービス運用では systemd / supervisor / docker 等でプロセス監視・ログ管理を行ってください。

---

## 主要な環境変数（抜粋）
（.env に記載して管理します。必須と推奨を区別）

必須（最低限）
- JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード

運用モード
- KABUSYS_ENV           : development | paper_trading | live （デフォルト: development）
  - paper_trading: execution は paper DB を使う
  - live: 本番運用（注意喚起のチェックあり）

DB / ファイルパス
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : paper trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH         : execution PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH        : Kill Switch の flag パス（デフォルト data/kill.flag）

ログ / 実行
- LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR               : ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒、デフォルト 60）

AI
- OPENAI_API_KEY        : OpenAI API キー（AI モジュール使用時必須）
- PAPER_FILL_MODE       : paper_trading の注文約定挙動 instant | partial | never | reject（デフォルト instant）

通知（任意）
- LINE_CHANNEL_ACCESS_TOKEN : LINE 通知用トークン（任意）
- LINE_USER_ID              : 通知先ユーザー ID（任意）

特別挙動
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアする (0/1、デフォルト 0)
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env の自動ロードを無効化

---

## 運用ファイル / フラグ
- data/stop_requested.flag : run_execution / run_monitoring がループを抜けるためのローカル停止フラグ（手動で作成）
- data/kill.flag          : KillSwitch が作成する停止フラグ（Execution を停止するため）
- data/execution.pid      : ExecutionEngine が PID を書き込むファイル
- logs/<app_name>.log     : 各コンポーネントのローテートログ（logs ディレクトリ、日次ローテート・30日保持）

停止方法（手動）
- 監視ループや実行スレッドを止めたい場合、プロセスに SIGINT（Ctrl+C）を送るか、data/stop_requested.flag を作成します。KillSwitch 条件で自動的に data/kill.flag が作成されることもあります。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主なファイル・モジュールです。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化層
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム・データ鮮度監視
    - risk_monitor.py         — ドローダウン等のリスク監視
    - kill_switch.py          — Kill Switch 実装（flag ファイル書込）
    - trade_monitor.py        — （滞留注文等の監視、コード参照あり）
    - alert_manager.py        — （アラート送信管理、LINE など）
  - execution/
    - execution_engine.py     — ExecutionEngine（発注セッション管理）
    - broker_factory.py       — BrokerClient の生成（Mock/Real 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロ NLP）
  - data/                    — 実行時生成データ（DB / flag / pid / logs 等は外部に置くこと推奨）

---

## 注意事項 / 運用上のヒント
- 監視（run_monitoring）は常に Settings.sqlite_path（本番監視 DB）を参照します。監視は実運用の DB を見るため、開発時に誤って本番 DB を壊さないよう注意してください。
- Execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite に完全に分離して発注シミュレーションを行います（本番 DB を汚さない）。
- AI モジュールを使うには OPENAI_API_KEY の設定が必須です。API 呼び出しはレート制限や一時エラーに対してリトライ処理を行いますが、API コストやレート上限には注意してください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります（warning が出ます）。
- Kill Switch はドローダウンやポジション上限の超過を検知すると data/kill.flag を書き込み、Execution 側はこれを検知して安全停止します。KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると危険なのでデフォルト 0 を推奨します。
- .env は絶対に Git 等で公開しないでください（シークレットを含むため）。

---

## 追加情報 / 開発者向け
- テストや CI のために .env の自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 設定検証（validate_config）は PyYAML がないと config/*.yaml の内容検証をスキップします。yaml の検証を行いたい場合は PyYAML をインストールしてください。
- ローカルでの paper_trading 検証:
  1. KABUSYS_ENV=paper_trading を .env に設定
  2. python -m kabusys.run_execution を実行（MockBroker を使い paper DB に記録）
  3. python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD で結果を確認

---

README は以上です。追加で「導入手順の自動化 (Dockerfile / systemd ユニット)」や「config/*.yaml のフォーマット説明」「個別モジュールの API ドキュメント」などが必要であれば、その点を指定していただければ追記します。