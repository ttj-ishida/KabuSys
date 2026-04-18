# KabuSys

日本株向けの自動売買システムのライブラリ／起動スクリプト群です。  
このリポジトリには、発注実行エンジン・監視（Monitoring）・研究（Research）・ポートフォリオ構築・AI 補助（ニュース NLP / レジーム判定）などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要なライブラリ
- セットアップ手順
- 使い方（起動スクリプト・ツール・ライブラリAPI）
- 主要環境変数（抜粋）
- ディレクトリ構成（簡易ツリー）
- トラブルシューティング / 注意点

---

プロジェクト概要
- KabuSys は日本株の自動売買を目的としたモジュール群および運用用スクリプト群です。
- 発注実行（ExecutionEngine）、実行の監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）、ポートフォリオ構築、研究用ファクター計算、ニュース NLP による銘柄センチメント評価や市場レジーム判定などを備えています。
- 設定は .env ファイルおよび config/*.yaml により行い、Settings クラスで集中管理されます。

---

主な機能一覧
- Execution
  - ExecutionEngine を起動して発注ロジックを実行（本番 / ペーパートレード分離）
  - BrokerClientFactory により実運用ブローカー or MockBroker を選択
  - リスク管理（RiskManager）、注文管理（OrderManager / OrderRepository）、Reconciler など
- Monitoring
  - システム・プロセス・データ鮮度・トレードログを定期ポーリングして SQLite に記録
  - Kill Switch: ドローダウンやポジション上限超過で data/kill.flag を書き込みエンジン停止
  - AlertManager 経由で通知（LINE トークン等を利用する設計）
- Research
  - DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計要約
- AI
  - ニュース記事を LLM（OpenAI）でスコアリングして ai_scores に保存
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（score_regime）
  - エラー・レート制限は指数バックオフで扱うフェイルセーフ実装
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
  - 統一的ログ設定、プロセス優先度設定ユーティリティ

---

必要なライブラリ（主なもの）
- Python 3.9+
- duckdb
- psutil
- openai (OpenAI SDK)
- PyYAML（config YAML 検証を使う場合）
- その他、実行環境により標準ライブラリ以外が追加されることがあります

インストール例（仮）
pip install duckdb psutil openai PyYAML

---

セットアップ手順（ローカル起動の簡易ガイド）
1. リポジトリをクローンし、Python 仮想環境を作成して有効化する
2. 依存パッケージをインストール（上記参照）
3. .env を作成
   - 対話式で作る: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
4. 設定検証（必須項目のチェック）
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱い（exit 1）
5. データディレクトリの確認
   - デフォルト DB 等は data/ フォルダ配下（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
   - logs/ ディレクトリが作成され、アプリ別ログ（execution.log, monitoring.log など）が出力されます
6. （オプション）OpenAI を使う場合は OPENAI_API_KEY を .env に設定

---

使い方（主要コマンド例）

- 実行エンジン（ExecutionEngine）起動
  - 本番/開発/ペーパーは KABUSYS_ENV で切り替え
  - 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合、MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
  - Execution 起動は PID ファイル（data/execution.pid）を使い、data/stop_requested.flag や data/kill.flag で制御できます

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
  - Monitoring は常に本番 sqlite_path（Monitoring DB）を使います（環境に依らず）

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新できます

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- ライブラリ関数（コードから利用）
  - ポートフォリオ:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
  - 研究:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
    - これらは DuckDB 接続を受け取り prices_daily / raw_financials を参照します
  - AI:
    - from kabusys.ai import score_news
    - from kabusys.ai.regime_detector import score_regime
    - OpenAI API のキーを環境変数 OPENAI_API_KEY または関数引数で指定

---

主要環境変数（抜粋）
- 必須（最低限設定が必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行・データ関連
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH — Execution の PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" で有効、デフォルト "0"）
- ログ / 実行調整
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
  - LOG_DIR — ログの出力先ディレクトリ（デフォルト logs/）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- Paper / Mock Brokers
  - PAPER_FILL_MODE — ペーパートレードでの約定モード ("instant" | "partial" | "never" | "reject")

（完全な一覧は kabusys.config.Settings クラスおよび config_setup.py の ITEMS を参照してください）

---

ディレクトリ構成（主要ファイル）
（src/kabusys 以下の簡易ツリー）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — 統一ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity
  - execution/                — 発注関連（OrderManager, ExecutionEngine 等）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ / 永続化層
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
    - news_nlp.py             — ニュース記事の LLM スコアリング
    - regime_detector.py      — 市場レジーム判定
  - tools/
    - paper_verification_report.py

---

制御ファイル / 運用フロー（簡単）
- 起動 / 停止
  - run_execution が起動中は PID ファイル（data/execution.pid）を生成
  - 外部から停止させたい場合は data/stop_requested.flag（run scripts に uses）や data/kill.flag（KillSwitch が作成）を利用
- Monitoring は stop_requested.flag を検知してループを止めます
- KillSwitch は risk 条件を満たすと kill.flag を作成し ExecutionEngine に停止信号を与えます

---

トラブルシューティング / 注意点
- .env を決して Git にコミットしないでください（機密情報を含む）
- ログディレクトリや data/ の書き込み権限がないとファイルハンドラや DB 作成に失敗します
- OpenAI を利用する機能は API キーが必要。未設定時は例外またはフェイルセーフ動作（スコア 0 等）になることがあります（関数による）
- Monitoring は常に本番用の sqlite_path を使用する設計です（環境に関わらず）
- Paper Trading は本番 DB と分離され、デフォルトで data/paper_trading.db を使用します
- psutil の機能は OS に依存します。プロセス優先度設定や CPU affinity が失敗する場合は警告ログのみで継続します

---

開発者向けメモ
- DuckDB 接続を渡してファクター計算系を組み合わせれば、データベースにある prices_daily / raw_financials 等を元に研究が可能です
- LLM 呼び出し部分はテスト時に差し替え可能（内部で _call_openai_api を patch する設計）
- 設定検証ツールで YAML のパースを行うため PyYAML があると便利ですが、なくても動作します（検証はスキップ）

---

以上が README の概要です。必要であれば以下の追記可能です：
- 具体的な .env のサンプル（.env.example 形式）
- systemd / crontab / docker-compose 用の起動例
- ExecutionEngine / Broker のインターフェース詳細（OrderRepository / OrderManager 等の API）
どの情報が欲しいか教えてください。