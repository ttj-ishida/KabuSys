README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースのシステムです。
コードベースは以下の主要機能群で構成され、プロダクション/ペーパートレードの両モードに対応します。

- 注文発行・約定管理（ExecutionEngine）
- システム・注文・リスク監視（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ）
- ファクター計算・特徴量探索（Research）
- ニュースの NLP スコアリング・レジーム判定（AI）
- 各種ユーティリティ（ログ設定・プロセス優先度など）
- 運用支援ツール（.env ウィザード、設定検証、レポート生成）

主な特徴
--------
- 本番・ペーパートレードの明確な分離（PAPER_TRADING_SQLITE_PATH 等）
- DuckDB を使った分析用データアクセス（prices_daily / raw_financials 等を想定）
- OpenAI を利用したニュースセンチメント（gpt-4o-mini を想定）
- 監視ループと Kill Switch（flag ファイル）による安全停止
- ログはコンソールと日次ローテートファイルに出力（logs/<app>.log）
- 設定ウィザードと起動前の検証ツールを含む

前提条件
--------
- Python 3.10 以上（PEP604 の型記法などを使用）
- 主要 Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML （config YAML 検証が必要な場合）
- SQLite は標準ライブラリで使用可能

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - プロジェクトルートは .git または pyproject.toml を目印に自動判定します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数ファイル (.env) の作成
   - 対話式ウィザード: python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 本番で OpenAI を使う場合は OPENAI_API_KEY を環境に設定してください（ウィザードでは OpenAI は必須項目ではありません）。
   - 生成後に python -m kabusys.validate_config で設定を検証してください。

5. ディレクトリ作成（必要に応じて）
   - data/ （DB・PID・flag 保存）
   - logs/（ログ出力）
   ほとんどは起動時に自動作成されますが、権限・パスの事前確認を推奨します。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD （必須）
- KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY （AI 機能利用時）
- KABUSYS_ENV （development / paper_trading / live。デフォルト: development）
- PAPER_FILL_MODE （paper_trading の約定挙動: instant|partial|never|reject。デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH （ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
- SQLITE_PATH （監視 DB、デフォルト: data/monitoring.db）
- LOG_LEVEL （DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR （ログ保存先、デフォルト: logs/）
- MONITOR_POLL_INTERVAL （監視ポーリング間隔（秒）、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START （起動時に kill.flag を自動クリアするか 1/0。production では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH （PID / Kill flag のパスを上書き可能）

使い方（起動例）
----------------

1) ExecutionEngine の起動
- 本番（KABUSYS_ENV=live）や通常動作:
  - export KABUSYS_ENV=live
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成すると起動ループは安全に停止します。
  - ExecutionEngine は pid ファイル（data/execution.pid 等）を生成します。

- ペーパートレード:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
  - paper_trading モードでは MockBrokerClient を利用し、データは data/paper_trading.db に記録され本番 DB と分離されます。

2) Monitoring の起動
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます。例:
  - export MONITOR_POLL_INTERVAL=30

3) 設定検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱いになります（exit code 1）。

4) .env の対話式作成
- python -m kabusys.config_setup

5) ペーパートレード検証レポート生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB パスは data/paper_trading.db。--db で上書き可能。

6) AI / レジーム判定・ニューススコア（プログラム呼び出し）
- AI 機能（news_nlp.score_news, regime_detector.score_regime）は Python API として提供されています。OpenAI キーが必要です。
  例（対話的に実行する場合）:
    from kabusys.ai.news_nlp import score_news
    # duckdb 接続を作り、target_date を指定して呼び出す

シャットダウン・Kill Switch
-------------------------
- システム監視・Kill Switch:
  - kill.flag（デフォルト: data/kill.flag）を書き込むことで ExecutionEngine に停止を促す設計です（KillSwitch モジュール）。
  - KillSwitch はドローダウン・ポジション上限等の条件でフラグを書き込みます。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされます（本番では推奨されません）。
- stop_requested.flag:
  - run_monitoring / run_execution のループは data/stop_requested.flag の存在を監視して安全停止します（運用側の停止用）。

ログ
---
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます。
- ログローテーションは日次（TimedRotatingFileHandler）で過去 30 日分を保持します。
- LOG_DIR 環境変数でログ出力先を変更できます。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースツリー（src/kabusys）内の主要なパッケージと役割の概観です。

- src/kabusys/
  - __init__.py                     — パッケージ定義（バージョン等）
  - config.py                       — 環境変数/.env のロード・Settings
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 起動前の設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py                   — ニュースを OpenAI でスコアリングして ai_scores に書き込むロジック
    - regime_detector.py            — マクロニュース + ETF MA で市場レジーム判定

  - monitoring/
    - monitoring_db.py              — SQLite ベースの監視 DB（スキーマ定義・永続化）
    - system_monitor.py             — システム状態・データ鮮度チェック
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - kill_switch.py                — Kill Switch 実装（flag ファイル生成）
    - monitoring_engine.py          — 各モニタを束ねるポーリングエンジン
    - （trade_monitor / alert_manager 等が連携）

  - execution/
    - execution_engine.py           — 実際の注文セッション実行ロジック（Engine）
    - broker_factory.py             — ブローカークライアント生成（Mock / 実環境切替）
    - order_manager.py, order_repository.py, risk_manager.py, reconciler.py
                                     — 発注管理・永続化・リスク管理等

  - portfolio/
    - portfolio_builder.py          — 候補選定・スコア順ソート
    - position_sizing.py            — 発注株数計算・資金配分ロジック
    - risk_adjustment.py            — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py            — モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
    - feature_exploration.py        — 将来リターン計算・IC 等の統計解析

  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成

  - utils/
    - logging_setup.py              — ログ設定ユーティリティ
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
    - （その他ユーティリティ群）

注意点 / 運用上のヒント
---------------------
- 本番モード（KABUSYS_ENV=live）では Kill Switch の設定や LINE 通知等の外部通知設定を十分確認してください。
- OpenAI 呼び出しは課金対象であり、API キーの管理・レート制限の考慮が必要です。rate limit や transient error に対しては実装側でリトライロジックがありますが、運用監視は必須です。
- DuckDB / SQLite ファイルは適切なバックアップ・ディスク容量監視を行ってください（設定でパスを変更可能）。
- ログディレクトリや data ディレクトリのパーミッションに注意してください。ファイル作成に失敗すると一部機能が無効化されます（ログファイル出力など）。

ライセンス・貢献
----------------
（リポジトリに LICENSE があればここに記載してください）

以上がこのコードベースの概要・セットアップ・基本的な使い方と構成です。必要であれば、各モジュール（ExecutionEngine の起動フロー、AI スコアリングの詳しい使い方、ポートフォリオ構築フロー等）について個別に詳細ドキュメントを作成します。どの部分のドキュメントがほしいか教えてください。