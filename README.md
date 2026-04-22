# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（軽量な実装）。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算・リサーチ、ポートフォリオ構築、AI を使ったニュース・レジーム判定などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムの参照実装です。主要な目的は次のとおりです。

- 発注ロジック（ExecutionEngine）とブローカークライアントの抽象化（ペーパートレードモードあり）。
- システム稼働状況・注文履歴・リスク指標の監視（SQLite を永続化層として使用）。
- DuckDB を用いたデータ分析・ファクター計算（研究モジュール）。
- OpenAI を利用したニュースセンチメント評価・市場レジーム判定（AI モジュール）。
- 設定ウィザードと起動前検証ツールで運用負荷を軽減。

設計方針は「環境による挙動分岐の明確化」「フェイルセーフ（API失敗などで例外を吸収して継続）」「ルックアヘッドバイアスの回避（時刻参照を明示的に受け渡す）」などです。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録
  - 発注履歴 / ポジション管理 / リスク制御の各コンポーネント（OrderManager, RiskManager, Reconciler 等）

- Monitoring
  - SystemMonitor（プロセス生存・リソース・データ鮮度監視）
  - TradeMonitor（注文の滞留・約定異常チェック 等）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じて data/kill.flag を書込み ExecutionEngine を停止させる）
  - MonitoringEngine（ポーリングループで各モニタを統合）
  - 起動スクリプト run_monitoring.py（MONITOR_POLL_INTERVAL により間隔設定可能）

- Data / Research
  - DuckDB を利用したファクター計算（momentum, volatility, value）
  - forward returns / IC 計算 / 統計サマリ用ユーティリティ
  - Portfolio コンポーネント（候補選定・重み計算・位置サイズ計算・セクター制限）

- AI
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメント集計（ai_scores テーブルへの書込み）
  - regime_detector: マクロニュース + ETF（1321）MA200乖離を合成して市場レジーム判定

- ユーティリティ
  - 設定ウィザード: python -m kabusys.config_setup（.env の作成/更新）
  - 設定検証: python -m kabusys.validate_config（.env と config/*.yaml のチェック）
  - ログ設定ユーティリティ（共通化）
  - process priority / cpu affinity ユーティリティ

- ツール
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

1. Python の準備
   - 推奨: Python 3.10+（DuckDB / psutil / openai 等の互換性を確認してください）
   - 仮想環境を作成して有効化することを推奨します。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリのインストール（代表的な依存）
   - pip install duckdb psutil openai
   - 任意（YAML 検証を行う場合）: pip install pyyaml
   - これらはプロジェクトに含まれる機能で必要となる主なパッケージです。requirements.txt があればそちらを使用してください。

3. ディレクトリ作成（初回）
   - data/ と logs/ が必要です。多くのモジュールが自動で作成しますが、事前に作ると権限の問題を回避できます。
     - mkdir -p data logs

4. .env の作成
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper trading 用 DB, デフォルト: data/paper_trading.db）
     - LOG_LEVEL（推奨: INFO）

   - 自動環境読み込み:
     - 起動時にプロジェクトルート（.git または pyproject.toml がある場所）から .env を自動で読み込みます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（起動前）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになります。

---

## 使い方（起動例）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=120  # 120秒間隔
  - 監視は常に Settings の sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 停止するにはプロセスを停止するか、プロジェクトルートの data/stop_requested.flag を作成して停止を促します。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し MockBrokerClient で記録します。
  - 実行中に停止シグナルを送るには data/stop_requested.flag を作成、または監視側の KillSwitch が data/kill.flag を書込むことで停止させることができます。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動でクリア（本番では推奨されません）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- AI モジュールの利用
  - news_nlp.score_news や regime_detector.score_regime はプログラムから呼び出して使用します。OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で渡します。
  - 例（スクリプト内で）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=os.environ.get("OPENAI_API_KEY"))

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）, デフォルト: development
- OPENAI_API_KEY — OpenAI API キー（AI 機能）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

---

## ロギング / ファイル / フラグ

- ログ: logs/<app_name>.log に日次ローテートで保存。setup_logging で統一的に設定されます。
- PID / フラグファイル:
  - data/execution.pid — ExecutionEngine の PID（設定により）
  - data/stop_requested.flag — ローカルで実行を終了させたい場合に作成（run_* スクリプトで参照）
  - data/kill.flag — KillSwitch による強制停止フラグ（監視が書き込む）
- DB マイグレーション: monitoring_db.init_monitoring_db は idempotent（既存テーブル/カラムの有無を検査して必要に応じて追加します）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_monitoring.py — Monitoring の起動スクリプト
  - run_execution.py — ExecutionEngine の起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite の永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文/約定監視: 参照元あり）
    - risk_monitor.py — ドローダウン・ポジション上限
    - kill_switch.py — kill.flag 書込みロジック
    - monitoring_engine.py — 各モニタ統合ループ
    - alert_manager.py — アラート送信（LINE など） ※実装参照
  - execution/ — 発注関連コンポーネント（Engine, OrderManager, RiskManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA200 + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

その他: config/*.yaml（設定雛形）、data/（DB・フラグファイル）、logs/（ログ出力）等

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では .env の中身を十分に確認してください。validate_config は live モード時に追加警告を出します。
- kill.flag は強力な手段です。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動で消去されますが、本番では 0 を推奨します。
- OpenAI を利用する機能は API 使用量とレイテンシに依存します。APIキーと料金体系に注意してください。失敗時は多くの箇所でフェイルセーフが効いています（スコアをスキップして継続など）。
- Paper Trading モードは本番 DB と完全に分離するよう設計されています。ペーパートレード時の DB パスを必ず確認してください。

---

## 参考コマンド集

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン起動
  - python -m kabusys.run_execution

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、この README にプロジェクトのさらに詳細な API 使い方（関数一覧・パラメータ説明）や例を付け加えます。どの部分を拡張しますか？