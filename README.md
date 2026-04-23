# KabuSys

日本株自動売買システムのパッケージ (一部抜粋)。  
このリポジトリには、実行エンジン・監視・ポートフォリオ構築・リサーチ・AI 補助モジュールなどが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買をサポートするモジュール群です。主な責務は次のとおりです。

- ExecutionEngine: 注文発行・約定管理・リスク管理を行う実行エンジン
- Monitoring: システム稼働状況、注文状況、リスク監視と Kill Switch の評価
- Portfolio: 銘柄選定・重み付け・株数決定（単元丸め）
- Research: DuckDB を使ったファクター計算・特徴量解析
- AI ユーティリティ: ニュースを LLM（OpenAI）で解析してスコア化、レジーム検出
- CLI ユーティリティ: .env ウィザード、設定検証、ペーパートレード検証レポート生成 等

設計方針として、ルックアヘッドバイアス回避（target_date を明示する等）、外部 API 呼び出しのフェイルセーフ、DB はローカルファイル（DuckDB / SQLite）を利用することが挙げられます。

---

## 主な機能一覧

- 実行（Execution）
  - 本番 / ペーパートレードの分離（KABUSYS_ENV により挙動切替）
  - RiskManager によるポジション上限・利用率制御
  - Reconciler / OrderManager / BrokerClientFactory による注文フロー
- 監視（Monitoring）
  - CPU / メモリ / ディスクの監視、プロセス存否チェック
  - データ鮮度チェック（DuckDB の prices_daily など）
  - Trade / Risk の監視、Kill Switch の発動（data/kill.flag）
  - ログ・ダッシュボード（SQLite）への永続化
- ポートフォリオ構築
  - シグナルから候補選定、等金額 / スコア重み、リスクベース配分
  - セクターキャップ、レジーム乗数の適用
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI 支援
  - ニュースの LLM センチメントスコア化（OpenAI）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.10 以上（typing の | を使用しているため）。

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証のため）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt は本リポジトリに含まれていない想定のため、実際のプロジェクトでは requirements.txt を参照してください）

4. 環境変数設定
   - 簡易に .env を作成するにはウィザードを利用:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db (paper_trading 時の専用 DB)
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — news_nlp / regime_detector 使用時に必要
     - PAPER_FILL_MODE — instant | partial | never | reject（ペーパートレードの約定挙動、デフォルト: instant）
     - MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring 用、デフォルト: 60）

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として exit(1)

6. データディレクトリ・ログディレクトリの確認
   - デフォルト DB/ログはプロジェクト直下の data/ や logs/ に置かれます。必要に応じて先に作成してください（logging_setup が自動作成を試みます）。

---

## 使い方（主要スクリプト）

- 実行エンジンを起動（デフォルトでは KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading.db に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在すると起動せず終了
    - 実行中に data/stop_requested.flag を作成するとエンジンに停止シグナルを送りシャットダウン
    - 実行時に logs/execution.log にログが出力される

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60 秒）
    - 監視は常に production 用 sqlite_path を使用（環境にかかわらず）
    - 停止は data/stop_requested.flag を作成することで行える

- .env 設定ウィザード
  - python -m kabusys.config_setup
  - 対話形式で .env を作成 / 更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数の代替）

- AI スコアリング（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースに基づく銘柄スコアを生成・ai_scores テーブルへ書込
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- run_monitoring は監視用 sqlite（settings.sqlite_path）を使います。run_execution は KABUSYS_ENV により paper_trading 用 DB を使うため、本番データと分離できます。
- Kill Switch: RiskMonitor が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（ExecutionEngine は起動時に kill_flag_clear_on_start を参照）。

---

## 重要なファイル / フラグ

- data/stop_requested.flag
  - run_execution / run_monitoring の停止フラグファイル。存在すると起動抑止および実行中の停止シグナルとなる。

- data/kill.flag
  - Monitoring がリスク重大事象を検出した場合に作成される Kill Switch。ExecutionEngine 側の起動時や起動中の挙動に影響。

- data/execution.pid
  - ExecutionEngine の PID ファイル（デフォルトパスは Settings.pid_file_path）

- logs/<app>.log
  - ログ出力先（setup_logging により日次ローテーション）

---

## 主要環境変数（抜粋、デフォルトあり）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- OPENAI_API_KEY — AI 機能利用時に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードでの約定モード（instant/partial/never/reject）

詳細は kabusys.config.Settings のプロパティドキュメントを参照してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数・.env の自動ロードと Settings クラス
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを LLM でスコア化するロジック
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite のテーブル初期化 / 永続化 API
  - monitoring_engine.py — 各モニタを束ねるエンジン
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度の監視
  - trade_monitor.py — （注文監視関連）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — （通知管理）
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数計算・制約実装
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- utils/
  - logging_setup.py — 統一ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- monitoring/monitoring_db.py, etc.

（実際のリポジトリには execution、data、strategy 等さらに多くのモジュールが存在する可能性があります）

---

## 運用メモ / ベストプラクティス

- 本番（KABUSYS_ENV=live）での起動は慎重に:
  - validate_config で設定・パスを必ず確認する
  - KILL_FLAG_CLEAR_ON_START は本番では 0 推奨（自動クリアは危険）
  - LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を整備するとアラート受信が可能
- ログ/DB のバックアップとパーミッションを検討する
- OpenAI を利用する場合は API キー管理を厳重に（環境変数で運用）
- ペーパートレードは本番 DB と分離されるため、検証や CI で活用する

---

必要に応じて README を拡張します（依存関係の完全な一覧、実行時のログ出力例、docker-compose サンプル等）。追加で記載したい項目があれば教えてください。