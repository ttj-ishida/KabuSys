README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。  
主な機能は取引実行エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算・リサーチ、ポートフォリオ構築、ニュース NLP（LLM を用いたセンチメント算出）などを含みます。  
設計方針として「本番 DB とペーパートレードの明確な分離」「ルックアヘッドバイアス防止」「フェイルセーフ（API失敗時はスキップ）」を重視しています。

主な特徴
--------
- ExecutionEngine: 実際の発注またはペーパートレード（KABUSYS_ENV に依存）を実行
- Monitoring: システム状態、注文ログ、リスク指標を定期ポーリングして永続化・アラート発火
- Portfolio モジュール: 候補選定・重み計算・ポジションサイズ算出・セクター制約
- Research モジュール: DuckDB を用いたファクター計算（Momentum / Volatility / Value）や IC 計算等
- AI モジュール: OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）
- ユーティリティ: 設定ウィザード、設定検証、ログ設定、プロセス優先度制御など
- 各種 CLI スクリプト（起動 / 設定 / 検証 / レポート生成）

セットアップ
------------
前提
- Python 3.9+（パッケージの依存に合わせて適宜）
- system パッケージ: duckdb, psutil, openai（AI 機能を使う場合）, PyYAML（config 検証で任意）など

推奨手順（ローカル開発）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（プロジェクトルートに配置）。例:
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も致命的に扱いたい場合は --strict を付ける

デフォルトのファイル・ディレクトリ
- DuckDB: data/kabusys.duckdb （環境変数 DUCKDB_PATH で変更可）
- SQLite (監視 DB): data/monitoring.db （SQLITE_PATH）
- Paper trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- ログ: logs/<app_name>.log（LOG_DIR 環境変数で変更可）
- Kill / Stop フラグ:
  - data/kill.flag — Kill Switch（ExecutionEngine に停止を促す）
  - data/stop_requested.flag — 各起動スクリプトの停止フラグ（存在でループ停止）

環境変数（主なもの）
-------------------
必須（起動前に設定）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

運用に関する主な設定
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
  - paper_trading: MockBroker を使用し Paper DB (PAPER_TRADING_SQLITE_PATH) に記録
  - live: 本番発注
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能（ニュース NLP / レジーム判定）で使用
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動でクリアする（0/1）

使い方（コマンド例）
-------------------
設定・検証
- .env 作成（対話式）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

起動
- 監視ループを起動（デフォルト: ポーリング 60 秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  補足:
  - monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視ログを記録します。
  - data/stop_requested.flag が作成されるとループが終了します。

- ExecutionEngine を起動
  python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録（本番 DB と分離）
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します
  - 実行中は data/execution.pid に PID を書きます。停止は stop flag を作成するか engine.stop() により制御されます
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を消します（本番では注意）

ユーティリティ / レポート
- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数も有効）

プログラム API（ライブラリとしての利用）
- 研究用・バッチ処理などはモジュールを直接呼べます。例:
  from kabusys.research import calc_momentum
  from kabusys.ai import score_news  # OpenAI API キーが必要

運用上の注意
------------
- 本番モード（KABUSYS_ENV=live）では設定・キーの管理に注意してください（validate_config はいくつかのガードを表示します）。
- kill.flag（KILL フラグ）や stop_requested.flag の扱いに注意。KILL_FLAG_CLEAR_ON_START=1 は本番で誤作動の原因になり得ます。
- ログは logs/ に日次ローテーションで保存され、デフォルトで 30 日分保持します（LOG_DIR 環境変数で変更可）。
- AI（OpenAI）を利用する機能は API 利用料がかかります。API の失敗時はフェイルセーフでスコア 0 を使う等の実装になっていますが、運用方針はあらかじめ決めてください。

ディレクトリ構成
---------------
（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py                        -- パッケージ定義
- config.py                          -- 環境変数 / 設定読み込み
- config_setup.py                    -- .env 対話ウィザード
- validate_config.py                 -- 設定検証 CLI

- run_execution.py                   -- ExecutionEngine 起動スクリプト
- run_monitoring.py                  -- Monitoring ポーリング起動スクリプト

- utils/
  - logging_setup.py                 -- ログ設定ユーティリティ
  - process_priority.py              -- プロセス優先度 / CPU affinity 設定

- monitoring/
  - monitoring_db.py                 -- SQLite 永続化（監視用）
  - system_monitor.py                -- システム状態 / データ鮮度監視
  - trade_monitor.py                  -- （注文ログ監視等）
  - risk_monitor.py                  -- ドローダウン / ポジション上限監視
  - monitoring_engine.py             -- 各 Monitor を束ねる
  - kill_switch.py                    -- kill.flag 書き込みユーティリティ
  - alert_manager.py                  -- （通知管理: LINE 等）

- execution/
  - execution_engine.py              -- 実行エンジン本体
  - broker_factory.py                -- ブローカークライアント生成（Mock含む）
  - order_manager.py                 -- 注文管理
  - order_repository.py              -- DB への注文ログ保存
  - reconciler.py                    -- ブローカー状態と DB を突合

- portfolio/
  - portfolio_builder.py             -- 候補選定・重みづけ
  - position_sizing.py               -- 株数算出・資金制約反映
  - risk_adjustment.py               -- セクターキャップ・レジーム乗数

- research/
  - factor_research.py               -- Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py           -- IC/統計サマリ等

- ai/
  - news_nlp.py                      -- ニュース NLP によるセンチメント算出（OpenAI 使用）
  - regime_detector.py               -- MA + マクロ NLP を用いたレジーム判定

- tools/
  - paper_verification_report.py     -- ペーパートレード検証レポート

ライセンス・貢献
----------------
本 README はコードベースに基づく利用説明です。実プロジェクトで利用する際はライセンス表記、開発ルール、CI/デプロイ手順等を追加してください。

補足
----
- ここに記載のコマンドはパッケージが src 配下にあり importable な状態（PYTHONPATH が通っている or pip install -e . された状態）を想定しています。開発環境で直接実行する際はプロジェクトルートから python -m kabusys.<module> で起動してください。
- 追加の設定ファイル（config/*.yaml）は validate_config により存在チェック／パースチェックを行えます。PyYAML がない場合は YAML チェックはスキップされ、警告が出ます。

質問や README の補足（設定項目の詳細説明や実行例の追加）が必要であれば教えてください。