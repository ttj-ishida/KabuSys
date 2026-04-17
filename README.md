KabuSys — 日本株自動売買システム
================================

これは日本株自動売買システム（KabuSys）のコードベースの簡易 README です。
以下はこのリポジトリの概要、機能、セットアップ・実行方法、ディレクトリ構成の説明です。

プロジェクト概要
----------------
KabuSys は日本株の自動売買フレームワーク（研究・ポートフォリオ構築・発注実行・監視・AI を用いたニュース評価等）です。  
設計方針の特徴：
- DuckDB（分析用）・SQLite（監視／ペーパートレード用）を用いたローカル DB レイヤ
- ペーパートレード（MockBroker）と本番（kabuステーション）を明確に分離
- モジュール分離（portfolio, research, ai, monitoring, execution 等）
- OpenAI を利用したニュースの NLP スコアリングや市場レジーム判定のサポート
- シンプルな Kill Switch / フラグファイルによる外部停止制御

主な機能一覧
-------------
- 環境設定ウィザード（.env の生成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の不足チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード対応）: run_execution.py
  - KABUSYS_ENV=paper_trading の時は専用 SQLite（data/paper_trading.db）を使用
- Monitoring（System / Trade / Risk）ポーリングエンジン: run_monitoring.py、monitoring_engine.py
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視側は環境にかかわらず本番 sqlite_path を使用（監視 DB と発注 DB を分離）
- Portfolio 構築ユーティリティ（候補選定・重み付け・株数計算・セクター制限等）
- Research ツール（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI モジュール
  - news_nlp: raw_news を OpenAI で評価して ai_scores に書き込む
  - regime_detector: マクロセンチメント + ETF MA を合成して market_regime を算出
- ツール: ペーパートレード検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）

セットアップ手順
----------------
前提:
- Python 3.9+ を推奨（明示的なバージョン指定はプロジェクトで管理してください）
- システムに sqlite3 が利用可能（標準）
- 必須 Python パッケージ: duckdb, psutil, openai
- 任意: PyYAML（config/*.yaml の構文チェックに利用）

例（仮想環境・pip 使用）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - （YAML チェックを使うなら）pip install PyYAML

3. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - .env は secrets を含むため Git へコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います

5. DB ファイル & data ディレクトリ
   - デフォルトでは data/ 以下にファイルを作成します（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更

主要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API（必須）
- KABUSYS_ENV: execution のモード（development, paper_trading, live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: 監視ループの秒数（run_monitoring 用）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant | partial | never | reject）

使い方（実行例）
----------------

1) 環境ウィザード（.env 作成）
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict

3) ペーパートレード実行（例）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - ペーパートレード時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用

4) 本番実行（ライブ）
   - KABUSYS_ENV=live python -m kabusys.run_execution
   - 実行時、data/execution.pid に PID を書き込む挙動がある（PID ファイルパスは Settings で指定可）

5) 監視プロセス起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で変更可能（例: MONITOR_POLL_INTERVAL=30）
   - 監視ループは data/stop_requested.flag が存在すると終了します（フラグファイルで停止）

6) Kill Switch（Execution を外部停止）
   - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine 停止を要求します
   - kill.flag をクリアするには KillSwitch.clear() またはファイル削除を行います
   - .env の KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリア（本番では 0 推奨）

7) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定: --from 2026-04-01 --to 2026-04-11
   - DB 指定: --db /path/to/paper_trading.db  または 環境変数 PAPER_TRADING_SQLITE_PATH

注意点 / 運用のヒント
- Monitoring はソース内コメントの通り「監視は本番 sqlite_path を使用」します。監視 DB を本番と分けたい場合は SQLITE_PATH を調整してください。
- run_execution は KABUSYS_ENV により paper_trading 用 DB を切り替えます（本番 DB と分離）。
- OpenAI を利用するモジュール（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。API 呼び出しはリトライロジックを持ちますが、API キー未設定時はエラー／フォールバックの取り扱いに注意してください（関数は例外を投げる場合があります）。
- .env 自動読み込み: config.py はプロジェクトルートを .git または pyproject.toml から検出し、自動で .env / .env.local を読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_FILL_MODE の有効値: instant | partial | never | reject。無効値を設定するとエラーになります。
- ログレベルは LOG_LEVEL で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

主要コマンドまとめ
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ディレクトリ構成
--------------
（リポジトリの src/kabusys 以下を簡略化して示します）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 層
    - monitoring_engine.py    — 各モニタを束ねるエンジン
    - system_monitor.py       — システム / データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常チェック
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — （アラート送信管理: 実装参照）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数計算・スケーリング
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      — ファクター計算（Momentum/Value/Volatility）
    - feature_exploration.py  — 将来リターン・IC・統計
    - __init__.py
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

ライブラリ依存（主なもの）
- duckdb
- psutil
- openai
- PyYAML（任意、validate_config の YAML 構文チェックに使用）

最後に
-----
この README はコードベース内のドキュメント・コメントを基に作成した要約です。運用前に必ず:
- .env を正しく設定し（秘匿情報は安全に管理）、
- python -m kabusys.validate_config でチェックし、
- ペーパートレード環境で十分に検証することを推奨します。

必要ならば、README を拡張してデプロイ手順、 systemd / supervisor のサービス定義例、より詳細な運用手順（ログローテーションやバックアップ方針等）を追記できます。希望があれば追加で作成します。