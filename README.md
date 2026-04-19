# KabuSys

日本株自動売買システムのコアライブラリ（部分サブセット）。  
このリポジトリには、監視・実行エンジンの起動スクリプト、設定ウィザード、監視用 DB 層、ポートフォリオ構築・ポジションサイジング、リサーチ／ファクター計算、AI を使ったニュース／レジーム判定ユーティリティなどが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、以下のような機能を持つ自動売買プラットフォームの基盤モジュール群です。

- 実行エンジン（ExecutionEngine）起動スクリプトとブローカー抽象化（本番 / ペーパートレード切替対応）
- 監視コンポーネント（System / Trade / Risk）と監視ループ起動スクリプト
- 監視ログの永続化（SQLite）
- ポートフォリオ構築（候補選定／重み付け）・ポジションサイズ計算・セクター制限などの純粋関数群
- 研究用ファクター計算、特徴量評価（DuckDB 接続を利用）
- OpenAI を使ったニュースセンチメント（ai.news_nlp）／市場レジーム判定（ai.regime_detector）
- 設定ウィザード（.env 作成支援）と設定検証ツール
- 各種ユーティリティ（ログ設定、プロセス優先度設定、paper trading 検証レポート）

設計方針の一部:
- DuckDB を研究用途の時系列 DB として利用（prices_daily / raw_financials 等）
- SQLite を監視ログ・注文履歴用に利用（monitoring.db / paper_trading.db）
- 本番とペーパートレードは可能な限り分離（ペーパートレードは別 SQLite を使用）
- LLM（OpenAI）呼び出しは失敗時にフォールバックするなど安全策を採用

---

## 主な機能一覧

- 設定関連
  - 対話式 .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- 実行 / 監視
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視ループ起動: python -m kabusys.run_monitoring
  - 停止フラグ / Kill Switch による安全停止
- 監視 DB
  - monitoring_db.py: system_status, trade_logs, positions, risk_logs, dashboard 等のスキーマと読み書き API
- モニタリング
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager（アラート送信は別実装想定）
- ポートフォリオ
  - 候補選定、等重／スコア重み付け、セクターキャップ、レジーム乗数、ポジション数算出、単元丸め等
- リサーチ
  - ファクター計算 (momentum / volatility / value)、将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - ニュースをまとめて銘柄ごとにセンチメントを算出し ai_scores へ書き込み
  - マクロセンチメント + ETF MA200 を組み合わせたレジーム判定
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主な依存パッケージ（抜粋）:
- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- そのほか標準ライブラリ（sqlite3, logging, threading 等）

インストール例（仮）:
- 仮想環境を作成してから:
  - pip install -r requirements.txt
  - または必要なパッケージだけ: pip install duckdb psutil openai pyyaml

（このリポジトリに requirements.txt がない場合はプロジェクト方針に合わせて依存を追加してください）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション / デフォルト:
- KABUSYS_ENV: execution 環境 (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時に使用)
- LOG_LEVEL: INFO
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai モジュールを使用する場合）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） — デフォルト 60（run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリアする、0=しない）

.env を使う場合は .env.example を参照して .env を作成してください。自動ロード仕様: OS 環境 > .env.local > .env（プロジェクトルートの検出に基づく）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順

1. リポジトリをチェックアウト
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）
5. 設定検証（起動前）:
   - python -m kabusys.validate_config
   - 必要なら --strict を付けると警告も失敗扱い
6. データディレクトリ（data/）やログディレクトリ（logs/）は自動作成されますが、権限等を確認してください。

---

## 使い方（主要コマンド例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - 通常起動:
    - python -m kabusys.run_execution
  - ペーパートレード環境:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 停止 / 強制停止フロー
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を監視しており、このファイルが作成されるとループを終了します。
  - Kill Switch（kill.flag）は KillSwitch を通じて発火され、ExecutionEngine に安全停止を促します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番環境では 0 を推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（ニューススコア / レジーム判定）
  - 環境変数 OPENAI_API_KEY を設定してから利用してください。
  - 例: OpenAI API キーをセットしてから ai.score_news / ai.score_regime 相当の関数を programmatically 呼び出す。

---

## 主要ファイル / ディレクトリ構成

（抜粋、主要なモジュールと説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数・設定読み込みと Settings クラス、自動 .env ロード機能
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（紙取引モード対応）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL により間隔変更可）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ作成と永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （取引監視ロジック、ここでは説明に含まれる）
    - kill_switch.py — kill.flag の読み書き
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信管理（インタフェース）
  - execution/ — 実行エンジン関連（Engine, OrderManager, BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み付け
    - position_sizing.py — 発注株数算出・aggregate cap / lot 単位調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースの LLM センチメントスコア取得と ai_scores 書込処理
    - regime_detector.py — ETF MA200 とマクロセンチメントを合成してレジーム判定
  - utils/
    - logging_setup.py — 統一ロギング設定（Stream + TimedRotatingFileHandler）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - tools/
    - paper_verification_report.py — Paper Trading のパッケージ検証レポート生成ツール

プロジェクトルートには data/（SQLite, PID, flag 等）と logs/（ログファイル）が作成されます（権限に注意）。

---

## 運用上の注意 / Tips

- 本番 (KABUSYS_ENV=live) では kill.flag の自動クリアを OFF（KILL_FLAG_CLEAR_ON_START=0）にしておくことを推奨します。
- run_monitoring は監視専用 DB（Settings.sqlite_path）を使用し、環境にかかわらず production 用 sqlite_path を参照します（監視は本番 DB を参照する設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して完全に分離された DB に記録します。
- OpenAI を使うモジュールを稼働させる場合、API キーが必要です。API 呼び出しはリトライ / フェイルセーフを実装していますが、料金やレート制限に注意してください。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能です。
- process_priority.set_process_priority はプラットフォーム依存の挙動があり、権限不足で設定できない場合は警告ログを出して継続します。

---

## 開発・拡張ポイント（参考）

- portfolio / research の関数群は純粋関数として設計されており、単体テストが書きやすい構成です。
- AI 部分はレスポンスバリデーションと部分書き込み（部分失敗時のデータ保護）に配慮されています。モデルやプロンプトのチューニングは容易に行えます。
- monitoring_db はスキーママイグレーションを簡易的に行う仕組み（カラム追加チェック）を備えています。将来的なスキーマ変更時はマイグレーション方針を拡張してください。

---

必要であれば、README に「例となる .env.example」「シーケンス図」「起動フロー（図）」などを追加できます。どの情報を追記したいか教えてください。