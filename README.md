README — KabuSys
=================

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・検証ツール群）です。  
主な目的は、ファクター計算・ポートフォリオ構築ロジック、発注エンジン（ExecutionEngine）、監視基盤（MonitoringEngine）および検証ツールを提供することです。  
DB は SQLite（監視・paper trading 等）と DuckDB（価格データ・リサーチ用途）を使用し、一部機能は OpenAI API を用いたニュース NLP / レジーム判定をサポートします。

主な特徴（機能一覧）
------------------
- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - Settings クラスで環境変数を一元管理
- 発注実行（Execution）
  - ExecutionEngine 起動スクリプト（run_execution）
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し本番 DB と分離（data/paper_trading.db）
  - 再起動時のリコンシリエーション（Reconciler）
  - OrderManager / OrderRepository による注文状態管理
  - リスク管理（RiskManager）
- 監視（Monitoring）
  - SystemMonitor（CPU/メモリ/ディスク、プロセス死活、データ鮮度）
  - TradeMonitor（滞留注文、約定異常チェック）
  - RiskMonitor（ドローダウン、ポジション上限等）
  - KillSwitch（フラグファイルによる ExecutionEngine 停止トリガ）
  - AlertManager（LINE Push によるアラート送信）
  - 継続実行用スクリプト（run_monitoring）
  - Streamlit ベースの監視ダッシュボード
  - 監視ログ永続化レイヤ（SQLite 用の monitoring_db）
- ポートフォリオ構築
  - 候補選定、等配分 / スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、資金制約対応）
- リサーチ / ファクター解析
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン（forward returns）、IC（Information Coefficient）等の統計ツール
- AI（OpenAI）
  - ニューステキストから銘柄別センチメントを算出（news_nlp）
  - ETF + マクロニュースを組み合わせた市場レジーム判定（regime_detector）
  - 両関数は API キーを要求し、失敗時は安全側にフォールバックする設計
- ツール
  - paper_verification_report: Paper Trading 実行結果の検証レポート生成

動作環境・依存ライブラリ（代表）
--------------------------------
- Python 3.9+（typing / modern 機能を利用）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- 標準ライブラリ: sqlite3, logging, argparse, datetime 等

セットアップ手順
----------------
1. リポジトリをチェックアウト
   - git clone <repo> && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix/macOS) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール
   - 推奨: requirements.txt を用意している場合は:
     - pip install -r requirements.txt
   - 主要パッケージ手動インストール例:
     - pip install duckdb psutil requests openai streamlit

4. 環境変数を準備
   - プロジェクトルートに .env / .env.local を置くことで自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 主要な環境変数（下記「環境変数」節を参照）を設定

5. データディレクトリを作成
   - デフォルト DB 等は data/ 以下を参照します:
     - mkdir -p data

6. DB 初期化は多くの場合自動的に行われます（init_monitoring_db が必要テーブルを作成）。DuckDB のテーブル等は別途データ投入が必要です。

主要な環境変数（Settings に基づく）
-------------------------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE push）用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のモック約定モード（instant | partial | never | reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 閾値（Monitoring 用）
- KABUSYS_ENV: 起動環境（development | paper_trading | live、デフォルト: development）
  - paper_trading を指定すると run_execution は MockBroker を使い PAPER_TRADING_SQLITE_PATH を使用
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）

使い方（起動・主なコマンド）
--------------------------

1) ExecutionEngine を起動（本番 / paper_trading）
   - デフォルト（環境変数に応じて本番 or paper）
     - python -m kabusys.run_execution
   - Paper trading 実行例:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - 備考: 起動時にプロセス優先度を high に設定します。paper_trading は本番 DB と分離され data/paper_trading.db を使用します。

2) Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
   - 重要: run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番 sqlite_path）を使います（監視ログは本番 DB に記録される仕様）

3) Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ブラウザで監視サマリ・ポジション・トレード履歴・最新システム状態等を確認できます（read-only モードで接続）

4) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD, --to YYYY-MM-DD（期間指定）
     - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
   - 出力: 稼働率・注文成功率・送信率・レイテンシ等のサマリと PASS/FAIL 判定

5) AI（ニューススコア / レジーム）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と target_date（date）を与えて銘柄別センチメントを ai_scores テーブルへ書き込む
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - ETF ma200 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込む
   - 両方とも OPENAI_API_KEY が必要。API 失敗時は安全側フォールバック（0.0 等）で例外を上位に波及させない設計が基本

注意事項 / 運用メモ
-------------------
- .env の自動読み込み
  - プロジェクトルートは __file__ の親を辿って .git か pyproject.toml を基準に判定します。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 監視 DB 初期化
  - init_monitoring_db() が呼ばれると必要なテーブルとインデックスを冪等的に作成します（マイグレーション処理も一部含む）
- kill.flag
  - KillSwitch が問題検出時に KILL_FLAG_PATH（デフォルト data/kill.flag）を作成します。ExecutionEngine はこのフラグを検出して安全にシャットダウンする運用を想定しています。flag の手動クリアは KillSwitch.clear() または該当ファイルを削除してください。
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用します。Mock の挙動は PAPER_FILL_MODE で制御され、DB は PAPER_TRADING_SQLITE_PATH に書き込みます（本番 DB と分離）。
- ロギング
  - 簡易に logging.basicConfig(level=logging.INFO) が使用されています。LOG_LEVEL を環境変数で調整してください。
- 権限関連
  - set_process_priority で優先度変更を試みますが、権限不足時は警告ログを出してスキップします。CPU affinity の設定も同様です。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数/Settings 管理（.env 自動読み込み含む）
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 結果検証レポート
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP（OpenAI） -> ai_scores 書き込み
  - regime_detector.py      — 市場レジーム判定（ETF MA + マクロニュース）
- monitoring/
  - __init__.py
  - monitoring_db.py        — SQLite 永続化レイヤ（テーブル作成 / CRUD）
  - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py        — 滞留注文 / 約定異常検出
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py          — kill.flag 書き込みロジック
  - alert_manager.py        — LINE Push 通知
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py  — Streamlit ベースの監視ダッシュボード
- portfolio/
  - __init__.py
  - portfolio_builder.py    — 候補選定 / 重み計算
  - position_sizing.py      — 株数算出 / 単元丸め / 集約キャップ
  - risk_adjustment.py      — セクターキャップ / レジーム乗数
- research/
  - __init__.py
  - factor_research.py      — Momentum / Volatility / Value 等の計算（DuckDB）
  - feature_exploration.py  — 将来リターン / IC / 統計サマリ
- execution/
  - order_manager.py        — 発注フロー / ステートマシンの外向きAPI
  - reconciler.py           — 起動時リコンシリエーション
  - （その他: broker_factory, order_repository, order_record 等はコードベースに含まれる想定）
- utils/
  - __init__.py
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
- research, data, strategy など（プロジェクト全体としてのモジュール群）

トラブルシューティング（よくある事例）
--------------------------------------
- DB が開けない / 権限エラー
  - data/ ディレクトリの存在とファイルパーミッションを確認
- OpenAI 呼び出しエラー
  - OPENAI_API_KEY が設定されているか、API 利用制限（レート）やネットワークを確認
- LINE 通知が送れない
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID を確認、LINE API のレスポンスコードをログで確認
- プロセス優先度設定失敗
  - 権限不足の可能性（root / 管理者権限が必要な操作があるためログに警告が出る）

最後に
-----
この README はリポジトリ内のソースコード（config / monitoring / execution / portfolio / research / ai 等）に基づいて作成しています。詳細な設計仕様（例: PortfolioConstruction.md, StrategyModel.md 等）が別途ある場合はそちらも参照してください。必要であれば、セットアップ用の requirements.txt やデプロイ手順（systemd ユニットファイル例など）も追記できます。要望があれば追加します。