# KabuSys — README

本ドキュメントは、このリポジトリ（KabuSys）の概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

## プロジェクト概要
KabuSys は日本株向けの自動売買 / リサーチ基盤です。  
主な目的は次の通りです：
- マーケットデータを使ったファクター計算・リサーチ
- ポートフォリオ構築（銘柄選定、配分、ポジション決定）
- 発注実行エンジン（実際のブローカー連携およびペーパートレード）
- システム監視・リスク監視（Kill Switch を含む）
- ニュース NLP による AI スコアリング・レジーム判定

コードはモジュール化され、DuckDB（時系列 / ファクターデータ）、SQLite（監視 / 発注ログ）を利用します。OpenAI API を使った NLP 機能も一部に含まれます（任意）。

## 主な機能一覧
- research:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- portfolio:
  - 候補選定（スコア順、上位N）
  - 計算ベースの重み（等金額 / スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（リスクベース、上限/単元丸め、集約スケーリング）
- execution:
  - ExecutionEngine（発注ロジック、リスク管理、リコンサイル等）
  - ブローカークライアントの抽象化 （paper_trading 用に Mock を使用可能）
- monitoring:
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、実行プロセス検知）
  - TradeMonitor（滞留注文、約定異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（フラグファイルで ExecutionEngine を止める）
  - MonitoringEngine（各 Monitor を束ねてポーリング、AlertManager 経由で通知）
- ai:
  - news_nlp: ニュース記事を LLM でセンチメント化し ai_scores に書込む
  - regime_detector: MA とマクロセンチメントを組合せて日次レジーム判定を行う
- tools:
  - paper_verification_report: ペーパートレード結果の検証レポート生成
- 設定・補助:
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前の環境・設定チェック CLI
  - utils: process priority / CPU affinity 管理ユーティリティ

## 前提・依存
- Python >= 3.10（Union 型 a | b を利用しているため）
- 必要パッケージ（一例、プロジェクトに requirements.txt がない場合は手動で）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定ファイル YAML の検証を行う場合に必要）
- 標準ライブラリ: sqlite3 等

インストール例:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージのインストール（例）:
  - pip install duckdb psutil openai pyyaml

※ 実際のプロジェクトでは requirements.txt / poetry / pipfile を用意してください。

## 環境変数（主なもの）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API（データ取得）
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（デフォルトあり / 任意）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（default: development）
  - paper_trading: 発注は MockBrokerClient を使い data/paper_trading.db に記録
- DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（default: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

## セットアップ手順（基本）
1. リポジトリをクローンし作業ディレクトリへ移動
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. 初期設定 (.env) を作成:
   - 対話式で作る:
     - python -m kabusys.config_setup
     - 質問に答えて .env を生成
   - あるいは .env.example を参考に手動作成
5. 設定を検証:
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict
6. 必要に応じて data ディレクトリを作成（DB ファイルの親ディレクトリ等）
   - デフォルトで data 以下が用いられることが多いです

## 使い方（主要コマンド）
- 環境ウィザード
  - python -m kabusys.config_setup
    - .env を対話式で作成 / 更新します

- 設定検証
  - python -m kabusys.validate_config [--strict]
    - 必須環境変数や config/*.yaml をチェックします
    - --strict を付けると警告も失敗（exit 1）として扱います

- 実行エンジン起動
  - python -m kabusys.run_execution
    - ExecutionEngine を起動します
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（または data/paper_trading.db）に記録されます
    - 起動時に data/stop_requested.flag があれば起動せず終了します
    - 実行中は data/execution.pid（デフォルト）を利用してプロセス検知を行います

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - SystemMonitor のポーリングループを開始します（デフォルト間隔 60 秒）
    - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（1 以上）
    - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path（SQLITE_PATH）を使用します
    - 監視ループは data/stop_requested.flag を検知すると終了します

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能
    - レポートは稼働率、注文成功率、送信率、レイテンシ等を出力し PASS/FAIL を判定します

- AI 機能
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して利用します
  - 実行時に OPENAI_API_KEY を環境変数に設定するか、引数で API キーを渡してください
  - ニューススコアやレジーム判定は DB の raw_news / news_symbols / prices_daily を参照します

## Kill Switch / 停止フラグ
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- run_execution / run_monitoring は data/stop_requested.flag の存在で動作を制御します（停止要求や起動抑止）。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動クリアします（本番では非推奨）。

## データベース（既定パス）
- DuckDB: data/kabusys.duckdb（価格・財務・ニュース・市場データなどの格納）
- SQLite (monitoring): data/monitoring.db（system_status, trade_logs, positions, risk_logs, dashboard）
- SQLite (paper trading): data/paper_trading.db（ペーパートレード用に分離）

monitoring_db モジュールは必要テーブルの初期化とマイグレーションを行います。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュール構成と簡単な説明です。

- kabusys/
  - __init__.py — パッケージのバージョン等
  - config.py — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py — .env を対話式に作成するウィザード
  - validate_config.py — 起動前の環境・設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート CLI
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書込む
    - regime_detector.py — マクロ + MA を合成して market_regime を生成
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化 API（MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / PID チェック
    - trade_monitor.py — 滞留注文 / 価格異常チェック
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag の生成 / 管理
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py — （アラート送信の管理、実装は別ファイル）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - risk_adjustment.py — セクター制限 / レジーム乗数
    - position_sizing.py — 株数決定・スケールダウン・単元丸め
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（各モジュールの詳細はソース内 docstring / コメントを参照してください）

## 開発・運用上の注意
- 本番（KABUSYS_ENV=live）では設定を慎重に扱ってください。validate_config の live ガードが警告を出します。
- OpenAI を使う機能は API コストとレート制限に注意してください。retry/backoff ロジックが組み込まれていますが、運用設計が必要です。
- .env ファイルは決してリポジトリにコミットしないでください（config_setup でも注意書きあり）。
- Monitoring は監視用 SQLite（SQLITE_PATH）を常に使用します。paper_trading は paper_sqlite_path で DB を分離します。
- 単体・統合テストの整備を推奨します（コードベースにはテストは含まれていません）。

---

必要に応じて README に追記します。特に知りたい点（実際の ExecutionEngine の設定・ブローカープラグイン実装、AlertManager の通知先設定、DB スキーマ詳細など）があれば教えてください。