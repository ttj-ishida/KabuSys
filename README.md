# KabuSys

日本株向けの自動売買システム（ライブラリ兼ランタイムスクリプト）。  
このリポジトリは取引エンジン、監視/アラート、ポートフォリオ構築、リサーチ、AI を使ったニュースセンチメント評価などの主要コンポーネントで構成されています。

Version: 0.1.0

## プロジェクト概要
KabuSys は以下を目的としたモジュール群と起動スクリプトを提供します。

- 発注を行う ExecutionEngine（本番/ペーパートレード対応）
- 実行状況・システム健全性を監視する Monitoring（Kill Switch を含む）
- リスク管理（ドローダウン監視、ポジション上限等）
- ポートフォリオ構築（候補選定、重み付け、株数算出）
- リサーチ用モジュール（モメンタム、バリュー、ボラティリティ等のファクター計算）
- AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定
- 設定ウィザード、設定検証、ペーパートレード検証用レポート生成ツール
- 共通ユーティリティ（ログ設定、プロセス優先度設定 等）

設計上、以下の点に配慮しています：
- 本番とペーパートレードの DB 分離（ペーパートレードは data/paper_trading.db）
- .env による環境変数管理と対話式ウィザード
- OpenAI 呼び出しに対するリトライ / フェイルセーフ
- DuckDB をリサーチ用 DB として使用
- 監視は別プロセスで行い、異常時にファイルベースの Kill Switch で Execution を停止可能

---

## 機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により MockBroker を使用）
  - run_monitoring.py: SystemMonitor と MonitoringEngine のポーリングループを実行（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定関連
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
  - Settings クラスで環境変数の集中管理
- 監視
  - MonitoringEngine: SystemMonitor, TradeMonitor, RiskMonitor を束ねる
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存確認
  - TradeMonitor: 注文状況・約定の検査（不完全データや異常を検出）
  - RiskMonitor: ドローダウン監視、ポジション上限の監視・ログ化
  - KillSwitch: 条件成立時に data/kill.flag を書き込み Execution 停止をトリガ
  - monitoring_db: 監視用 SQLite テーブル定義・永続化 API
- 実行（Execution）
  - BrokerClientFactory / MockBrokerClient（paper_trading 用）
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager（config ベース）
- ポートフォリオ構築
  - 候補選定、等重/スコア重み、ポジションサイズ計算（単元丸め・max/utilization 対応）
  - セクターキャップ、レジーム乗数算出
- リサーチ
  - calc_momentum, calc_volatility, calc_value（DuckDB 経由で prices_daily/raw_financials を参照）
  - 検証用: forward returns, IC 計算、統計サマリ
- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を銘柄毎に集約し LLM でスコア化して ai_scores に書き込む
  - regime_detector.score_regime: ETF の MA とマクロ記事の LLM 評価を合成して market_regime を判定・永続化
  - いずれも API キー未設定時はエラーまたはフェイルセーフを行う設計
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を集計して PASS/FAIL 判定のレポート出力

---

## 必要条件（推奨）
- Python 3.9+
- 必要な Python パッケージ（概ね下記）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- SQLite（標準ライブラリで利用）
- ネットワーク（本番で kabu API / OpenAI を使う場合）

（requirements.txt がある場合はそれを使用してください。なければ上記パッケージを pip でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン／展開
   - プロジェクトルートに移動（setup スクリプト類はプロジェクトルートを基準に動作します）

2. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 生成後、必要な環境変数（特に JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を設定してください。

   自動ロード:
   - プロジェクトルートに .env/.env.local があれば、自動的にロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. ディレクトリ確認
   - data/ と logs/ が作成されるように権限を確認してください。logs/ はログファイル用、data/ は DB/pid/flag 用です。

---

## 使い方（主要コマンド／例）

- ExecutionEngine（本番 or paper_trading）
  - 環境を指定して起動（paper_trading 例）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番実行（注意して設定を確認）:
    - KABUSYS_ENV=live python -m kabusys.run_execution

  実行特記事項:
  - paper_trading の場合、MockBrokerClient を使用しデータは data/paper_trading.db に記録され、本番 SQLite と完全分離されます。
  - 実行中は data/execution.pid が書かれます。
  - 停止フラグ data/stop_requested.flag が存在すると起動/動作を停止します。
  - Kill Switch（data/kill.flag）が書かれると ExecutionEngine 側で停止処理を行います。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に kill.flag を自動クリアします（本番では推奨しません）。

- Monitoring（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60 秒）
  - 監視は監視用 SQLite（設定により data/monitoring.db 等）へログを書きます
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視テーブルを作成します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いになります

- .env 作成ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH を優先します（--db が最優先）

- AI 関連（ニュース scoring / regime）
  - OpenAI API を利用するため、環境変数 OPENAI_API_KEY を設定してください
  - 関数はライブラリ API としても利用できます（例: kabusys.ai.score_news）

- ログ
  - logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション）
  - app_name 例: execution, monitoring（setup_logging で指定）
  - 標準出力にもログが出ます

---

## 重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合は必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB。デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START（0/1。1 で起動時に kill.flag を自動クリア）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔。run_monitoring が参照）

---

## 停止と Kill Switch の挙動
- 手動停止（run_monitoring / run_execution 内ループ）
  - data/stop_requested.flag を作成すると、run_monitoring と run_execution のループが停止（検知して安全終了）
- 自動停止（Kill Switch）
  - Monitoring の各種判定（ドローダウン超過・ポジション上限等）により kabusys.monitoring.kill_switch が data/kill.flag を書き込みます
  - ExecutionEngine は kill.flag の存在を検知すると安全に停止します
  - kill.flag は起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていればクリアされます（本番では注意）

---

## ライブラリとして利用する（簡単な例）
- ポートフォリオ関係をコードから呼ぶ例（擬似コード）
  - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  - candidates = select_candidates(buy_signals, max_positions=10)
  - weights = calc_score_weights(candidates)
  - shares = calc_position_sizes(weights, candidates, portfolio_value=100_000_000, available_cash=50_000_000, ...)

- リサーチ関数
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb")
  - results = calc_momentum(conn, date(2026, 4, 1))

---

## ディレクトリ構成
（代表的なファイル／ディレクトリのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — Settings / .env 自動読み込みロジック
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — 市場レジーム判定（MA + macro sentiment）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py           (参照: 実装の存在を想定)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py          (参照: 実装の存在を想定)
  - execution/
    - execution_engine.py       (実行エンジン本体)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

- data/                          — DB / pid / flag を配置する想定ディレクトリ（作成してください）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - kill.flag
  - stop_requested.flag

- logs/                          — ログ出力先（setup_logging が作成）

（実際の追加ファイルやサブモジュールはリポジトリの全体を参照してください）

---

## 注意事項 / 運用上のヒント
- 本番実行 (KABUSYS_ENV=live) の前に validate_config で設定を慎重に確認してください。LINE などのアラート設定も確認を推奨します。
- kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険です。誤って本番停止フラグを消す可能性があります。
- OpenAI を用いるモジュールは API 利用量・レート制限に注意してください。環境変数 OPENAI_API_KEY を確実に管理してください。
- DuckDB / SQLite のパスは環境変数で指定できます。運用環境に合わせて適切に分離してください（特に paper_trading と本番 DB）。
- ログディレクトリ作成に失敗してもコンソールログは出力されますが、ログローテーションは無効になります。logs/ の書き込み権限を確認してください。

---

この README はコードベース（src/kabusys/*）の現状実装に基づいて作成しました。細かな実装や追加のサブモジュールについては各ファイルの docstring とソースコードを参照してください。質問や追記したいセクションがあれば教えてください。