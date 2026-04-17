KabuSys — README
===============

概要
----
KabuSys は日本株向けの自動売買 / 監視 / 研究ツール群です。本リポジトリは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）: 注文発行・リスク管理・復旧（Reconciler）など。
- 監視コンポーネント: システム状態・注文の滞留・リスク（ドローダウン等）を定期的にチェックし、ログ・アラートを出力。
- ポートフォリオ構築ユーティリティ: 候補選定・重み計算・単元丸め・リスク調整。
- 研究用モジュール: ファクター計算・将来リターン計算・IC／統計サマリ。
- AI 支援機能: ニュースのセンチメント評価（OpenAI）や市場レジーム判定。
- 運用ツール: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード等。

特徴
----
- モジュール設計でテスト可能・差し替え容易（Mock ブローカー等）。
- DuckDB / SQLite を用いたオンディスクデータ（時系列・ニュース・スコア等）の集計・参照。
- OpenAI（gpt-4o-mini 等）を使ったニュース NLP と冪等的な書き込みロジック。
- 監視と KillSwitch による自動停止（フラグファイル方式）と LINE 通知（AlertManager）。
- Paper Trading モードにより本番 DB と分離した検証が可能。

セットアップ
----------
前提:
- Python 3.9+（実装が型ヒントに依存）
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
（pip install -r requirements.txt があればそれを使ってください。なければ上記を個別にインストールしてください。）

1. リポジトリをクローン / 取得
   - ソースルートに移動します（src/kabusys がパッケージルートになるように）。

2. 環境変数 / .env
   - .env.example（存在する場合）を参考に .env を作成してください。主要な環境変数:

     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject、デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite ファイルパス（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - PID_FILE_PATH, KILL_FLAG_PATH 等（必要時に上書き可能）

   - config.py はプロジェクトルートの .env / .env.local を自動ロードします（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

3. データディレクトリ
   - data/ フォルダ（例: data/monitoring.db, data/kabusys.duckdb）を作成してください。初回起動時に監視 DB テーブルは自動作成されます。

使い方
------
主要な実行コマンド（パッケージとして実行する想定）:

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor を起動して定期的にチェックを行い、監視ログ（SQLite）へ保存します。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔(秒)を上書き可。デフォルト 60 秒。
  - 監視プロセスは data/stop_requested.flag を監視し、存在するとループを終了します。
  - 監視は config.Settings.env にかかわらず本番用 sqlite_path を使用します（監視ログは本番 DB に記録）。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 説明: ブローカークライアント生成、OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の run_session をスレッドで開始します。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に書き込みます。本番 DB と完全に分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。起動中は同フラグを監視して停止します。
  - 実行時に PID は data/execution.pid に書き込まれます（設定によって変更可）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視 DB（read-only）を読みダッシュボードを表示します。監視が動いていないと DB が空のことがあります。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 説明: paper_trading DB（data/paper_trading.db デフォルト）から指標を集計してレポート（標準出力）を生成します。

- AI 機能
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を利用する際は OPENAI_API_KEY を設定してください。
  - 失敗時はフォールバック（スコア 0.0）する実装で、安全性に配慮していますが API キーは必須です。

停止 / フラグ
- stop_requested.flag:
  - run_monitoring / run_execution は共にプロジェクト直下 data/stop_requested.flag を監視します。存在すると安全にシャットダウンを試みます。
- kill.flag:
  - KillSwitch（監視サブシステム）が書き込むことで ExecutionEngine に停止を指示します（デフォルトパスは Settings.kill_flag_path）。
  - KillSwitch は drawdown やポジション上限を基に条件成立時に flag を作成します。
- kill.flag の解除:
  - KillSwitch.clear() により削除できます。手動で消す場合は data/kill.flag を削除してください（運用上の注意: 理由を確認の上で削除してください）。

ログ・優先度
- 起動スクリプトは最初に set_process_priority("high") を呼ぶことでプロセス優先度を上げようとします。プラットフォーム制約や権限がない場合は警告が出ますが継続します。

データベース
- monitoring_db.init_monitoring_db は監視用 SQLite に必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を作成・マイグレーションします。run_monitoring/run_execution は自動で呼び出します。
- DuckDB は prices_daily, raw_financials, raw_news 等の分析データを格納する想定です（research / ai モジュールが参照）。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数 / 設定管理
- run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                  — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py                   — SQLite 永続化層（init / MonitoringDB）
- system_monitor.py                  — システム状態・データ鮮度監視
- trade_monitor.py                   — 注文滞留・約定異常監視
- risk_monitor.py                    — ドローダウン・ポジション上限監視
- kill_switch.py                     — フラグファイルによる停止シグナル
- alert_manager.py                   — LINE 通知用
- monitoring_engine.py               — 各 Monitor を束ねるエンジン
- streamlit_dashboard.py             — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py, order_repository.py, reconciler.py, execution_engine.py 等
  — 注文ライフサイクル、リコンシリエーション、ExecutionEngine（主要ロジックは同ディレクトリに集約）

src/kabusys/portfolio/
- portfolio_builder.py               — 候補選定・重み計算
- position_sizing.py                 — 株数決定・単元丸め・キャップ処理
- risk_adjustment.py                 — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py                 — モメンタム / ボラティリティ / バリュー等
- feature_exploration.py             — 将来リターン・IC・統計サマリ

src/kabusys/ai/
- news_nlp.py                        — ニュースセンチメント（OpenAI）処理
- regime_detector.py                 — ETF + マクロニュースでレジーム判定

src/kabusys/tools/
- paper_verification_report.py       — Paper Trading 検証レポート生成

src/kabusys/utils/
- process_priority.py                — プラットフォーム依存の優先度設定ユーティリティ

注意事項 / 運用メモ
-------------------
- Paper Trading モードは本番 DB と書き込みを分離する設計です。KABUSYS_ENV=paper_trading を指定すると paper_sqlite_path が使用されます。
- OpenAI を使う機能は API コストとレート制限に注意してください。実装はリトライとクリップ処理を行い、失敗時はフェイルセーフ（スコア 0.0 やスキップ）します。
- 監視と実行はフラグファイルで相互に制御できます。運用時はフラグの存在・理由を必ず確認してください。
- 各モジュールは副作用を抑え、DB 書き込みは明示的に行うよう設計されていますが、初期起動時には必ずバックアップと検証を行ってください。

サンプル: 簡単な起動手順
1. .env を準備して必要な環境変数をセット
2. duckdb / sqlite ファイルを所定の場所（data/）に配置または空ファイルを作成
3. 監視を起動:
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
4. 別ターミナルで実行エンジンを起動（paper_trading の例）
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
5. 検証レポート:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

貢献 / 開発
-----------
- コードはモジュール毎に分割されています。ユニットテストを書く場合は個々の純粋関数や I/O をモックしてテストしてください（例: OpenAI 呼び出しは patch 可能）。
- .env の取り扱いや DB パスは config.Settings を通じて取得するため、テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使い自動ロードを無効化することができます。

ライセンス
---------
（ここにプロジェクトのライセンスを記載してください）

問い合わせ
----------
（運用者・開発者・連絡先情報を必要に応じて追加してください）

以上。必要ならば README にサンプル .env.example、requirements.txt、運用手順の詳細（systemd ユニットや docker-compose 例など）を追加できます。どの情報を追加しますか？