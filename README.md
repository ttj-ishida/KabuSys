README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を目的とした Python パッケージです。本リポジトリには取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（LLM を使ったセンチメント評価）などのモジュールが含まれています。設計方針として、本番 DB とペーパートレード DB の分離、ログの統一管理、LLM 呼び出しのリトライ・フェイルセーフが盛り込まれています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（Mock）を切替可能
  - リスク管理（Position limit / Drawdown 等）
  - 注文履歴の永続化（SQLite）
- Monitoring（監視）
  - システムリソース監視（CPU/メモリ/ディスク）
  - 発注・約定ログ監視（滞留注文や異常約定検出）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（条件成立で ExecutionEngine に停止シグナル）
- ポートフォリオ構築
  - 候補選定・重み計算（等金額 / スコア加重）
  - セクター上限の適用、レジーム乗数
  - ポジションサイズ計算（単元考慮、利用可能現金でのスケール）
- Research / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Spearman）や統計サマリ
- AI（LLM）連携
  - news_nlp: ニュース記事を集約して OpenAI API で銘柄別センチメントを算出・保存
  - regime_detector: ETF の MA200 等とマクロニュースで市場レジーム判定
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 起動前チェック（validate_config）
  - Paper Trading 検証レポート生成ツール

前提条件
--------
- Python 3.10 以上（型ヒントの | 演算子等を使用）
- 必要な主要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
- SQLite / DuckDB（ファイルベース。サーバ不要）
- （任意）PyYAML は config/*.yaml の構文チェックで使用されますが必須ではありません。

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （必要に応じて）pip install pyyaml

   ※ requirements.txt が無い場合は上記を手動でインストールしてください。

4. 初期設定（.env 作成）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 作成後に設定検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告をエラー扱いにできます。

5. ディレクトリ / ファイルの確認
   - デフォルトで使用されるファイル / ディレクトリ:
     - data/monitoring.db（SQLite、監視ログ）
     - data/paper_trading.db（PAPER_TRADING mode 用 SQLite）
     - data/kabusys.duckdb（DuckDB 分析 DB）
     - logs/（ログファイル）
     - data/execution.pid（ExecutionEngine PID）
     - data/kill.flag（Kill Switch トリガファイル）
     - data/stop_requested.flag（監視・実行の停止フラグ）
   - 必要に応じて手動で data/ や logs/ を作成してください（起動時に自動作成される場合もあります）。

使い方（起動例）
----------------

- ExecutionEngine（発注エンジン）起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV 環境変数で指定
    - KABUSYS_ENV=development（開発）
    - KABUSYS_ENV=paper_trading（ペーパートレード。MockBroker を使用し data/paper_trading.db を利用）
    - KABUSYS_ENV=live（本番）
  - 起動コマンド:
    - python -m kabusys.run_execution
  - 停止方法:
    - 実行中に data/stop_requested.flag を作成すると安全に終了します（監視からも検出されます）。
    - Kill Switch が発動すると data/kill.flag が書き込まれ、ExecutionEngine に停止シグナルが送られます。

- Monitoring（監視）起動
  - ポーリングループで各種チェックを実施します。
  - 起動コマンド:
    - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（デフォルト 60 秒）
  - 監視は Settings に依存し、monitoring は環境にかかわらず本番 sqlite_path を使用します（デフォルト data/monitoring.db）。

- .env ウィザード / 設定検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - 実行例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能。

注意すべき環境変数（主要）
--------------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1。live では 0 推奨）

実装上の挙動・運用ポイント
-------------------------
- ログ: kabusys.utils.logging_setup.setup_logging により stdout + 日次ローテートファイル（logs/<app>.log）に出力します。
- DB マイグレーション: monitoring_db.init_monitoring_db はテーブル作成と簡易マイグレーション（カラム追加）を行います。冪等化されています。
- プロセス優先度: 起動時に set_process_priority("high") を呼び出します（権限がない場合は警告）。
- Kill Switch: RiskMonitor の判定で KillSwitch が作動すると data/kill.flag に理由を書き込みます。Execution 起動時はこのフラグを検知して終了する挙動が組み込まれています。
- ペーパートレード: KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、本番 DB と完全に分離された paper_trading.db に記録されます。

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動ロード・Settings クラス
  - config_setup.py           — .env 対話式ウィザード（cli）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - broker_factory.py
    - execution_engine.py
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
  - data/
    - pipeline.py
    - stats.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

サンプル運用フロー
------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定を検証（python -m kabusys.validate_config）
3. 分析用 DB を準備（prices_daily / raw_news 等の投入は DuckDB 側）
4. 監視プロセスをデーモン化して起動（python -m kabusys.run_monitoring）
5. ExecutionEngine を起動（python -m kabusys.run_execution）
6. 定期的に Paper Trading レポートを生成し評価（tools/paper_verification_report）

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

補足
----
- YAML の構文チェックを利用する場合は PyYAML をインストールしてください。インストールされていない場合 validate_config は YAML チェックをスキップして警告を出します。
- OpenAI API を使用する機能は API キーが必須です。通信エラーやレート制限はリトライロジックで緩和されますが、運用では適切なキーとレート管理を行ってください。
- 本 README はコードベースの主要な挙動と運用のポイントをまとめたものです。より詳細な設計や仕様はソースコード内の docstring / コメントを参照してください。

お問い合わせ / 開発
-------------------
- 開発時の設定読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

以上。