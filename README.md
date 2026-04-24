# KabuSys

日本株向けの自動売買 / リサーチ基盤の一部を収めたコードベースです。  
本リポジトリには以下の主要機能（監視・発注エンジン、ポートフォリオ構築、ファクター計算、AI を用いたニュース解析など）を実装しています。

**注意**: この README はリポジトリ内のコードを元にした導入・運用ガイドです。実運用時は必ず設定検証やテスト環境での検証を行ってください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 環境変数（主要なもの）
- 停止 / Kill スイッチの扱い
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ用ユーティリティ群です。  
主な目的は以下のとおりです。

- ExecutionEngine による発注および注文管理（本番 / ペーパートレード対応）
- MonitoringEngine によるプロセス・システム・注文状態の継続監視、アラート発行
- ポートフォリオ構築（銘柄選定、配分、ポジションサイズ計算）
- リサーチ（ファクター計算、将来リターン、IC 計算など）
- AI（OpenAI）を用いたニュースセンチメント解析・レジーム判定
- 設定ウィザード・検証ツール、検証レポート出力ツール

設計方針として、ほとんどのモジュールは副作用を持たない純粋関数または DB 抽象層で分離されています。SQLite / DuckDB でローカルにデータを持ち、必要に応じて外部 API（kabuステーション / J-Quants / OpenAI）を利用します。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードは MockBroker を使用）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを収集
- 設定管理
  - config_setup.py: .env の対話式生成・更新ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
- 監視
  - monitoring_engine.py: System / Trade / Risk 各 Monitor を束ねる
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 監視ロジック
  - monitoring_db.py: SQLite ベースの監視データ永続化層
  - kill_switch.py: 条件に応じて kill.flag を書き込み ExecutionEngine に停止シグナルを送る
- 発注・実行
  - execution/*: BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等
- ポートフォリオ（純粋関数）
  - portfolio/*: 銘柄選定、重み計算、リスク調整、ポジションサイズ計算
- リサーチ
  - research/*: ファクター計算（momentum/value/volatility）、特徴量探索、IC 計算
- AI 関連
  - ai/news_nlp.py: OpenAI によるニュースセンチメント計算と ai_scores への書き込み
  - ai/regime_detector.py: マクロセンチメントと ma200 を合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

---

## セットアップ手順

前提:
- Python 3.9 以上を推奨（使用ライブラリに合わせる）
- ローカルで DuckDB / SQLite ファイルを使用（サーバ起動不要）

1. リポジトリをクローン / 配布パッケージを展開。

2. 依存ライブラリをインストール（最低限の例）:
   - duckdb
   - psutil
   - openai（AI 機能利用時）
   - PyYAML（validate_config の YAML 検証を利用する場合）
   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

3. .env の作成（対話ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードに沿って必要なキー（J-Quants トークン、Kabu API パスワード等）を入力してください。

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの作成（必要に応じて）
   デフォルトでは `data/` 配下に SQLite / DuckDB / PID / flag ファイルが置かれます。スクリプトが自動作成する部分もありますが、権限やパスに注意してください。

---

## 使い方（主要コマンド）

- ExecutionEngine 起動（本番 or paper_trading は KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - 実行前に `.env` の KABUSYS_ENV を設定してください。
  - paper_trading の場合、MockBrokerClient を用い、デフォルトで `data/paper_trading.db` を使います。

- Monitoring 起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔のオーバーライド:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    デフォルトは 60 秒。1 秒以上の整数を指定してください。

- .env の対話式作成 / 更新:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコア／レジーム判定はライブラリ関数として呼び出す:
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

  これらを CLI から直接叩く小ラッパーは用意されていないため、スケジューラやバッチスクリプトから呼び出してください。

---

## 主要な環境変数（抜粋）

- 必須（少なくとも実行時に設定が必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境関連
  - KABUSYS_ENV — 実行モード。development / paper_trading / live （デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch が書き込むフラグ（デフォルト: data/kill.flag）

- モニタリング
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

- Paper Trading / Mock 座標
  - PAPER_FILL_MODE — paper_trading 時の約定挙動（instant / partial / never / reject。デフォルト: instant）

- AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

その他は config/*.yaml により細かい挙動を制御する想定です（validate_config で存在チェックを行います）。

---

## 停止 / Kill スイッチの扱い

- 一時停止（run_monitoring / run_execution の手動停止）
  - どちらの起動スクリプトもプロジェクトルートの `data/stop_requested.flag` の存在をチェックします。  
    このファイルが存在すると（監視ループや実行ループは）安全に停止します。  
    例: 停止要求を出すには `touch data/stop_requested.flag` （Unix 系）を実行してください。

- Kill Switch（自動停止条件）
  - Monitoring の RiskMonitor + KillSwitch により、ドローダウンやポジション過多などの条件を満たすと `data/kill.flag` を書き込みます。  
  - ExecutionEngine（起動ロジック）は kill.flag を参照して発注停止・クリーンアップを行う設計になっています（設定により動作）。  
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると kill.flag が自動クリアされますが、本番では 0 を推奨します。

---

## ロギング

- setup_logging() 経由で統一的にログ設定されます。出力先はコンソール（stdout）と日次ローテートされたファイル（logs/<app_name>.log）。
- ログレベルは LOG_LEVEL 環境変数で指定できます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（__version__ など）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み機能含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - ai/
    - news_nlp.py — ニュースを OpenAI へ送りセンチメントを ai_scores に書き込む
    - regime_detector.py — ma200 とマクロセンチメントを合成してレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB の初期化・アクセス層
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — フラグファイルによる停止制御
    - alert_manager.py — (アラート処理：LINE 等の送信実装想定)
  - execution/ — ExecutionEngine、OrderManager、BrokerFactory、RiskManager 等
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定ロジック、aggregate cap、lot 単位処理
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ — 実行時に使用する SQLite/DuckDB/PID/flag ファイル（デフォルトパス）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では十分な検証・分離（DB・APIキー）と監査を行ってください。
- .env ファイルは絶対に Git 等にコミットしないでください（config_setup.py のヘッダにも注記あり）。
- OpenAI を使う機能は API 使用料が発生します。API キー・利用量を管理してください。
- Monitoring の閾値や RiskManager の設定は config/*.yaml または環境変数で調整可能です。まずは paper_trading で十分に検証してください。
- DuckDB / SQLite ファイルのバックアップ・ローテーション、ログローテーション（logs/）の監視を運用で行ってください。

---

この README は主要な利用方法と設計の概観を提供します。より詳細な仕様（アルゴリズムの理論的背景やパラメータチューニング方針など）は各モジュールの docstring や別途用意されているドキュメント（例: PortfolioConstruction.md, StrategyModel.md）を参照してください。