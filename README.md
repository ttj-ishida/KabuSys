# KabuSys

日本株向けの自動売買システム（ライブラリ／実行スクリプト群）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / インストール
- セットアップ手順（.env 作成、検証）
- 実行方法（主要スクリプト）
- 環境変数（主要項目）
- 使い方（ユースケース別）
- ディレクトリ構成（主要ファイル説明）
- 補足（ログ・停止フラグ等）

---

プロジェクト概要
----------------
KabuSys は日本株自動売買システムのコードベースです。  
主な機能は以下の通りです。

- 戦略のためのファクター計算（モメンタム/バリュー/ボラティリティ等）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 実行エンジン（ExecutionEngine）とブローカークライアント（本番 / ペーパートレード分離）
- 監視モジュール（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ニュース NLP（OpenAI を用いた銘柄・マクロのセンチメント評価）
- Paper Trading 向けの検証レポート出力ツール
- Logging / プロセス優先度など運用ユーティリティ

設計方針の一部:
- DuckDB / SQLite をローカル DB として利用（分析・監視）
- Paper trading と live は DB を分離（安全）
- ルックアヘッドバイアスを避ける設計（外部時刻参照に注意）
- フェイルセーフ設計（API失敗時はスキップ or デフォルト値で継続）

主な機能一覧
-------------
- 環境設定ウィザード（kabusys.config_setup.run_wizard）
- 設定検証 CLI（kabusys.validate_config）
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録
- 監視エンジン起動スクリプト（run_monitoring.py）
  - ポーリングで System/Trade/Risk をチェックしアラート・Kill Switch を評価
  - ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
- Portfolio モジュール（選定・重み・位置サイズ・リスク調整）
- Research モジュール（ファクター計算、IC 等）
- AI モジュール
  - news_nlp: ニュースから銘柄ごとにセンチメントを算出し ai_scores テーブルへ書込
  - regime_detector: マクロ＋MA により市場レジームを判定し market_regime に保存
- tools/paper_verification_report.py: ペーパートレード DB に対する検証レポート生成

前提条件 / インストール
-----------------------
推奨 Python バージョン: 3.10+

必須（主要）ライブラリ（プロジェクトに合わせてインストールしてください）:
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config YAML の検証を行う場合）
- (標準ライブラリ) sqlite3, logging, argparse, threading 等

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

もし requirements.txt がプロジェクトルートにあれば:
```bash
pip install -r requirements.txt
```

セットアップ手順
----------------

1. プロジェクトルートへ移動（.git / pyproject.toml を基準に自動でルート検出します）
2. .env を作成する（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV 等を尋ねます。

3. 設定検証
   ```bash
   python -m kabusys.validate_config
   ```
   --strict オプションを付けると警告も失敗扱いにできます:
   ```bash
   python -m kabusys.validate_config --strict
   ```

4. DB 用ディレクトリの作成（.env の DUCKDB_PATH / SQLITE_PATH 等に合わせて）
   - run_* スクリプトはログディレクトリ (logs/) や data/ を自動作成しますが、権限や配置を確認してください。

主要な環境変数
----------------
（.env へセットする主要なキー）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合必須)
- KABUSYS_ENV (development / paper_trading / live) — デフォルト development
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数; デフォルト 60)
- PAPER_FILL_MODE (paper_trading 時の約定挙動: instant|partial|never|reject)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート通知用、任意)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag をクリアするか。0/1。production は 0 推奨)

使い方（代表的なコマンド）
------------------------

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（本番/ペーパー設定は KABUSYS_ENV で制御）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、Paper DB（data/paper_trading.db）へ書き込みます。
  - 起動前に data/kill.flag が立っていると起動せず終了します（安全機構）。

- Monitoring 起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒）。
  - 監視は本番 sqlite_path を常に使用します（環境に依らず）。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  --db オプションで DB パスを指定できる。指定なければ PAPER_TRADING_SQLITE_PATH または data/paper_trading.db を参照。

- AI 機能（ライブラリとして呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  ※ 直接 CLI は提供していないため、別スクリプトから呼び出すか、ExecutionEngine 内で利用されます。

停止・Kill Switch / 停止フラグ
------------------------------
- kill.flag（デフォルト: data/kill.flag）
  - KillSwitch により書き込まれ、ExecutionEngine に停止シグナルを送ります。
  - run_execution は起動時に kill.flag の存在を確認し、存在すれば起動しません（安全）。
  - KillSwitch.evaluate() は drawdown や position limit 等の条件で kill.flag を書き込みます。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアしますが、本番では 0 を推奨します。

- stop_requested.flag（run_monitoring/run_execution が参照）
  - 監視スクリプト・実行スクリプトは data/stop_requested.flag 等を確認して安全にシャットダウンします。

ログ
----
- ログは logs/<app_name>.log（TimedRotatingFileHandler, 日次ローテーション, 30日保持）とコンソールに出力されます。
- logging 設定は kabusys.utils.logging_setup.setup_logging で統一管理されています。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主なモジュールと役割（抜粋）です:

- __init__.py
  - パッケージ定義、__version__ 等

- config.py
  - 環境変数読み込み・Settings クラス（.env 自動ロード、必須チェック等）

- config_setup.py
  - .env の対話式生成ウィザード

- validate_config.py
  - .env と config/*.yaml の整合性チェック CLI

- run_execution.py
  - ExecutionEngine の起動スクリプト（本番 / paper_trading 切替、PID / 停止フラグ処理）

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL で制御）

- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス稼働チェック
  - risk_monitor.py: ドローダウン・ポジション数監視
  - trade_monitor.py: （発注状態監視: 滞留注文・約定異常など）
  - monitoring_engine.py: 各モニタを束ねるループ
  - kill_switch.py: kill.flag の書き込み管理
  - alert_manager.py: アラート送信用（LINE など。実装箇所を参照）

- execution/
  - ExecutionEngine 等、OrderManager・RiskManager・Reconciler 周りの実装（ブローカー連携、発注管理等）
  - broker_factory.py: ブローカークライアントの生成（Mock / 本番）

- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 発注株数計算（ロット丸め・スケールダウンロジック含む）
  - risk_adjustment.py: セクター上限・レジーム乗数

- research/
  - factor_research.py: ファクター計算（momentum/value/volatility）
  - feature_exploration.py: 前方リターン / IC / 統計サマリ
  - __init__.py: 外部公開 API

- ai/
  - news_nlp.py: ニュース記事の LLM センチメント集計・ai_scores 書込
  - regime_detector.py: マクロ＋MA による market regime 判定

- tools/
  - paper_verification_report.py: Paper Trading 検証レポート生成スクリプト

補足・運用メモ
--------------
- Paper Trading と Live はデータベースを分離しておく設計です（安全性確保）。
- AI（OpenAI）を利用する機能は API キーが必要です。失敗時は保守的なデフォルトで処理を継続する実装になっていますが、キーの管理には注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（setup_logging の挙動）。
- process_priority.set_process_priority("high") が起動時に呼ばれます。環境によっては権限不足で失敗する場合があります（警告ログに留まります）。
- DuckDB/SQLite のファイルパスとアクセス権を事前に確認してください。

お問い合わせ / 開発ノート
-----------------------
この README は現状のソースコードから生成した概要ドキュメントです。  
詳細な設計（PortfolioConstruction.md / StrategyModel.md 等）がリポジトリにあればそちらも参照してください。

必要であれば、README にサンプル .env のテンプレートや起動 & 実行ログ例、CI 用コマンド等を追記できます。ご希望があれば追記内容を教えてください。