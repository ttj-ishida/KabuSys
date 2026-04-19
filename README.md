# KabuSys

日本株向け自動売買システムの参照実装（ライブラリ + 起動スクリプト群）

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要なコンポーネントを集めたプロジェクトです。  
主な機能は次の通りです。

- 注文実行エンジン（実口座 / ペーパートレード切替）
- 監視（プロセス・システムリソース・データ鮮度・注文の異常検知）
- リスク管理（ドローダウンやポジション上限の監視と Kill Switch）
- ポートフォリオ構築（銘柄選定、重み算出、リスク調整、ポジションサイジング）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- 運用ツール（設定ウィザード、設定検証、ペーパートレード検証レポート生成）

設計方針として「ルックアヘッドバイアスを避ける」「本番とペーパートレードを分離」「外部 API 呼び出しは明示的に管理」などを意識して実装されています。

---

## 機能一覧

- 起動スクリプト
  - config_setup: .env を対話式で作成／更新
  - validate_config: .env と config/*.yaml の事前検証
  - run_execution: ExecutionEngine の起動（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring: SystemMonitor のポーリングループ起動
  - tools.paper_verification_report: ペーパートレード結果の検証レポート出力

- 監視（monitoring パッケージ）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス稼働 / データ鮮度監視
  - TradeMonitor: 注文の滞留・約定異常検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を作成し ExecutionEngine を停止
  - MonitoringDB: SQLite ベースの監視ログ保持（テーブル作成・マイグレーション含む）
  - MonitoringEngine: 各 Monitor を束ねるポーリング実行器

- 実行（execution パッケージ）
  - BrokerClientFactory: 本番/モックブローカーの生成
  - ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager: 注文の発行と管理、リスク制御

- ポートフォリオ（portfolio パッケージ）
  - 銘柄選定（select_candidates）
  - 重み計算（calc_equal_weights, calc_score_weights）
  - セクター制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
  - ポジションサイジング（calc_position_sizes）

- 研究（research パッケージ）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算・IC 計算・統計サマリ（feature_exploration）

- AI（ai パッケージ）
  - news_nlp.score_news: OpenAI を使ったニュースセンチメントの銘柄スコア化（ai_scores へ書込）
  - regime_detector.score_regime: マクロニュース＋ETF MA 乖離を用いた市場レジーム判定（market_regime テーブルへ保存）

- ユーティリティ
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - config: .env 自動読み込み・設定取得ラッパー

---

## 前提 / 必要環境

- Python 3.10 以上（型記法に PEP 604 を使用）
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検証に任意で必要）

例: pip で最低限インストールする場合
```
pip install duckdb psutil openai PyYAML
```

SQLite は標準ライブラリで提供されます。

---

## セットアップ手順

1. レポジトリをクローンして作業ディレクトリに移動
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - pip install -r requirements.txt  （requirements.txt がない場合は前節のパッケージを個別に）
4. 初期 .env を作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 生成された .env を編集して環境変数を設定（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等は必須）
   - 自動ロードはデフォルトで有効（プロジェクトルートの .env / .env.local を読み込み）
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証（起動前の必須チェック）
   - python -m kabusys.validate_config
   - 問題がある場合は表示されるエラー／警告に従って修正してください
   - --strict オプションを付けると警告も失敗扱いになります

6. データディレクトリの作成（必要に応じて）
   - デフォルト DB / ログパスは .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR 等で上書き可能
   - デフォルト: data/monitoring.db, data/kabusys.duckdb, logs/

---

## 使い方（起動例）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（実運用／ペーパートレードは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
    - 実行時に data/stop_requested.flag や data/kill.flag の存在を確認し、適切に停止・保護されます。
    - PID ファイル: data/execution.pid（設定で上書き可）

- SystemMonitor（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）
  - 監視は本番の sqlite_path を常に参照します（環境に依存せず本番 DB を使う設計）
  - 停止は data/stop_requested.flag を作成することで行います

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - DB パスは引数または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- AI モジュール（ニュース NLP / レジーム判定）利用
  - OpenAI API キーは環境変数 OPENAI_API_KEY を設定
  - モジュール関数をインポートして利用可能（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）
  - API 呼び出しはリトライ・フォールバックの仕組みを備えていますが、API キー未設定時は例外になります

---

## 主要な環境変数（抜粋・デフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- LOG_DIR — default: logs/
- OPENAI_API_KEY — OpenAI 呼び出し用（ai モジュールで必要）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant | partial | never | reject）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値が設定されていれば無効化）

Settings クラス（src/kabusys/config.py）に全プロパティとデフォルト値が記載されています。必須変数が未設定の場合は起動時にエラーになります。

---

## 運用上の注意

- 本番モード（KABUSYS_ENV=live）では LINE 通知や kill flag 設定などを確認の上で運用してください。validate_config は本番用のガードチェックを行います。
- Kill Switch はドローダウンやポジション上限などの重大条件で data/kill.flag を書き込み ExecutionEngine に停止信号を送ります。KILL_FLAG_CLEAR_ON_START 環境変数（デフォルト 0）に注意してください（本番では 0 推奨）。
- ペーパートレードは本番 DB と分離されますが、DuckDB（分析用）やログディレクトリは共通化する場合があるため運用方針に応じて .env を調整してください。
- ロギングは標準出力と日次ローテートファイルの両方に出力します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py  — 環境設定 / .env 自動ロード
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義と DB ラッパー
    - system_monitor.py — システム監視
    - trade_monitor.py — 注文監視（実装参照）
    - risk_monitor.py — ドローダウン・ポジション監視
    - kill_switch.py — Kill Switch 実装
    - monitoring_engine.py — 各 Monitor を束ねる実行器
    - alert_manager.py — アラート送信ロジック（実装参照）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py — 統一ログ設定
    - process_priority.py — 優先度 / CPU affinity
    - __init__.py

（上記は主要ファイルのみの抜粋です。詳細はソースツリーを参照してください。）

---

## 開発者向けメモ

- DuckDB は分析用テーブル（prices_daily / raw_financials / raw_news 等）を想定しています。研究モジュールは DuckDB 接続を受け取り SQL／Python で処理します。
- OpenAI との統合は retry / validation / JSON 抽出等の堅牢化ロジックを備えていますが、API スキーマの変更やレスポンス不整合に注意してください。
- ユニットテストでは外部 API 呼び出し部分（OpenAI 等）をモックする設計になっています（内部では _call_openai_api を patch しやすく作られています）。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup のヘッダーにも警告あり）。

---

## 参考コマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report --db <path> --from YYYY-MM-DD --to YYYY-MM-DD

---

必要があれば README に「設定例の .env.example」や「起動システムd ユニットファイル例」「CI/CD での DB 初期化スクリプト」などの追加セクションを追記します。どの情報が欲しいか教えてください。