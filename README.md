# KabuSys

日本株自動売買システムのサンプル実装。ポートフォリオ構築、発注実行（本番 / ペーパートレード）、監視、研究（ファクター計算）および AI ベースのニュースセンチメント評価などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の役割を持つ Python パッケージ群です。

- シグナル → ポートフォリオ構築 → 発注までの ExecutionEngine（本番・ペーパートレード対応）
- システム稼働監視（CPU / メモリ / ディスク / データ鮮度 / 発注滞留 等）
- リスク監視（ドローダウン・ポジション上限）と Kill Switch（停止フラグ）
- DuckDB を用いた研究用ファクター計算 / 特徴量評価
- OpenAI を利用したニュース NLP / レジーム判定
- ペーパートレード検証レポート生成ツール

設計方針は「本番発注ロジックと研究ロジックの分離」「フェイルセーフ（API失敗時は安全側で継続）」「ルックアヘッドバイアス回避（date を明示的に渡す）」などです。

---

## 主な機能一覧

- Execution（run_execution.py）
  - 本番 / ペーパートレード切り替え（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント抽象化（ペーパー時は Mock）
  - リスク管理（RiskManager）、オーダー管理（OrderManager）、Reconciler、ExecutionEngine

- Monitoring（run_monitoring.py / monitoring/*）
  - SystemMonitor：プロセス状態・データ鮮度を監視し `system_status` に記録
  - TradeMonitor：注文ログの監視（滞留注文・異常約定など）
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクログ
  - KillSwitch：条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringEngine：各 Monitor を束ねてポーリング実行

- DB 層
  - monitoring_db.init_monitoring_db：監視用 SQLite スキーマ（冪等）
  - duckdb を分析用データベースに使用（データは prices_daily / raw_financials 等を想定）

- 研究 / リサーチ（research/*）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC 計算、統計サマリ

- AI（ai/*）
  - news_nlp.score_news：OpenAI を使ったニュースから銘柄別センチメント（ai_scores テーブル更新）
  - regime_detector.score_regime：ETF MA とマクロニュースを組み合わせて市場レジーム判定（market_regime 更新）

- ツール
  - config_setup.py：.env の対話式ウィザード生成
  - validate_config.py：起動前設定検証 CLI
  - tools.paper_verification_report：ペーパートレード DB から検証レポート生成

- ユーティリティ
  - logging_setup.setup_logging：統一的なログ設定（stdout + 日次ローテーション）
  - process_priority.set_process_priority：プロセス優先度設定（Windows / POSIX 対応）

---

## セットアップ手順

前提：Python 3.10+ を推奨（型注釈や構文に依存）。

1. リポジトリをクローン / 展開
2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール（最低限の例）
   - pip install duckdb psutil openai
   - オプション（YAML 検証用）: pip install pyyaml
   - （requirements.txt がある場合はそれを使用）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0|1

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで exit(1)

6. データディレクトリ作成（ログ・DB 保存先など）
   - デフォルトでは `data/`、`logs/` を使用するので適宜作成（logging_setup が自動作成を試みますが権限に注意）

---

## 使い方（起動 / 停止 / ツール）

- ExecutionEngine を起動（バックグラウンドで動かす想定）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用されペーパートレード DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録されます。
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
    - 実行中は pid ファイル（デフォルト data/execution.pid）を作成します。

- Monitoring を起動（監視ループを開始）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関係なく production 設定の sqlite_path を使用して監視データを記録します。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで監視ループが検知して終了します。

- 停止（Kill / Graceful Stop）
  - Kill Switch（自動）：RiskMonitor + KillSwitch の条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送る設計。
  - 手動停止: 実行中のプロセスに対しては通常の OS シグナル（Ctrl+C / kill）や、`data/stop_requested.flag` を作ることで run_execution/run_monitoring が検知して終了します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
  - 確認指標: 稼働率、注文成功率、送信率、P95 レイテンシ など。閾値はソース内で定義（例: uptime >= 99%、fill_rate >= 90%）。

---

## 主要環境変数（まとめ）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境 / 動作制御
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading のとき発注は MockBrokerClient により隔離される
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）

- DB 関連
  - DUCKDB_PATH: 分析用 DuckDB（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）

- 監視関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_PATH: KillSwitch の flag ファイルパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）※本番では 0 を推奨

- AI
  - OPENAI_API_KEY: news_nlp / regime_detector で必要

---

## ログ

- logging_setup.setup_logging を各起動スクリプト最初に呼んでいるため、標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。
- ファイルは日次ローテーションで最大 30 日分保持されます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py               — パッケージ定義
  - config.py                 — 環境変数・設定取得ロジック（Settings クラス）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB の初期化・永続化 API
    - monitoring_engine.py    — 各モニタを束ねるエンジン
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py        — 注文ログ監視（滞留注文等）※実装参照
    - risk_monitor.py         — ドローダウン・ポジション制限監視
    - alert_manager.py        — 通知（LINE など）管理（実装参照）
    - kill_switch.py          — kill.flag の生成・管理
  - execution/
    - execution_engine.py     — 発注エンジン本体（セッション管理等）
    - broker_factory.py       — BrokerClient 作成（Mock / 本番）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・スコアソート・重み算出
    - position_sizing.py      — 発注株数計算（ロット丸め・キャップ）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等の計算
    - feature_exploration.py  — IC / forward returns / summary 等
  - data/（実行環境で生成される想定）
    - monitoring.db
    - paper_trading.db
    - kill.flag
    - stop_requested.flag
  - utils/
    - logging_setup.py
    - process_priority.py

---

## 開発・運用上の注意

- .env は漏洩してはならない秘密情報を含むため、絶対に Git にコミットしないでください（config_setup 生成時にも注意書きあり）。
- KABUSYS_ENV が `live` の場合は設定を慎重に確認してください（validate_config.py に本番向け警告あり）。
- Monitoring は監視 DB に常に「本番用の sqlite_path」を使います（環境にかかわらず monitoring.db に記録）。
- OpenAI 使用部分は API のレート制限や課金に注意してください。ネットワーク / API エラーはリトライ・フェイルセーフで扱われますが、スループットやコストは運用設計に影響します。
- プロセス優先度設定は psutil を用いて行われます。権限不足で失敗する可能性があります（警告出力されスキップ）。

---

## よく使うコマンド例

- .env を作成・更新（対話式）
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動
  - python -m kabusys.run_execution

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

README の内容はコード内ドキュメンテーション（docstring）に基づいてまとめています。運用前には必ず `python -m kabusys.validate_config` で設定を確認し、必要な環境変数・ディレクトリ権限・外部サービス（kabuステーション、OpenAI 等）の接続確認を行ってください。