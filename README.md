# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買フレームワーク（小規模プロダクション / ペーパートレード両対応）です。  
本 README はコードベースの主要コンポーネント・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の役割を担うモジュール群で構成されています。

- 注文送信／注文管理（ExecutionEngine）
- システム監視（Monitoring）
- ポートフォリオ構築（ファクター計算・ウェイト算出・サイズ計算）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI 連携（ニュースセンチメント評価 / レジーム判定）
- 設定管理・ユーティリティ（.env ウィザード、設定検証、ログ設定、プロセス優先度設定 等）
- 検証ツール（Paper Trading 検証レポート生成）

設計方針として、本番 DB とペーパートレード DB を分離、DuckDB を分析用に利用、.env による設定管理、ロギングは統一インターフェースで日次ローテート、OpenAI など外部 API 呼び出しはフェイルセーフ設計になっています。

---

## 機能一覧（主要）

- ExecutionEngine 起動（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
  - リスク管理（RiskManager）、OrderManager、Reconciler を組み合わせて発注セッションを実行
  - 停止フラグ（data/stop_requested.flag / data/kill.flag / data/execution.pid）に対応

- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態・株価データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常等の監視
  - RiskMonitor: ドローダウン・ポジション上限検出とアラート記録
  - KillSwitch: 条件により ExecutionEngine 停止のための kill.flag 書き込み
  - MonitoringDB: SQLite を用いた監視ログ永続化（テーブル作成は冪等）

- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等重/スコア重み、ポジションサイズ計算（単元株丸め・利用可能現金に基づくスケーリング）
  - セクター上限適用、レジームに応じた乗数計算

- 研究用（research パッケージ）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計

- AI モジュール（ai パッケージ）
  - news_nlp: ニュースを OpenAI に送り銘柄ごとにセンチメントを算出し ai_scores に書き込み（バッチ・リトライ実装）
  - regime_detector: ETF(1321) MA200 とマクロニュース LLM 評価を合成して market_regime を算出

- ユーティリティ
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml のスタティックチェック CLI
  - logging_setup: Stream + TimedRotatingFileHandler による統一ログ設定
  - process_priority: psutil を使ったプロセス優先度／CPU affinity 設定

- ツール
  - paper_verification_report: ペーパートレード DB を解析し稼働率・約定率・レイテンシ等の検証レポートを出力

---

## セットアップ手順（開発 / ローカル実行向け）

1. リポジトリをクローンし、Python 仮想環境を準備
   - python 3.10+ を想定（コード上の型注釈などから）
   - 仮想環境有効化後、必要パッケージをインストールしてください（以下は例）:
     - duckdb, psutil, openai, PyYAML（任意で config 検証用）、その他必要なパッケージ
   - 例:
     - pip install duckdb psutil openai PyYAML

2. .env を作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードに従い必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力
   - 生成された .env は絶対に Git にコミットしないでください

3. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

4. データディレクトリ
   - デフォルトでは data/ 配下に SQLite / PID /フラグを格納します。必要時に .env でパスを変更してください。
   - ログはデフォルト logs/ に出力され、アプリ名ごとに日次ローテーションします。

5. OpenAI を使う機能を利用する場合
   - 環境変数 OPENAI_API_KEY を設定するか、各関数に api_key を渡してください。

---

## 重要な環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード

- 実行環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading: MockBroker を使用、paper DB に記録
    - live: 本番モード（発注が実行されます）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

- ログ / ログレベル
  - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
  - LOG_DIR — ログディレクトリ（デフォルト: logs/）

- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH — PID / kill.flag のパス（デフォルト: data/execution.pid, data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" で有効、デフォルト: "0"）

- Paper Trading 動作
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時に必要）

（上記以外にもコード内で参照される環境変数が存在します。.env.example を参照してください。）

---

## 使い方（主なコマンド例）

- 対話式 .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗とする）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - 本番／ペーパーは KABUSYS_ENV で切り替え:
    - KABUSYS_ENV=development python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動後は data/execution.pid に PID が書かれ、停止指示は data/stop_requested.flag（監視プロセス用）や data/kill.flag（KillSwitch 用）を用いる

- Monitoring を起動（ポーリング）
  - MONITOR_POLL_INTERVAL を上書きして実行:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- 研究・AI 関数はモジュールをインポートして利用
  - 例: from kabusys.research import calc_momentum
  - AI スコア付与: kabusys.ai.score_news(conn, target_date, api_key=...)

- ログの確認
  - デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）

---

## 停止・安全機構

- stop フラグ:
  - data/stop_requested.flag — run_execution/run_monitoring が監視している停止フラグ（存在するとループ終了）
  - data/kill.flag — KillSwitch が書き込み、ExecutionEngine に明示的停止を要求する（存在すると Execution を停止）
  - data/execution.pid — ExecutionEngine の PID 管理

- KillSwitch は RiskMonitor の結果などに基づき kill.flag を作成する仕組み（冪等で再書き込みしません）。本番では KILL_FLAG_CLEAR_ON_START を "0" にすることを推奨します。

---

## ディレクトリ構成（主要部分）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings オブジェクト
  - config_setup.py — .env ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py — ニュースセンチメント LLM インタフェース
    - regime_detector.py — レジーム判定
    - __init__.py

  - execution/  （発注関連コンポーネント）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
    - __init__.py

- data/ — 実行時に使用する SQLite、PID、フラグ等（デフォルトパス）
- logs/ — ログファイル（デフォルト）

---

## 開発・運用時の注意点

- .env は機密情報（APIキー等）を含むため絶対にコミットしないこと。
- KABUSYS_ENV=live の場合は本番発注されるため、設定（LINE 通知先・kill フラグ挙動等）を十分に確認すること。
- OpenAI API の呼び出しは外部依存でありレート制限・エラー対策（リトライ・バックオフ）が実装されていますが、請求・利用制限に注意してください。
- DuckDB / SQLite のパスは .env で適切に分離する（特に paper_trading と production の DB は明確に分離すること）。
- ロギングは日次ローテートで 30 日分保持されます。ストレージ容量管理を検討してください。

---

## コントリビュート / 拡張案（簡単に）

- 銘柄別 lot_size のサポート（現状はグローバル lot_size）
- position_sizing の GPU/並列化や高速化（大規模 universe 向け）
- ai モジュールの unit テスト（OpenAI 呼び出しのモック化推奨）
- monitoring のアラート通知チャネル追加（Slack、PagerDuty 等）

---

必要に応じて README に追記します。特定のコマンドの実行例や設定ファイル例（.env.example / config/*.yaml）の生成を希望される場合は、その旨お知らせください。