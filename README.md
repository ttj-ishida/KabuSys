KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買／研究プラットフォームです。  
主な目的は「戦略の実装・検証・運用」を安全に行うことで、以下の機能群を備えます。

- ExecutionEngine（発注エンジン）: 本番／ペーパートレード対応の発注処理
- Monitoring（監視）: プロセス・リソース・注文状況・リスクの定期監視、Kill Switch
- Portfolio construction: 候補選定・重み算出・ポジションサイズ計算・セクター制約
- Research: DuckDB を用いたファクター計算・特徴量探索
- AI 機能: ニュースのセンチメント解析（OpenAI API を利用）・市場レジーム判定
- ツール: ペーパートレード検証レポート生成など

主な機能一覧
--------------
- 実行環境分離
  - KABUSYS_ENV による環境切替（development / paper_trading / live）
  - paper_trading モードでは MockBroker を使用し、ペーパートレード用 DB に記録
- 発注制御
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - リスク制限（最大ポジション比率、利用率、ドローダウン等）
- 監視・アラート
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセスの監視
  - TradeMonitor / RiskMonitor: 滞留注文・約定異常・ドローダウン等の検出
  - KillSwitch によるフラグファイル停止機能（data/kill.flag）
- ポートフォリオ構築
  - 候補選定（スコア順）、等比率／スコア比率配分、リスクベースのポジションサイズ計算
  - セクター上限適用、レジーム乗数の適用
- 研究（Research）
  - DuckDB に格納した prices_daily / raw_financials を使ったファクター計算（Momentum/Value/Volatility 等）
  - 将来リターン計算・IC（Information Coefficient）評価・統計サマリー
- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア算出（gpt-4o-mini、JSON Mode 推奨）
  - マクロニュース + ETF MA 乖離を合成した市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレードの稼働率・成立率・レイテンシ等のレポート生成

セットアップ手順
----------------
前提: Python 3.9+ を想定（プロジェクトの pyproject.toml / packaging に依存します）。  
必須の外部パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config ファイルの検証に任意で使用）
（実際の requirements.txt がある場合はそちらを使用してください）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. パッケージインストール（例）
   - pip install duckdb psutil openai pyyaml

3. プロジェクト設定
   - 対話式ウィザードで .env を生成：
     - python -m kabusys.config_setup
     - ウィザードは J-Quants トークンや KABU API パスワード、データベースパス、KABUSYS_ENV などを対話形式で作成します。
   - 設定検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

4. データディレクトリ作成（必要に応じて）
   - デフォルトのデータパスは data/ 以下：
     - SQLite: data/monitoring.db（SQLITE_PATH）
     - DuckDB: data/kabusys.duckdb（DUCKDB_PATH）
     - ペーパー用 SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
   - ログディレクトリ: logs/（LOG_DIR 環境変数で変更可）

主要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時に必要）
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）、デフォルト 60）

使い方（起動・主要コマンド）
---------------------------
- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使いペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - プロセス優先度を高く設定し、PID ファイル（data/execution.pid）を管理します。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境にかかわらず本番の sqlite_path（SQLITE_PATH）を使って監視ログを保存します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 停止は data/stop_requested.flag の作成で行えます（または Ctrl+C）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

停止・Kill Switch
- Kill Switch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（Monitoring 側の KillSwitch が書き込み）。  
- 実行中の監視/エンジンは data/stop_requested.flag の存在を検知して安全に停止します。  
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で可能ですが、本番では推奨されません。

ログ
- 共通のログ設定ユーティリティ（kabusys.utils.logging_setup）を通じてログ出力を統一しています。  
- デフォルトは stdout と logs/<app_name>.log（日次ローテーション、30日保持）。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースツリー（src/kabusys）の主要構成と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数読み込み・Settings クラス（各種設定プロパティ）
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュースセンチメントの OpenAI 呼び出しと DB 書き込みロジック
    - regime_detector.py — ETF MA とマクロニュースで市場レジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化レイヤ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文滞留などの監視: 実装ファイルが存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込み/管理
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - alert_manager.py — （アラート通知管理: 実装ファイルが存在）
    - ...

  - execution/
    - execution_engine.py — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py — Broker クライアントの抽象化（Mock/実ブローカ）
    - reconciler.py
    - risk_manager.py
    - ...

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出・資金配分
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py

  - data/
    - pipeline.py — （データ取り込み/ユーティリティ。get_last_price_date 等を提供）
    - stats.py — z-score 正規化等ユーティリティ
    - ...

  - tools/
    - paper_verification_report.py — ペーパートレード向け検証レポート生成
    - __init__.py

  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

注意事項 / トラブルシューティング
----------------------------------
- OpenAI API を利用する機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。未設定時は明示的に例外を投げます（呼び出し時）。
- DuckDB / SQLite のパスは環境変数で設定できます。デフォルトは data/ 配下です。ディレクトリがない場合は自動作成される箇所もありますが、権限等に注意してください。
- psutil を使ってプロセス優先度や CPU affinity を設定します。権限不足で設定できない場合は警告ログが出ますが動作は継続します。
- run_monitoring/run_execution は stop flag（data/stop_requested.flag）や kill.flag を参照するため、手動で停止したい場合にファイルを作成して制御できます。
- config/*.yaml（system_config.yaml 等）は運用の設定ファイル群です。validate_config はこれらファイルの存在・パースをチェックします（PyYAML がある場合のみ内容の検証を行います）。

開発・拡張のヒント
-------------------
- research モジュールは DuckDB 接続を受け取り SQL を主体に処理する設計です。テストやローカル分析で活用できます。
- AI 呼び出し部分はリトライ・バリデーション・部分書き込みを意識した堅牢な設計になっています。テストでは _call_openai_api をモックしてください。
- logging_setup を使うことで全スクリプトのログ出力が統一されます。ログディレクトリやレベルは環境変数で簡単に切り替えられます。

ライセンス・貢献
----------------
- 本リポジトリのライセンスや貢献方法はプロジェクトルートの LICENSE / CONTRIBUTING に従ってください（存在する場合）。

以上が KabuSys の概要と使い方の基本説明です。具体的な設定値や運用手順は運用環境に合わせて .env / config/*.yaml を調整してください。追加で README に記載したいサンプル .env テンプレートや requirements.txt の生成などを希望される場合はお知らせください。