README
======

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。  
主な機能は以下のとおりです。

- 発注エンジン（ExecutionEngine）: 本番 / ペーパートレーディングを切り替え可能
- 監視（Monitoring）: システム稼働状況・データ鮮度・取引状況・リスク指標の定期チェック
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイジング、セクター制約など
- リサーチ: ファクター計算（Momentum / Value / Volatility 等）、特徴量探索（IC 等）
- AI 補助: ニュースの NLP スコアリング（OpenAI）・市場レジーム判定
- 運用ユーティリティ: .env ウィザード、設定検証、ペーパートレード検証レポート等

特徴
----
- 設定は .env / 環境変数で管理（自動ロード機能あり）
- DuckDB（分析用）と SQLite（監視 / 発注ログ）を併用
- ペーパートレードは本番 DB と完全分離（デフォルト: data/paper_trading.db）
- ログはコンソール + 日次ローテーション（logs/<app>.log）
- OpenAI を用いた NLP 処理は失敗に寛容なフォールバック実装（リトライ・部分書き込み等）

セットアップ
------------
1. Python 環境
   - Python 3.10+ を推奨
2. 依存パッケージ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config/*.yaml の内容を検証する場合）
   例: pip install duckdb psutil openai PyYAML
3. リポジトリルートに移動して .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 既存の .env がある場合、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
4. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   - --strict を付けると WARNING も失敗扱いで exit(1) になります
5. データ / ログ用ディレクトリ
   - デフォルトで data/ と logs/ を利用します。起動時に自動作成される場合があります。

主要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード DB、デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能を使う場合に必要)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動でクリアするか、0/1)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト 60)
- PAPER_FILL_MODE (paper_trading の MockBroker 挙動: instant|partial|never|reject)

使い方
------

1. 設定作成と検証
   - .env の作成（対話式）
     python -m kabusys.config_setup
   - 設定検証
     python -m kabusys.validate_config
     （--strict を指定すると警告が FAIL 扱い）

2. 監視プロセス起動
   - デフォルトでは MONITOR_POLL_INTERVAL=60 秒でポーリングします。環境変数で上書き可。
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 終了方法:
     - Ctrl+C（KeyboardInterrupt）
     - またはルートプロジェクトの data/stop_requested.flag を作成すると安全に停止します（スクリプトはこのファイルを監視しているため）。

3. 実行（Execution）プロセス起動
   - 本番 / ペーパートレードは KABUSYS_ENV で切替。
     - ペーパートレード例:
       KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - 本番例:
       KABUSYS_ENV=live python -m kabusys.run_execution
   - 実行時の挙動:
     - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へログを残します。
     - 起動前に data/stop_requested.flag が存在すると起動を中止します。
     - 実行中に同ファイルを作成するとエンジンは停止します。
     - kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は KillSwitch による強制停止シグナル（ExecutionEngine を止めるために監視側が書き込む）。

4. Paper Trading 検証レポート
   - ペーパートレード DB をもとに期間指定で検証レポートを出力します。
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を直接指定:
     python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI 機能
   - ニュース NLP（銘柄別センチメント）:
     - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
     - 要 OPENAI_API_KEY（引数または環境変数）
   - 市場レジーム判定:
     - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - 同じく OPENAI_API_KEY が必要

ログ
----
- デフォルト: logs/<app_name>.log（日次ローテーション、30 日分保持）
- setup_logging() を全スクリプトが呼び出します（app_name に "monitoring" / "execution" 等を指定）。
- コンソール出力は stdout（stderr ではない）に送られます。

停止 / Kill スイッチ
-------------------
- stop_requested.flag (data/stop_requested.flag)
  - run_monitoring/run_execution の起動ループはこのファイルの存在を監視しており、あれば安全に終了します（オペレーショナルな停止用）。
- kill.flag (Settings.kill_flag_path、デフォルト data/kill.flag)
  - KillSwitch が書き込むと ExecutionEngine に対する停止命令として機能します。Execution 側は起動時に kill.flag をクリアするオプションがあります（KILL_FLAG_CLEAR_ON_START=1）が、本番では 0 を推奨します。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は本リポジトリの主なファイル・ディレクトリ構成の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite テーブル作成 / DB 操作ラッパ
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 取引ログ監視（ファイルに含まれる想定）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - kill_switch.py          — kill.flag 書込みロジック
    - alert_manager.py        — （アラート送信ロジック：LINE 等）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体
    - broker_factory.py       — ブローカークライアント生成（Mock / 実ブローカー）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py

注意事項 / 運用上の留意点
-----------------------
- .env に API キーやパスワード等のシークレットを保存する場合は絶対に Git 等へコミットしないでください。
- KABUSYS_ENV=live を設定する前に validate_config で設定を十分に確認してください（LINE 通知設定や Kill Switch 関連に注意）。
- OpenAI API を利用する箇所は API 料金が発生します。rate limit や失敗時の挙動（リトライ、フォールバック）に注意してください。
- ログディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソールのみの出力になります（警告が出ます）。

貢献・拡張
-----------
- config/*.yaml を用いた設定追加、AI モデルの差し替え、ブローカー実装の追加などが想定されます。
- research や portfolio モジュールは純粋関数群として設計されており、ユニットテストが容易です。

ライセンス
---------
（ここにライセンス表記を入れてください）

お問い合わせ
------------
（プロジェクト保持者 / メンテナの連絡先を記載してください）