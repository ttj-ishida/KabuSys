KabuSys
=======

日本株向け自動売買システム（ライブラリ／実行スクリプト群）
バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買に必要な主要コンポーネントを備えたパッケージです。  
主に以下の機能を提供します。

- 注文実行エンジン（ExecutionEngine）とその周辺ユーティリティ
- モニタリング（System / Trade / Risk）と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定・重み付け・位置サイズ計算）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- AI を使ったニュースセンチメント（OpenAI 経由のスコアリング）
- 設定ウィザードおよび設定検証ツール
- ペーパートレード向け分離（本番 DB と分離されたペーパー DB）
- 運用検証用レポート生成ツール（Paper Trading 検証レポート）

主な特徴
--------
- 環境（KABUSYS_ENV）に応じた振る舞い:
  - development / paper_trading / live
  - paper_trading 時は MockBrokerClient を使用し別 DB（data/paper_trading.db）に記録
- ログは一元管理: コンソール（stdout）＋日次ローテーションファイル（logs/<app>.log）
- モニタリングは独立したプロセスで動作し、停止フラグ（data/stop_requested.flag / data/kill.flag）で制御
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定機能（APIキー必要）
- DuckDB：分析・リサーチ用データ格納（デフォルト data/kabusys.duckdb）
- SQLite：監視・発注ログ保存（デフォルト data/monitoring.db / data/paper_trading.db）

セットアップ手順
---------------
1. Python 環境
   - 推奨: Python 3.9+（使用しているライブラリに依存）
   - 仮想環境を作成・有効化してください（venv / poetry 等）

2. 依存パッケージのインストール
   - requirements.txt がある場合はそれに従ってください（このリポジトリには明示的な requirements が含まれていません）。
   - 少なくとも以下が必要になります:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（設定ファイル検証で任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env の準備
   - 対話式ウィザードで .env を生成／更新できます:
     - python -m kabusys.config_setup
   - 生成後、設定を検証します:
     - python -m kabusys.validate_config
     - 厳密モード（警告も FAIL）: python -m kabusys.validate_config --strict

4. デフォルトディレクトリの作成（必要に応じて）
   - data/ や logs/ は各ユーティリティが自動作成しますが、権限等で作れない場合は事前に作成してください。

主要環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行環境（development | paper_trading | live） default=development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: paper_trading 時の約定振る舞い（instant|partial|never|reject） default=instant
- DUCKDB_PATH: DuckDB ファイルパス default=data/kabusys.duckdb
- SQLITE_PATH: SQLite（監視 DB）パス default=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite パス default=data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） default=INFO
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒） default=60
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1） default=0
- LOG_DIR: ログ保存ディレクトリ（default=logs）

使い方（主なスクリプト）
-----------------------

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に生成／更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告でも exit(1) になります。

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - プロセス優先度を "high" に設定し、ExecutionEngine を別スレッドで動作させます。
  - 停止するには data/stop_requested.flag を作成するか、Execution 側で kill.flag を検知します。

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - デフォルト 60 秒間隔で System / Trade / Risk をチェックします（環境変数 MONITOR_POLL_INTERVAL で上書き可）。
  - monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用します。
  - 監視ループ中に data/stop_requested.flag を検出すると終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。

- AI / リサーチの利用
  - AI ニューススコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn は duckdb.Connection（DuckDBPyConnection）
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 各関数は OpenAI API キー（引数または OPENAI_API_KEY 環境変数）を必要とします。

停止・Kill フラグ
-----------------
- run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag により外部停止できます（作成で停止指示）。
- KillSwitch（監視がトリガーした強制停止）は data/kill.flag を書き込みます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 にしていない限り手動で削除するまで残ります。
- PID ファイル:
  - data/execution.pid（ExecutionEngine の PID を格納する場所）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定読み込みロジック
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前の設定検証ツール
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — Monitoring 起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py             — ニュースを OpenAI で評価して ai_scores に書き込み
  - regime_detector.py      — マーケットレジーム判定
- monitoring/
  - monitoring_db.py        — SQLite テーブル定義 / 永続化層
  - monitoring_engine.py    — マルチモニター束ねコンポーネント
  - system_monitor.py       — システム状態 / データ鮮度監視
  - trade_monitor.py        — 注文滞留／約定異常監視（ファイル内に記載）
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py          — kill.flag 制御
  - alert_manager.py        — 通知ラッパ（LINE 等）
- execution/
  - execution_engine.py     — 実行エンジン本体（EngineConfig など）
  - broker_factory.py       — BrokerClient の生成（実ブローカ or Mock）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py      — Momentum / Value / Volatility 等の計算
  - feature_exploration.py  — IC / forward returns 等
- data/
  - pipeline.py             — prices 等のデータ取得ユーティリティ（参照あり）
  - stats.py                — 正規化ユーティリティ等
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py        — ログ初期化ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity 設定

設定ファイル（外部）
- .env                     — 環境変数（config_setup で生成）
- config/*.yaml            — 各種設定ファイル（system_config.yaml 等）。存在しないと validate_config で警告。

注意事項 / 運用上のヒント
-------------------------
- 本番（KABUSYS_ENV=live）で稼働させる際は特に JQUANTS_REFRESH_TOKEN・KABU_API_PASSWORD・LINE の設定を慎重に確認してください。validate_config は live 時に追加のガードをチェックします。
- .env は絶対にバージョン管理にコミットしないでください（config_setup で生成されるヘッダにも注意喚起あり）。
- AI 機能は OpenAI API を利用します。API レート制限やコストに注意してください。失敗時はフェイルセーフで処理が継続する設計になっていますが、設定と鍵は適切に管理してください。
- ログディレクトリのパーミッション問題等でファイル出力ができない場合、コンソール出力のみで継続します（logging_setup が警告出力）。
- Paper Trading は本番 DB と分離されます。PAPER_TRADING_SQLITE_PATH によりパスを変更可能。

開発者向け
----------
- 単体関数は副作用を持たない純粋関数として実装されている箇所（portfolio.*, research.*）が多く、ユニットテストが書きやすい設計です。
- OpenAI 呼び出しや外部依存はモック差し替えを想定しており、テストで patch して制御できます（例: kabusys.ai.news_nlp._call_openai_api を patch）。

ライセンス / バージョン
-----------------------
- パッケージのバージョンは src/kabusys/__init__.py 内の __version__ を参照してください（本コードベースでは 0.1.0）。

問い合わせ / 追加情報
---------------------
- リポジトリ内の各モジュールには詳細な docstring / コメントが付与されています。必要な機能や拡張点は該当ファイルを参照してください。

以上が README の概要です。必要であれば「導入手順の詳細（requirements.txt、systemd ユニット例、Dockerfile 例）」「config/*.yaml の説明」「各テーブルスキーマ詳細」など追記できます。どの部分を詳しく書きますか？