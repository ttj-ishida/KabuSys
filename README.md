KabuSys — 日本株自動売買フレームワーク
=================================

このリポジトリは日本株向けの自動売買（Execution）・監視（Monitoring）・リサーチ（Research）・AI（ニュースNLP / レジーム判定）などの機能を提供する軽量なフレームワーク群です。モジュールは可能な限り純粋関数／副作用の少ない設計を志向しており、SQLite / DuckDB をデータ永続化に用います。

要点
- 実稼働用（live）・ペーパー取引（paper_trading）・開発（development）を環境変数 KABUSYS_ENV で切り替え可能
- 監視（MonitoringEngine）により実行プロセス・注文滞留・ドローダウン等を定期チェックし、LINE への通知や kill.flag による ExecutionEngine 停止を行える
- ExecutionEngine はブローカークライアント（実ブローカー or Mock）経由で発注を行い、Reconciler による起動時リコンシリエーションを実装
- DuckDB を用いたファクター計算・リサーチ機能、OpenAI を利用したニュースセンチメント評価・市場レジーム判定を含む

主な機能
- execution
  - ExecutionEngine（発注・リスク管理・注文管理）
  - OrderManager / OrderRepository / Reconciler（起動時の自動同期）
  - ブローカークライアントの抽象化（実口座・Mock の切替）
- monitoring
  - SystemMonitor：プロセス状態、CPU/メモリ/ディスク、データ鮮度を監視
  - TradeMonitor：滞留注文、約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：フラグファイルにより ExecutionEngine を停止
  - AlertManager：LINE push によるアラート送信（クールダウン有）
  - MonitoringDB：監視ログ（SQLite）用の永続化層 + マイグレーション
  - Streamlit ダッシュボード（監視可視化）
- portfolio
  - 候補選定・重み計算・リスク調整・ポジションサイズ計算（純粋関数群）
- research
  - ファクター計算（Momentum / Volatility / Value）と特徴量解析（IC, forward returns, summary）
  - DuckDB 接続を受け取り SQL / Python で計算（外部 API なし）
- ai
  - news_nlp：raw_news を集約して OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores に保存
  - regime_detector：ETF の MA200 とマクロニュースセンチメントを合成して日次レジーム判定を行い market_regime に保存
- tools
  - paper_verification_report：ペーパー取引DBを解析して稼働率・注文成功率・レイテンシ等の検証レポートを生成

セットアップ手順（ローカル開発）
---------------------------------
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（例: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit
   - （実際のプロジェクトでは requirements.txt を用意して pip install -r requirements.txt）
4. 環境変数の設定
   - プロジェクトルートに .env（または .env.local）を配置すると自動読み込みされる（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 主要な環境変数（例・必須 / デフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用: default: data/paper_trading.db)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (アラート送信用、未設定なら送信はスキップ)
     - PAPER_FILL_MODE (paper_trading のフィルモード: instant | partial | never | reject）デフォルト "instant"
     - MONITOR_POLL_INTERVAL（監視ループ秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / CPU_THRESHOLD_PCT 等（監視閾値）
5. データディレクトリを作成
   - mkdir -p data

初期 DB 作成
- monitoring 用 SQLite テーブルは run_monitoring や run_execution 実行時に init_monitoring_db() によって自動作成・マイグレーションされます。

使い方（主要なコマンド）
-----------------------
- 監視ループを起動（常駐）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（例: MONITOR_POLL_INTERVAL=30）

- ExecutionEngine を起動（当日のセッション実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と分離します

- Streamlit 監視ダッシュボード（開発向け）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- AI 関連（プログラム的に利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（duckdb.connect(...)）と対象日を与えると ai_scores に書き込みます
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルに日次レジームを書き込みます
  - どちらも OPENAI_API_KEY を渡すか環境変数に設定する必要があります

設定ファイル / 環境変数の自動読み込み
----------------------------------
- config.Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。
- OS 環境変数は .env の値より優先され、.env.local は .env の上書きに使われます。
- 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py — パッケージメタ情報
- config.py — 環境変数・設定管理（.env 読込・Settings クラス）
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント取得（OpenAI 経由）、ai_scores へ書き込み
  - regime_detector.py — MA200 + マクロニュースで市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・読み書きラッパー（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 制御
  - alert_manager.py — LINE Push API 経由のアラート
  - monitoring_engine.py — 各 Monitor を束ねる実行ループ
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード（CLI 起動）
- portfolio/
  - portfolio_builder.py — 候補選定, 等配分・スコア配分
  - risk_adjustment.py — セクター制限・レジーム乗数
  - position_sizing.py — 株数計算・スケールダウン等
- research/
  - factor_research.py — Momentum / Volatility / Value の計算（DuckDB）
  - feature_exploration.py — 将来リターン計算・IC・統計サマリー
- execution/
  - order_manager.py — OrderState 管理・発注ワークフロー
  - reconciler.py — 起動時リコンシリエーション（OrderSent 照合・ポジション差分）
  - （その他 broker_factory, order_repository 等のモジュール群: ブローカ抽象化）
- tools/
  - paper_verification_report.py — ペーパー取引検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

運用上の注意 / ベストプラクティス
--------------------------------
- 本番運用では KABUSYS_ENV=live を設定し、監視プロセスと ExecutionEngine を別プロセスで運用してください。
- Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を参照する（安全性のため監視ログは本番 DB を参照する設計に注意）。
- paper_trading モードは本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使用します（デフォルト data/paper_trading.db）。
- OpenAI 呼び出しはネットワーク・レート制限等で失敗することを想定しており、フェイルセーフ（ゼロスコアでフォールバック、部分成功の保護）設計になっています。
- PID ファイル（Settings.pid_file_path）および kill.flag を使った外部停止制御をサポートしています。起動時のフラグクリア制御は Settings.kill_flag_clear_on_start をご確認ください。
- process_priority.set_process_priority を呼んでプロセス優先度を上げる（管理者権限が必要な場合がある）ため、権限に注意してください。

トラブルシューティング
---------------------
- DB テーブルがない / スキーマ不整合:
  - init_monitoring_db() が実行されていれば必要テーブルと簡易マイグレーションを作成します。権限・ファイルパスを確認してください。
- OpenAI API エラー:
  - API キーの有無、ネットワーク、レート制限を確認。ログは警告を出してフェイルセーフにフォールバックします。
- LINE 通知が送れない:
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID の設定を確認。未設定時は通知はスキップされログ出力のみになります。

拡張ポイント
-------------
- broker クライアントの追加（新しい証券会社 API）
- 単元株数や手数料モデルの銘柄別サポート
- Streamlit ダッシュボードの追加ウィジェット（グラフ等）
- CI 用のテストスイート（ユニットテスト / 統合テスト）

ライセンス / 貢献
-----------------
- 本 README はコードベースから自動作成されています。実際の公開時は LICENSE ファイル・CONTRIBUTING ガイドラインを追加してください。

以上。必要であれば README に含める環境変数の .env.example や具体的な起動コマンドのスニペット（systemd ユニット例 など）を追記します。どの部分を詳しく追記しましょうか？