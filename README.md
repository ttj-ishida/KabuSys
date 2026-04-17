# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部実装を含みます。  
各種モジュールは取引エンジン、監視、ポートフォリオ構築、ファクター研究、AI（ニュースNLP／レジーム判定）などで構成されています。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ自動売買フレームワークです。

- 注文実行（ExecutionEngine） — 実際のブローカーAPI／ペーパートレード用のモックを通じた発注処理
- 監視（Monitoring） — システム健全性、データ鮮度、注文滞留、約定異常、リスク（ドローダウン、ポジション上限）を継続監視
- ポートフォリオ構築 — 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム補正
- リサーチ／ファクター計算 — DuckDB 上の価格・財務データからファクターを計算
- AI モジュール — ニュースを LLM（OpenAI）でスコアリングし、マクロセンチメントと統合して市場レジーム判定
- ユーティリティ／ツール — .env ウィザード、設定検証、ペーパートレード検証レポート等

設計方針の例：
- DuckDB は分析用（prices_daily, raw_financials 等）に使用。SQLite は監視ログ／発注ログ等の永続化に使用。
- 本番／ペーパー環境を分離（ペーパートレード時は専用 SQLite を使用）。
- LLM 呼び出しは API キー必須で、リトライロジック・レスポンス検証を実装。
- ルックアヘッドバイアスを避ける（日時参照方法に配慮）。

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し DB を分離）
- run_monitoring.py: SystemMonitor をポーリングして system_status 等を記録（MONITOR_POLL_INTERVAL で間隔設定可能）
- monitoring/*: 監視関連（SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, MonitoringDB, KillSwitch, AlertManager）
- portfolio/*: 候補選定・重み付け・ポジションサイズ計算・セクター制限・レジーム乗数
- research/*: DuckDB を使ったファクター／リターン計算、IC や統計サマリー
- ai/*: ニュースNLP（score_news）・市場レジーム判定（score_regime） — OpenAI を使用
- tools/paper_verification_report.py: ペーパートレード検証レポート生成
- config_setup.py: .env 対話ウィザード（初期設定の生成）
- validate_config.py: 環境変数・config/*.yaml の事前検証ツール
- utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

---

## 必要な環境変数（主なもの）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意・デフォルト
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: `development`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（`1` でクリア、デフォルト `0`）

注意:
- monitoring（run_monitoring）は環境にかかわらず Settings.sqlite_path（デフォルト: `data/monitoring.db`）を使用します。
- ExecutionEngine は KABUSYS_ENV が `paper_trading` の場合、ペーパートレード専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。

---

## セットアップ手順（基本）

1. リポジトリをクローンし Python 環境を用意
   - 推奨: 仮想環境（venv / poetry / pipenv 等）
2. 必要な Python パッケージをインストール
   - 例: requirements.txt がある場合は `pip install -r requirements.txt`
   - 必須ライブラリ（実装内で参照）: duckdb, psutil, requests, openai（AI を使う場合）、PyYAML（設定ファイル検証を行う場合）
3. .env を作成
   - 対話式ウィザード: `python -m kabusys.config_setup`
   - もしくは手動でルートに `.env` を作成し必要項目を設定
4. 設定検証（任意）
   - `python -m kabusys.validate_config`
   - `--strict` を付けると警告もエラー扱いになります
5. data ディレクトリ作成（自動で作られる場合もありますが権限調整のため確認）
   - `mkdir -p data`
6. DuckDB / SQLite 初期化はアプリ起動時に自動で行われます（monitoring DB のスキーマは init_monitoring_db で冪等的に作成・マイグレーションされます）。

---

## 使い方（主要コマンド）

- 設定ウィザード（.env を生成／更新）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: 実行中は data/execution.pid 等を扱います。停止は `data/stop_requested.flag` を作成するか KillSwitch による `data/kill.flag` を利用します。
  - KABUSYS_ENV が `paper_trading` の場合、MockBroker を使い `data/paper_trading.db` に記録します。
- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`
  - run_monitoring は常に Settings.sqlite_path（監視 DB）を使用します（環境に依存しません）。
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パス: `data/paper_trading.db`（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- AI / レジーム判定（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キー（OPENAI_API_KEY 環境変数または api_key 引数）が必要

停止方法の例:
- run_monitoring / run_execution が監視する停止フラグ:
  - data/stop_requested.flag — 存在を検知すると監視ループ / エンジンは終了処理を行います
- KillSwitch は特定のリスク条件発生時に data/kill.flag を書き込んで ExecutionEngine を停止させます（ExecutionEngine 起動時にこのフラグの自動クリア設定を `KILL_FLAG_CLEAR_ON_START=1` で行えますが、本番では推奨されません）。

ログレベルの設定:
- LOG_LEVEL 環境変数で調整（DEBUG/INFO/WARNING/...）

プロセス優先度:
- 起動スクリプトでは set_process_priority("high") が呼ばれます（psutil 必須）。権限やプラットフォームによってはスキップされます。

---

## ディレクトリ構成（src/kabusys ベース）

- kabusys/
  - __init__.py — パッケージ設定（version 等）
  - config.py — 環境変数／.env 自動読み込み、Settings クラス
  - config_setup.py — .env 対話式ウィザード（CLI）
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度／CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite スキーマ作成・永続化 API（MonitoringDB）
    - system_monitor.py — CPU/MEM/DISK/プロセス PID / データ鮮度チェック
    - trade_monitor.py — 注文滞留／約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書込み・管理
    - alert_manager.py — LINE によるプッシュ通知（クールダウンを持つ）
    - monitoring_engine.py — 複数 Monitor の束ねとループ制御
  - execution/ (一部参照されるモジュールは存在を想定)
    - execution_engine.py, broker_factory.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, order_record.py など（本コードベースの一部）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け（equal / score）
    - position_sizing.py — 株数計算・ロット丸め・Aggregate cap
    - risk_adjustment.py — セクター制限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — momentum/volatility/value 等ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）→ ai_scores 書込
    - regime_detector.py — マクロ＋MA200 からレジーム判定（OpenAI optional）
    - __init__.py

補足:
- monitoring_db.init_monitoring_db() はテーブル作成だけでなく、既存 DB に対する軽微なマイグレーション（カラム追加）も行います（冪等）。
- tools / research モジュールは DuckDB 上の分析用データ（prices_daily, raw_financials, raw_news 等）を前提としています。

---

## 注意点・運用上のヒント

- 本番環境（KABUSYS_ENV=live）では、kill_flag_clear_on_start を `0` にしておくことを強く推奨します。自動クリアは危険です。
- OpenAI 呼び出しは料金発生・レート制限の可能性があるため、API キーの管理とレート制御を考慮してください。score_news / score_regime はリトライ・フォールバックの実装がありますが、長時間のブロック等を考慮した監視が必要です。
- ペーパートレード時は DB を分離するため、本番データとログが混ざりません。PAPER_FILL_MODE を設定して約定挙動を変更できます。
- データ鮮度チェックは DuckDB 上の get_last_price_date を参照します。prices_daily の取り込みが遅れると警告／アラート対象になります。
- LINE 通知を使う場合は LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を設定してください（AlertManager が使用）。

---

この README はコードの主要部分からの抜粋・要約です。詳細な挙動・パラメータや運用ルールは各モジュールの docstring / ソースコード内コメントを参照してください。README に記載の無い実行パラメータや拡張機能はソースコード側の実装に従います。