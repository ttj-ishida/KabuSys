# KabuSys

日本株自動売買システムのコアライブラリと実行スクリプト群。

このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント / レジーム判定）などの主要コンポーネントを含みます。各モジュールは可能な限り副作用を抑え、テスト可能な純粋関数と明確な永続化層（SQLite / DuckDB）に分離して設計されています。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- ExecutionEngine 起動スクリプト（run_execution）
  - 本番 / ペーパートレーディング切替
  - RiskManager / OrderManager / Reconciler 等の組み立て
  - PID ファイル & stop フラグによる制御

- Monitoring（run_monitoring / MonitoringEngine）
  - System / Trade / Risk モニタを定期実行
  - Kill Switch（条件に応じた停止フラグの書き込み）
  - 監視ログを SQLite に永続化（system_status / trade_logs / risk_logs / positions / dashboard）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額/スコア加重の重み計算
  - セクター上限適用、レジーム乗数
  - 発注株数（単元株丸め・リスクベース等）

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）や統計サマリー

- AI（kabusys.ai）
  - ニュースを OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に保存
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定

- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 起動前の設定検証 CLI（validate_config）
  - 日次ローテーションログ設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity ユーティリティ（utils.process_priority）
  - ペーパートレード検証レポート生成ツール（tools.paper_verification_report）

---

## 必要な依存パッケージ（代表）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合に必要）

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# または setup.py / pyproject に応じて pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンしてワークツリーへ移動
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env の作成（対話式ウィザード推奨）

対話式に .env を作成する:
```bash
python -m kabusys.config_setup
```

必要最低限の環境変数（.env の例）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — (AI 機能を使う場合)
- LOG_LEVEL — (DEBUG/INFO/…)

起動前検証:
```bash
python -m kabusys.validate_config
# --strict を付けると警告もエラー扱いで終了
python -m kabusys.validate_config --strict
```

注意:
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- 自動環境読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用）。

---

## 実行方法（使い方）

以下は代表的な実行コマンドです。各スクリプトは package のモジュールとして実行できます。

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）:
```bash
python -m kabusys.run_execution
```
- Monitoring を起動（監視ループ）:
```bash
python -m kabusys.run_monitoring
```
- Paper Trading 検証レポート（期間指定オプションあり）:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- .env 対話型ウィザード:
```bash
python -m kabusys.config_setup
```
- 設定検証:
```bash
python -m kabusys.validate_config
```

環境変数の挙動で知っておくべき点:
- KABUSYS_ENV:
  - development: 開発（発注なしの挙動を想定）
  - paper_trading: ペーパートレード（MockBroker を使用、data/paper_trading.db を使用）
  - live: 本番（実際に発注）
- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔（秒）。デフォルト 60。0 以下や不正値はデフォルトにフォールバック。
- PAPER_FILL_MODE:
  - ペーパートレード時の約定モード。instant / partial / never / reject のいずれか。
- OPENAI_API_KEY:
  - AI 機能（news_nlp, regime_detector）利用時に必要。
- PID / Stop / Kill flag:
  - run_execution は data/execution.pid を PID ファイルに使用（設定可能）
  - 停止用フラグ: data/stop_requested.flag（run scripts が検知して終了）
  - Kill Switch: data/kill.flag（監視が条件に応じて書き込むことで ExecutionEngine 停止を誘導）

ログ:
- デフォルトログディレクトリ: logs/
- setup_logging() がルートロガーを初期化し、stdout と日次ローテートファイル（<app_name>.log）へ出力します。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御します。

停止/強制終了:
- 実行中のエンジンを停止したい場合はプロセスへ SIGINT（Ctrl+C）か、data/stop_requested.flag を作成してください。
- Kill Switch がトリガーされると data/kill.flag が作成され、次回 ExecutionEngine の起動チェックで検知されます。起動時に自動でクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できますが、本番では 0 を推奨します。

---

## 主要モジュールと用途の簡単メモ

- kabusys.config
  - .env 読み込み、Settings クラス（環境変数ラッパー）
- kabusys.config_setup
  - .env 対話型作成ウィザード
- kabusys.validate_config
  - 起動前の設定検証 CLI
- kabusys.run_execution
  - ExecutionEngine 起動スクリプト（paper_trading 切替等）
- kabusys.run_monitoring
  - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL で調整）
- kabusys.monitoring.*
  - MonitoringDB（SQLite 永続化）、System/Trade/Risk Monitor、KillSwitch、MonitoringEngine、アラート管理等
- kabusys.execution.*
  - ブローカーファクトリ、ExecutionEngine、OrderManager、RiskManager 等（エンジン本体）
- kabusys.portfolio.*
  - 候補選定、重み、ポジションサイズ、セクター上限、レジーム乗数
- kabusys.research.*
  - ファクター計算、将来リターン、IC、統計サマリ（DuckDB を参照）
- kabusys.ai.*
  - news_nlp.score_news（ニュースセンチメント → ai_scores）
  - regime_detector.score_regime（ETF MA + マクロ NLP → market_regime）
- kabusys.tools.paper_verification_report
  - ペーパートレード検証レポート生成（SQLite の trade_logs / system_status を集計）

---

## ディレクトリ構成

（リポジトリのルートに `src/kabusys` がある構成を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
      - ... (ExecutionEngine, OrderManager, RiskManager 等)
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
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
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

- data/ (ランタイムで使用されるファイルを想定)
  - monitoring.db (SQLITE_PATH のデフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
  - kabusys.duckdb (DUCKDB_PATH のデフォルト)
  - execution.pid
  - stop_requested.flag
  - kill.flag

- logs/ (ログ出力先、デフォルト)

---

## 開発・拡張のヒント

- DuckDB をローカルに準備し、prices_daily / raw_financials / raw_news 等のテーブルにデータを入れると、research / ai の機能をローカル検証できます。
- AI 機能は OpenAI の API レートやレスポンスフォーマットの変化に依存するため、テスト時は _call_openai_api をモック化してユニットテストを作成してください（コード内で想定されています）。
- monitoring/monitoring_db.py は冪等なスキーマ初期化を行い、古い DB に対する軽微なマイグレーションも実施します。データ互換を壊さないよう注意して変更してください。
- ログ設定は utils.logging_setup.setup_logging() を各起動スクリプト冒頭で呼ぶ想定です。運用では LOG_DIR/LOG_LEVEL を環境変数で調整してください。

---

必要であれば README に追記する内容（例: 詳細な .env.example、起動時の systemd unit / Dockerfile サンプル、各モジュールの API 仕様書など）を指定してください。