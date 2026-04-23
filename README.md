# KabuSys

日本株自動売買システムの軽量コアライブラリ（README 日本語版）

このリポジトリは、戦略評価・ポートフォリオ構築・発注実行・監視・AIベースのニュース解析などを含む自動売買基盤の主要コンポーネント群を収めています。設計は本番運用とペーパートレードの分離、ログ管理、フェイルセーフ（Kill Switch 等）を重視しています。

---

## プロジェクト概要

- 戦略（ファクター計算、特徴量探索）やポートフォリオ構築（銘柄選定・重み計算・株数決定）を行う純粋関数群を提供。
- ExecutionEngine による発注処理（実口座 or ペーパートレード分離）をサポート。
- Monitoring 系（System / Trade / Risk）による定期監視とアラート発行、Kill Switch による安全停止機構を備える。
- OpenAI を用いたニュースの NLP スコアリング、レジーム判定モジュールを提供（API キー必須）。
- DuckDB / SQLite をデータ基盤として利用。ログは標準出力と日次ローテートファイルへ出力。

---

## 主な機能一覧

- 設定管理
  - .env の自動ロード（プロジェクトルートに基づく）
  - 対話式ウィザード（python -m kabusys.config_setup）で .env を生成
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行 / 発注
  - ExecutionEngine（実口座 or paper_trading モード）
  - BrokerClientFactory によるブローカークライアント切替（paper_trading は Mock を使用し DB を分離）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリング監視
  - MonitoringEngine による定期実行・アラート・Kill Switch 評価
  - SQLite に監視ログ永続化（monitoring_db）
- ポートフォリオ構築
  - 銘柄選定（select_candidates）
  - 重み付け（等金額 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター上限適用、レジーム乗数
- 研究（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（情報係数）算出、統計サマリ
- AI（OpenAI）
  - ニュースの銘柄別センチメントスコアリング（ai.news_nlp）
  - マクロニュース + ETF MA を用いた市場レジーム判定（ai.regime_detector）
- ツール
  - Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+（実際の互換性はプロジェクト方針に合わせてください）
- Git リポジトリをクローン済み

1. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検証をする場合）
   - 例:
     ```bash
     pip install duckdb psutil openai PyYAML
     ```
   - （実プロジェクトでは requirements.txt / pyproject.toml があればそれに従ってください）

3. .env の作成
   - 対話式ウィザードを使うと簡単です:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成（プロジェクトに .env.example がある場合は参考にしてください）。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV = development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（0/1）

4. DB 初期化
   - 監視用 SQLite テーブルは起動時に自動作成されます（init_monitoring_db を呼ぶため手動操作不要）。
   - DuckDB 用のスキーマはプロジェクトの data 構成に従って準備してください（prices_daily や raw_financials 等をロードする必要あり）。

5. ログディレクトリ作成
   - デフォルトの logs/ ディレクトリは自動作成されますが、アクセス権やパスを変更する場合は LOG_DIR を環境変数で設定できます。

注意:
- 自動環境変数ロードはデフォルトで有効です。テストで無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env は機密情報を含むため Git へコミットしないでください。

---

## 使い方（起動例）

- 設定検証
  ```bash
  python -m kabusys.validate_config
  # --strict を付けると警告も失敗扱いに
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine（発注エンジン）起動
  - paper_trading と live は KABUSYS_ENV によって切替
  - paper_trading では MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
  ```bash
  python -m kabusys.run_execution
  ```
  - 停止方法: プロセスを SIGINT（Ctrl+C）するか、監視側から kill.flag を書き込むと停止します（data/kill.flag）。
  - 実行時は PID ファイルを data/execution.pid に書きます（設定で変更可）。

- Monitoring（監視ループ）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に上書き可能（デフォルト 60 秒）。
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は monitoring.db（Settings.sqlite_path）へログを書き込みます。MonitoringEngine は各モニタを呼び出し、必要に応じて Kill Switch を発動します。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニューススコア付与 / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - モジュール API を用いる例（プログラム内から呼び出す）:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 安全停止 / フラグファイル

- 停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring スクリプトが監視している「プロセス停止要求」フラグ（存在するとループ終了）。
  - data/kill.flag — KillSwitch が書き込むファイルで ExecutionEngine 停止を指示。
- KillSwitch の評価は MonitoringEngine 内で行われ、条件（ドローダウン・ポジション数制限など）に合致すると kill.flag を作成します。
- kill.flag を手動で消す場合:
  - ファイルを削除するか、起動時の設定 KILL_FLAG_CLEAR_ON_START=1 により自動クリアできます（本番では 0 推奨）。

---

## ディレクトリ構成（主なファイルと説明）

以下はソースツリー（src/kabusys）内の主要モジュールとファイルの抜粋です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック、Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - execution/  （発注関連コンポーネント）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
    - ...（ブローカ・発注ロジック）

  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化
    - system_monitor.py — システム状態監視（CPU/MEM/DISK・データ鮮度・プロセス生存）
    - trade_monitor.py — 注文/約定監視（滞留注文・異常約定など）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（フラグファイル書き込み）
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - alert_manager.py —（アラート送信ロジック：LINE 等）

  - portfolio/
    - portfolio_builder.py — 銘柄選定・スコア基準
    - position_sizing.py — 株数算出・資金制限・丸め処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — モメンタム／ボラティリティ／バリュー等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py

  - ai/
    - news_nlp.py — OpenAI を使ったニュースセンチメント解析（銘柄別）
    - regime_detector.py — マクロ + ETF MA を用いたレジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
    - __init__.py

  - utils/
    - logging_setup.py — 統一的なログ設定（console + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

- data/ （実行時に作成されることが多い）
  - monitoring.db / paper_trading.db / kabusys.duckdb
  - execution.pid, stop_requested.flag, kill.flag, etc.

- logs/
  - execution.log, monitoring.log, ...（日次ローテーション）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定ミスが重大な実取引損失につながるため、validate_config を必ず実行して警告・エラーを確認してください。
- .env 内の機密情報（API トークン・パスワード）は Git にコミットしないでください。
- OpenAI 等外部 API 呼び出しはネットワーク/課金リスクがあるため、API キー管理とレート制限に注意してください。
- paper_trading モードではデータベースが分離されますが、実運用コードの動作確認は慎重に行ってください。

---

## よく使うコマンドまとめ

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- 発注エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```

- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの主要機能と運用フローの概要をまとめたものです。詳細は各モジュール（特に execution/, monitoring/, ai/, research/）のドキュメントやソースコードの docstring を参照してください。必要であればセクションを拡張して運用手順や API 使用例を追加します。