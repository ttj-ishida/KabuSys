# KabuSys

日本株自動売買システムの参考実装（ライブラリ / 実行スクリプト群）。

このリポジトリはトレーディング戦略の研究・ポートフォリオ構築・発注エンジン・監視・AI 補助モジュールを含むモジュール群を提供します。実運用用というよりは設計例・参考実装を兼ねた構成です。

---
## プロジェクト概要
- コア機能:
  - シグナル→ポートフォリオ構築→ポジションサイジング→発注（ExecutionEngine）
  - 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
  - DuckDB を使ったリサーチ（ファクター計算、特徴量探索）
  - OpenAI を用いたニュース NLP（銘柄センチメント）／市場レジーム判定
  - Paper Trading 用の分離 DB（仮想発注）と検証レポート生成
  - ログ設定・プロセス優先度制御等のランタイムユーティリティ

---
## 機能一覧
- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Broker クライアントの抽象化（本番 or モック）
  - リスク管理（ポジション上限、ドローダウン等）
  - 発注ログ（SQLite trade_logs）・ダッシュボード永続化
- Monitoring
  - system_status / trade_logs / risk_logs / positions / dashboard を保持する SQLite ベースの監視 DB 初期化
  - SystemMonitor：CPU/メモリ/ディスク監視、プロセス生存チェック、データ鮮度チェック
  - TradeMonitor：注文滞留・約定異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、kill.flag 生成
  - MonitoringEngine：各モニタを束ねてポーリング、アラート送信フック
- Research（DuckDB）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計サマリ
- AI
  - news_nlp: raw_news → OpenAI（gpt-4o-mini）で銘柄単位センチメント算出 → ai_scores に書き込み
  - regime_detector: ETF 1321 の MA とマクロニュースを合成して市場レジームを判定して保存
- Utilities
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ロギング統一設定（logs/<app>.log 日次ローテーション）
  - プロセス優先度・CPU affinity 設定ユーティリティ
- Tools
  - paper_verification_report: Paper Trading DB から稼働率・注文成功率・レイテンシ等を評価するレポート出力

---
## 必要要件
- Python 3.9+
- 必要な主要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証のため任意）
- （requirements.txt があればそれを使用してください）
  - pip install -r requirements.txt

---
## セットアップ手順（簡易）
1. リポジトリをクローンしワークディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 要件ファイルがない場合は主要パッケージを個別にインストール:
     - pip install duckdb psutil openai PyYAML

4. .env を作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等を設定してください
   - .env は絶対に Git にコミットしないでください

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を指定すると警告も失敗扱いになります

6. データディレクトリの準備
   - デフォルトでは data/ に DB とフラグファイルが作成されます
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を調整

---
## 主要コマンド（実行例）
- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 実行時に Settings.env（KABUSYS_ENV）が paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します
  - 実行中は data/execution.pid に PID を書き込みます。停止は data/stop_requested.flag または kill.flag によって検知します

- Monitoring 起動（ポーリング）
  - python -m kabusys.run_monitoring
  - デフォルトポーリング間隔: 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能）
    - 例: export MONITOR_POLL_INTERVAL=30

- .env 対話ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュール（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY（環境変数）または api_key 引数が必要

---
## 主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API 用
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: 発注はモック、DB は PAPER_TRADING_SQLITE_PATH
- DB 関連
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト、監視用）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- AI
  - OPENAI_API_KEY: OpenAI API キー
- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング秒数（デフォルト: 60）
- その他
  - PID_FILE_PATH: data/execution.pid（デフォルト）
  - KILL_FLAG_PATH: data/kill.flag（Kill Switch 用）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の埋め方）

---
## 監視 DB（SQLite）テーブル概要
init_monitoring_db により次のテーブルを作成（冪等）します:
- system_status: CPU/メモリ/Disk、プロセス健全性、記録時刻
- trade_logs: 発注ログ（event_type: Created/Sent/Filled 等）、latency_ms カラムあり
- positions: 現在保有ポジション
- risk_logs: リスクアラート履歴
- dashboard: 単一行（id=1）で集約情報を保持（portfolio_value / cash / drawdown_pct / peak_value など）

---
## Kill / Stop の仕組み
- kill.flag (Settings.kill_flag_path、デフォルト data/kill.flag)
  - KillSwitch が書き込むことで ExecutionEngine に対する停止シグナルになります
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って自動クリアされないよう）
- stop_requested.flag (data/stop_requested.flag)
  - run_execution.py / run_monitoring.py がこのファイルの存在を検知すると穏やかに停止します
- data/execution.pid: 実行中プロセスの PID が書かれます

---
## ログとプロセス設定
- ログ: logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション／30日保持）
- setup_logging(app_name="execution") を各起動スクリプトで使用
- 起動時に set_process_priority("high") を呼んでプロセス優先度を上げます（OS により制約あり）

---
## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py                  — 環境変数 / Settings
- config_setup.py            — .env 対話ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py (参照実装がある場合)
- execution/                  — ExecutionEngine, OrderManager, BrokerFactory 等（モジュール群）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- data/ (実行時に生成される)
  - monitoring.db (default SQLITE_PATH)
  - kabusys.duckdb (default DUCKDB_PATH)
  - paper_trading.db (paper_trading 用)
  - execution.pid
  - kill.flag / stop_requested.flag
- logs/ (実行時に生成される)

（注）一部のモジュールは上記に含まれない補助ファイル・サブパッケージと連携します。実際のリポジトリ全体構成はローカルのツリーを参照してください。

---
## 開発メモ / 注意点
- .env は自動読み込みされます（プロジェクトルート検出ロジックにより .env/.env.local を読み込み）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading モードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使う処理は API 呼び出しで失敗した場合にフェイルセーフ（スコア 0.0 で継続、部分失敗時は既存データ保護）する実装になっていますが、本番での利用は十分なテストを推奨します。
- ログディレクトリ作成やプロセス優先度設定は OS 権限に依存します。権限不足時は警告ログを出して継続します。

---
## よくあるコマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定チェック: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

README に不足している操作やモジュールの動作詳細（例: ExecutionEngine の細部、Broker の実装、アラート送信先設定等）については該当モジュールの docstring を参照するか、必要なら追加でドキュメントを作成します。