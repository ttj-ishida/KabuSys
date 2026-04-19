# KabuSys

軽量な日本株自動売買システムのコードベースです。  
このリポジトリには発注エンジン、監視機構、ポートフォリオ構築・ポジションサイジングロジック、リサーチ用ファクター計算、そしてニュースセンチメントを用いた AI モジュールなどが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に関わる以下の主要機能を提供します。

- 発注・実行エンジン（ExecutionEngine）
  - 実際のブローカ接続（kabuステーション）またはペーパートレード（MockBrokerClient）での発注が可能
  - リスク管理、オーダー管理、照合（reconciler）機構を内包

- 監視（Monitoring）
  - システム状態（CPU / メモリ / ディスク）、データ鮮度、滞留注文、ドローダウン監視
  - kill.flag による安全停止（Kill Switch）
  - 監視ログは SQLite（monitoring.db）へ永続化

- ポートフォリオ構築（Portfolio）
  - 候補選定、等金額／スコア加重配分、リスクベースのポジションサイズ計算
  - セクターキャップやレジームに応じた調整処理

- リサーチ（Research）
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー等

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（ai_scores テーブル）
  - ETF の MA200 とマクロニュースを合成した市場レジーム判定（market_regime テーブル）

- ツール
  - .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（paper_verification_report）

---

## 主な機能一覧（抜粋）

- Execution
  - BrokerClientFactory による環境依存のブローカ生成（paper_trading では Mock）
  - RiskManager（ポジション上限、資金利用上限、ドローダウン等）
  - OrderRepository / OrderManager / Reconciler

- Monitoring
  - SystemMonitor（プロセス生存・データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション数）
  - MonitoringEngine（各 Monitor のポーリング統合）
  - MonitoringDB（SQLite による永続化）

- Portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（risk_based / equal / score）
  - apply_sector_cap, calc_regime_multiplier

- Research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary

- AI
  - score_news（ニュース集約 → OpenAI → ai_scores 書き込み）
  - score_regime（regime 判定を市場データ + OpenAI で実行）

---

## 動作要件（推奨）

- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の検証で任意）
- SQLite（組み込み）
- インターネット接続（OpenAI を利用する場合）

requirements.txt が無い場合は次のようにインストールしてください（例）:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリへ移動する

2. Python 仮想環境を作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   pip install duckdb psutil openai PyYAML

4. 環境変数の準備
   - 対話式ウィザードで .env を作成:
     python -m kabusys.config_setup
   - もしくは .env を手動で作成し、下記の主要な環境変数を設定してください（サンプル）:

     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - OPENAI_API_KEY — OpenAI を使う場合に必須
     - PAPER_FILL_MODE — instant|partial|never|reject（paper_trading 時の動作）

   - .env 作成後、設定を検証:
     python -m kabusys.validate_config
     - strict モード: python -m kabusys.validate_config --strict

5. データディレクトリ（デフォルト）
   - data/ にログや DB、フラグファイルが置かれます。必要に応じて作成されます。

---

## 使い方（起動・主要コマンド）

- 実行エンジン（ExecutionEngine）起動:
  python -m kabusys.run_execution

  注意:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録されます（本番 DB と分離）。
  - 実行中の停止は data/stop_requested.flag（run_execution/run_monitoring が監視している停止フラグ）や data/kill.flag による挙動で制御できます。
  - 実行時に data/execution.pid が作成されます。

- 監視ループ起動:
  python -m kabusys.run_monitoring

  オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視 DB は共通で運用する設計）。

- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラム内呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  いずれも OPENAI_API_KEY を環境変数で設定するか、api_key を明示的に渡してください。

---

## プロセス制御とフラグ

- 停止フラグ:
  - data/stop_requested.flag: run_monitoring/run_execution のループでチェックされ、存在するとループを終了します（プロセスの優雅な停止シグナル）。
  - data/kill.flag: KillSwitch が発動すると書き込まれるファイルで、ExecutionEngine に対する停止要求として機能します。KillSwitch は監視条件（ドローダウン超過、ポジション数超過等）でトリガーされます。

- PID ファイル:
  - data/execution.pid（ExecutionEngine 起動時に作成）

---

## ロギング

- 全起動スクリプトは共通の logging 設定ユーティリティを利用します（kabusys.utils.logging_setup.setup_logging）。
- デフォルトでコンソール出力（stdout）および日次ローテーションファイル（logs/<app_name>.log）に記録します。ログディレクトリは環境変数 LOG_DIR で上書き可能。
- LOG_LEVEL でログ出力量を設定します（デフォルト: INFO）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 自動ロード / Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

subpackages:
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）で ai_scores を生成
  - regime_detector.py     — マクロ + MA200 によるレジーム判定
- monitoring/
  - monitoring_db.py       — SQLite テーブル定義・読み書きラッパ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (参照実装あり)
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
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

（注）上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）の設定は慎重に扱ってください。validate_config による事前チェックを推奨します。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup にもその旨が記載されています）。
- OpenAI を利用するモジュールは API の利用料金やレート制限を受けます。OPENAI_API_KEY の管理・モニタリングを行ってください。
- paper_trading は発注のシミュレーション向けです。本番口座に影響を与えないよう DB を分離しています。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を調整できます（秒、デフォルト 60）。0 や負の値を設定すると自動でデフォルトにフォールバックします。

---

## トラブルシューティング

- 設定エラー / 欠落：
  - python -m kabusys.validate_config を実行し、エラーや警告を確認してください。
- DB スキーマやマイグレーション：
  - monitoring_db.init_monitoring_db は起動時に必要なテーブルと一部のカラム追加マイグレーションを自動実行します。
- ログファイルが作成されない：
  - LOG_DIR の書き込み権限、あるいはログディレクトリの作成失敗ログをコンソールで確認してください（logging_setup は作成失敗時にコンソール警告を出します）。
- OpenAI 呼び出しで失敗が多い：
  - レート制限やネットワークエラーは指数バックオフでリトライする実装ですが、APIキーやネットワーク、レート制限状況を確認してください。

---

## 開発・拡張ポイント（参考）

- position_sizing では将来的に銘柄ごとの lot_size を扱う拡張が検討されています。
- news_nlp と regime_detector は OpenAI 呼び出し周りのリトライ・バリデーションを備えていますが、ローカルテスト用に API 呼び出し部分をモック化してユニットテストを行うことを推奨します。
- DuckDB を用いた分析・リサーチはデータサイズに対して高速に動作するので、バッチ分析やバックテスト用途に適しています。

---

必要であれば README の英語版、デプロイ手順（systemd / docker / cron など）や推奨構成ファイル（例: .env.example、requirements.txt）も作成します。どの情報を追加したいか指示してください。