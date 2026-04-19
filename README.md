KabuSys — 日本株自動売買システム（README）
======================================

概要
---
KabuSys は日本株向けの自動売買プラットフォーム向けに設計された Python 製ライブラリ／実行フレームワークです。本コードベースは以下の主要機能を備えます。

- 発注エンジン（ExecutionEngine）とその運用周辺（OrderManager / RiskManager / Reconciler）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- AI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI API 統合）
- ペーパートレード検証レポート生成ツール
- .env 対話ウィザード / 設定検証 CLI / DB 初期化とマイグレーションサポート

主な特徴
---
- 環境（development / paper_trading / live）に応じた動作分離（ペーパートレード用 DB は本番と分離）
- 監視側から Execution を停止する Kill Switch（flag ファイルベース）
- DuckDB を使った調査・分析パイプライン、SQLite を監視・トレードログ用に使用
- OpenAI（gpt-4o-mini）を用いたニュース NLP とレジーム判定（フェイルセーフ実装）
- ロギングは統一的にセットアップ（コンソール + 日次ローテーションファイル）

前提・依存
---
推奨: Python 3.10+
主な依存ライブラリ（requirements.txt が無い場合は個別にインストール）:
- duckdb
- psutil
- openai
- PyYAML（config 検証で利用）
- （必要に応じて）requests 等

セットアップ手順
---
1. リポジトリをクローンして仮想環境を作成・有効化
   - 例:
     python -m venv .venv
     source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例（最低限のパッケージ）:
     pip install duckdb psutil openai PyYAML

   - 実際にはプロジェクトに requirements.txt があれば:
     pip install -r requirements.txt

3. 必要ディレクトリを作成
   - data/ と logs/ を作成しておくと安全:
     mkdir -p data logs

4. .env の初期作成
   - 対話式ウィザードで .env を作成・更新できます:
     python -m kabusys.config_setup
   - ウィザード終了後、設定検証を実行:
     python -m kabusys.validate_config
     - --strict を付けると警告も FAIL 扱いになります。

5. DB 初期化
   - monitoring 用 SQLite（デフォルト: data/monitoring.db）は実行時に自動作成・マイグレーションされます（init_monitoring_db）。
   - Paper Trading を使う場合、PAPER_TRADING_SQLITE_PATH を指定できます（デフォルト: data/paper_trading.db）。

主要環境変数（抜粋）
---
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant / partial / never / reject）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時必須）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒。run_monitoring のデフォルトは 60 秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

使い方（実行例）
---
- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 or ペーパートレードは KABUSYS_ENV で切替）
  python -m kabusys.run_execution

  補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます（本番 DB と分離）。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します。
  - Execution は起動時に data/execution.pid を作成します（PID ファイル）。

- 監視ループを起動
  python -m kabusys.run_monitoring

  補足:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番 sqlite_path を参照してログを残します（環境に依らず同じ monitoring DB を使う設計）。
  - 監視から KillSwitch がトリガーされると data/kill.flag が作成され、ExecutionEngine の停止を促します。

- Paper Trading 検証レポート（ツール）
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

- AI によるニューススコアリング（ライブラリ呼び出し）
  - OpenAI API キーを設定した上で、プログラムから呼び出します:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

  - 市場レジーム評価:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

ログ
---
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日保持）。
- setup_logging() により stdout（コンソール）とファイル出力の両方にログが出ます。
- app_name は各起動スクリプトで "execution" / "monitoring" 等に設定されています。

停止・Kill スイッチ
---
- 実行停止フラグ:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループは検知して停止します（安全な手動停止）。
- Kill Switch:
  - 監視側（KillSwitch）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促す仕組みです。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します（誤って自動クリアされると危険）。

DB とマイグレーション
---
- 監視 DB 初期化: init_monitoring_db(conn) がテーブル作成・マイグレーションを行います。起動時に自動実行されます。
- Paper Trading DB は settings.is_paper の場合に paper_sqlite_path を使用します（本番監視 DB と隔離）。
- DuckDB は時系列データやリサーチ用の分析に利用します（DUCKDB_PATH）。

ディレクトリ構成（抜粋）
---
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 自動ロード処理、Settings クラス
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

- execution/                — 発注エンジン周辺（OrderManager 等）
- monitoring/
  - monitoring_db.py        — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py      — momentum / volatility / value 等
  - feature_exploration.py  — forward returns / IC 等
- ai/
  - news_nlp.py             — ニュース NLP スコアリング（OpenAI 統合）
  - regime_detector.py      — 市場レジーム判定
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

（上記は抜粋です。実際のサブモジュールはさらに細分化されています。）

開発メモ / 注意点
---
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きあり）。
- OpenAI を使う処理は API の失敗をフェイルセーフに扱う実装になっていますが、API キー管理は慎重に。
- run_monitoring はデフォルトで本番の monitoring DB を参照します（監視は環境に関わらず本番 DB を使う仕様）。
- プロセス優先度設定（set_process_priority）と PID 管理はプラットフォーム差分に対応していますが、権限の問題で設定に失敗することがあります（警告ログが出ます）。

補足（よく使うコマンドまとめ）
---
- .env の作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行:
  python -m kabusys.run_execution
  python -m kabusys.run_monitoring

- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- ライブラリ的な利用:
  from kabusys.research import calc_momentum
  from kabusys.ai import score_news

ライセンス・連絡
---
プロジェクトのライセンスやメンテナー情報はリポジトリルートの LICENSE / CONTRIBUTING を参照してください。

以上。README に不足している項目（例: 実際の requirements.txt、より詳しい ExecutionEngine の使い方、alert_manager の外部通知設定等）があれば、その部分を指定してください。必要に応じて追加のドキュメント（起動フロー図や設定例）を作成します。