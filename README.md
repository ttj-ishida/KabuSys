README
=====

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
主な目的は以下のとおりです。

- 戦略（ファクター計算・ポートフォリオ構築）およびポジションサイズの計算
- 発注エンジン（ExecutionEngine）による注文管理（本番 / ペーパートレード対応）
- システム監視（Monitoring）・アラート・Kill Switch（停止フラグ）
- ニュースの NLP によるセンチメント評価や市場レジーム判定（OpenAI 利用）
- 検証ツール（ペーパートレード検証レポート等）
- .env 対話ウィザード / 設定検証 CLI

主な設計方針として、DB（DuckDB / SQLite）は明確に分離され、AI 呼び出し部分は失敗時のフェイルセーフが組み込まれています。

機能一覧
--------
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - BrokerClientFactory により環境（paper_trading / live）に応じたクライアントを生成
  - ペーパートレード時は別 SQLite（data/paper_trading.db）に記録して本番 DB と完全分離

- Monitoring
  - SystemMonitor：CPU／メモリ／ディスク監視、データ鮮度・プロセス生存チェック
  - TradeMonitor：発注ログの監視（滞留注文、約定異常等）
  - RiskMonitor：ドローダウン・ポジション数上限監視、ダッシュボード更新
  - KillSwitch：条件により data/kill.flag を書き込み ExecutionEngine に停止シグナルを送信
  - MonitoringEngine：上記 Monitor を束ねるポーリングループ（run_monitoring.py）

- Portfolio / Strategy
  - ポートフォリオ構築: 候補選定、等金額／スコア重み、セクター上限、レジーム乗数
  - ポジションサイズ計算: risk_based / equal / score に対応、単元株丸め、aggregate cap

- Research
  - ファクター計算（モメンタム/バリュー/ボラティリティ）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ

- AI
  - news_nlp: raw_news を集約し OpenAI（gpt-4o-mini 等）でセンチメントを算出・ai_scores へ書き込み
  - regime_detector: ETF の MA とマクロニュースを合成して market_regime を算出

- ツール
  - paper_verification_report: ペーパートレード DB から運用検証レポートを生成

セットアップ手順
----------------

前提
- Python 3.10+ を想定（型注釈で | を使うため）
- システムに sqlite3 が含まれていること（標準）
- 必要パッケージ（一例）:
  - duckdb
  - psutil
  - openai
  - PyYAML （config 検証でオプション）
  - その他テスト用パッケージ等

1) 仮想環境作成（例）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2) 依存パッケージをインストール（例）
   pip install duckdb psutil openai PyYAML

   （パッケージ管理はプロジェクトの要件ファイルに合わせてください。）

3) リポジトリルートで初期ディレクトリ作成
   mkdir -p data logs

4) .env の準備
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 生成後、設定チェック:
     python -m kabusys.validate_config
     # --strict を付けると警告も失敗扱いになります

主要な環境変数（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB。デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- その他 README 内のツール固有設定に準ずる

使い方
------

1) 設定ウィザード・検証
   - .env を対話式で作成 / 更新:
     python -m kabusys.config_setup
   - 設定検証:
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict

2) 監視プロセス起動
   - 単純実行:
     python -m kabusys.run_monitoring
   - ポーリング間隔を変更する場合:
     export MONITOR_POLL_INTERVAL=30  # 単位: 秒（1 以上）
     python -m kabusys.run_monitoring
   - 監視は Settings に従い本番 sqlite_path を使用します（監視用 DB は環境にかかわらず同じです）。
   - 停止フラグ: プロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します。

3) ExecutionEngine 起動
   - 実行:
     python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使って data/paper_trading.db に記録します。
   - 実行中の停止:
     プロジェクトルート/data/stop_requested.flag を作成するとエンジンが安全停止を試みます。
   - PID ファイル:
     data/execution.pid（デフォルト）に PID が書かれます。

4) Paper Trading 検証レポート
   - 例（期間指定可）:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   - 簡易基準: 稼働率・注文成立率・送信率・P95 レイテンシ等の閾値に基づいて PASS/FAIL を出力します。

5) AI（ニュース NLP / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - conn は duckdb 接続（duckdb.connect(path)）を渡す
     - api_key を None にすると環境変数 OPENAI_API_KEY を参照
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - 同様に OpenAI API キーを必要とする

注意点・運用上のポイント
- ペーパートレードと本番の DB は分離されています（paper_trading 用 SQLite を利用）。
- .env は絶対にバージョン管理にコミットしないでください（config_setup.py にも注意書きあり）。
- OpenAI API 呼び出しはリトライやスコアのクリップなどエラーハンドリングを備えていますが、API キーやコストに注意してください。
- ログは logs/ に日次ローテーションで保存されます。ログディレクトリが作成できない場合はコンソール出力のみになります。
- Monitoring の Kill Switch は RiskMonitor の結果に基づいて data/kill.flag を書き込み、ExecutionEngine 側で検出して停止する仕組みです。KILL_FLAG_CLEAR_ON_START により起動時に自動でフラグをクリアする設定がありますが、本番では 0 を推奨します。

ディレクトリ構成（主要ファイル）
-------------------------------
プロジェクトの src/kabusys 配下の主なモジュール構成（抜粋）:

- kabusys/
  - __init__.py
  - config.py                — .env 自動読み込み・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/               — 発注/注文管理関連コンポーネント（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py
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
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使う DB / フラグファイル等)
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - kill.flag, stop_requested.flag, execution.pid

（上記はコードベースからの抜粋です。細かなサブモジュールや追加ファイルは実際のリポジトリをご確認ください。）

ライセンス・貢献
----------------
- 本ドキュメントはコードベースに基づく概要説明です。実運用での利用・改変は適宜ライセンス条項に従ってください。
- バグ報告や機能提案はリポジトリの Issue を利用してください。

以上。必要であればサンプル .env テンプレートや起動例の詳細（systemd ユニット、Dockerfile、CI 設定例）を追加で作成します。どの情報を優先して追加しますか？