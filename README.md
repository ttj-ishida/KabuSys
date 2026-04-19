# KabuSys — README (日本語)

KabuSys は日本株向けの自動売買 / 研究 / 監視を目的としたモジュール群です。本リポジトリは本番発注エンジン、監視エンジン、ポートフォリオ構築、ファクター計算、AI を用いたニュース評価などの機能を含みます。

以下はコードベースに基づく README.md です。

---

## プロジェクト概要

KabuSys は次のような機能を提供する Python ベースの自動売買フレームワークです。

- 日次・リアルタイムに近いワークフローでの発注（ExecutionEngine）
- システム稼働監視・データ鮮度チェック・リスク監視（Monitoring）
- ペーパートレード用の分離 DB を使った検証運用モード
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ファクター計算・特徴量探索（DuckDB を使用した分析）
- ニュースを LLM(OpenAI) で評価する AI モジュール（センチメント → ai_scores）
- 構成ウィザード・設定検証スクリプト・レポート生成ツール

設計上の注意点：
- .env（環境変数）を用いて挙動を切り替えます。
- Paper Trading（KABUSYS_ENV=paper_trading）の場合、発注はモッククライアントに切り替わり専用 SQLite DB に書き込みます（本番 DB と分離）。
- 監視（monitoring）はどの環境でも本番の sqlite_path を参照します（運用監視は本番 DB を監視する想定）。

---

## 主な機能一覧

- 実行エンジン（run_execution.py）
  - ブローカークライアントの抽象化（本番 / モックを切替）
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の起動
  - 停止フラグ（data/stop_requested.flag）検知で安全停止
  - paper_trading 時は data/paper_trading.db を利用

- 監視エンジン（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - Kill Switch（条件で data/kill.flag を書き込み、ExecutionEngine を停止）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）

- 環境設定ツール
  - config_setup.py: 対話式で .env を作成・更新
  - validate_config.py: .env と config/*.yaml のチェック（--strict で警告を FAIL 扱い）

- 研究・分析
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン・IC・統計サマリ

- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定・等重・スコア重み
  - portfolio.position_sizing: 株数決定（リスクベース・等分配等）
  - portfolio.risk_adjustment: セクターキャップ・レジーム乗数

- AI（OpenAI）連携
  - ai.news_nlp: ニュースを LLM でセンチメント評価して ai_scores に書き込み
  - ai.regime_detector: ETF MA とマクロニュースでレジーム判定し market_regime に書き込み

- ユーティリティ
  - tools.paper_verification_report: Paper Trading の検証レポート生成
  - utils.logging_setup: 統一ログ設定（コンソール + 日次ローテートファイル）
  - utils.process_priority: プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

1. Python 環境を準備（推奨: 仮想環境）
   - Python 3.9+ を使用してください（コードは型注釈に modern syntax を使用）。

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. 依存パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証用、任意）
   - 例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. .env の作成
   - 対話式ウィザードを使う:
   ```
   python -m kabusys.config_setup
   ```
   - または手動でプロジェクトルートに `.env` を作成する。最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 代表的なオプション（デフォルトがあるため不要な場合あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（paper_trading 時）
     - LOG_LEVEL / LOG_DIR
     - OPENAI_API_KEY（AI モジュールを使う場合）

   - サンプル最小 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）
   - デフォルトの SQLite / DuckDB / logs ディレクトリ等が無ければ自動作成されますが、権限等の問題がある場合は事前に作成してください。

---

## 使い方

- 実行エンジンを起動（本番/ペーパーは KABUSYS_ENV に依存）
```
python -m kabusys.run_execution
```
- 監視エンジンを起動
```
python -m kabusys.run_monitoring
```
  - ポーリング間隔を環境変数で変更:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は常に Settings.sqlite_path（本番用 sqlite_path）を使用します。

- 停止 / 停止フラグ
  - data/stop_requested.flag: run_monitoring/run_execution のループ停止判定に使用（存在すると起動中プロセスが終了）。
  - data/kill.flag: KillSwitch が書き込むフラグで ExecutionEngine に停止シグナルを送信（存在すると起動を阻止 / 停止）。
  - KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

- Paper Trading 用レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を直接指定する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI モジュール（スクリプトから呼び出す・API キー必要）
  - OPENAI_API_KEY を環境変数に設定しておくか、関数呼び出し時に明示的に渡します。
  - 例（ライブラリ利用）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

- ロギング
  - ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数または setup_logging の引数で変更可能。
  - ログレベルは LOG_LEVEL（または setup_logging の level 引数）で制御。

---

## 主要ファイル / ディレクトリ構成

以下は主要モジュールとその概略です（ソースツリーの抜粋）。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings クラス (.env 自動ロード機能含む)
  - config_setup.py — .env を対話式に作成/更新するウィザード
  - validate_config.py — 起動前に設定・ファイルの整合性をチェックする CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - execution/  (発注関連コンポーネント)
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py

  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル定義・DB ラッパー
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス生存チェック
    - trade_monitor.py — 注文ログ監視（滞留注文・約定異常など）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグファイルにより Execution 停止指示
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - alert_manager.py — LINE 等への通知（実装箇所あり）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・利用資金のスケール調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — Momentum, Volatility, Value の計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリ

  - ai/
    - news_nlp.py — OpenAI を用いたニュースセンチメント評価（ai_scores へ書込）
    - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定

  - tools/
    - paper_verification_report.py — Paper Trading の評価レポート生成

  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity（psutil 使用）

- data/ (既定)
  - monitoring.db (SQLITE_PATH のデフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
  - kabusys.duckdb (DUCKDB_PATH のデフォルト)
  - execution.pid, stop_requested.flag, kill.flag など

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 主要:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（INFO 等）
- LOG_DIR（ログ保存先）
- OPENAI_API_KEY（AI 機能利用時）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリア、0/1）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリアを有効にしないでください（KILL_FLAG_CLEAR_ON_START=0 推奨）。
- paper_trading は本番データベースと完全に分離されるよう設計されていますが、設定ミスによる参照先の取り違えに注意してください。
- OpenAI API を使用する機能は API レート制限やエラーに備えたリトライロジックを持ちますが、API キーやコスト管理を十分に行ってください。
- ログディレクトリや DB ファイルの書き込み権限を事前に確認してください（自動作成できない環境もあります）。

---

README は以上です。必要であれば次の項目を追加で生成できます：
- 開発者向けの詳細なアーキテクチャ図
- 各モジュールの API ドキュメント（関数一覧と引数）
- サンプル .env.example ファイル

どれを追加しますか？