README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のサンプル実装です。  
主要な機能群（発注エンジン、監視、ポートフォリオ構築、ファクター計算、AI を用いたニュース評価など）がモジュール化されており、本番（live） / ペーパートレード（paper_trading） / 開発（development）を環境切替で扱えます。

主な設計方針
- 環境変数（.env）により設定を管理。プロジェクトルートの .env / .env.local を自動読み込み（必要に応じて無効化可）。
- 発注ロジックと監視は別プロセスで実行。監視から停止フラグを書き込む Kill Switch を備え、安全停止をサポート。
- Paper Trading は本番 DB と分離（data/paper_trading.db を使用）。
- DuckDB を分析用に、SQLite を監視 / 履歴用に使用。
- OpenAI（gpt-4o-mini）をニュース NLP / レジーム判定に利用可能（API キー必須）。

機能一覧
--------
- ExecutionEngine 起動 / 発注管理（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によりブローカークライアントを抽象化
  - RiskManager / OrderManager / Reconciler 連携
- Monitoring（run_monitoring.py、monitoring エンジン）
  - SystemMonitor（CPU/メモリ/ディスク/プロセス生存 / データ鮮度）
  - TradeMonitor（滞留注文・約定異常などの検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（data/kill.flag による安全停止）
  - AlertManager 経由の通知（LINE トークン未設定でも動作）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等加重／スコア加重、ポジションサイズ計算、セクター上限、レジーム乗数
- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー のファクター計算（DuckDB）
  - 将来リターン計算、IC（Spearman）などの分析ユーティリティ
- AI（kabusys.ai）
  - news_nlp: ニュースを LLM でセンチメント評価し ai_scores へ書き込み
  - regime_detector: ETF（1321）MA + マクロ記事センチメントで市場レジーム判定
- 開発ユーティリティ
  - 環境設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）
- ログ共通設定（kabusys.utils.logging_setup）
  - stdout と日次ローテートファイルへ出力

前提条件
--------
- Python 3.9+
- 必要な Python パッケージ（代表例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML の検証を行う場合）
- データディレクトリ（data/）とログディレクトリ（logs/）への書き込み権限

セットアップ手順
--------------
1. リポジトリをクローンし、Python 仮想環境を作成／有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （開発時）pip install PyYAML

3. ディレクトリ作成（必要なら）
   - mkdir -p data logs

4. .env の作成（ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくはプロジェクトルートに手動で .env を作成

5. 設定の検証
   - python -m kabusys.validate_config
   - 問題があれば .env や config/*.yaml を修正
   - --strict を付けると警告も失敗扱いになる: python -m kabusys.validate_config --strict

代表的な環境変数（重要なもの）
--------------------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合の API キー
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- PID_FILE_PATH: execution.pid のパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。不正値はデフォルトにフォールバック。

使い方（起動とコマンド）
------------------------
- 環境構築済みで .env を設定済みであることを前提。

1) ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し data/paper_trading.db に記録（本番 DB と分離）
     - 実行中は data/execution.pid に PID を書き込む
     - data/stop_requested.flag が存在すると起動を拒否 / 実行中は停止を要求

2) Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）
     - 監視プロセスは監視用 SQLite（settings.sqlite_path）を使用。run_monitoring は環境にかかわらず production sqlite_path を使う（監視 DB は本番を参照）
     - 監視は SystemMonitor / TradeMonitor / RiskMonitor を使って各種判定を行い、必要に応じて kill.flag を書き込む

3) .env の初期作成（ウィザード）
   - python -m kabusys.config_setup

4) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになる

5) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

停止方法・Kill Switch
---------------------
- 実行中の ExecutionEngine を監視側から停止するためのフラグ:
  - data/kill.flag を書き込むと ExecutionEngine 側で検知して停止する（KillSwitch が書き込む）
  - KillSwitch は RiskMonitor の判定（例: DRAWDOWN、POSITION_LIMIT）から発動する
- 手動で強制停止したい場合:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring は起動しないか実行中に停止処理を行う
  - 実行中のプロセスは PID ファイル（data/execution.pid）を確認して適切に停止する

ログ
----
- ログはデフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテート）へ出力
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理
- LOG_DIR 環境変数でログディレクトリを変更可能

開発者向け / テスト向けユーティリティ
-------------------------------------
- MonitoringEngine.run_once(): 1回だけ各 Monitor を実行（テスト用）
- SystemMonitor.check_once(...), RiskMonitor.check_once(...): 単体実行・単体テストが容易
- AI モジュールの OpenAI 呼び出しは内部関数を patch / mock してユニットテスト可能
- config._find_project_root() は __file__ を基点にプロジェクトルートを探索するため、パッケージ化後も安定

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数/設定読み込み
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor 起動スクリプト

サブパッケージと主なモジュール:
- ai/
  - news_nlp.py                 — ニュース NLP（OpenAI 利用）
  - regime_detector.py          — 市場レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py            — SQLite 用永続化層
  - monitoring_engine.py        — 各 Monitor のオーケストレータ
  - system_monitor.py           — CPU/メモリ/ディスク/データ鮮度監視
  - risk_monitor.py             — ドローダウン / ポジション上限監視
  - kill_switch.py              — kill.flag 操作ユーティリティ
- portfolio/
  - portfolio_builder.py        — 候補選定 / 重み計算
  - position_sizing.py          — 株数決定・丸め・キャップ
  - risk_adjustment.py          — セクター上限・レジーム乗数
- research/
  - factor_research.py          — Momentum/Value/Volatility 計算（DuckDB）
  - feature_exploration.py      — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py            — ロギング共通設定
  - process_priority.py         — プロセス優先度・CPU affinity 設定

その他トップレベル（実行時生成）
- data/                         — デフォルト DB・PID・フラグ等（例: monitoring.db, paper_trading.db, execution.pid, kill.flag, stop_requested.flag）
- logs/                         — ログファイル（例: logs/execution.log, logs/monitoring.log）

注意事項 / 運用ヒント
--------------------
- run_monitoring は「監視プロセス」であり、監視用 SQLite（SQLITE_PATH）を参照します。run_monitoring は KABUSYS_ENV に関わらず監視 DB（settings.sqlite_path）を使用する点に注意してください。
- run_execution は KABUSYS_ENV=paper_trading の場合、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- OpenAI を有効にする場合、API キーは安全に管理してください（.env を Git 管理しないこと）。
- ログディレクトリ作成や DB 接続に失敗した場合、ログはコンソールのみになる設計です（設計上のフォールバックあり）。
- 本番環境（KABUSYS_ENV=live）での起動は十分なテスト・設定確認の上で行ってください（validate_config の警告に注意）。

ライセンス / 著作権
------------------
（この README では省略）プロジェクト内 LICENSE や pyproject.toml に従ってください。

補足
----
- README に記載していない内部実装の詳細は各モジュールの docstring を参照してください。モジュール内部にはログ出力や入力検証、DB マイグレーションなど運用を考慮した注釈が多く含まれています。