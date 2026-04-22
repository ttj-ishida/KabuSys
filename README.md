README
======

概要
----
KabuSys は日本株を対象とした自動売買システムの骨格ライブラリです。  
戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（本番 / ペーパートレード）、監視・アラート、AI（ニュースセンチメント・レジーム判定）などの機能をモジュール化して提供します。

主な設計方針
- 本番データベースとペーパートレード DB を分離（ペーパー時は data/paper_trading.db を使用）
- DuckDB を分析用に使用、SQLite を監視 / 発注ログに使用
- 環境変数 / .env による設定管理（対話式ウィザード / 検証ツールあり）
- OpenAI を使った NLP 処理は API キー必須（失敗時は安全側にフォールバック）

機能一覧
--------
- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
  - run_monitoring.py：SystemMonitor のポーリングループを起動（監視ログの永続化）
- 設定管理 / ツール
  - config_setup.py：.env の対話式ウィザード（初期設定）
  - validate_config.py：.env と config/*.yaml の起動前検証ツール
- 監視（monitoring パッケージ）
  - system_monitor.py：システム状態・データ鮮度監視
  - trade_monitor.py（トレード監視、滞留注文など）
  - risk_monitor.py：ドローダウン・ポジション数監視（Kill Switch 連携）
  - monitoring_db.py：監視ログ用 SQLite の永続化レイヤ
  - monitoring_engine.py：各 Monitor を束ねてポーリング、アラート発信
- 発注 / 実行（execution パッケージ）
  - ExecutionEngine、OrderManager、RiskManager、Reconciler、BrokerFactory 等
  - paper_trading に対応（MockBrokerClient + 専用 SQLite）
- ポートフォリオ構築（portfolio パッケージ）
  - 銘柄選定・重み計算（等配分 / スコア配分）
  - セクターキャップ、レジーム乗数、単元株丸め、ポジションサイズ計算
- 研究（research パッケージ）
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns, IC, summary）
- AI（ai パッケージ）
  - news_nlp: raw_news を OpenAI で解析して銘柄ごとのスコアを ai_scores に書き込む
  - regime_detector: ETF（1321）MA 乖離 + マクロニュースで市場レジーム判定
- ツール
  - tools/paper_verification_report.py：ペーパートレード検証レポート生成

セットアップ手順
----------------
前提
- Python 3.9+（ソース内型注釈を利用）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（validate_config の YAML 検証に使用）

インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存をインストール（requirements.txt がある場合はそれを利用）
   - pip install duckdb psutil openai
   - 任意: pip install pyyaml

.env 作成
1. 対話式ウィザードで作成:
   - python -m kabusys.config_setup
   - ウィザードに従って JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等を設定してください。

2. 手動で環境変数を設定する場合は .env に書くか、OS の環境変数として設定できます。
   - 自動 .env 読み込みはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN：J-Quants API 用
- KABU_API_PASSWORD：kabuステーション API パスワード

よく使う設定（デフォルト値）
- KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必要）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動、デフォルト: instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒間隔（run_monitoring で利用、デフォルト: 60）

使い方
------
設定検証
- .env と config/*.yaml を検証:
  - python -m kabusys.validate_config
  - 厳密モード（警告も FAIL）: python -m kabusys.validate_config --strict

ログ設定
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。
- ログレベルは LOG_LEVEL 環境変数で設定可能。

実行（本番 / ペーパー）
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成すると安全に停止します（起動時に停止フラグがあると起動せず終了）。
  - ペーパートレード: KABUSYS_ENV=paper_trading を設定して起動すると MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH に記録されます。

- Monitoring 起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト: 60）。
  - 監視は Settings.sqlite_path を使用してデータを永続化（monitoring は環境にかかわらず 本番 sqlite_path を使用します）。

AI 処理（ニューススコア / レジーム判定）
- news_nlp.score_news を呼ぶには OPENAI_API_KEY が必要です。モジュール API を直接呼ぶ例:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="sk-...")

- regime_detector.score_regime 同様に OPENAI_API_KEY が必要:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="sk-...")

ペーパートレード検証レポート
- tools/paper_verification_report を実行して期間指定でレポートを出力:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト: data/paper_trading.db）。

停止 / Kill Switch
- 監視側が条件を満たすと data/kill.flag を作成して ExecutionEngine に停止シグナルを送る仕組みがあります。
- ExecutionEngine 側は起動時に kill.flag の自動クリアを制御する設定 KILL_FLAG_CLEAR_ON_START（デフォルト 0）を参照します。

ディレクトリ構成
----------------
ルート（省略可能ファイル）
- pyproject.toml, .git/ ...

パッケージ（src/kabusys/）
- __init__.py
- config.py                — 環境変数 / .env 自動読み込みロジックと Settings クラス
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

subpackages
- ai/
  - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
- monitoring/
  - monitoring_db.py       — SQLite スキーマ / ラッパー
  - system_monitor.py      — システム状態監視
  - trade_monitor.py       — 発注ログ監視（滞留注文・約定異常等）※ソースの一部のみ提示
  - risk_monitor.py        — ドローダウン / ポジション数監視
  - kill_switch.py         — kill.flag 書込みユーティリティ
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - alert_manager.py       — アラート送信（LINE 等）※ソース省略あり
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数決定・投下資金制限
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — momentum / value / volatility 計算
  - feature_exploration.py — forward returns, IC, summary
- execution/                — Execution 関連コンポーネント（Engine, BrokerFactory 等）※詳細はソース参照
- utils/
  - logging_setup.py       — ログ設定ユーティリティ（stdout + 日次ローテート）
  - process_priority.py    — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

データ / 動作ファイル（デフォルト）
- data/kabusys.duckdb         — DuckDB（分析用）
- data/monitoring.db          — 監視 SQLite（monitoring）
- data/paper_trading.db       — ペーパートレード SQLite（paper_trading 環境）
- data/execution.pid          — ExecutionEngine の PID ファイル（設定で変更可）
- data/stop_requested.flag    — ローカル停止フラグ（run_execution / run_monitoring が参照）
- data/kill.flag              — Kill Switch が作成する停止フラグ

注意点 / ベストプラクティス
---------------------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live の場合は特に注意（validate_config は live を検出すると警告を出します）。
- OpenAI を使う機能は API コストとレート制限に留意してください。API エラーは多くの箇所でフェイルセーフ（0.0 フォールバックやスキップ）処理されていますが、本番運用では監視・アラートを整備してください。
- run_monitoring は MONITOR_POLL_INTERVAL を環境変数で上書き可能。0 以下など不正値はデフォルト 60 秒にフォールバックします。

お問い合わせ / 開発
-----------------
- 各モジュールはドキュメントストリング・注釈が充実しています。実装変更時は docstring・タイプヒントを更新してください。
- テストや CI を追加する際は .env の自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化して下さい。

以上。README に書かれているコマンドや環境変数を参考に、まずは python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で検証してから各スクリプトを実行してください。