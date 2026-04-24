README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコアライブラリ群です。
主な責務は以下のとおりです。

- 発注エンジン（ExecutionEngine）と監視（Monitoring）を起動・運用するスクリプト
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- AI を使ったニュースセンチメント評価 / レジーム判定（OpenAI API）
- 監視用 DB（SQLite）および監視ロジック（リスク・トレード・システム監視）
- 開発補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

機能一覧
--------
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading DB に記録
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視ログを収集し、必要時 Alert / Kill Switch を発動

- 設定管理
  - config_setup.py: 対話式ウィザードで .env を生成 / 更新
  - validate_config.py: .env と config/*.yaml の簡易検証 CLI

- モジュール（抜粋）
  - portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター上限・レジーム乗数
  - research: DuckDB 上で動くファクター計算（momentum, volatility, value）と特徴量解析（forward returns, IC 等）
  - ai: ニュース NLP（OpenAI を使った銘柄センチメント scoring）とレジーム判定
  - monitoring: 監視 DB（SQLite）への永続化、SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - tools: ペーパートレード検証レポート生成スクリプト

- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテートファイル）
  - process_priority: プラットフォームに依存しないプロセス優先度設定（high/normal/low）

セットアップ手順
--------------
1. リポジトリをクローンする:
   - git clone <リポジトリURL>
   - cd <プロジェクトルート>

2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows (cmd): .venv\Scripts\activate.bat

3. 依存パッケージをインストール:
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要なランタイム依存:
     - duckdb, psutil, openai, PyYAML（設定検証のため）など
     - 例: pip install duckdb psutil openai PyYAML

4. .env の作成:
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で .env を作成
   - 自動読み込み: プロジェクトルートに .env / .env.local があると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

5. 設定の検証:
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたい場合は --strict を付ける

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI モジュール使用時に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading の MockBroker 動作: instant | partial | never | reject、デフォルト: instant）

使い方
------
1) 実行（ExecutionEngine）
- 通常起動（本番/テストは KABUSYS_ENV に依存）:
  - python -m kabusys.run_execution
- ペーパートレードで起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレードはデフォルトで data/paper_trading.db を使用して本番 DB と分離します

- 停止方法:
  - 監視スクリプトや手動により data/stop_requested.flag を作成すると、実行ループが停止します
  - Kill Switch（自動停止）は data/kill.flag を書き込み、ExecutionEngine に停止信号を与えます（Settings.kill_flag_path で変更可）

2) 監視（Monitoring）
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例えば 30秒: MONITOR_POLL_INTERVAL=30）
  - 監視は環境にかかわらず本番の sqlite_path を使用する設計（監視ログは共通 DB）

3) 設定ウィザード / 検証
- python -m kabusys.config_setup
- python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで exit code 1

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パスは 環境変数 PAPER_TRADING_SQLITE_PATH / data/paper_trading.db

5) AI/Research モジュール利用
- AI 機能（ニュース NLP / レジーム判定）は OpenAI API キーが必要です（OPENAI_API_KEY）
- 例: kabusys.ai.score_news を呼び出して DuckDB 接続と日付を与える（本 README は API 使用例のコードレベル説明を省略）

ログ
---
- 共通的なログ設定: kabusys.utils.logging_setup.setup_logging を利用
- デフォルト: stdout に加え logs/<app_name>.log に日次ローテーションで保存（logs ディレクトリ）
- app_name 例: "execution", "monitoring"（この値は各起動スクリプトで設定）

停止・Kill 手順のまとめ
--------------------
- シンプルな停止（全プロセスの監視ループを対象）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループを止めます
- 自動停止（リスク等のため ExecutionEngine を止めたい）:
  - KillSwitch が条件を満たすと data/kill.flag を書き込みます（Settings.kill_flag_path）
  - ExecutionEngine は起動時に kill.flag をクリアするオプション（KILL_FLAG_CLEAR_ON_START=1）がありますが、本番では 0 を推奨

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュースセンチメントスコア（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ / ラッパー
    - system_monitor.py
    - trade_monitor.py         — （トレード監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （アラート管理）
  - utils/
    - logging_setup.py
    - process_priority.py
  - portfolio, research, ai, monitoring の他多数のモジュール

注意事項・運用上のポイント
-----------------------
- .env は決してリポジトリにコミットしないでください（config_setup でもその旨を表示）
- 本番環境で KABUSYS_ENV=live を使用する場合、LINE アラート等の設定を必ず確認してください
- OpenAI API を使う機能はネットワーク/レート制限/レスポンス不整合に対して堅牢化（リトライやフェイルセーフ）されていますが、API キーの管理は厳重に行ってください
- DuckDB は分析用のローカル DB として設計されています。prices_daily / raw_financials 等のテーブルを前提とした処理が多いです
- process_priority が最初に high に設定されます（psutil を利用）。権限不足で失敗する場合は警告が出ますが動作自体は継続します

開発者向け
----------
- 単体関数は極力副作用を持たない純粋関数として実装されている箇所が多い（portfolio モジュールなど）。ユニットテストが書きやすい設計です
- DuckDB 接続を渡して SQL を実行する形で研究系のコードが分離されています
- テストでは環境変数自動ロードを無効にするために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用できます
- OpenAI への呼び出しをテストで差し替えるために、適所で _call_openai_api をパッチする設計になっています

ライセンス・バージョン
--------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）
- ライセンス情報やその他メタデータはプロジェクトルートの README / LICENSE / pyproject.toml を参照してください（存在する場合）

サンプルコマンド一覧
-------------------
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレードレポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

さらに質問があれば、どの機能について README を拡充すべきか（例: 起動オプション詳細、DB スキーマ、サンプル .env、テスト手順 等）を教えてください。必要に応じて追記します。