KabuSys
=======

日本株向けの自動売買／リサーチ基盤のサンプル実装です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、LLM を使ったニュース NLP / レジーム判定など、売買システムに必要な主要コンポーネント群を含みます。

主な特徴
--------
- 発注エンジン（ExecutionEngine）
  - 本番（kabuステーション）・ペーパートレード（MockBrokerClient）を切り替え可能
  - 注文管理・リスク管理・約定再突合などの仕組みを備える
- 監視（Monitoring）
  - システム稼働状況、データ鮮度、滞留注文、ドローダウン監視
  - Kill Switch（条件に応じて data/kill.flag を書いて ExecutionEngine を停止）
  - 日次ロギング / SQLite に監視ログを保存
- ポートフォリオ構築ライブラリ
  - 候補選定、等分配・スコア加重、リスク調整（セクター上限、レジーム乗数）、株数決定（単元丸め・集約キャップ）
- リサーチ
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value など）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）連携
  - ニュース記事のセンチメント集約（news_nlp）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（regime_detector）
  - API エラー時のリトライやフェイルセーフ実装
- ツール
  - ペーパートレード検証レポート生成スクリプト（tools.paper_verification_report）
- ユーティリティ
  - 一貫したログ設定（logs/<app>.log、日次ローテーション）
  - プロセス優先度・CPU アフィニティ設定ユーティリティ
  - .env 対話ウィザードと設定検証 CLI

セットアップ手順
----------------
1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境を作成して有効化する例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール
   - 必須:
     - duckdb, psutil, openai
   - 任意（設定検証時の YAML 検証）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

   （このリポジトリに requirements.txt が無い場合は上のパッケージを手動で用意してください）

3. 環境変数の準備
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - あるいは .env を直接作成して以下の主要キーを設定してください（最低限必須）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
     - PAPER_FILL_MODE（instant | partial | never | reject）（ペーパートレードの約定挙動）

   - 注意: .env は絶対にリポジトリにコミットしないでください。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ等の作成
   - 通常は起動時に必要なディレクトリ（data/, logs/）を自動作成しますが、権限などで失敗する場合があるため事前に作ると安心:
     - mkdir -p data logs

使い方
------
- 環境セットアップ（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告を強制的に FAIL として扱う

- 監視サービス起動
  - 簡易起動:
    - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可（デフォルト 60）
    - 監視は本番用 sqlite_path を使用（KABUSYS_ENV に依存せず monitoring DB は同一）

- 発注エンジン（Execution）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録して本番 DB と分離
    - 起動前に data/stop_requested.flag が存在する場合は起動をスキップ
    - Execution は data/execution.pid に PID を書く（PID ファイルパスは Settings で変更可）

- Kill Switch / 停止フラグ
  - KillSwitch は監視から条件を満たすと data/kill.flag を書き込み、Execution 起動時や実行中のエンジンに停止を促します
  - 実行中の Engine を強制停止させたい場合は data/stop_requested.flag を作成するか、kill.flag を利用する設計です（各スクリプトで参照されるフラグが若干異なります）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能
  - OpenAI を使う機能（ニュースセンチメント / レジーム判定）を呼ぶ際は OPENAI_API_KEY を設定してください
  - API 呼び出しは各関数（kabusys.ai.news_nlp.score_news / kabusys.ai.regime_detector.score_regime）経由で行います

主要環境変数（まとめ）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 重要・よく使う:
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレード時の fill 動作（instant/partial/never/reject）
  - KILL_FLAG_CLEAR_ON_START: "1" にすると Execution 起動時に kill.flag を自動クリア（本番では推奨しない）

ディレクトリ構成（抜粋）
----------------------
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス：環境変数読み込み・検証、自動 .env ロード機能
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 時は MockBrokerClient）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システムリソース・プロセス PID・データ鮮度の監視
    - trade_monitor.py — （コードベースに含まれる想定モジュール）滞留注文等の検出
    - risk_monitor.py — ドローダウン、ポジション上限の監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信の抽象）
  - execution/
    - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等（起動スクリプトから利用）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数決定・集約キャップ・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等の計算（DuckDB 経由）
    - feature_exploration.py — forward returns / IC / summary 等
  - ai/
    - news_nlp.py — ニュース集約 → OpenAI でセンチメント → ai_scores へ保存
    - regime_detector.py — ETF MA + マクロニュースでレジーム判定（OpenAI使用）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

補足／設計上の注意
-----------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）をベースに行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリが作成できない場合はコンソール出力のみになります。
- AI 呼び出し部分はリトライや JSON バリデーションを行い、部分失敗時にも他のデータを保護する実装になっています。API キーは環境変数または明示的引数で渡してください。
- 本番（KABUSYS_ENV=live）での実運用はリスクが伴うため、必ず設定検証と十分なテストを実施してください。validate_config の live 向けガードや KILL_FLAG_CLEAR_ON_START のチェックを参照してください。

開発・拡張
-----------
- DuckDB 上のテーブル（prices_daily / raw_financials / raw_news / ai_scores 等）を用いて、研究モジュールや AI モジュールは外部通信なしで再現性ある計算が可能です。
- Execution / Broker クライアントの実装は抽象化されており、BrokerClientFactory を拡張して新しいブローカーを追加できます。
- モニタリングルールやアラート送信先は alert_manager を実装することでプラグインできます。

ライセンスや貢献指針は本リポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（無ければプロジェクト管理者に問い合わせてください）。

以上。セットアップや運用で不明点があれば、どの機能について知りたいかを教えてください。追加でサンプル .env テンプレートや起動例を記載します。