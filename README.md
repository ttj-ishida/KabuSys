# KabuSys

日本株自動売買システム（プロトタイプ）

バージョン: 0.1.0

概要:
KabuSys は日本株向けの自動売買基盤のプロトタイプです。戦略のためのファクター計算・リサーチ機能、ポートフォリオ構築、発注実行エンジン（paper/live 切替対応）、監視・Kill Switch、LLM を用いたニュースセンチメント／レジーム判定などを含みます。設計は本番運用を想定し、フェイルセーフ（フェイルオープン）や冪等性を重視しています。

---

## 主な機能

- 実行（Execution）
  - ExecutionEngine（発注・注文管理・リスク管理・再整合）
  - Paper trading モード（MockBrokerClient、データは data/paper_trading.db に分離）
  - 発注ログの永続化（SQLite）

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス有無監視
  - TradeMonitor / RiskMonitor：滞留注文・約定異常・ドローダウン・ポジション上限監視
  - Kill Switch：条件発動で data/kill.flag を書き込み Execution を停止
  - 監視 DB（SQLite）へのログ永続化（monitoring_db）

- ポートフォリオ構築（pure functions）
  - 銘柄選定、等分配／スコア加重、ポジションサイズ算出、セクター上限、レジーム乗数

- リサーチ
  - ファクター計算（Momentum, Volatility, Value など） — DuckDB ベース
  - 特徴量探索: 将来リターン計算、IC（情報係数）計算、統計サマリー

- AI（LLM）
  - news_nlp: ニュースを OpenAI（gpt-4o-mini 等）でスコアリングして ai_scores に保存
  - regime_detector: MA200 とマクロニュースを組み合わせて市場レジーム判定

- ユーティリティ
  - 設定ウィザード（.env 作成）
  - 設定検証 CLI（.env と config/*.yaml のチェック）
  - ロギング設定（標準出力 + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上（型アノテーションで | 演算子を使用）
- SQLite（標準ライブラリに含まれます）
- 推奨依存ライブラリ: duckdb, psutil, openai, PyYAML（検証用）

例（UNIX 系）:

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数設定
   - python -m kabusys.config_setup を実行して対話式に .env を作成
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使用する場合: OPENAI_API_KEY を設定

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）

6. DB/ディレクトリの準備
   - デフォルトで data/ 以下にファイルを作成します。必要に応じて .env のパスを変更してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: LLM を使う機能で必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 専用 DB）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（0/1、本番で1は危険）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）

注意:
- monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。
- paper_trading モードでは発注処理はモック化され紙上で data/paper_trading.db に記録されます。

---

## 使い方（よく使うコマンド例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し paper_trading DB に記録

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI スコア / レジーム判定（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

プロセス停止:
- 監視/実行ともにプロジェクトルートの data/stop_requested.flag を検知して順次停止します（スクリプト内で参照）。
- Kill Switch がトリガーした場合は data/kill.flag が書き込まれ、ExecutionEngine の停止やアラートが発生します。

ログ:
- ログは標準出力（stdout）と logs/<app_name>.log（日次ローテート、30 日保持）へ出力されます。
- setup_logging() により統一的に設定されます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/...
- __init__.py — パッケージ定義（バージョン）
- config.py — 環境変数読み込み・Settings クラス（デフォルトパス・バリデーション）
- config_setup.py — .env 対話式生成ウィザード
- validate_config.py — 設定検証 CLI

- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

- monitoring/
  - monitoring_db.py — 監視用 SQLite スキーマと DB 操作ラッパー
  - system_monitor.py — システム状態・データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — Kill Switch 実装
  - monitoring_engine.py — 各モニターを束ねる実行ループ
  - alert_manager.py, trade_monitor.py 等（アラート送信・取引監視）

- execution/
  - execution_engine.py — 発注セッション管理（Engine）
  - broker_factory.py — ブローカークライアント生成（本番 / モック）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・リスク関連ロジック

- portfolio/
  - portfolio_builder.py — 銘柄選定・スコアソート
  - position_sizing.py — 株数決定・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — ファクター計算（Momentum/Value/Volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- ai/
  - news_nlp.py — ニュースセンチメント分析（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA200 + LLM）

- tools/
  - paper_verification_report.py — Paper Trading レポート生成ツール

その他:
- data/ — デフォルトの DB・フラグ・PID ファイル配置（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid）
- logs/ — ログファイル出力先（デフォルト）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）は慎重に扱うこと。validate_config は live 設定時に警告を出します。
- KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険（自動で Kill Flag を消すため）。
- monitoring は常に SQLITE_PATH（本番用監視 DB）を使用します。paper_trading と分離するには paper_sqlite_path を利用してください。
- OpenAI の呼び出しはレート制限や一時エラーを想定し、リトライとフォールバック（0.0）で安全側に設計されています。
- DuckDB はリサーチ用途で利用されます。大規模データ処理時のリソース制約に注意してください。

---

## 補足

- この README はコードベースの主要部分から抜粋して作成しています。より詳細な設計・アルゴリズムの説明は各ソースファイル（docstring）や設計ドキュメント（存在する場合）を参照してください。
- 不足している依存や詳細（requirements.txt、運用スクリプト、systemd/unit ファイル等）はプロジェクトの実運用要件に応じて追加してください。

この README を起点に、まずは仮想環境で .env を作成 → validate_config → paper_trading モードで動かして挙動を確認することを推奨します。