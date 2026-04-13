# KabuSys

日本株自動売買システム（モジュール群）のリポジトリ README。

このドキュメントはコードベース（src/kabusys 以下）を参照して、概要・機能・セットアップ・起動方法・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント群（シグナル生成、ポートフォリオ構築、発注管理、監視、リサーチ、AI 補助機能など）を提供するモジュール群です。主要な特徴は以下のとおりです。

- DuckDB / SQLite を用いたオンプレ型データ処理・永続化
- ExecutionEngine（発注・リスク管理・再同期待ち合わせ）
- MonitoringEngine（システム・注文・リスク監視、LINE 通知、kill flag による停止）
- Paper Trading モード（本番 DB と分離して data/paper_trading.db に記録）
- AI 支援（OpenAI を用いたニュースの NLP スコアリング、レジーム判定）
- 研究用ユーティリティ（ファクター計算・特徴量探索）
- ストリームリット製の監視ダッシュボード

---

## 機能一覧（主要）

- monitoring
  - システム状態（CPU/メモリ/ディスク）とデータ鮮度の監視（system_monitor）
  - 注文滞留や約定の異常価格検出（trade_monitor）
  - ドローダウン・ポジション上限監視とアラート / kill.flag の発行（risk_monitor / kill_switch）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
  - 監視ログ永続化層（SQLite：monitoring_db.py）
- execution
  - OrderManager（発注フロー・状態遷移の管理）
  - Reconciler（起動時リコンシリエーション）
  - BrokerClientFactory を通じた本番 / モックの切替（paper_trading モード）
- portfolio
  - 銘柄選定・重み算出・単元丸めなど（portfolio_builder, position_sizing, risk_adjustment）
- research
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）等の解析ツール
- ai
  - ニュース NLP スコアリング（OpenAI を使い ai_scores を生成）
  - 市場レジーム判定（ETF MA とマクロニュースの融合）
- tools
  - Paper Trading 検証レポート作成スクリプト（paper_verification_report.py）

---

## 前提条件（開発環境）

- Python 3.9+
- DuckDB（Python パッケージ：duckdb）
- psutil
- requests
- openai（ai 機能を使う場合）
- streamlit（ダッシュボード起動時）
- その他の標準ライブラリ

推奨: 仮想環境（venv / pipenv / poetry 等）を利用してください。

---

## セットアップ手順（ローカル）

1. リポジトリをクローンして作業ディレクトリに移動

2. 仮想環境作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトで requirements.txt / pyproject.toml がある場合はそちらを使ってください）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（OS 環境 > .env.local > .env の順）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要な環境変数（主なもの）

以下は config.py に基づく主要設定項目です。

- 必須（実行機能により）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 接続先 / パス:
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、本番: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用: data/paper_trading.db）

- 実行モード / ログ:
  - KABUSYS_ENV：development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL：DEBUG | INFO | WARNING | ERROR | CRITICAL

- Paper Trading 固有:
  - PAPER_FILL_MODE：instant | partial | never | reject（デフォルト: instant）

- 監視 / プロセス:
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag をクリア）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）

- AI:
  - OPENAI_API_KEY（AI 機能を使う場合必須）

注意: monitoring の DB 初期化（init_monitoring_db）は SQLite ファイルを作成します。monitoring は環境にかかわらず config.sqlite_path（本番パス）を使用する点に注意してください。一方、run_execution は `KABUSYS_ENV=paper_trading` のときに paper_sqlite_path を使い本番と分離します。

---

## 実行方法（代表例）

ルートの Python モジュールとして用意されている起動スクリプトを使います。

- 監視ループ（SystemMonitor の単純起動）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 実行:
    - python -m kabusys.run_monitoring
  - 補足:
    - 起動時にプロセス優先度を "high" に設定しようとします（権限がなければスキップされます）。
    - 監視は monitoringDB（config.sqlite_path）へ記録します（環境に依存せず本番パス）。

- ExecutionEngine（発注エンジン）
  - Paper Trading モード（本番 DB と分離して data/paper_trading.db を使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 通常（development/live）:
    - KABUSYS_ENV=development python -m kabusys.run_execution
  - 補足:
    - 起動時にプロセス優先度を "high" に設定します。
    - BrokerClientFactory により paper_trading の場合はモックブローカーを使用します。

- Streamlit ダッシュボード（監視）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite DB を開き、現在のポジション・ログ・最新のシステム状態を表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH を指定すると PAPER_TRADING_SQLITE_PATH より優先して DB を参照

- AI 機能（例）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を必要とします。関数呼び出し時に api_key を渡すことも可能です。

---

## 監視・停止関連（運用メモ）

- PID および kill flag:
  - ExecutionEngine は起動時に PID を PID_FILE_PATH に書き込む想定（設定により）。
  - KillSwitch は KILL_FLAG_PATH（data/kill.flag）を書き込むことで ExecutionEngine 停止要求を送ります。kill.flag が存在すると ExecutionEngine 停止ロジック（起動側実装が必要）が動作します。
  - Kill flag は KillSwitch.clear() で削除できます。Settings.kill_flag_clear_on_start が "1" の場合、ExecutionEngine 起動時にクリアする運用が可能です。

- MONITOR_POLL_INTERVAL:
  - run_monitoring のポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書きできます（デフォルト 60 秒）。不正値（0 や負の値）はデフォルトにフォールバックします。

---

## ディレクトリ構成（主要ファイル説明）

（src/kabusys/ 以下を想定）

- __init__.py
  - パッケージ公開情報（__version__ など）

- config.py
  - 環境変数の自動ロード（.env, .env.local）と Settings クラス（各種パス・閾値・フラグの取得）

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モードに対応）

- monitoring/
  - monitoring_db.py — SQLite による監視ログテーブル作成と簡易 CRUD（init_monitoring_db, MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/プロセスの状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常価格の監視
  - risk_monitor.py — ドローダウン・ポジション上限監視。ダッシュボード更新 / リスクログ登録
  - kill_switch.py — kill.flag の書き込み・管理
  - alert_manager.py — LINE Messaging API への Push 通知（クールダウン管理あり）
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit を使った監視ダッシュボード

- execution/
  - order_manager.py — 発注フロー（作成・送信・同期）の上位 API
  - reconciler.py — 起動時のリコンシリエーション（注文・ポジションの突合せ）
  - order_repository.py 等（DB 周り） — 注文レコード管理（SQLite）
  - broker_factory / broker_api — ブローカー抽象化（実ブローカー / モック）

- portfolio/
  - portfolio_builder.py — 候補選定・重み付け（等比重／スコア重み）
  - position_sizing.py — 発注株数算出（単元丸め・aggregate cap）
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ

- ai/
  - news_nlp.py — raw_news を集約して OpenAI に投げ、ai_scores を生成
  - regime_detector.py — ETF MA とマクロニュース LLM を組み合わせて日次で市場レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成（監視データの集計と PASS/FAIL 判定）

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity の設定ユーティリティ

その他、細かなユーティリティやデータ処理用モジュールが含まれています。

---

## 開発・運用の注意点

- DB マイグレーション:
  - init_monitoring_db は既存 DB に対して安全にカラム追加などの簡易マイグレーションを行います（冪等）。
- Paper Trading と本番 DB の分離:
  - run_execution は KABUSYS_ENV=paper_trading のとき data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）を使用します。監視は production の sqlite_path を使用する設計になっている箇所があるため、運用時は格納先に注意してください。
- AI 関連:
  - OPENAI_API_KEY が未設定だと ai.score_news / regime scoring は ValueError を投げます。API 呼び出し失敗時はフェイルセーフで 0 相当の値にフォールバックする実装箇所もありますが、キーの設定を推奨します。
- プロセス優先度:
  - 起動スクリプトは可能ならプロセス優先度を "high" に設定しますが、権限不足・OS 非対応の場合は警告を出してスキップします。

---

## よく使うコマンドまとめ

- 仮想環境作成・依存インストール（例）
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt  （存在する場合）

- 監視ループ起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（paper）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

この README はコードの注釈・ドキュメント文字列に基づいて作成しています。実運用や拡張時は各モジュールの docstring / ログ出力を確認し、必要に応じて設定値（.env）や DB パスを調整してください。質問や追加のドキュメント化が必要であればお知らせください。