# KabuSys — README

日本株自動売買フレームワーク（KabuSys）リポジトリの README です。  
このドキュメントはコードベース（src/kabusys 以下）を元に作成しています。セットアップ方法や主要な機能、実行方法、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・検証・監視を行うためのモジュール群です。主に以下の機能を持ちます。

- 実行エンジン（ExecutionEngine）による発注管理（本番 / ペーパートレード対応）
- 監視コンポーネント（System / Trade / Risk）によるシステム・注文・リスク監視
- ポートフォリオ構築、ウェイト計算、ポジションサイジングの純粋関数群
- 研究用モジュール（ファクター計算、特徴量探索）
- ニュース NLP / レジーム判定（OpenAI API を利用したセンチメント評価）
- ユーティリティ（設定ウィザード・設定検証・ログ設定等）
- 運用/検証用ツール群（例: Paper Trading 検証レポート生成）

設計上の特徴：
- 本番 / ペーパートレードは DB を分離（PAPER_TRADING 用 DB を使用）
- DuckDB を分析用、SQLite を監視・ログ用に想定
- OpenAI 統合（ニュースセンチメント、レジーム判定）をオプションで利用可能
- フラグファイル（data/kill.flag, data/stop_requested.flag）で外部から停止や Kill Switch を制御

---

## 主な機能一覧

- Execution
  - 実際の注文発行を担う ExecutionEngine（kabuステーション API またはモック）
  - RiskManager によるポジション上限・資金制限・レート制御
  - OrderManager / OrderRepository による注文保存と再照合

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、Execution プロセスの監視
  - TradeMonitor：注文滞留や約定異常の検出
  - RiskMonitor：ドローダウン監視、ポジション上限監視、ダッシュボード更新
  - MonitoringEngine：上記を束ねて定期的に実行、アラート送信や Kill Switch 評価

- Portfolio（銘柄選定・配分）
  - 候補選定、等配分 / スコア加重配分、リスクベースのポジションサイジング
  - セクターキャップ適用、レジーム乗数の計算

- Research（研究用）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI 統合）
  - ニュース記事のセンチメントスコア化（ai_scores テーブルへ書き込み）
  - マクロニュースを用いた市場レジーム判定（market_regime テーブルへ保存）

- ツール
  - .env 設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール

---

## セットアップ手順（ローカル開発向け）

1. Python 環境準備（推奨: pyenv + venv/virtualenv）
   - Python 3.10 以降を想定（コードは型注釈を使用）
   - 仮想環境を作成・有効化してください。

2. 依存パッケージをインストール
   - requirements.txt はリポジトリに含まれない可能性があるため、最低限の主な依存は以下です：
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（設定検証で YAML 検査を行う場合に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - 実際のプロジェクトでは requirements.txt / poetry / pipenv 等を用意してください。

3. プロジェクトルートで .env を用意
   - 対話式ウィザードで作成する:
     - python -m kabusys.config_setup
   - または手動で .env を作成（例が .env.example にあるなら参照）
   - 必須環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - OPENAI_API_KEY（AI 機能利用時）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
   - 注意: .env は機密情報を含むため Git にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データ / ログ用ディレクトリ作成
   - data/ と logs/ は自動作成される処理もありますが、権限等で失敗する場合があるため事前作成を推奨します。
     - mkdir -p data logs

---

## 使い方（起動 / 実行例）

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルトは 60 秒。0 以下は無効でデフォルトにフォールバックします。
  - 監視は本番用 sqlite_path（Settings.sqlite_path）を常に使用します（環境に依らず）。

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合:
    - MockBrokerClient を使用してペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
    - 本番 DB と完全に分離して動作します。
  - 実行エンジンは data/stop_requested.flag の存在や data/execution.pid を使用して状態管理します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI（ニューススコア / レジーム）
  - ニューススコア: kabusys.ai.score_news を呼ぶことで ai_scores テーブルに書き込みます（実行スクリプトは提供されている関数経由で利用）。
  - レジームスコア: kabusys.ai.regime_detector.score_regime を実行すると market_regime テーブルへ保存します。
  - いずれも OPENAI_API_KEY が必要です。

- 停止 / Kill
  - ExecutionEngine を即時停止させたい場合は data/kill.flag を書き込む（KillSwitch によって検出されます）。
  - 監視ループ / 実行ループを外部から終了させたい場合は data/stop_requested.flag を作成してください（多数の起動スクリプトで使用）。
  - KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

---

## 重要な環境変数（抜粋とデフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境 / ログ
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）

- データベースパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

- Paper Trading 固有
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- OpenAI / LINE
  - OPENAI_API_KEY（AI 機能利用時）
  - LINE_CHANNEL_ACCESS_TOKEN（任意: アラート通知）
  - LINE_USER_ID（任意: アラート送信先）

- その他
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（Settings で管理）

---

## ログ・データ保存

- ログ
  - デフォルトディレクトリ: logs/
  - ログは StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日分保存）で出力されます。
  - ログファイル名はアプリ名（例: execution.log / monitoring.log）。

- データ
  - 監視ログ、注文ログ、ダッシュボード等は SQLite（SQLITE_PATH）へ保存されます。
  - 分析用のテーブル（prices_daily / raw_news / ai_scores 等）は DuckDB（DUCKDB_PATH）で扱います。
  - ペーパートレードは PAPER_TRADING_SQLITE_PATH を使用して本番と分離されます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理（自動 .env ロード、Settings クラス）
- config_setup.py — .env 対話式作成ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine の起動スクリプト
- run_monitoring.py — SystemMonitor の起動スクリプト

サブパッケージ（主要ファイルのみ抜粋）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
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
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

data/ と logs/ はランタイムで使用するディレクトリ（プロジェクトルート）。

---

## 注意事項・運用上のポイント

- 本番（KABUSYS_ENV=live）では設定ミスに注意してください（validate_config の警告や --strict モードを活用）。
- .env は機密情報を含むため絶対にリポジトリへコミットしないでください。
- OpenAI を利用するモジュールは API 呼び出しに失敗した場合にはフォールバック（ゼロスコアやスキップ）する実装ですが、API キーの漏洩・コスト管理には注意してください。
- ペーパートレードは実際の送金や発注を行わないモックを使って動作検証できるよう設計されています。ペーパートレード時は PAPER_TRADING_SQLITE_PATH をチェックしてください。
- process_priority や CPU affinity の設定は OS による制約・権限により失敗する場合があります（警告ログが出ます）。

---

この README はコードベースの構成と挙動を簡潔にまとめたものです。開発や運用を始める際はまず `python -m kabusys.config_setup` → `.env` 作成 → `python -m kabusys.validate_config` で安全性を確認してから、`run_monitoring` / `run_execution` を順に起動してください。必要があれば各モジュールのソース（src/kabusys 以下）を参照して詳細挙動を確認してください。