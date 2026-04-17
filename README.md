# KabuSys

バージョン: 0.1.0

日本株自動売買システム（ライブラリ／ランタイム群）の一部です。本リポジトリはトレーディングエンジン、監視機構、ポートフォリオ構築、リサーチ、AI（ニュースNLP／レジーム判定）などを含むモジュール群を提供します。

以下はこのコードベースに関する README（日本語）です。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要スクリプト・CLI）
- 設定項目（環境変数）
- データベース・ファイルパス
- 主要コンポーネントの説明
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・運用基盤です。戦略実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算／特徴量解析）、AI を用いたニュースセンチメント評価／市場レジーム判定などの機能を備えています。

設計方針の例：
- 本番とペーパートレードを分離（KABUSYS_ENV=paper_trading で専用 DB を使用）
- LLM 呼び出しは API キー依存（OpenAI）でフェイルセーフを重視
- DuckDB を用いたリサーチ処理、SQLite を監視・注文ログに使用
- .env による設定管理と対話式ウィザード / 検証 CLI を提供

---

## 主な機能一覧

- ExecutionEngine 起動（run_execution.py）
  - 本番 / ペーパートレードモード対応（MockBroker を使用）
  - リスク管理、オーダー管理、照合（reconciler）など組み込み
- Monitoring（run_monitoring.py / monitoring_engine）
  - システム状態（CPU / メモリ / ディスク）、プロセス監視、データ鮮度チェック
  - 注文滞留や約定異常の検知、ドローダウン監視（KillSwitch による停止シグナル生成）
  - 監視ログは SQLite（monitoring.db）に永続化
- ポートフォリオ構築（portfolio モジュール）
  - 候補選定、等配分・スコア加重、セクター制約、ポジションサイズ計算
- リサーチ（research モジュール）
  - Momentum/Value/Volatility 等のファクター計算（DuckDB 接続）
  - 将来リターン、IC 計算、ファクター統計
- AI（ai モジュール）
  - ニュースの LLM センチメント評価（news_nlp）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（regime_detector）
- ユーティリティ
  - 設定ウィザード（config_setup.py）: .env を対話的に生成
  - 設定検証（validate_config.py）: 起動前チェック
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
  - プロセス優先度 / CPU affinity ユーティリティ（utils/process_priority.py）

---

## セットアップ手順

前提:
- Python 3.9+（型記述で | 型を使用しているため 3.10 推奨）
- SQLite（標準ライブラリで利用可）
- DuckDB（pip から duckdb パッケージ）
- psutil（プロセス優先度 / CPU 情報）
- openai（AI 機能利用時）
- （任意）PyYAML（設定検証時の YAML パース）

推奨インストール例:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - オプション: pip install pyyaml

3. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成（本リポジトリでは .env.example を期待）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も含めて厳密にチェックする場合: python -m kabusys.validate_config --strict

注意:
- AI 機能を使うには環境変数 OPENAI_API_KEY を設定してください。
- .env は Git に含めないでください（config_setup.py にも警告あり）。

---

## 使い方（主要スクリプト）

すべてのランチャーはモジュール実行可能（python -m ...）として提供されています。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔秒数を上書き可能（デフォルト: 60）
  - 監視は monitoring 用の sqlite_path（Settings.sqlite_path）を常に使用（環境に依らず本番用監視 DB）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db（Settings.paper_sqlite_path）にログを記録し、本番 DB と分離する
  - 起動前に data/stop_requested.flag が存在すると起動を行わず終了
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止する（Graceful stop）

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に生成／更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 日付範囲指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パス指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数の代替）

---

## 設定（主な環境変数）

必須（validate_config でもチェックされる）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

重要な任意／デフォルト
- KABUSYS_ENV — 実行環境（development | paper_trading | live） デフォルト: development
  - paper_trading: Execution は paper_db を使用
  - live: 本番モード（注意が多い）
- OPENAI_API_KEY — OpenAI を使う AI 機能で必須
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG|INFO|...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"1" で有効。デフォルト 0 を推奨）
- PID_FILE_PATH / KILL_FLAG_PATH — 各種フラグ・PID ファイルのパス

詳細は kabusys.config.Settings クラスのプロパティをご参照ください。

---

## データベース / 重要ファイル

デフォルトのファイルパス（一部）
- data/kabusys.duckdb — DuckDB（価格データ・raw_news 等）
- data/monitoring.db — 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）
- data/paper_trading.db — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時）
- data/execution.pid — Execution の PID（run_execution が使用）
- data/stop_requested.flag — 外部からプロセスに停止リクエストを送るためのフラグファイル（run_* スクリプトで参照）
- data/kill.flag — Kill Switch が生成する停止フラグ（ExecutionEngine が検出して停止）

監視 DB（monitoring.db）に作成される主なテーブル
- system_status — CPU/メモリ/ディスク/プロセス状態の履歴
- trade_logs — 発注・約定イベントログ（latency_ms カラム含む）
- positions — 保有ポジション
- risk_logs — リスク関連イベント（DRAWDOWN_ALERT / STALE_ORDER / PRICE_ANOMALY 等）
- dashboard — 集計（portfolio_value, cash, drawdown_pct 等）

監視 DB の初期化は init_monitoring_db()（冪等）で行われます。

---

## 主要コンポーネントの説明（概要）

- config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings クラス（環境変数アクセス）
  - .env 読み込みロジックはシェル形式に近い柔軟なパーサを実装

- config_setup.py
  - .env の対話式生成・更新ウィザード

- validate_config.py
  - 起動前の設定検証（必須 env の存在、パスの親ディレクトリチェック、YAML パースチェック等）

- run_execution.py
  - ExecutionEngine を起動・監視するスクリプト（ペーパートレード時は別 DB を使用）
  - プロセス優先度設定、PID ファイル管理、停止フラグ検出

- run_monitoring.py
  - SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で制御）
  - Monitoring 用 DB を用いて system_status 等を永続化

- monitoring/*
  - system_monitor.py: システム状態・データ鮮度チェック（get_last_price_date を参照）
  - trade_monitor.py: 注文滞留・約定異常の検出
  - risk_monitor.py: ドローダウン・ポジション上限の監視および dashboard 更新
  - kill_switch.py: 条件に応じて kill.flag を書き込み Execution を停止させる
  - monitoring_db.py: SQLite に対する読み書きラッパ（MonitoringDB）

- portfolio/*
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定、重み付け、株数計算、セクター制約、レジーム乗数

- research/*
  - factor_research.py, feature_exploration.py: ファクター計算、将来リターン、IC、統計サマリー（DuckDB を参照）

- ai/*
  - news_nlp.py: raw_news を取って OpenAI に投げ、銘柄ごとのセンチメントを ai_scores テーブルへ格納
  - regime_detector.py: ETF（1321）MA200 とマクロニュース LLM を合成して日次レジーム判定

- tools/paper_verification_report.py
  - ペーパートレード DB を集計して PASS/FAIL 判定のレポートを生成

- utils/process_priority.py
  - psutil を使った OS 横断のプロセス優先度設定＆ CPU affinity（失敗してもスキップ）

---

## 実運用上の注意点 / 運用メモ

- KABUSYS_ENV=live を使用する場合は慎重に設定を確認してください（validate_config で警告あり）。
- kill.flag（Settings.kill_flag_path）や stop_requested.flag（data/stop_requested.flag）といったフラグファイルによりプロセスの起動/停止制御を行います。運用手順を標準化してください。
- AI（OpenAI）呼び出しにはコストがかかります。rate limit・ネットワーク障害・API エラーに対するリトライ処理は組み込まれていますが、運用監視を推奨します。
- Paper trading では paper_trading.db に完全分離してログが残るため、本番データの汚染を防げます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

subpackages / モジュール（主要ファイル）
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (未展開部分)
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- tools/
  - __init__.py
  - paper_verification_report.py
- utils/
  - __init__.py
  - process_priority.py
- execution/ (リポジトリ内で参照される実行関連モジュール群 — 一部コードは省略)
- monitoring/monitoring_db.py（監視 DB 初期化・アクセス）

data/ （実行時に使用するファイル群、デフォルト）
- data/kabusys.duckdb
- data/monitoring.db
- data/paper_trading.db
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

---

## 参考コマンドまとめ

- 対話式 .env 作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

必要に応じて README に含めるサンプル .env のテンプレートや運用手順（例: systemd / supervisor 用のユニットファイル、バックアップスクリプト）を追加できます。ほかに記載したい内容（たとえば特定モジュールの API 使用例、テスト手順、CI 設定など）があれば教えてください。