# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買のためのツール群（バックテスト/リサーチ/実運用補助）を含む軽量なフレームワークです。  
主に以下を提供します：

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視用ポーリングループ（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ファクター計算・リサーチユーティリティ（DuckDB ベース）
- ニュース NLP / レジーム判定（OpenAI を利用するモジュール）
- ペーパートレード検証レポート作成ツール
- 設定ウィザード / 設定検証 CLI

README の内容：
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要スクリプトの実行方法）
- ディレクトリ構成（主要ファイル・モジュールの説明）

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発を支援するライブラリ兼運用ユーティリティ群です。  
設計方針の抜粋：

- 設定は .env ファイルまたは環境変数で管理
- DuckDB / SQLite をローカル DB として使用（分析/監視）
- Paper Trading（ペーパートレード）を環境分離して実行可能
- OpenAI（gpt-4o-mini）を用いたニュース NLP とレジーム検出（任意）
- モジュールは可能な限り純粋関数・副作用少なめに設計

---

## 機能一覧

- 設定関連
  - `.env` 初期化ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 実行 / 監視
  - 実行エンジン起動スクリプト: run_execution.py
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し別 DB（data/paper_trading.db）へ記録
    - 停止はフラグファイル（data/stop_requested.flag または data/kill.flag）で制御
  - 監視ループ起動スクリプト: run_monitoring.py
    - システム状態・注文・リスクをポーリングし persist（SQLite）およびアラート発行
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- 監視モジュール
  - SystemMonitor（システム資源・データ鮮度監視）
  - TradeMonitor（注文滞留・約定異常監視）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じた停止フラグ出力）
- ポートフォリオ構築
  - 候補選定 / 等金額・スコア重み配分
  - セクター上限適用、レジーム乗数
  - 株数決定（リスクベース / 等配分 / スコアベース）、単元丸め、aggregate cap
- リサーチ
  - ファクター計算: モメンタム / ボラティリティ / バリュー
  - 将来リターン、IC（情報係数）、統計サマリー
  - DuckDB ベースの SQL + Python 実装
- AI
  - ニュース NLP（OpenAI で銘柄別センチメントを算出）
  - レジーム検出（ETF ma200 とマクロ記事の LLM センチメントを合成）
- ユーティリティ
  - ロギング設定（stdout + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity の簡易切替
  - Paper Trading 検証レポート生成ツール

---

## 前提（推奨）環境

- Python 3.10+
  - 型注釈 (A | B) を使用しているため Python 3.10 以上を想定
- 必要な Python パッケージ（主要）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config.yaml の内容検証が必要な場合に任意）
- 標準ライブラリ: sqlite3 等

最低限のインストール例（venv 内で）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

requirements.txt がある場合はそちらを使ってください（本リポジトリには含まれていない場合があります）。

---

## セットアップ手順

1. リポジトリをチェックアウトする

2. 仮想環境を作成して依存をインストール
   - 例: pip install duckdb psutil openai pyyaml

3. 環境変数設定（.env）
   - 対話式ウィザードで初期 .env を作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` に以下のキーを設定（最低限必須）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト development
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, 例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, 例: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（任意: DEBUG/INFO/…）
     - PAPER_FILL_MODE（paper_trading の注文約定挙動: instant / partial / never / reject）
   - 設定の検証:
     ```bash
     python -m kabusys.validate_config
     # --strict をつけると警告もエラー扱いで exit(1)
     python -m kabusys.validate_config --strict
     ```

4. 必要なディレクトリ（data, logs）を作成
   - 多くのスクリプトは自動的に作成しますが、手動で用意することも可能:
     ```bash
     mkdir -p data logs
     ```

5. （任意）paper_trading を使う場合は .env で KABUSYS_ENV=paper_trading を設定

---

## 使い方（主要スクリプト）

- 実行エンジンを起動
  - 通常（本番 / 開発 / paper_trading を env で選ぶ）:
    ```bash
    python -m kabusys.run_execution
    ```
  - 動作概要:
    - Settings に基づき SQLite / DuckDB に接続
    - paper_trading 環境なら専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用（本番 DB と分離）
    - BrokerClientFactory からブローカークライアントを作成（paper_trading では Mock）
    - ExecutionEngine を別スレッドで run_session() 実行
    - 停止は data/stop_requested.flag を作成（run_execution はこのフラグを監視して停止）

- 監視ループを起動
  - 監視サービス（System / Trade / Risk をポーリング）:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 主要挙動:
    - デフォルトのポーリング間隔は 60 秒
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き（正の整数）
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視記録は単一 DB に集約）
    - data/stop_requested.flag を検知するとループを終了

- Paper Trading 検証レポート生成
  - ペーパートレード DB を参照して検証レポートを標準出力に表示
    ```bash
    # デフォルト DB: data/paper_trading.db
    python -m kabusys.tools.paper_verification_report
    # 期間指定
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # DB を明示的に指定
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
    ```

- 環境設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- AI 機能（ニュース NLP / レジーム検出）
  - OPENAI_API_KEY を設定しておく（.env または環境変数）
  - プログラムから呼び出す例（DuckDB 接続を用意してから）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意:
    - API 失敗時はフェイルセーフで部分的スキップまたはデフォルト値にフォールバックする設計
    - API 呼び出しはレート制限等でリトライロジックあり

- ログ
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション）
  - コンソールは stdout に出力
  - LOG_DIR 環境変数でログディレクトリを変更可能

---

## 停止・Kill Switch の仕組み

- 外部からの停止要求:
  - run_execution.py / run_monitoring.py はプロジェクトルートの data/stop_requested.flag を監視しています。ファイルが存在すると正常に停止します。
  - KillSwitch（監視側）からは data/kill.flag に理由を書き込み、ExecutionEngine に対する停止要求を表現します。ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の設定に応じて kill.flag を削除できます（本番では 0 推奨）。
- PID ファイル:
  - run_execution は data/execution.pid を使用（ExecutionEngine の設定で指定）
- クリア:
  - KillSwitch.clear() で kill.flag を削除できます（起動時のクリア等で利用）

---

## よく使う環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要/推奨:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" は自動クリア、開発用。推奨は "0"）

設定検証は python -m kabusys.validate_config で確認できます。

---

## ディレクトリ構成（概要）

リポジトリの主要構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数読み取り・検証・デフォルト管理
  - config_setup.py
    - .env の対話式ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite のスキーマ初期化 / 永続化ラッパ
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — （注文監視ロジック）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねて実行するエンジン
    - alert_manager.py — 通知（LINE 等）を統括（実装箇所あり）
  - execution/
    - execution_engine.py — 実際の注文・セッション管理（Engine）
    - broker_factory.py — broker client の生成（Mock/実ブローカー切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 実行系コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定、cap/丸めロジック
    - risk_adjustment.py — セクター制限、レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value の計算（DuckDB）
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py — ニュースの銘柄別センチメント算出（OpenAI）
    - regime_detector.py — ma200 とマクロニュースでレジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — 共通のログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記のうち一部モジュールは本 README の抜粋に含まれていない実装ファイルを参照しています）

---

## 開発・運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定や kill flag の扱いに注意してください。validate_config は live モード時に追加警告を出します。
- AI（OpenAI）を使う機能は API キーと通信の安定性に依存します。API 呼び出しはリトライを行いますが、コスト/レート制限に注意してください。
- run_monitoring は監視データを本番 sqlite_path に書き込みます（KABUSYS_ENV に依存せず本番パスを使用）。
- Paper Trading は実アカウントと分離する設計ですが、設定を誤ると実発注が行われる可能性があるため KABUSYS_ENV の切替と .env の管理は慎重に行ってください。
- ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみで動作します（ログ設定は寛容に設計）。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- 実行エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```
- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの主要機能と運用手順をまとめたものです。個々のモジュール（ExecutionEngine の内部、TradeMonitor の詳細、アラート連携等）は別ドキュメント（設計書 / コメント）を参照してください。必要であれば、特定モジュールの詳細なドキュメント（API 使用例、設計ノート、設定例）を追記します。