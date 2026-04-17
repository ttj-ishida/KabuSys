KabuSys
======

KabuSys は日本株向けの自動売買 / リサーチ基盤のサンプル実装です。
ポートフォリオ構築・ポジションサイジング、リサーチ（ファクター算出・特徴量解析）、AI を使ったニュースセンチメント評価、
発注エンジン（ExecutionEngine）と監視（Monitoring）を備え、実運用およびペーパートレード両対応で設計されています。

主な目的は「実運用に近いアーキテクチャ」を示すことであり、
各モジュールはユニットテストしやすい純粋関数／明確な入出力で実装されています。

主な機能
-------
- 環境設定管理
  - .env 自動ロード（プロジェクトルート検出）と対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行エンジン（Execution）
  - ExecutionEngine を起動してブローカーへ発注（本番／ペーパートレード切替）
  - BrokerClientFactory による実ブローカー / モック切替
  - 注文管理・リスク管理・照合（OrderManager / RiskManager / Reconciler）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
  - Kill Switch（閾値超過等で停止フラグを書き込み、Execution を安全停止）
  - LINE 通知（AlertManager、トークン未設定時はログのみ）
- ポートフォリオ構築
  - 候補選定、等配分／スコア配分、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap、コストバッファ等）
- リサーチ
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI（LLM）連携
  - ニュースを LLM（OpenAI）でセンチメント評価して ai_scores に書き込み（news_nlp）
  - マクロ + ETF MA200 を合成して市場レジーム判定（regime_detector）
  - API 呼び出しはリトライとフェイルセーフを備え、安全にフォールバック
- ツール
  - ペーパートレード検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ
----------
前提
- Python 3.9+
- SQLite（標準ライブラリ）
- DuckDB（推奨: duckdb パッケージ）
- psutil（プロセス優先度 / CPU affinity）
- openai（AI 機能を使う場合）
- requests（LINE 通知）
- PyYAML（config YAML 検証を行う場合、任意）

推奨インストール例:
- 仮想環境を作成してアクティベート
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

- 必要パッケージをインストール（例）
  - pip install duckdb psutil openai requests PyYAML

初期設定 (.env)
1. ウィザードで対話的に .env を作成:
   - python -m kabusys.config_setup
   - 画面の案内に従い必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力します。

2. 設定検証:
   - python -m kabusys.validate_config
   - 問題があれば表示されます。--strict を付けると警告も失敗扱いになります。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading の場合、MockBroker と data/paper_trading.db を使用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を有効にする場合
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）

使い方
-----

1) 実行エンジン（ExecutionEngine）を起動
- 通常（環境変数は .env で設定済みを前提）:
  - python -m kabusys.run_execution
- ペーパートレード（環境切替）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - paper_trading モードでは MockBrokerClient を利用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に保存されます。
- 実行中の安全停止:
  - run_execution はプロジェクトルート/data/stop_requested.flag の存在を監視しています。停止したい場合はファイルを作成してください（または Monitoring の KillSwitch が data/kill.flag を作成します）。
- PID ファイル:
  - 実行時に data/execution.pid を使用/更新します。SystemMonitor はこの PID ファイルを確認してプロセス存在を検証します。

2) 監視ループを起動
- python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は Settings.sqlite_path（data/monitoring.db のデフォルト）を使用します（KABUSYS_ENV に関係なく本番監視 DB を参照する設計）
  - 監視は system/trade/risk をチェックし、
    必要に応じて kill.flag を作成して ExecutionEngine に停止を促します。
  - 監視を終了するにはプロジェクトルート/data/stop_requested.flag を作成するか Ctrl+C。

3) AI / レジーム / ニューススコアリング
- ニュースセンチメント（ai/news_nlp.py）:
  - kabusys.ai.score_news を呼び出すと duckdb 接続と target_date、OpenAI API キーで ai_scores を更新します。
  - コマンドラインから利用する場合、スクリプト経由で独自の CLI 等を作成してください。
- レジーム判定（ai/regime_detector.py）:
  - kabusys.ai.regime_detector.score_regime を呼び出し market_regime テーブルへ記録します。
- 注意: OPENAI_API_KEY が必要。API 失敗時はフェイルセーフ（デフォルト値で継続）を取ります。

4) ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report
  - オプション --from / --to で日付範囲指定、--db で DB パス上書き可
  - デフォルト DB: env または data/paper_trading.db

停止・Kill Switch の挙動
- run_execution / run_monitoring はどちらもプロジェクトルート/data/stop_requested.flag の存在を監視してループを終了します。
- Monitoring の KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。kill.flag は ExecutionEngine に対する高優先度停止シグナルとして利用されます（実際の停止挙動は ExecutionEngine 側の実装に依存）。
- kill.flag は KillSwitch.clear() で消去可能。Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動クリアしますが、本番環境では設定しないことを推奨します。

ディレクトリ構成（主要ファイル）
--------------------------------
以下はソースツリー（src/kabusys）内の主要モジュール概観です。実際のパッケージは src/kabusys 以下にあります。

- src/kabusys/
  - __init__.py                 — パッケージ定義（バージョン等）
  - config.py                   — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - execution/                   — 実行系コンポーネント（Engine, OrderManager, BrokerFactory 等）
    - (OrderRepository, ExecutionEngine, Reconciler, RiskManager 等の実装)
  - monitoring/
    - monitoring_db.py          — SQLite 用永続化層（テーブル初期化・CRUD ユーティリティ）
    - monitoring_engine.py      — モニタ束ねクラス
    - system_monitor.py         — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py          — 注文滞留 / 約定異常チェック
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — Kill Switch ロジック（kill.flag 書込）
    - alert_manager.py          — LINE 通知（プッシュ）
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数計算・丸め・キャップ
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py        — モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py    — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py               — ニュースセンチメント評価（OpenAI）
    - regime_detector.py        — マクロ + MA200 による市場レジーム判定（OpenAI）
  - utils/
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ

注意事項 / 運用上のポイント
-------------------------
- .env は機密情報を含むため絶対にコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- KABUSYS_ENV=live を使う場合は特に注意（validate_config は本番時に追加警告を出します）。
- OpenAI を使う機能は料金やレート制限に注意してください（リトライ・バックオフ実装あり）。
- 監視はデフォルトで monitoring DB（SQLite）へログを書きます。運用では定期バックアップや適切な永続化を検討してください。
- psutil によりプロセス優先度や CPU affinity を変更します。実行環境の権限によっては設定が失敗します（警告のみ）。

開発・テスト
-------------
- 各モジュールは外部副作用を極力排した設計です。DB 接続や OpenAI 呼び出し箇所は差し替え / モックが容易です。
- monitoring_engine.run_once() を使うと一回だけ監視処理を実行でき、ユニットテストに便利です。
- news_nlp._call_openai_api / regime_detector._call_openai_api はテスト時にパッチして外部依存を排除できます。

ライセンス / 貢献
-----------------
- 本リポジトリのライセンスやコントリビューション方針が別途ある場合はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（ここでは省略）。

この README はコード構成と運用に関する主要点をまとめたものです。詳細な設計資料（PortfolioConstruction.md, StrategyModel.md 等）がある場合はそちらを参照してください。質問や補足があればお知らせください。