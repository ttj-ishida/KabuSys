README
======

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした軽量な Python パッケージです。
主な目的は次の通りです。

- 自動発注エンジン（ExecutionEngine）による発注・注文管理（本番 / ペーパー切替対応）
- システム監視（プロセス生存、CPU/メモリ/ディスク、データ鮮度など）
- リスク監視（ドローダウン、ポジション上限など）と Kill Switch による安全停止
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ファクター計算・リサーチ（モメンタム、バリュー、ボラティリティ等）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント分析）
- ペーパートレード検証レポート生成ツール

特徴
----
- 環境変数 / .env による設定管理（config_setup で対話式生成、validate_config で検証）
- DuckDB（時系列・分析用）と SQLite（監視・注文ログ用）を利用したデータ管理
- OpenAI API を利用したニュースセンチメント評価（ai モジュール）
- 監視ループ・アラート・Kill Switch による安全運用支援
- ペーパートレード用 DB を本番 DB と分離（KABUSYS_ENV=paper_trading）

機能一覧（要約）
----------------
- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（KABUSYS_ENV によりペーパー/本番切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
- 設定関連
  - config.py — 環境変数読み込み・Settings クラス（必須/デフォルト値を定義）
  - config_setup.py — .env 対話式ウィザード（生成/更新）
  - validate_config.py — 起動前検証 CLI（必須環境変数・ファイル・パス等のチェック）
- 監視
  - monitoring/monitoring_db.py — SQLite スキーマ初期化と永続化 API
  - monitoring/system_monitor.py — プロセス生存・リソース・データ鮮度チェック
  - monitoring/trade_monitor.py, monitoring/risk_monitor.py, monitoring/kill_switch.py 等（アラート・Kill Switch）
  - monitoring/monitoring_engine.py — 各モニタを統合してポーリング実行
- 発注・実行（execution/*）
  - ブローカークライアント生成、OrderManager、ExecutionEngine、Reconciler、RiskManager 等（実行ロジック）
- ポートフォリオ構築（portfolio/*）
  - 候補選定、重み計算、リスク調整、ポジションサイズ計算（純粋関数）
- リサーチ（research/*）
  - ファクター計算（momentum/volatility/value）、将来リターン、IC 計算、統計要約
- AI（ai/*）
  - news_nlp.py — ニュースを OpenAI に投げて銘柄ごとにセンチメントを ai_scores に書込
  - regime_detector.py — ma200 とマクロセンチメントで市場レジームを判定
- ツール
  - tools/paper_verification_report.py — ペーパートレードの検証レポート出力
- ユーティリティ
  - utils/logging_setup.py — 共通ログ設定（コンソール + 日次ローテーション）
  - utils/process_priority.py — クロスプラットフォームのプロセス優先度 / CPU affinity

前提・依存
-----------
- Python 3.9+（ソースは型ヒントで modern な構文を利用）
- パッケージ（例、pip install で導入）
  - duckdb
  - psutil
  - openai (ai 機能を使う場合)
  - PyYAML（validate_config で YAML 検証を有効にしたい場合）
- SQLite（標準ライブラリに同梱）
- ネットワーク接続（OpenAI や kabuAPI 等を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン / 配布パッケージを配置し、Python 仮想環境を作成・有効化します。

2. 必要パッケージをインストールします（例）:
   pip install duckdb psutil openai PyYAML

   ※ OpenAI を使わない場合は openai のインストールは不要です。

3. .env の準備
   - 対話式ウィザードで .env を作る:
     python -m kabusys.config_setup

   - 必須環境変数（最低限設定が必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - その他の主要な環境変数（一部デフォルトあり）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラートで必要

   - .env を生成したら設定検証:
     python -m kabusys.validate_config
     --strict を付けると警告も失敗として扱います。

4. データディレクトリの用意（必要に応じて）
   - data/ フォルダはログ・DB・フラグファイル等を保存します。実行時に自動作成されることもありますが、適切なパーミッションを確認してください。

使い方（主なコマンド）
---------------------
- 実行エンジン起動（通常は systemd / supervisor 等でデーモン化して運用）
  python -m kabusys.run_execution

  動作ポイント:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 実行中に data/stop_requested.flag を作成すると Engine が停止します。
  - 実行時に data/execution.pid（デフォルト）へ PID を書きます。

- 監視ループ起動
  python -m kabusys.run_monitoring

  動作ポイント:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（settings.sqlite_path）を使って監視ログを残します。
  - 停止フラグ: data/stop_requested.flag を検知するとループを終了します。

- .env 対話式作成
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  DB パスはオプション > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト の順に解決されます。

重要なファイル / フラグ
----------------------
- data/kill.flag
  - KillSwitch が書き込むフラグファイル。存在すると ExecutionEngine による発注を停止させるためのシグナルになります。
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に自動クリアされる設定になっている点に注意（本番では 0 推奨）。

- data/stop_requested.flag
  - run_monitoring / run_execution の起動ループを終了させるためのローカル指示ファイル。

- data/execution.pid
  - ExecutionEngine が PID を保存するファイル（デフォルト）。

- logs/
  - デフォルトのログディレクトリ。LOG_DIR で変更可。utils.logging_setup.setup_logging によって日次ローテーションされます。

設定（主要な Settings）
----------------------
Settings クラス (kabusys.config.Settings) で取得される主な設定（環境変数名 / デフォルト）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (default: 0)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視しきい値）
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL（デフォルト INFO）
- PAPER_FILL_MODE（paper_trading の MockBroker の約定挙動: instant | partial | never | reject）

ディレクトリ構成（抜粋）
--------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor 起動スクリプト

- ai/
  - news_nlp.py              — ニュースセンチメント取得（OpenAI）
  - regime_detector.py       — 市場レジーム判定
- monitoring/
  - monitoring_db.py         — SQLite スキーマ + 永続化 API
  - system_monitor.py        — システム・データ鮮度監視
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — kill.flag 書込ユーティリティ
  - monitoring_engine.py     — 各 Monitor 統合ループ
  - alert_manager.py         — （アラートを送信する責務）
  - trade_monitor.py         — 注文滞留 / 約定異常検出
- execution/
  - execution_engine.py      — ExecutionEngine 本体
  - broker_factory.py        — ブローカークライアント生成（実/モック）
  - order_manager.py         — 発注管理
  - order_repository.py      — DB への注文ログ保存
  - reconciler.py            — 注文再整合処理
  - risk_manager.py          — 発注時のリスクチェック
- portfolio/
  - portfolio_builder.py     — 候補選定・重み付け
  - position_sizing.py       — 株数決定ロジック
  - risk_adjustment.py       — セクター上限・レジーム乗数
- research/
  - factor_research.py       — ファクター計算
  - feature_exploration.py   — 将来リターン・IC 等の分析ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py         — ログ設定
  - process_priority.py      — プロセス優先度ユーティリティ

開発者向けメモ / 運用注意
-----------------------
- 本番運用時は KABUSYS_ENV=live を慎重に扱ってください。validate_config は live 時に追加警告を出します（LINE 設定、KILL_FLAG_CLEAR_ON_START など）。
- OpenAI を使う機能（ai.news_nlp, ai.regime_detector）は API キー（OPENAI_API_KEY）を必要とし、呼び出しはリトライとフォールバックの仕組みがあります。API コストとレート制限に注意してください。
- Monitoring は run_monitoring のログを参照し、kill.flag を書き込む実装になっています。Kill Switch により ExecutionEngine を安全に停止できますが、設定ミスで誤発動しないように注意してください。
- DuckDB と SQLite のパスは環境変数で切り替え可能です。テスト/ペーパー用 DB は本番 DB と明確に分離してください。

ライセンス・バージョン
---------------------
パッケージバージョン: kabusys.__version__ = 0.1.0

（ライセンス情報はリポジトリのトップレベルに別途記載してください）

お問い合わせ / 貢献
------------------
バグ報告・改善提案は issue を立ててください。Pull Request は歓迎します。README にない機能の詳細はソースコードの docstring を参照してください。