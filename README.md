# KabuSys

日本株自動売買システムのパッケージ (内部ユーティリティ・監視・ポートフォリオ・AI / リサーチ機能を含む)

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコンポーネント群です。  
主な目的は以下：

- 発注エンジン（ExecutionEngine）による注文管理（本番 / ペーパートレード対応）
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch による安全停止
- ポートフォリオ構築（候補選定、配分、ポジションサイズ計算、リスク調整）
- リサーチ用ファクター計算・特徴量解析（DuckDB を使用）
- ニュース NLP / レジーム判定などの AI 補助モジュール
- ペーパートレード検証レポート生成ツール

設計方針として「本番データとペーパートレード DB の分離」「ルックアヘッドバイアス回避」「外部 API 失敗時はフェイルセーフで継続」などが採用されています。


## 主な機能一覧

- run_execution: 発注エンジン起動（本番 / paper_trading 切替対応、ペーパートレードは MockBrokerClient を使用）
- run_monitoring: システム／トレード／リスク監視ループ（ポーリング、SQLite にログ保存）
- monitoring_engine: 各モニタを束ねたポーリングエンジンとアラート発行
- monitoring_db: 監視ログの永続化（SQLite テーブル定義 + マイグレーション）
- KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
- RiskMonitor: ドローダウン／ポジション上限監視と通知
- Portfolio モジュール: 候補選定、重み計算、ポジションサイズ決定、セクターキャップ、レジーム乗数
- research: DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）と IC 等の解析
- ai.news_nlp / ai.regime_detector: OpenAI を用いたニュースセンチメント解析・市場レジーム判定（API キー必要）
- tools.paper_verification_report: ペーパートレード結果の検証レポート生成
- config_setup / validate_config: .env の対話的生成と設定検証 CLI
- logging_setup, process_priority: ログ設定・プロセス優先度ユーティリティ


## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（例）

   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール

   本リポジトリには requirements.txt が付随していない想定のため、主な依存ライブラリをインストールしてください：

   ```
   pip install duckdb psutil openai
   ```

   - DuckDB: リサーチ・AI のクエリに使用
   - psutil: システム監視 / プロセス優先度設定
   - openai: ニュース NLP / レジーム判定（使用する場合のみ必須）
   - 追加で PyYAML を使うと validate_config の YAML 検証が有効になります：
     ```
     pip install pyyaml
     ```

4. 環境変数 / .env の準備

   対話式ウィザードで .env を生成できます：

   ```
   python -m kabusys.config_setup
   ```

   生成後、設定が適切か検証します：

   ```
   python -m kabusys.validate_config
   ```

   重要な環境変数（例）：
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - PAPER_FILL_MODE（paper_trading 用: instant | partial | never | reject）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB。デフォルト: data/paper_trading.db）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - LOG_LEVEL（DEBUG/INFO/...）
   - LOG_DIR（ログ出力先、デフォルト: logs/）
   - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）、KILL_FLAG_CLEAR_ON_START など

   注意: .env は決して Git にコミットしないでください。


## 使い方（起動例 / CLI）

- Execution エンジンを起動

  本番（KABUSYS_ENV=live）または paper_trading に応じて挙動が変わります。paper_trading では MockBrokerClient を使い、別 DB に記録します。

  ```
  python -m kabusys.run_execution
  ```

  - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止シグナルを送れます。

- Monitoring を起動（ポーリング監視ループ）

  ```
  python -m kabusys.run_monitoring
  ```

  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
    例: 30 秒ごとにポーリングする場合：
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```

- .env の対話式セットアップ

  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）

  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告を FAIL 扱いにする
  ```

- ペーパートレード検証レポートを生成

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  DB パスはオプション `--db` または環境変数 PAPER_TRADING_SQLITE_PATH で指定できます。

- AI 機能（ニュース NLP / レジーム判定）

  モジュール関数はプログラムから呼び出して使います。API キーは環境変数 OPENAI_API_KEY（または引数で渡す）を設定してください。

  例（内部的な使用例）:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

  注意: OpenAI API 呼び出しはリトライ・フェイルセーフを備えていますが、API キーは必須です。


## 停止 / Kill Switch

- 即時停止を意図する場合は `data/kill.flag` に理由を記述して書き込むと ExecutionEngine を停止する（KillSwitch による仕組み）。
- 監視ループ・エンジンの安全停止指示は `data/stop_requested.flag` を作成すると run_monitoring / run_execution 側で検知して終了します。
- 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨（自動クリアは危険）。


## ログ・プロセス優先度

- ログはデフォルトで標準出力（stdout）とファイル（logs/<app_name>.log）に日次ローテーションで出力されます。ログディレクトリは LOG_DIR 環境変数で上書き可能。
- 起動スクリプトは最初にプロセス優先度を "high" に設定しようとします（プラットフォームに依存し失敗する場合は警告を出して続行します）。


## ディレクトリ構成（主要ファイル）

リポジトリの主要なソース配置は下記の通り（src/kabusys 以下）：

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 定義 / 永続化 API
    - system_monitor.py       — CPU/MEM/DISK/データ鮮度監視
    - trade_monitor.py        — （トレード監視、コードベースに存在）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — Kill Switch 実装（kill.flag 書き込み）
    - monitoring_engine.py    — モニタの束ね・ポーリングロジック
    - alert_manager.py        — （アラート通知管理、コードベースに存在）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体（起動・セッション管理）
    - order_manager.py        — 注文管理
    - order_repository.py     — 注文永続化（SQLite 等）
    - broker_factory.py       — BrokerClient の生成（本番 / mock 切替）
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・集約キャップ処理
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/volatility/value）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py             — ニュースセンチメント集約・OpenAI 呼び出し
    - regime_detector.py      — マクロ + ETF MA200 でレジーム判定
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成

その他、data/（デフォルト DB / フラグファイル置場）や logs/（ログ）をルートに想定しています。各スクリプトはこれらの相対パスをデフォルトで使用します。


## 補足・運用上の注意

- ペーパートレードは paper_trading 専用 DB（デフォルト: data/paper_trading.db）へ記録され、本番 DB と完全に分離されます。KABUSYS_ENV を適切に設定してください。
- AI 機能（OpenAI）を使用する場合は API キーの管理に注意してください（.env に保存しても構いませんが Git 管理下に置かないでください）。
- validate_config を使って起動前に設定漏れ・明らかな不整合を検出することを推奨します。
- logging_setup はログディレクトリ作成に失敗するとファイル出力を無効化して標準出力のみで動作します。
- DuckDB は大規模なリサーチ / 集計に使います。性能上の制約やディスク容量に注意してください。

---

README はコードベースの主要な起点・ユーティリティをまとめたものです。具体的な ExecutionEngine の設定値やブローカー実装、戦略ロジックは各モジュールのドキュメント / ソース内コメントを参照してください。必要であれば各モジュールの使い方や設定例を追記します。