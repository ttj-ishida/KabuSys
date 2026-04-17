# KabuSys

日本株自動売買システムのリポジトリ（抜粋）。  
この README はリポジトリ内の主要スクリプト・モジュールに基づき、導入手順・使い方・ディレクトリ構成などを日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買（ExecutionEngine）・監視（Monitoring）・リサーチ/ファクター計算・ポートフォリオ構築・AI（ニュースセンチメント／レジーム判定）を含む統合的なシステムです。  
設計方針の一部：

- Execution と Monitoring を分離（監視は Execution の安定性や注文挙動を検査し、必要に応じて Kill Switch を発動）
- Paper Trading（擬似発注）モードによる本番 DB との完全分離
- DuckDB を用いた分析用データ、SQLite を監視・トレードログ保存に利用
- OpenAI（gpt-4o-mini 等）を利用したニュース NLP による銘柄別スコアリングやマクロセンチメント活用
- 自動化済みの .env ウィザードや設定検証ツールを提供

---

## 主な機能一覧

- Execution（発注エンジン）
  - Broker クライアントの切り替え（本番 / paper_trading）
  - Order 管理、Risk Manager、Reconciler、ExecutionEngine の実行
  - PID / stop フラグによる実行制御

- Monitoring（監視）
  - システムリソース監視（CPU, メモリ, ディスク）
  - Execution プロセス存在チェック（PID ファイル）
  - 注文滞留・約定異常・ドローダウン・ポジション上限の監視
  - Kill Switch（条件到達で data/kill.flag を書き込み Execution を停止させる）
  - 監視ログを SQLite（monitoring.db）へ永続化

- Research / Data
  - DuckDB 上でのファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン、IC 計算、ファクター統計サマリー

- Portfolio Construction
  - 候補選定、等配分 / スコア加重配分
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（lot 単位丸め・キャッシュ上限考慮）

- AI（OpenAI）
  - ニュース記事を LLM に渡して銘柄ごとのセンチメントを ai_scores テーブルへ格納
  - マクロニュースと ETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）

- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証ツール（validate_config）
  - Paper Trading の検証レポート出力ツール（tools.paper_verification_report）

---

## セットアップ手順

前提
- Python 3.10+（typing に `X | Y` 構文を使用）
- Git リポジトリのルートにいる想定

1. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 必須パッケージ例:
     - duckdb
     - psutil
     - openai
     - (任意) PyYAML — config/*.yaml の検証に使用
   - 例:
     - pip install duckdb psutil openai PyYAML

   注意: requirements.txt が無い場合は上記を個別にインストールしてください。

3. データディレクトリ作成（デフォルトの DB / PID / フラグ保存先）
   - mkdir -p data

4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 必要な環境変数（最低必須）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 他の主な環境変数（デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - LOG_LEVEL — INFO など
     - OPENAI_API_KEY — AI 機能利用時に必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知（任意）

5. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も FAIL とする:
     - python -m kabusys.validate_config --strict

---

## 使い方

基本的な実行コマンド（パッケージを PYTHONPATH に含めていること。開発中はリポジトリルートで実行）：

- ExecutionEngine を起動（実運用 / ペーパートレード切替は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録される
    - プロセス優先度を高に設定し、データベース接続・各コンポーネントを組み立てて ExecutionEngine.run_session を別スレッドで開始
    - data/stop_requested.flag を作成すると安全に停止処理をトリガー

- Monitoring（SystemMonitor 単体のポーリングループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト: 60）
  - Monitoring は KABUSYS_ENV にかかわらず production 用の sqlite_path（Settings.sqlite_path）を使用して監視ログを記録

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで終了コード 1 を返す

- AI / 研究機能（ライブラリ関数として利用）
  - ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 接続を渡して使用します（OpenAI API キーが必要）

運用上のフラグ / ファイル
- data/stop_requested.flag: run_execution / run_monitoring のループ停止検知に使用
- data/execution.pid: ExecutionEngine が書き込む PID ファイル（SystemMonitor は存在確認する）
- data/kill.flag: KillSwitch が書き込み Execution を停止させる（アラートや手動トリガに利用）

ログレベルや各種パラメータは環境変数（.env）や Settings クラスで調整できます。

---

## よく使う環境変数（一覧）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（INFO など）
- MONITOR_POLL_INTERVAL — run_monitoring 用ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 kill.flag クリア（0 推奨）

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主なファイルと役割（抜粋）です。

- kabusys/
  - __init__.py
  - config.py — Settings クラス（環境変数読み込み・.env 自動ロード）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/ (実際の実装は一部省略)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常の判定
    - risk_monitor.py — ドローダウン・ポジション上限の判定
    - kill_switch.py — kill.flag の書き込みロジック
    - monitoring_engine.py — 各 monitor を束ねるオーケストレータ
    - alert_manager.py — （アラート送信ロジック、実装抜粋）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数算出・丸め・キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マクロセンチメント + MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール

（実際のリポジトリでは data/、config/、scripts/ 等が並ぶ想定です）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）での実行前に必ず validate_config を実行し設定を確認してください。
- .env は決してリポジトリへコミットしないでください（config_setup も README に注意書きあり）。
- Paper Trading モードは本番 DB と完全に分離されるよう設計されています。実運用前に paper_trading を活用して検証してください。
- OpenAI を利用する機能は API コストと応答の不確実性（JSON パース失敗等）を考慮しており、失敗時はフェイルセーフ（スコア 0.0 等）で継続する設計です。API キー管理には注意してください。
- プロセス優先度 / CPU affinity の設定は psutil に依存します。権限不足で設定失敗する場合がありますが、その場合は警告ログが出て処理は継続します。

---

必要に応じて README を補足（実行例のコマンド、環境変数のデフォルト表、テーブルスキーマの詳細など）できます。追加で記載したい項目があれば教えてください。