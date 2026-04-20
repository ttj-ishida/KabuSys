KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買／研究／監視を目的とした小規模なフレームワークです。  
主要機能（戦略の生成・ポートフォリオ構築・発注・監視・AI ベースのニュース解析・検証レポート生成）をモジュール化して提供します。  
本リポジトリは実行用スクリプト・設定管理・監視・ポートフォリオ構築ロジック・研究用ユーティリティを含みます。

特徴（機能一覧）
----------------
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV 環境変数）
  - RiskManager、OrderManager、Reconciler 等のコンポーネントで安全制御
  - ペーパートレード時は MockBrokerClient を使用し専用 SQLite DB（data/paper_trading.db）へ記録

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度監視
  - TradeMonitor: 注文滞留や約定異常など監視（実装ファイル参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、Kill Switch 書き込み
  - MonitoringEngine: 各モニタを束ねたポーリングループ
  - 監視ログは SQLite（デフォルト: data/monitoring.db）へ永続化

- ポートフォリオ構築（純粋関数）
  - 銘柄選定（スコア/ランク）、等金額・スコア加重配分
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（単元株丸め・資金上限考慮）

- 研究用モジュール（Research）
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（情報係数）、統計サマリ等

- AI（OpenAI）連携
  - ニュース NLP（gpt-4o-mini）で銘柄ごとのセンチメントスコアを生成し ai_scores に格納
  - 市場レジーム判定（ETF MA200 とマクロセンチメントの合成）

- ツール
  - 設定ウィザード（.env 自動生成支援）
  - 設定検証 CLI（.env・config/*.yaml のチェック）
  - Paper Trading 検証レポート生成スクリプト

セットアップ手順
----------------

1. 推奨 Python バージョン
   - Python 3.10 以上（型注釈に | が使われているため）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な必要パッケージ（目安）:
     - duckdb, psutil, openai
     - PyYAML （config/*.yaml のパース検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. 環境変数 / .env 設定
   - 推奨: python -m kabusys.config_setup で対話的に .env を作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI API を使う場合に必要
     - PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
   - 自動読み込み:
     - プロジェクトルート（.git または pyproject.toml）から .env/.env.local が自動読み込みされます。
     - 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. ログディレクトリ
   - デフォルト: logs/
   - LOG_DIR 環境変数で変更可能
   - ログは日次ローテーション（30日保持）

使い方（主要コマンド）
--------------------

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告を FAIL 扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン（Execution）
  - 起動:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録されます
    - 起動時に data/stop_requested.flag が存在すると起動を行わず終了
    - data/execution.pid に PID を書く仕組み（Engine に渡されます）

- 監視ループ（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト: 60）
  - 注意:
    - Monitoring は環境に関係なく本番の sqlite_path を使用して監視ログを記録します（監視ログは settings.sqlite_path を参照）
    - 停止は data/stop_requested.flag を作成すると検知してループを抜けます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプション または 環境変数 PAPER_TRADING_SQLITE_PATH を使えます

- AI モジュール（ニュース分析 / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - プログラムから直接呼び出す場合は kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を使用

停止・Kill Switch 関連
--------------------
- ExecutionEngine の停止シグナルは主に以下のフラグファイル操作で制御されます:
  - data/stop_requested.flag: 実行中の run_execution/run_monitoring が検知して安全に停止
  - data/kill.flag: KillSwitch が書き込み、Execution 側で停止（本番用の緊急停止）
- KillSwitch は RiskMonitor の判定結果（ドローダウン超過、ポジション上限超過）により data/kill.flag を書き込みます
- 設定で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアできます（本番では 0 を推奨）

ディレクトリ構成（主要ファイル）
-------------------------------

src/kabusys/
- __init__.py
- config.py                     — 環境変数と Settings
- config_setup.py               — .env 対話ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — Monitoring ポーリング起動スクリプト

src/kabusys/execution/
- broker_factory.py, execution_engine.py, order_manager.py, ...（発注関連）

src/kabusys/monitoring/
- monitoring_db.py               — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- system_monitor.py              — システム状態・データ鮮度監視
- trade_monitor.py               — 注文ログ監視（滞留・異常チェック）
- risk_monitor.py                — ドローダウン・ポジション監視
- kill_switch.py                 — kill.flag 書き込みユーティリティ
- monitoring_engine.py           — モニタ束ね実行

src/kabusys/portfolio/
- portfolio_builder.py           — 候補選定・重み計算
- position_sizing.py             — 株数決定・資金・lot 切り捨てロジック
- risk_adjustment.py             — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py             — ファクター計算（momentum/volatility/value）
- feature_exploration.py         — 将来リターン、IC、summary 等

src/kabusys/ai/
- news_nlp.py                    — ニュース NLP スコアリング（OpenAI）
- regime_detector.py             — 市場レジーム判定（MA200 + マクロセンチメント）

src/kabusys/tools/
- paper_verification_report.py   — Paper Trading 検証レポート生成

src/kabusys/utils/
- logging_setup.py               — ログ初期化ユーティリティ
- process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ

data/ （実行時に使用）
- monitoring.db (default)        — 監視用 SQLite（Settings.sqlite_path）
- paper_trading.db               — ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）
- execution.pid                   — ExecutionEngine の PID（Engine により生成）
- stop_requested.flag             — 手動停止フラグ（存在すれば各 run_* が終了）
- kill.flag                       — Kill Switch フラグ（作成されると Execution 側を停止）

注意事項・運用上のヒント
-----------------------
- 本番稼働前に必ず python -m kabusys.validate_config で設定検証を行ってください。
- KABUSYS_ENV=live の場合は特に LINE 通知などアラート設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確認してください。
- .env は絶対に VCS にコミットしないでください（config_setup でも README に注意書きあり）。
- OpenAI を利用する機能は API 利用料が発生します。API キー管理に注意してください。
- ログや DB のパスは Settings で上書き可能です。複数環境を使い分けたい場合は PAPER_TRADING_SQLITE_PATH や SQLITE_PATH、DUCKDB_PATH を適切に設定してください。

追加情報
---------
- DuckDB は研究（ファクター計算・AI 前処理）で利用します。大規模データの集計・探索に便利です。
- psutil を用いてプロセス優先度やリソース使用率を監視・制御します。権限不足で優先度設定が失敗することがありますが警告ログに留まります。

問題報告 / 貢献
----------------
バグや改善提案があれば Issue を作成してください。Pull Request は歓迎します。README の改善提案も歓迎です。

---

この README はコードベースの主要な要点を抜粋してまとめたものです。詳細は各モジュールの docstring やソースコードコメントを参照してください。