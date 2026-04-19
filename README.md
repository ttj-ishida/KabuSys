# KabuSys

日本株向け自動売買システムのリファレンス実装です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築・リスク管理、研究用ファクター計算、AI を使ったニュース評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール群で構成されています。

- 発注エンジン（実口座 / ペーパートレード切替可）
- システム監視・リスク監視・アラート管理（Kill Switch を含む）
- ポートフォリオ構築（候補選定、配分、ポジションサイズ計算）
- リサーチ用ファクター計算（DuckDB 経由で価格データを集計）
- AI を使ったニュースセンチメント評価（OpenAI）
- 運用支援ツール（設定ウィザード、設定検証、検証レポート）

設計方針として、実運用を意識した堅牢性（フェイルセーフ、冪等性、ログ整備）と、テストしやすい純粋関数・副作用の最小化を重視しています。

---

## 主な機能一覧

- ExecutionEngine
  - 実口座 / ペーパートレード（MockBroker）を環境変数で切替
  - リスク管理・注文管理・整合性チェック
- MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor
  - CPU / メモリ / ディスク / データ鮮度の監視
  - ポジション数・ドローダウンの監視、kill.flag による停止信号出力
- KillSwitch
  - 閾値超過時に data/kill.flag を書き込み、ExecutionEngine を停止させる仕組み
- Portfolio モジュール
  - 候補選定、等金額/スコア重み配分、リスクに基づくポジションサイズ算出
- Research
  - Momentum / Volatility / Value 等のファクター計算、IC 計算・統計要約
- AI（news_nlp / regime_detector）
  - OpenAI を用いたニュースセンチメント評価・市場レジーム判定（gpt-4o-mini を想定）
- ユーティリティ
  - 設定ウィザード（.env 作成）
  - 設定検証 CLI（config/*.yaml、必須環境変数のチェック）
  - Paper Trading 検証レポート生成ツール

---

## 前提・依存

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb
  - psutil
  - openai
  - PyYAML（任意：構成ファイル検証用）
- 標準ライブラリ：sqlite3 など

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. 環境変数（.env）を作成
   - 対話式ウィザードで .env を作成できます：
     ```
     python -m kabusys.config_setup
     ```
   - 作成後、設定を検証：
     ```
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict   # 警告を FAIL 扱いにする
     ```

5. データ・ログ用ディレクトリを確認（必要なら作成）
   - 既定パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/
   - 起動時に自動作成されることが多いですが、権限や配置を事前に確認してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション:
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定モード）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
- LOG_LEVEL, LOG_DIR
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発用）

監視用:
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

---

## 実行方法（例）

- ExecutionEngine（発注エンジン）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録します（本番 DB から分離）。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

停止方法:
- 停止フラグファイルを設置することで安全停止を促せます（スクリプトは data/stop_requested.flag を監視）。
- KillSwitch による強制停止は data/kill.flag を書き込みます（Monitoring が検知して ExecutionEngine を停止させます）。

---

## 使い方の注意点・運用メモ

- 本番稼働時は KABUSYS_ENV=live、LINE 通知設定などを必ず確認してください（validate_config の警告参照）。
- OpenAI を使うモジュール（news_nlp / regime_detector）は API キーと利用コストに注意してください。失敗時はフェイルセーフで継続する設計です。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR 環境変数で変更できます。
- データベーススキーマはマイグレーション処理を含む初期化ロジックがあり、既存 DB に対して后方互換のカラム追加を試みます。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - execution/               — 発注関連（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続層（schema/init）
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — OpenAI を使ったニューススコアリング
    - regime_detector.py
  - tools/
    - paper_verification_report.py

- config/
  - *.yaml                  — 各種設定テンプレート（system_config.yaml 等）
- data/                     — データベース・フラグファイル（例: monitoring.db, paper_trading.db）
- logs/                     — ログ出力先（デフォルト）

---

## 追加情報 / トラブルシューティング

- YAML の検証には PyYAML が必要です（validate_config で使用）。未インストールなら該当チェックをスキップします。
- DuckDB / SQLite ファイルへの接続はパスの指定（環境変数）で変更可能です。権限やパスの親ディレクトリが存在するか事前確認してください。
- Process priority / CPU affinity の設定は OS の権限によって失敗することがあります（警告ログのみで継続します）。
- OpenAI 呼び出しはリトライ・バックオフ等の保護を入れていますが、API 利用制限やコストには注意してください。

---

必要であれば、本 README の英語版や各モジュールの API ドキュメント（関数引数・戻り値の詳細）、デプロイ手順（systemd / Supervisor / cron）のテンプレートを追加作成できます。要望があれば教えてください。