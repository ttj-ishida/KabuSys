# KabuSys

日本株向け自動売買システムのコードベース（抜粋）。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視基盤（Monitoring）、ポートフォリオ構築・リスク管理、リサーチ／ファクター計算、AI を用いたニュース NLP 等のコンポーネントで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群です。

- 日次・リアルタイムの売買戦略実行（ExecutionEngine）
- システム稼働状況・注文状態・リスク監視（Monitoring）
- 銘柄選定・配分・ポジションサイズ計算（Portfolio module）
- DuckDB を用いたファクター計算・リサーチ（Research）
- OpenAI を活用したニュースセンチメント評価・レジーム判定（AI）
- 開発操作を支援するツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の一部：
- 本番用とペーパートレード用の DB は分離（ペーパートレード時は専用の SQLite DB を使用）
- 環境変数または .env による設定管理（.env の対話式ウィザードあり）
- ロギングは統一的に設定（stdout + 日次ローテートファイル）
- OpenAI 呼び出しはフェイルセーフ／リトライを考慮

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - ブローカークライアントの切替（本番 / paper_trading で Mock を利用）
  - リスク管理（RiskManager）・注文管理（OrderManager）・リコンシリエーション
- Monitoring
  - SystemMonitor（CPU/メモリ/Disk、データ鮮度、プロセス生存）
  - TradeMonitor（注文の滞留や約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - Kill Switch（条件を満たすと data/kill.flag を書き込む）
  - MonitoringEngine（複数モニタをまとめてポーリング）
- Portfolio
  - 候補選定、等配分・スコア加重配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research
  - Momentum, Volatility, Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC 計算、特徴量の統計要約
- AI
  - ニュース NLP による銘柄ごとのセンチメントスコア生成（OpenAI）
  - レジーム判定（MA + マクロセンチメントの合成）
- Tools
  - 設定ウィザード（config_setup.py）による .env の生成
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - ログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity（utils/process_priority.py）
  - 設定読み込みと Settings（config.py）
- 永続層（監視）
  - monitoring_db: SQLite ベースのテーブル定義と簡易 CRUD（system_status, trade_logs, positions, risk_logs, dashboard）

---

## セットアップ手順

前提
- Python 3.10+
- Git（リポジトリをクローンできること）

1. リポジトリをクローンし、作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必要パッケージの一部（最低限）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証用に任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があるなら `pip install -r requirements.txt` を利用）

4. .env の準備
   - 対話式ウィザードで作成（推奨）:
     - python -m kabusys.config_setup
   - または手動で `.env` をルートに配置（.env.example を参考に必須の環境変数を設定）

   必須（少なくとも設定が必要なもの）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   本番 / 動作モード
   - KABUSYS_ENV: development / paper_trading / live

   OpenAI API を使う場合
   - OPENAI_API_KEY 環境変数を設定

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題があれば警告 / エラーが表示されます。--strict を付けると警告も失敗扱いになります。

6. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / PID / フラグは `data/` に作成されます。必要なら事前に権限を確認してください。

---

## 実行／使い方

※ すべてプロジェクトルートで実行してください（.env 自動ロードはプロジェクトルート検出に依存します）。

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録します。
    - 起動時に `data/execution.pid` へ PID を書き込みます。
    - 停止フラグ `data/stop_requested.flag` を監視し、存在するとエンジンは停止します。

- Monitoring の起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  - 挙動:
    - SQLite（Monitoring DB）は環境に関係なく本番の sqlite_path（Settings.sqlite_path）を使用します（監視ログは一元管理）。
    - 終了は KeyboardInterrupt、もしくは data/stop_requested.flag の検出。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に生成／更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit code 1）になります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）

- AI モジュール（プログラム内で利用）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

- ログ
  - デフォルト出力: stdout とログファイル（logs/<app_name>.log 日次ローテート）
  - ログレベルは環境変数 LOG_LEVEL（デフォルト INFO）で制御可能

---

## 重要なファイル・フラグ

- data/stop_requested.flag
  - run_execution / run_monitoring が監視している停止フラグ。存在するとループを抜けます。
- data/kill.flag
  - Kill Switch（監視）によって書き込まれる停止要求フラグ（ExecutionEngine 停止のため）。
- data/execution.pid
  - ExecutionEngine の PID ファイル（run_execution によって使用）。
- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite (production): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db

---

## 主要ディレクトリ構成

（src/kabusys 配下の主なファイル／ディレクトリを抜粋）

- src/kabusys/
  - __init__.py
  - config.py — Settings クラス、.env 自動ロードロジック
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 + 永続化 API
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — （注文系モニタ、抜粋には含まれている想定）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルにより停止指示を出すユーティリティ
    - monitoring_engine.py — 各モニタをまとめる
  - execution/ (発注ロジック、OrderManager 等の実装)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py — ロギング初期化
    - process_priority.py — プロセス優先度 / CPU affinity 設定

---

## 動作モード（KABUSYS_ENV）

- development
  - 開発・テスト用。発注は抑止される想定（実際の BrokerClient の実装に依存）。
- paper_trading
  - MockBroker を利用し、発注フローやログは paper_trading 用 DB に記録（本番 DB と分離）。
- live
  - 実際のブローカー API を使って発注するモード。利用時は各種設定（LINE 通知、キルスイッチ等）を慎重に。

---

## 注意事項 / 運用メモ

- .env は機密情報を含むため Git 管理してはいけません。config_setup のヘッダにもその旨が記載されています。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=1 にしないことを推奨（誤って Kill Switch をクリアしてしまうリスク）。
- OpenAI / 外部 API 呼び出しはネットワークエラーやレート制限に備え、リトライやフォールバック処理が組み込まれていますが、運用上の監視とキーの管理を行ってください。
- run_monitoring はデフォルトで 60 秒間隔のポーリング（MONITOR_POLL_INTERVAL で上書き可能）を行います。

---

## よく使うコマンド（まとめ）

- .env の作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README はコードベースの抜粋から作成しています。実際の運用や詳細な API 仕様は各モジュールのドキュメントやソース内ドキュメント（docstring）を参照してください。必要であれば、各サブモジュール（execution, monitoring, ai, portfolio, research）の詳細な README を別途作成します。どの部分を深掘りしたいか教えてください。