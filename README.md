# KabuSys

日本株自動売買システムのコアライブラリおよび起動スクリプト群です。  
このリポジトリは、戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究用ユーティリティ、LLMベースのニュース解析などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株に対する自動売買システムの核となるモジュール群です。主な機能は次のとおりです。

- データ取得・集計（DuckDB を用いた時系列データ参照）
- ファクター計算（モメンタム / ボラティリティ / バリュー等）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 発注実行エンジン（paper_trading モードではモックブローカー）
- 監視（システム状態・注文ログ・リスク監視・Kill Switch）
- ニュースNLP（OpenAI を用いた銘柄別センチメント評価）
- 研究支援ツール（IC計算、特徴量探索、Paper Trading 検証レポート等）
- 環境設定ウィザード・設定検証 CLI

設計方針の一部：
- ルックアヘッドバイアスを避ける（API・日付参照の扱いに配慮）
- 本番 DB と paper_trading の DB を明確に分離
- 障害時はフェイルセーフ（API失敗などはスキップやフォールバック）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔設定可能）
- 設定管理
  - config_setup.py: .env の対話式ウィザード（初期作成・更新）
  - validate_config.py: .env と config/*.yaml の起動前検証 CLI
  - Settings クラス: 環境変数のラップ（KABUSYS_ENV, DBパス等）
- 監視
  - monitoring_engine.py / system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py
  - monitoring_db.py: SQLite を用いた監視ログの永続化
- 発注・実行関連（execution/*）
  - BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等（実行フローの組み立て）
- ポートフォリオ
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（等金額・スコア配分、リスク調整、枠組み）
- 研究・分析
  - research.factor_research: モメンタム / ボラティリティ / バリューファクターの計算
  - research.feature_exploration: 将来リターン計算、IC、統計サマリ
- AI（OpenAI）
  - ai.news_nlp: raw_news を LLM で解析し銘柄別スコアを ai_scores テーブルへ書き込み
  - ai.regime_detector: ETF（1321）MA とマクロニュースの LLM センチメントを組み合わせて市場レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

---

## セットアップ手順

前提:
- Python 3.9+（ソースは型ヒント等で新しいバージョン向けに記述されています）
- pip によるパッケージインストール権限

推奨パッケージ（抜粋）:
- duckdb
- psutil
- openai
- pyyaml（設定検証で YAML を検証したい場合）
- （必要に応じて）その他依存パッケージ

例:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # (Unix)
2. 依存関係をインストール（requirements.txt があればそれを使用）
   - pip install duckdb psutil openai pyyaml
   - もし requirements.txt を用意する場合は pip install -r requirements.txt

3. プロジェクトルートで .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
   - .env の代表的な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時に必須）
     - LOG_LEVEL（例: INFO）
     - その他: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用）

注意:
- .env はリポジトリにコミットしないでください（シークレットを含みます）。
- validate_config.py で設定検証を行ってください:
  - python -m kabusys.validate_config
  - 警告も失敗にする場合は --strict を付ける

---

## 使い方（主なコマンド）

プロジェクトルートで以下を実行します。モジュールは package 内のスクリプトとして実行できます。

- 設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパー用ともに設定に従う）
  - python -m kabusys.run_execution
  - 注意: 起動時に data/stop_requested.flag があると起動しません
  - paper_trading の場合、Settings.is_paper が True で MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を利用します

- Monitoring 起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）
  - 監視は常に本番用 sqlite_path を参照します（KABUSYS_ENV に依らず監視データは本番DBへ）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能

- AI 機能（スクリプト経由またはライブラリ呼び出し）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - api_key は None の場合 OPENAI_API_KEY 環境変数を参照
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ:
- デフォルトで logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリを作成します）
- setup_logging(app_name="...") が各起動スクリプトで呼ばれます

停止フラグ・プロセス管理:
- data/kill.flag: Kill Switch のフラグ（監視モジュールによって書き込まれる）
- data/stop_requested.flag: 各デーモン起動ループ停止トリガ（run_monitoring/run_execution が監視）
- data/execution.pid: 実行エンジンの PID ファイル（設定でパス指定可能）

---

## 環境変数（代表的なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## 開発時の注意点 / 実運用上の注意

- 本番環境（KABUSYS_ENV=live）では kill_flag 等の設定に十分注意してください。validate_config.py は live 時に追加の警告を出します。
- OpenAI を利用する機能は API コストやレート制限に注意してください。スクリプト内で指数バックオフ・リトライ実装がありますが、運用ではさらに制御が必要な場合があります。
- paper_trading モードは必ず本番 DB と分離された SQLite を使用するよう設計されています。
- ログや DB のファイルパスは .env で変更可能です。ログディレクトリ作成に失敗した場合はコンソールのみの出力にフォールバックします。

---

## ディレクトリ構成

（主要ファイル・ディレクトリのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — Settings / 自動 .env ロード
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — SystemMonitor 起動スクリプト
    - monitoring/
      - monitoring_db.py           — SQLite のスキーマ & 永続化 API
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/                         — 実行時に生成される想定のディレクトリ（DB / pid / flag など）

プロジェクトルートには .env(.example)、config/*.yaml、pyproject.toml/.git などが置かれる想定です（config/*.yaml は各種設定テンプレート）。

---

## 参考・補足

- DB マイグレーション: monitoring_db.init_monitoring_db() はテーブル作成の冪等処理と簡易マイグレーション（カラム追加）ロジックを含みます。
- ログ設計: kabusys.utils.logging_setup.setup_logging を各起動スクリプトの最初に呼び出して統一したログ出力を確保しています。
- プロセス優先度: utils.process_priority.set_process_priority("high") を起動時に実行して優先度を上げる（権限により失敗する場合は警告を出してスキップします）。
- テスト: 各モジュールは純粋関数や依存注入を意識して設計されています（OpenAI 呼び出し等は差し替えやモックが可能）。

---

必要であれば、この README をベースに「デプロイ手順」「運用ドキュメント（監視アラートのしきい値・運用フロー）」「テストケース」などの追加ドキュメントも作成します。どの項目を優先して欲しいか教えてください。