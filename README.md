# KabuSys

日本株自動売買システムのコードベース（簡易 README）

概要・使い方・セットアップ手順を日本語でまとめています。開発・検証・本番（paper_trading / live）での起動や各種ユーティリティの使い方を記載しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム／研究ツール群です。本リポジトリは以下のような機能を含みます。

- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化（本番・ペーパートレード対応）
- 監視（Monitoring）: システム稼働性・データ鮮度・取引ログ・リスク監視
- ポートフォリオ構築ロジック（候補選定、重み計算、ポジションサイズ算出、セクターキャップ）
- リサーチモジュール（ファクター計算、将来リターン、IC 計算等）
- AI 補助モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、レポート生成）

主要な設計方針:
- 本番 DB とペーパートレード DB を分離
- ルックアヘッドバイアス回避（日時参照の扱いに注意）
- フェイルセーフ（API 失敗時は安全側で継続）
- ロギング・監視・KillSwitch による安全停止

---

## 機能一覧（抜粋）

- サービス起動スクリプト
  - run_execution.py — 発注エンジン起動（KABUSYS_ENV により paper_trading モードに切替）
  - run_monitoring.py — 監視ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定可能）
- 設定管理
  - config_setup.py — .env の対話式ウィザード
  - validate_config.py — 環境変数／設定ファイルの事前検証（--strict オプションあり）
- DB / 監視
  - monitoring_db.py — SQLite による監視ログ層（system_status / trade_logs / positions / risk_logs / dashboard）
  - monitoring_engine.py / system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py
- ポートフォリオ関連
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- リサーチ
  - research/factor_research.py, research/feature_exploration.py
- AI（OpenAI 連携）
  - ai/news_nlp.py — ニュースを LLM でスコア化して ai_scores に保存
  - ai/regime_detector.py — マクロ + ETF MA に基づく市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成
- ユーティリティ
  - utils/logging_setup.py — 一貫したログ設定（コンソール + 日次ローテーション）
  - utils/process_priority.py — プラットフォーム差を吸収した優先度設定

---

## セットアップ手順

前提:
- Python 3.9+（プロジェクトの実行環境に合わせて適宜）
- 必要な外部ライブラリ（下記参照）

1. リポジトリを取得／クローンする

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - 任意: pip install PyYAML（config YAML の検証を行う場合）

   ※ requirements.txt がない場合は上記パッケージを最低限インストールしてください。  
   - duckdb: 解析／ファクター／ai モジュールの DB 操作用  
   - psutil: システムモニタ（CPU/メモリ/ディスク/プロセス管理）  
   - openai: ニュース NLP / レジーム判定で使用（API キー必須）  
   - PyYAML: validate_config の YAML 内容検証を行う場合に推奨

4. .env を作成する
   - 対話式ウィザードを使用（推奨）:
     - python -m kabusys.config_setup
   - 最低必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 便利な環境変数（一例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時に必須）
     - LOG_LEVEL, LOG_DIR, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE など（README 下部のサンプル参照）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - strict モードで警告を FAIL とみなす: python -m kabusys.validate_config --strict

6. データディレクトリ作成（logs / data）
   - 多くのスクリプトが data/ や logs/ 配下にファイルを作成します。必要に応じて権限を確認してください。

---

## 使い方（起動例）

基本的にパッケージモジュールとして直接実行できます。

- 監視の起動（Monitoring）
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（例: 30）。
  - python -m kabusys.run_monitoring
  - 停止方法:
    - data/stop_requested.flag を作成すると監視ループは次のサイクルで終了します（run_monitoring 内でチェック）。
    - KeyboardInterrupt（Ctrl+C）でも停止します。

- 実行エンジンの起動（ExecutionEngine）
  - KABUSYS_ENV によりブローカーが切り替わります（paper_trading モードでは MockBrokerClient を使用し、専用の paper DB に書き込みます）。
  - python -m kabusys.run_execution
  - 停止方法:
    - data/stop_requested.flag の作成で実行エンジンに停止指示が伝播します（エンジンはフラグを検出して停止処理を実行します）。
    - Kill Switch（監視コンポーネントが data/kill.flag を書く）により強制停止される場合があります。

- .env の対話式作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として扱います。

- ペーパートレード検証レポート作成
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定することも可能

- AI 機能
  - OPENAI_API_KEY が必要（環境変数か関数呼び出し時の引数で指定）
  - ai モジュールは DuckDB 接続を受け取り、ai_scores / market_regime 等を更新します（詳しくは ai/news_nlp.py / ai/regime_detector.py を参照）

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行制御 / 環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1）
- DB 関連
  - DUCKDB_PATH — 分析用 DuckDB のパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- AI
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector 用）
- ログ
  - LOG_LEVEL — DEBUG / INFO / ...
  - LOG_DIR — ログ出力先（デフォルト: logs/）
- 監視
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - PID_FILE_PATH, KILL_FLAG_PATH — Settings で参照

注意: .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも同様の注意書きあり）。

---

## 動作上の注意・トラブルシューティング

- ファイル／ディレクトリ作成権限
  - logs/ や data/ の作成に失敗するとファイルログが無効化される場合があります（コンソールログのみで継続）。
- プロセス優先度設定
  - set_process_priority は OS と権限に依存します。権限不足で警告が出る場合がありますが、処理は継続します。
- OpenAI API
  - レート制限や 5xx などの一時エラーはリトライ実装がありますが、API キーは必ず設定してください。AI 呼び出し失敗時は安全側のフォールバックが行われます（例: macro_sentiment=0）。
- Kill Switch / stop flag
  - 監視コンポーネントはリスク閾値を超えると data/kill.flag を書き、ExecutionEngine を停止させる設計です。KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に自動でクリアされますが、本番環境では 0 を推奨します。
- DB マイグレーション
  - init_monitoring_db は冪等にテーブルと一部カラムの追加（マイグレーション）を行います。既存 DB に対する操作は注意して行ってください。

---

## ディレクトリ構成（抜粋）

以下はソースツリーの主要部分（src/kabusys/）の例です。

```
src/kabusys/
├── __init__.py
├── config.py
├── config_setup.py
├── validate_config.py
├── run_monitoring.py
├── run_execution.py
├── utils/
│   ├── __init__.py
│   ├── logging_setup.py
│   └── process_priority.py
├── monitoring/
│   ├── monitoring_db.py
│   ├── monitoring_engine.py
│   ├── system_monitor.py
│   ├── trade_monitor.py
│   ├── risk_monitor.py
│   ├── kill_switch.py
│   └── alert_manager.py  (実装想定)
├── execution/
│   ├── execution_engine.py
│   ├── order_manager.py
│   ├── order_repository.py
│   ├── broker_factory.py
│   └── reconciler.py
├── portfolio/
│   ├── __init__.py
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py
│   └── regime_detector.py
├── tools/
│   ├── __init__.py
│   └── paper_verification_report.py
└── data/                # 実行時に使用する DB / flag / pid など（リポジトリで未管理にすること）
```

---

## 追加例（よく使うコマンド）

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

---

## 最後に（運用上の推奨）

- 本番環境（KABUSYS_ENV=live）では、LINE 等のアラート設定を必ず確認してください（validate_config でチェック可能）。
- Kill Switch と stop フラグの運用ルールをチームで定め、誤操作を防いでください。
- DB（特に本番 SQLite）のバックアップとログローテーションの確認を行ってください。

---

もし README の別言語版や、より詳細なデプロイ手順（systemd サービス定義、Dockerfile、CI 設定等）が必要であれば、その用途に合わせて追加で作成します。