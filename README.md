KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本プロジェクトは取引実行、監視、ポートフォリオ構築、ファクター計算、ニュース NLP によるセンチメント評価、検証ツールなどを含みます。実行エンジン（ExecutionEngine）と監視モジュール（MonitoringEngine）を分離しており、本番（live）・ペーパートレード（paper_trading）・開発（development）モードをサポートします。

主な特徴
--------
- ExecutionEngine：発注管理・リスク管理・リコンシリエーション機能を持つ発注実行フレームワーク
- Monitoring：システム状態・注文滞留・ドローダウン等を定期監視しログ保存、アラート送信（LINE）
- Portfolio construction：候補選定・重み付け・ポジションサイズ算出（等分配・スコア加重・リスクベース）
- Research：DuckDB 上でのファクター計算（モメンタム・ボラティリティ・バリュー）と特徴量解析ツール
- AI モジュール：OpenAI を使ったニュースセンチメント評価・市場レジーム判定（gpt-4o-mini を想定）
- Tools：ペーパートレード用検証レポート生成、Streamlit ベース監視ダッシュボード等
- 安全設計：起動時プロセス優先度設定、KillSwitch（フラグファイル）による安全停止、DB マイグレーションの冪等処理

セットアップ手順
----------------
前提
- Python 3.10+ を想定（typing / match を多用しないが Path 型などを使用）
- システムに duckdb, psutil, requests, openai, streamlit 等をインストール可能であること

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数 / .env
   - 必要な環境変数を設定（以下「主要な環境変数」参照）
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（既存の OS 環境変数は保護）。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要な環境変数（抜粋とデフォルト）
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視ログ用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知 用（未設定時は送信をスキップ）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject、デフォルト instant）
- PID_FILE_PATH / KILL_FLAG_PATH / その他閾値（CPU_THRESHOLD_PCT 等）

使い方
------

1) 実行エンジン（ExecutionEngine）を起動
- 本番（live）モード:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- ペーパートレード（MockBroker 使用、DB を分離）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレードでは PAPER_TRADING_SQLITE_PATH に指定した DB（既定 data/paper_trading.db）に書き込みます

動作概要:
- 起動時にプロセス優先度を "high" に設定
- sqlite (監視 DB / paper DB) と DuckDB に接続
- BrokerClientFactory により本番ブローカー or MockBroker を生成
- ExecutionEngine.run_session() を実行（詳細は execution パッケージ実装による）

2) 監視ループ（Monitoring）を起動
- python -m kabusys.run_monitoring
- 動作:
  - MONITOR_POLL_INTERVAL（秒）で SystemMonitor.check_once() を含む監視ループを回します（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を使用（KABUSYS_ENV に依存しない）ため、監視ログは本番 DB に保存されます
  - 起動時にプロセス優先度を "high" に設定

3) Streamlit ダッシュボード（監視 UI）
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Read-only 接続で監視 DB を閲覧できます

4) Paper Trading 検証レポート生成
- コマンド:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  - --db PATH による DB 指定（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシなどの要約と PASS / FAIL 判定

運用上のポイント / フェイルセーフ
- KillSwitch: RiskMonitor が一定条件（ドローダウン超過、ポジション上限超過）を満たすと data/kill.flag を書き、ExecutionEngine 側で停止を受ける仕組み
- PID ファイル: ExecutionEngine は起動時に PID ファイルを書きます。SystemMonitor はその PID を監視し、stale PID を検出すると削除してリスクイベントをログ化します
- DB マイグレーション: init_monitoring_db() はテーブル作成と簡易マイグレーション（カラム追加）を冪等に行います
- AI 呼び出し: OpenAI API はリトライ・バックオフを実装。API キー未設定時は例外を投げる（明示的に環境変数を設定してください）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                — パッケージ定義（version 等）
- config.py                  — 環境変数 / .env 自動読み込み / Settings クラス
- run_execution.py           — ExecutionEngine 起動用エントリポイント
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py              — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py       — マーケットレジーム判定（MA + マクロ NL 評価）
- monitoring/
  - monitoring_db.py         — SQLite 監視 DB の永続化層
  - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py         — 注文滞留・約定価格異常検出
  - risk_monitor.py          — ドローダウン / ポジション数監視
  - alert_manager.py         — LINE へプッシュ通知
  - kill_switch.py           — フラグファイルによる停止指示
  - monitoring_engine.py     — 各 Monitor をまとめる実行ループ
  - streamlit_dashboard.py   — Streamlit ベースの監視画面
- execution/
  - order_manager.py         — 発注フロー（状態遷移 / send / sync）
  - reconciler.py            — 起動時リコンシリエーション（注文・ポジション整合）
  - ...（broker_factory, execution_engine, order_repository 等を含む）
- portfolio/
  - portfolio_builder.py     — 候補選定、等配分・スコア配分
  - position_sizing.py       — 株数計算（単元丸め、スケーリング）
  - risk_adjustment.py       — セクターキャップ、レジーム乗数
- research/
  - factor_research.py       — モメンタム / ボラティリティ / バリュー計算（DuckDB）
  - feature_exploration.py   — 将来リターン・IC・統計サマリー等
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - process_priority.py      — プロセス優先度・CPU affinity ユーティリティ
- data/                      — （運用時に作成される DB / PID / flag 等を格納する想定ディレクトリ）

開発メモ
--------
- Settings（config.py）はプロジェクトルート（.git または pyproject.toml）を探索して .env を自動読み込みします。テスト時に自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB は prices_daily / raw_financials / raw_news 等のリサーチ用データを保持します。AI モジュールは DuckDB 上の raw_news を参照してバッチで API を呼びます。
- 各モジュールは「DB 参照なし」か「副作用排除」な純粋関数群（portfolio, research の一部）として設計されており、単体テストが容易です。
- API 呼び出し（OpenAI など）はリトライロジックを持ち、失敗時は安全なフォールバック（0.0 等）をする設計です。

よくある起動例
---------------
- 監視（デフォルト 60 秒間隔）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード実行:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード検証（2026-04-01〜2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視 DB を指定）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

サポート / 拡張ポイント
-----------------------
- BrokerClientFactory によるブローカーインタフェースを追加すれば、他ブローカーへも接続可能です
- 単元（lot_size）を銘柄ごとに対応させる等、position_sizing の柔軟化が推奨されます
- AI モジュール（OpenAI）の出力検証・プロンプトの改善は精度向上に直結します

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンス・貢献方法等を記載してください）

以上。必要があれば README にさらに詳細な環境変数一覧、サンプル .env、ユニットテスト実行方法、CI 設定例などを追記します。どの情報を補足しますか？