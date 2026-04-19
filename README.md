# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買システムの一部実装（ライブラリ + 起動スクリプト群）です。  
小規模なトレーディングエンジン、監視（Monitoring）、リサーチ/ファクター計算、AI を使ったニューススコアリングなどの機能を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動スクリプト・ツール）
- 主要設定項目（環境変数）
- ディレクトリ構成（ファイル一覧）
- 運用メモ / 注意点

---

プロジェクト概要
- KabuSys は日本株の自動売買ワークフローを構成するモジュール群（発注エンジン、監視、ポートフォリオ構築、リサーチ、AIニュース処理など）です。
- ローカル開発 / ペーパートレード / 本番（live）を切り替え可能な設定構成を持ち、ペーパートレードは本番 DB と完全分離されます。
- DuckDB（分析用）と SQLite（監視・注文ログ用）を使ってデータを保持します。
- ロギング・プロセス優先度・Kill Switch 等、運用想定のユーティリティが組み込まれています。

---

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
  - プロセス優先度設定、PID 管理、停止フラグ検出
- Monitoring（監視）
  - run_monitoring.py による定期ポーリング（MONITOR_POLL_INTERVAL で間隔変更可）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に system_status / trade_logs / positions / risk_logs / dashboard を永続化
  - KillSwitch による flag ファイルでの安全停止
- リサーチ（research）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Information Coefficient）などの統計処理
- ポートフォリオ構築（portfolio）
  - 候補選定、等重/スコア重み付け、ポジションサイズ計算、セクター制限・レジーム乗数
- AI（ai）
  - news_nlp: OpenAI を用いたニュースのセンチメントスコアリング（ai_scores テーブルへ書込）
  - regime_detector: MA200 とマクロ記事スコアで市場レジーム判定
- ツール
  - config_setup.py: 対話式 .env ウィザード（初期設定・更新）
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート出力
- ユーティリティ
  - logging_setup: stdout + 日次ローテートファイルの統一ロギング
  - process_priority: Windows/Linux の差を吸収した優先度設定
  - DB マイグレーションや永続化層（monitoring_db）

---

セットアップ手順（開発・運用向け）
1. Python 環境を用意（推奨: 3.9+）
2. 依存関係をインストール
   - requirements.txt は本リポジトリに含まれている想定です。例:
     - pip install -r requirements.txt
   - 主要依存例: duckdb, psutil, openai, pyyaml（YAML 検証用）
3. プロジェクトルートを確認
   - 本コードはパッケージとして src/kabusys 以下にあります。プロジェクトルートには .env/.env.local, data/, logs/ 等が置かれます。
4. 環境変数設定
   - .env を作成する最も簡単な方法:
     - python -m kabusys.config_setup
   - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 本番で OpenAI を使う場合: OPENAI_API_KEY を設定
   - 自動ロード無効化（テスト等）: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)
6. data ディレクトリ作成（必要な場合）
   - SQLite / DuckDB のデフォルトパスは data/ 以下です。起動時に自動作成されることもありますが、権限等に注意してください。

---

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBroker を使い、PAPER_TRADING_SQLITE_PATH に記録する
- データベース
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト: 監視用）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- ログ / プロセス
  - LOG_LEVEL: DEBUG/INFO/...
  - LOG_DIR: logs/
  - PID_FILE_PATH: data/execution.pid
- AI
  - OPENAI_API_KEY
- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
- Kill Switch 動作
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1)

短い .env サンプル（実運用時は秘密情報を保護してください）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

使い方（よく使うコマンド）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動: KABUSYS_ENV=paper_trading のとき専用 DB に書き込み、本番とは分離されます
  - 停止: data/stop_requested.flag の作成で安全に停止（または kill.flag があれば起動を停止）
- 監視プロセス起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（秒）
  - 監視は本番 sqlite_path を常に使用（環境にかかわらず）
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パス指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも可）
- AI ニューススコアリング（ライブラリ呼び出し）
  - Python から:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn は duckdb.connect(...)
- 市場レジーム判定（ライブラリ呼び出し）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

ログと運用
- ログ出力: logs/<app_name>.log を日次ローテートで出力（logs/ ディレクトリ）
- stdout も常に出力（StreamHandler）。ファイル出力はログディレクトリ作成に失敗すると無効化されます。
- プロセス優先度: 起動スクリプトは最初に set_process_priority("high") を呼びます（プラットフォームに依存）

停止 / Kill Switch
- data/kill.flag を書き込むと ExecutionEngine に停止命令を与える（KillSwitch により作成）。
- data/stop_requested.flag は run_execution/run_monitoring の外部停止フラグとして使用されます。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag を消去します（本番では 0 推奨）。

---

ディレクトリ構成（主要ファイル）
（src/kabusys 以下。省略されているファイルやサブパッケージは実装により差分あり）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス、自動 .env ロードロジック
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し、ai_scores 反映）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロスコア）
  - research/
    - __init__.py
    - factor_research.py     — momentum/volatility/value 等
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定、重み計算
    - position_sizing.py     — 株数計算、aggregate cap 対応
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - monitoring/
    - monitoring_db.py       — SQLite DB スキーマ & 永続化 API
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （存在）トレード監視（滞留注文等）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — フラグファイルで停止命令を発行
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （想定）アラート送信（LINE 等）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

data/ と logs/（プロジェクトルート）
- data/monitoring.db           — 監視用 SQLite（デフォルト）
- data/paper_trading.db       — ペーパートレード用 SQLite（paper_trading 用）
- data/kabusys.duckdb         — DuckDB（分析用）
- data/execution.pid          — 実行エンジン PID（run_execution が利用）
- data/kill.flag              — Kill Switch が書き込む停止フラグ
- data/stop_requested.flag    — 外部停止要求フラグ
- logs/<app_name>.log         — 日次ローテートログ

---

実装上の注意 / 運用メモ
- DB マイグレーションや列追加は monitoring_db.init_monitoring_db() で冪等に処理されます（既存 DB に latency_ms / peak_value を追加するロジックあり）。
- Monitoring は常に settings.sqlite_path（本番 DB）を使用します。paper_trading の隔離は run_execution 側で行われます。
- OpenAI API を使用するモジュールは、APIキーが未設定のときに ValueError を投げます（スクリプト呼び出し時は環境変数 OPENAI_API_KEY をセットしてください）。
- リトライロジック: OpenAI 呼び出しは一部のエラー（429/ネットワーク/5xx 等）で指数バックオフの再試行を行います。テスト時は内部の _call_openai_api をモックできます。
- Cron/サービス化する場合、run_monitoring / run_execution は stdout ログとログファイルの両方に出力されます。ログディレクトリの権限に注意してください。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えば .env の自動ロードを抑制できます（ユニットテストや CI 用）。

---

貢献 / 拡張案
- stocks マスタに銘柄ごとの lot_size を持たせ、position_sizing を拡張
- trade_monitor / alert_manager の充実（通知チャネル増強）
- PyPI 配布用のパッケージ化、CLI インストール時に entry_points を追加

---

以上がこのコードベースの概要・セットアップ・使い方です。README に記載してほしい追加情報（例: 依存パッケージの正確なバージョンや systemd サービス例など）があれば教えてください。