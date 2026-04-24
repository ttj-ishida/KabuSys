README
=====

概要
----
KabuSys は日本株向けの自動売買・研究・監視フレームワークです。本リポジトリは以下の主要コンポーネントを含みます。

- ExecutionEngine: ブローカークライアント経由で発注を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働状況・注文状態・リスクをポーリングして永続化・アラート出力する監視基盤
- Portfolio モジュール: 候補選定、配分計算、リスク調整、ポジションサイズ計算
- Research モジュール: ファクター計算、特徴量探索、IC 計算など DuckDB ベースの分析ユーティリティ
- AI モジュール: OpenAI を用いたニュースセンチメント / レジーム判定支援
- CLI ツール: .env 対話ウィザード、設定検証、Paper Trading 検証レポート生成 など

特徴
----
- 本番・ペーパートレードの分離: KABUSYS_ENV により paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用
- DuckDB を使った分析向けデータレイク（デフォルト: data/kabusys.duckdb）
- 監視ログは SQLite（data/monitoring.db）に永続化
- OpenAI を利用したニュース NLP（gpt-4o-mini を想定）により銘柄別センチメントを生成
- Monitor による Kill Switch（data/kill.flag）で実行エンジンの安全停止
- ログは daily ローテーション（logs/<app>.log）で保存

前提 / 依存
------------
- Python 3.10 以降（型ヒントの構文を使用）
- 必要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML をパースする場合に必要）
- SQLite は標準ライブラリで利用可能

詳細はプロジェクトの requirements.txt を用意している場合はそちらを参照してください（本コードスニペットには requirements.txt が含まれていません）。

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （必要に応じて他の依存を追加）

4. .env 設定
   - 対話式ウィザードを使って初期 .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動で .env を作成
   - 自動で .env を読み込む仕組み（.env / .env.local）を持ちます。自動ロードは
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用トークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: 実行環境 ('development' | 'paper_trading' | 'live')（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- OPENAI_API_KEY: OpenAI を使う機能（ニュース NLP / レジーム判定）で必要
- LOG_LEVEL: ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60） — run_monitoring で参照
- PAPER_FILL_MODE: ペーパートレードでのフィルモード ('instant' | 'partial' | 'never' | 'reject')

使い方（主なコマンド）
---------------------

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します
    - 起動時に data/stop_requested.flag が立っている場合は起動せず終了
    - 実行中は data/execution.pid に PID を書く（設定によりパスは変更可能）
    - 停止は monitoring 側の kill.flag によるシグナルや stop flag により行います

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒、デフォルト 60）
    - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用して監視ログを永続化
    - stop flag（data/stop_requested.flag）を検知すると安全停止

- .env 対話式ウィザード
  - python -m kabusys.config_setup
  - .env を初期作成・更新するためのインタラクティブツール

- 設定検証 CLI
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --db PATH でデータベースパスを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

運用・開発メモ
--------------
- ロギング:
  - 共通ユーティリティ kabusys.utils.logging_setup.setup_logging() を使って、コンソール（stdout）と logs/<app>.log（日次ローテーション）に出力します
- Stop / Kill フラグ:
  - run_* スクリプトは data/stop_requested.flag（停止要求フラグ）を参照して自己停止します
  - Monitoring の KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（存在チェック・クリア機能あり）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアします（本番では注意）
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等でテーブル作成を行い、既存 DB に必要カラムがない場合は ALTER TABLE による簡易マイグレーションを実施します
- AI 機能:
  - kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime は OpenAI API キーを必要とします（OPENAI_API_KEY または引数で渡す）
  - API 呼び出しはリトライ・バリデーション・スコアクリップ等の保護ロジックを備えています
- Paper検証基準:
  - paper_verification_report には稼働率・注文成功率・送信率・P95 レイテンシ等の閾値が組み込まれています。詳細はツール内の定数を参照してください。

ディレクトリ構成
----------------
（主要ファイル、抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・重み計算
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - position_sizing.py           — 株数決定・スケーリング（lot_size 対応）
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py       — 将来リターン・IC・統計サマリー
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py           — マクロ + ETF MA200 による市場レジーム判定（OpenAI 併用）
  - monitoring/
    - monitoring_db.py             — 監視用 SQLite 永続化層 + MonitoringDB クラス
    - monitoring_engine.py         — 複数 Monitor の束ね・通知・kill 評価
    - system_monitor.py            — システムリソース・データ鮮度の監視
    - trade_monitor.py             — （コードスニペット上は省略）注文滞留・約定異常検出
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 書込みロジック
    - alert_manager.py             — （省略）LINE 等への通知管理
  - utils/
    - __init__.py
    - logging_setup.py             — ログ初期化ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/                          — デフォルトのデータ・DB 保存先（実行時に生成）
  - config/                        — config/*.yaml（system_config, strategy, risk, ...）

補足
----
- validate_config.py で設定チェックを行い、必須環境変数や config/*.yaml の存在・パース検証が可能です。運用前に必ず実行してください。
- 本コードは設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に依存する実装方針を含んでいます。戦略やリスクパラメータの調整は該当ドキュメントに従って行ってください。
- 本 README はコードベースから抽出した情報に基づく概要です。詳しいパラメータや内部仕様は各モジュールのドキュメント文字列（docstring）を参照してください。

ライセンス / 貢献
-----------------
- 備考: ライセンス情報や貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING ファイルを参照してください（このスニペットには含まれていません）。

お問い合わせ
-----------
- 開発・運用に関する質問はリポジトリの issue を利用するか、プロジェクトの運用担当者へお問い合わせください。