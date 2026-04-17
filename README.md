# KabuSys

日本株向けの自動売買 / 研究フレームワーク（プロトタイプ）。  
このリポジトリには、取引エンジンの起動スクリプト、監視・アラート機能、ポートフォリオ構築・ポジションサイジングロジック、研究用ファクター計算、LLM を使ったニュース NLP / レジーム判定などが含まれます。

主に以下の用途を想定しています。
- 戦略の研究・バックテスト（DuckDB 上の時系列データ）
- ペーパートレード（本番 DB と分離）
- 実運用（kabuステーション 等を経由した発注）とそれを守る監視・Kill Switch

対応 Python バージョン: 3.10+

---

## 主な機能（抜粋）

- 環境管理
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行エンジン
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading / Live の切替（KABUSYS_ENV に依存）
  - Mock ブローカ（paper_trading 時は data/paper_trading.db を利用）

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - システムリソース・データ鮮度監視、滞留注文・約定異常検出、ドローダウン監視
  - Kill Switch（data/kill.flag）で ExecutionEngine を安全に停止
  - 監視ログの永続化（SQLite / monitoring.db）

- ポートフォリオ構築
  - 候補選定、等比率/スコア加重、セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め・aggregated cap）

- 研究（Research）
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ

- AI（LLM）
  - ニュースセンチメント集約と ai_scores への保存（OpenAI）
  - マクロニュース + ETF ma200 を用いた市場レジーム判定（LLM と計量指標の合成）
  - API 呼び出しはリトライ・バックオフを実装

- ユーティリティ
  - プロセス優先度・CPU affinity 設定（psutil を利用）
  - Paper Trading 用の検証レポート生成スクリプト

---

## セットアップ

前提
- Python 3.10+
- SQLite（OS 標準）
- 推奨パッケージ（例: pip install）:
  - duckdb
  - psutil
  - openai
  - requests
  - PyYAML (config ファイル検証をする場合)
例（仮の requirements 一覧）:
  pip install duckdb psutil openai requests PyYAML

環境変数 / .env
- .env（リポジトリルート）に設定を置くことを想定しています。自動で .env / .env.local をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 主要な環境変数（必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 主要なオプション（デフォルト値）
  - KABUSYS_ENV — execution モード（development / paper_trading / live）（default: development）
  - DUCKDB_PATH — data/kabusys.duckdb
  - SQLITE_PATH — data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — data/paper_trading.db（paper_trading 用）
  - LOG_LEVEL — INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
  - PAPER_FILL_MODE — paper_trading の約定挙動（instant/partial/never/reject、default: instant）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、default: 60）

.env の作成はウィザードを使うと簡単です:
  python -m kabusys.config_setup

設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告を FAIL 扱いにする

データディレクトリ
- デフォルトで data/ 以下を使用します（DB 等）。実行前にディレクトリを作成してください（多くのコードは起動時に親ディレクトリがなければ警告を出します）。

---

## 使い方（主なコマンド）

- 設定ウィザード（.env を作成 / 更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  （--strict を付けると警告も非ゼロ終了扱い）

- 監視プロセス起動（Monitoring）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（秒、デフォルト 60）
  - 監視は本番 sqlite_path を常に使用（KABUSYS_ENV に依存しない）
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループを抜けます

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
  - 停止: data/stop_requested.flag を作成すると実行エンジンへ停止依頼
  - 起動時に data/execution.pid（PID ファイル）を扱うため、プロセス管理に注意してください

- Paper Trading 検証レポート（任意期間）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で指定可能）
  - 稼働率、約定率、レイテンシ等を算出して PASS/FAIL 判定を出力

- AI スコアリング / レジーム判定（ライブラリ関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB の接続オブジェクトを受け取り、テーブルに書き込みます（ai_scores / market_regime 等）

注意:
- OpenAI を使う機能は OPENAI_API_KEY が必要です。API 呼び出しはリトライ / バックオフを実装していますが、料金とレート制限に注意してください。

---

## 監視・停止フラグ

- 実行停止・Kill Switch 関連ファイル
  - data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ（存在すれば安全に終了）
  - data/kill.flag — KillSwitch が設定するファイル（ExecutionEngine 停止のため）
  - data/execution.pid — ExecutionEngine の PID ファイル

KillSwitch（kabusys.monitoring.kill_switch）が生成する理由は監視ログに残り、ExecutionEngine は kill.flag を検知して停止します。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下の主な構成）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / .env ロードと Settings クラス
  - config_setup.py        — .env 対話ウィザード CLI
  - validate_config.py     — 設定検証 CLI
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py     — SQLite スキーマ初期化 + DB アクセス層
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py    — システム状態・データ鮮度監視
    - trade_monitor.py     — 注文滞留・約定異常監視
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — Kill Switch 実装（kill.flag 書き込み）
    - alert_manager.py     — LINE Push によるアラート送信
  - execution/             — ExecutionEngine の関連クラス群（エンジン / ブローカー / 注文管理 等）
    - (OrderRepository, OrderManager, ExecutionEngine, Reconciler, RiskManager, BrokerFactory 等)
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み算出
    - position_sizing.py    — 株数決定・資金配分・単元丸め
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py— 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py           — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py    — ETF ma200 + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート出力

（上記はコードベースの主要モジュール・ファイルを抜粋したものです）

---

## 実運用上の注意点

- KABUSYS_ENV を慎重に設定してください。live モードでは実際に発注されます。
- 本番環境（live）では LINE トークン等の通知設定、KILL_FLAG_CLEAR_ON_START=0（自動クリア無効）を推奨します。
- process priority / cpu affinity 設定は権限に依存します。psutil の例外は警告でスキップされます。
- OpenAI を使用する機能は API コストとレートに注意してください。API エラーはフェイルセーフとして処理されますが、結果欠如により運用判断が変わる可能性があります。
- DB マイグレーションは簡易対応が入っています（monitoring_db.init_monitoring_db が既存スキーマを検査してカラム追加を行う等）。大きなスキーマ変更には注意してください。

---

## 開発 / デバッグのヒント

- ログレベルは .env の LOG_LEVEL で切替できます。開発中は DEBUG を指定すると詳細ログを見られます。
- DuckDB のクエリはローカルで簡単に試せます。research モジュールは DuckDB 接続を受け取り SQL を実行します。
- unit テストやモックで OpenAI 呼び出しを差し替えるために各モジュール内の API 呼び出し箇所 (_call_openai_api 等) を patch する設計になっています。

---

必要であれば、README にサンプル .env テンプレートや、具体的な ExecutionEngine / Broker の設定方法、監視アーキテクチャ図、より詳しいディレクトリツリーを追加できます。どの内容を優先して追記しましょうか？