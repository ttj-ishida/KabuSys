# KabuSys

日本株向け自動売買システムの一部実装（ライブラリ・起動スクリプト・運用ツール群）。

このリポジトリには実運用・検証に必要なコンポーネント（ExecutionEngine、Monitoring、ポートフォリオ構築、リサーチ、AI 補助モジュールなど）が含まれます。各モジュールはできるだけフェイルセーフに設計され、ペーパートレード用 DB の分離や Kill Switch などの運用機能を備えています。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件
- セットアップ手順
- 使い方（起動・検証・ツール）
- 主な環境変数
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意

---

## プロジェクト概要

- 名称: KabuSys
- 用途: 日本株自動売買システム（発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI によるニュース評価など）
- 設計方針:
  - 環境変数 / .env で設定を管理（対話式ウィザードと検証 CLI を提供）
  - Paper Trading（ペーパートレード）機能は本番 DB と完全分離
  - 監視側は停止フラグ / kill flag / PID ファイル等で運用制御可能
  - DuckDB を分析用に、SQLite を監視/履歴用に利用
  - OpenAI（gpt-4o-mini）連携によるニュース NLP / レジーム判定機能あり（API キー必須）

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - 実行環境に応じて MockBroker（ペーパートレード）を使用
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）に記録
  - リスク管理、オーダー管理、再締め処理などの統合

- Monitoring（run_monitoring.py / monitoring package）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による ExecutionEngine の停止指示（KillSwitch）
  - 監視ログの永続化（SQLite via monitoring_db）
  - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視は環境に関係なく本番 sqlite_path を使用（注意）

- Portfolio（銘柄選定・配分・サイズ計算）
  - 候補選定、等金額・スコア加重、リスクベースサイズ算出
  - セクターキャップ、レジーム乗数の適用

- Research（DuckDB ベースのファクター計算 / 特徴量解析）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）など統計解析ユーティリティ

- AI（ニュース NLP / レジーム判定）
  - raw_news を LLM でスコア化して ai_scores に保存（score_news）
  - ETF（1321）MA とマクロニュースを組み合わせたレジーム判定（score_regime）
  - OpenAI API キー（OPENAI_API_KEY）が必要

- 運用ツール
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 前提条件

- Python 3.10 以上（型ヒントの | 演算子などを利用）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config/*.yaml の検証に任意で使用）
- SQLite（組み込み）およびファイルシステムアクセス権（data/, logs/ に書き込み）

インストール例:
```
python -m pip install --upgrade pip
python -m pip install duckdb psutil openai PyYAML
```
（プロジェクトに requirements.txt がある場合はそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する
2. 必要パッケージをインストール（上記参照）
3. .env の作成（推奨: ウィザードを使用）
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動作成（.env.example を参考に）
4. 設定の検証:
   ```
   python -m kabusys.validate_config
   ```
   警告も含めて厳格にチェックしたい場合は `--strict` を付けると警告が FAIL 扱いになります。
5. 必要ディレクトリ（data/, logs/）が自動作成されますが、権限等を確認してください。

---

## 使い方

### 環境変数の主要項目（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う / 重要:
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

詳細は `kabusys.config.Settings` を参照してください。

### 起動: ExecutionEngine（取引実行）

- 実行:
  ```
  python -m kabusys.run_execution
  ```
- 挙動:
  - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード DB に記録し、MockBroker を使用します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます（設定で上書き可能）。
  - 停止は stop_requested.flag を作成するか、kill.flag を監視側から書く運用などがあります。

### 起動: Monitoring（監視ループ）

- 実行:
  ```
  python -m kabusys.run_monitoring
  ```
- 挙動:
  - SystemMonitor, TradeMonitor, RiskMonitor を初期化してポーリングを行います。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルトは 60 秒。
  - 監視は KABUSYS_ENV に関わらず settings.sqlite_path（本番監視 DB）を使用します（重要）。
  - 監視ループの停止は data/stop_requested.flag を作成（存在確認）することで行います。

### 設定検証

- CLI:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

### .env 設定ウィザード

- 対話式で .env を生成/更新:
  ```
  python -m kabusys.config_setup
  ```

### Paper Trading 検証レポート

- コマンド:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- オプション `--db` でペーパートレード用 DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能）。

### AI 機能（ニュース NLP / レジーム判定）

- OpenAI API キー（OPENAI_API_KEY）が必要
- モジュール関数を直接呼び出して利用（CLI スクリプトは同梱されていません）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## ディレクトリ構成（主要ファイル説明）

（リポジトリ内の `src/kabusys` を基準に抜粋）

- kabusys/
  - __init__.py
  - config.py
    - Settings: 環境変数 / .env の読み込み・検証ロジック
  - config_setup.py
    - .env の対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリングスクリプト
  - utils/
    - logging_setup.py: 統一的なログ設定（stdout + 日次ローテーションファイル）
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py: SQLite を使った監視ログの永続化層
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: （注文周り監視。ファイル内に実装）
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag の読み書きロジック
    - monitoring_engine.py: 各 Monitor を束ねる
    - alert_manager.py: （アラート送信の抽象管理）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - 実行エンジン関連の実装（発注、リスク、ブローカー抽象など）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
      - 候補選定・重み付け・株数決定ロジック
  - research/
    - factor_research.py, feature_exploration.py
      - DuckDB を利用したファクター計算・解析
  - ai/
    - news_nlp.py: ニュースを LLM でスコア化して ai_scores に書き込む処理
    - regime_detector.py: ETF MA とニュースを組み合わせたレジーム判定
  - tools/
    - paper_verification_report.py: ペーパー取引検証レポート生成スクリプト

（上記は主要ファイルの抜粋です。実際のファイルはさらに細分化されています。）

---

## 運用上の注意

- 監視（run_monitoring）は設定にかかわらず settings.sqlite_path（本番監視 DB）を使用します。テスト時は注意して DB パスを指定してください。
- ペーパートレードでは PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と分離されます。必ずペーパートレード時に設定を確認してください。
- Kill Switch（data/kill.flag）は本番で重大な操作を行うため、KILL_FLAG_CLEAR_ON_START=1 の設定は本番では推奨されません（起動時に誤ってクリアされる可能性があるため）。
- MONITOR_POLL_INTERVAL は秒数。0 以下や不正な値は無視され、デフォルト 60 秒が使われます。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- OpenAI を利用する機能は API 呼び出しに伴うコストとレート制限が発生します。API キーの管理とレート制御設定を適切に行ってください。
- データベースのスキーマ変更を行う場合は既存データのマイグレーション方針を確認してください（monitoring_db は一部自動マイグレーションを行いますが、完全ではありません）。

---

README はここまでです。追加で「導入手順（Docker / systemd サービス定義）」や「開発用ユニットテスト・CI 設定」などを追記したい場合は、目的に応じてテンプレートを作成できます。必要であれば教えてください。