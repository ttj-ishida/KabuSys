README
=====

概要
----
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。  
売買実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算 / 特徴量探索）、AI を使ったニュース NLP / レジーム判定、各種ユーティリティを含みます。  
設計方針としては「本番 DB とペーパートレードを明確に分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時は安全側フォールバック）」を重視しています。

主な機能
--------
- ExecutionEngine: 発注処理・注文管理・リスク管理・照合（reconciler）
  - KABUSYS_ENV=paper_trading 時は MockBroker を用いペーパートレード用 DB に記録
- Monitoring: システム稼働・データ鮮度・注文ログ・リスク（ドローダウン／ポジション上限）監視
  - kill.flag による安全停止、stop_requested.flag によるループ停止等の仕組み
- Portfolio construction: 候補選定、重み計算、ポジションサイズ計算、セクター制約・レジーム乗数
- Research: DuckDB を用いたファクター計算（Momentum / Volatility / Value）と特徴量解析（forward returns, IC, summary）
- AI ユーティリティ:
  - news_nlp: OpenAI（gpt-4o-mini 等）でニュースをスコアリングし ai_scores に保存
  - regime_detector: MA200 乖離 と マクロニュースの LLM スコアを合成して market_regime を決定
- ユーティリティ:
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成スクリプト（tools.paper_verification_report）
  - ロギングセットアップ・プロセス優先度設定ユーティリティなど

動作要件（概略）
----------------
- Python 3.9+（ソースは型注釈を利用）
- 主要外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config/*.yaml の内容検証を行う場合に任意で利用）
- OS: Linux / macOS / Windows（プロセス優先度・CPU affinity はプラットフォーム依存で限定的に対応）

セットアップ手順
----------------
1. リポジトリをクローンしてワークツリーへ移動
   - 例: git clone ... && cd <project-root>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （OpenAI を使わないなら openai は不要、YAML 検証をしないなら PyYAML は不要）

4. 環境変数の初期化（.env）
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
     - これによりプロジェクトルートに .env が作成／更新されます（.env は絶対に Git に入れないでください）
   - 必要な主要環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - .env を直接編集する場合は .env.example を参考にしてください（存在する場合）。

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も含めて厳密に確認したい場合:
     - python -m kabusys.validate_config --strict

基本的な使い方
--------------
- 実行（Production / Paper の違い）
  - ExecutionEngine を起動:
    - 本番相当: KABUSYS_ENV=live python -m kabusys.run_execution
    - ペーパートレード: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      - paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
  - Monitoring を起動:
    - python -m kabusys.run_monitoring
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
    - run_monitoring は常に本番用の sqlite_path を参照（監視ログは共有 DB）
  - Paper Trading 検証レポート:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を使う代替）

- AI 機能（ニュース NLP / レジーム判定）
  - news_nlp.score_news, ai.regime_detector.score_regime を利用する関数群があります。
  - 実行には OPENAI_API_KEY の設定が必要です（引数で直接キーを渡すことも可）。
  - API 呼び出しはエクスポネンシャルバックオフ・部分失敗耐性を持ちます。

停止・制御フラグ
----------------
- data/stop_requested.flag
  - run_monitoring と run_execution の起動ループでは stop_requested.flag を確認します。ファイルを作ることでループの終了を促進できます（daemon やテスト用）。
- Kill Switch（data/kill.flag）
  - 監視からの評価（ドローダウンやポジション上限など）により KillSwitch がトリガーされると data/kill.flag に理由を書き込み、ExecutionEngine に停止指示を与えます。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

ログ
---
- ログは kabusys.utils.logging_setup.setup_logging を通して設定されます。
  - コンソール出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）をサポート
  - デフォルトのログディレクトリは logs/
  - LOG_LEVEL 環境変数でログレベルを調整可能

主要コマンド例
--------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視ループ（ポーリング）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主なモジュールと用途です（省略あり）。

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数 / .env 読み込み・バリデーション
  - config_setup.py
    - .env の対話式生成ウィザード
  - validate_config.py
    - 起動前の環境・ファイル検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV による動作分岐）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で調整可）
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
    - 発注フローとリスク管理の実装（注: MockBroker を含む）
  - monitoring/
    - monitoring_db.py: SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py: CPU/メモリ/ディスク/データ鮮度 / 実行プロセス監視
    - trade_monitor.py: 注文滞留や約定の異常検知（コードを参照）
    - risk_monitor.py: ドローダウン / ポジション上限監視
    - kill_switch.py: kill.flag 書き込みロジック
    - monitoring_engine.py: 各モニタの統合ポーリング
    - alert_manager.py: （アラート送信の抽象化）
  - portfolio/
    - portfolio_builder.py: 候補選定・重み付け
    - position_sizing.py: 発注株数計算（lot rounding / aggregate cap）
    - risk_adjustment.py: セクターキャップ / レジーム乗数
  - research/
    - factor_research.py: Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py: forward returns / IC / summary
  - ai/
    - news_nlp.py: ニュースの LLM スコアリング（ai_scores への書き込み）
    - regime_detector.py: MA200 と LLM を組み合わせたレジーム判定
  - data/ (実行時に生成されることが多い)
    - monitoring.db（SQLITE_PATH デフォルト）
    - paper_trading.db（ペーパートレード）
    - kabusys.duckdb（DUCKDB_PATH デフォルト）
    - execution.pid / kill.flag / stop_requested.flag
  - tools/
    - paper_verification_report.py: ペーパートレード検証用レポート生成

注意事項 / 運用上のヒント
-----------------------
- .env は機密情報（API トークン等）を含むため絶対にリポジトリにコミットしないでください。
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知などのアラート設定を事前に確認してください（validate_config がライブ用の追加チェックを行います）。
- OpenAI API を使う処理は API 料金やレート制限に注意してください。APIキーは安全に保管してください。
- ログディレクトリ作成に失敗した場合は標準出力のみで継続する設計です（推奨は logs ディレクトリを作成しておくこと）。
- run_execution/run_monitoring は stop_requested.flag を見て安全に停止できます。運用スクリプトや systemd からはこのフラグの管理を行うと安全です。

ライセンス / 責務
-----------------
- 本プロジェクトはサンプル実装／学習用のコードを想定しています。実際の証券取引システムとして用いる場合は、追加の検証・監査・法的確認が必要です。

---

この README はコードベースの主要機能・運用方法の要約です。より詳細な動作やパラメータについては各モジュール（src/kabusys 以下）の docstring と実装を参照してください。必要であれば、各コンポーネント（ExecutionEngine、Monitoring、AI モジュール等）ごとの詳細ドキュメントも作成します。