# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
このドキュメントはコードベースから読み取れる設計意図・起動方法・主要機能をまとめたものです。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド・ツール）
- 環境変数（主なもの）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意点

---

プロジェクト概要
- KabuSys は日本株向けの自動売買基盤です。信号生成 → ポートフォリオ構築 → 発注 → 監視／リスク管理／リコンシリエーションまでを含む構成を想定しています。
- コアは純粋関数群（ポートフォリオ構築・ポジションサイズ計算・リスク調整）、実行エンジン（ExecutionEngine）、監視系（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）、およびAI支援モジュール（ニュースセンチメント、レジーム判定）で構成されています。
- DuckDB を分析用データ（価格やファイナンス）に、SQLite を監視ログ・注文ログ等の永続化に使用します。

主な機能一覧
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等金額／スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - 単元株丸め、risk-based / equal / score 配分による株数計算（calc_position_sizes）
  - セクター上限適用（apply_sector_cap）
  - レジームに応じた乗数算出（calc_regime_multiplier）
- リサーチ（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の統計分析
- AI
  - ニュース記事のセンチメント評価（news_nlp.score_news）
    - OpenAI（gpt-4o-mini）を使い、銘柄単位で -1.0〜1.0 のスコアを ai_scores テーブルへ書き込む
  - マクロ + ETF MA200 による市場レジーム判定（regime_detector.score_regime）
- 実行・発注（execution）
  - Broker クライアント抽象化（本番 or paper_trading 用 Mock）
  - OrderManager / Reconciler による起動時リコンシリエーション・状態同期
- 監視（monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の検知 & risk_logs 登録
  - KillSwitch: 閾値超過で data/kill.flag を書き込み実行エンジン停止を促す
  - MonitoringEngine: 上記モニターを束ね定期実行
  - Streamlit ダッシュボード（監視 DB の可視化）
- 運用ツール
  - paper_verification_report: Paper Trading DB を解析し検証レポートを生成

セットアップ手順（簡易）
1. Python の仮想環境作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 必須（コード参照）: duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml がある想定です。なければ上記を参考に必要パッケージを追加してください。

3. 環境変数設定
   - リポジトリルートに .env を作成することを想定（config.py に .env / .env.local 自動読み込みの処理あり）。
   - 自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データディレクトリ
   - デフォルトで data/ 以下に DB や PID / flag ファイルを置きます（存在しない場合は作成してください）。
   - 例: mkdir -p data

使い方（起動コマンド・ツール）
- 実行エンジン起動 (ExecutionEngine)
  - スクリプト: src/kabusys/run_execution.py
  - 実行例:
    - python -m kabusys.run_execution
  - KABUSYS_ENV による挙動:
    - KABUSYS_ENV=paper_trading: MockBrokerClient を使用し data/paper_trading.db を利用（本番 DB と分離）
    - その他: 本番 DB（Settings.sqlite_path）を使用
  - 停止: data/stop_requested.flag を作成すると安全に停止できます

- 監視ループ起動 (SystemMonitor 単体)
  - スクリプト: src/kabusys/run_monitoring.py
  - 実行例:
    - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60秒）
  - 監視は本番 sqlite_path を環境にかかわらず使用します（運用監視は一元管理）

- Streamlit 監視ダッシュボード
  - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
  - 実行例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - ファイル: src/kabusys/tools/paper_verification_report.py
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで SQLite ファイルを指定可能

- AI 関連関数（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（DuckDBPyConnection）を受け取り DB に書き込みます。環境変数 OPENAI_API_KEY または引数で API キーを渡してください。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — 必須（Settings.jquants_refresh_token）
- KABU_API_PASSWORD — 必須（kabuステーション API 用）
- OPENAI_API_KEY — OpenAI 呼び出し時（AI モジュール）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- PAPER_TRADING_SQLITE_PATH — paper_trading 時の専用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE 通知）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

ディレクトリ構成（主要ファイル説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョンなど）
  - config.py — 環境変数の読み込み・Settings クラス（.env 自動読み込み挙動や各種パス設定）
  - run_execution.py — ExecutionEngine 起動スクリプト（スレッドで実行、stop flag を監視）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading DB を解析し検証レポートを標準出力に出す CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・スケーリング・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - ai/
    - news_nlp.py — ニュースを OpenAI でセンチメント化し ai_scores に書き込む処理
    - regime_detector.py — ETF MA200 とマクロニュースの LLM 評価を組み合わせてレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視テーブル作成・CRUD（MonitoringDB クラス）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — kill.flag 管理（ファイル書込で ExecutionEngine 停止シグナル）
    - alert_manager.py — LINE push による通知（クールダウン管理あり）
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py — 監視データの可視化（Streamlit）
  - execution/
    - order_manager.py / reconciler.py / order_repository.py / ... — 発注管理、リコンシリエーション等
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity の設定ユーティリティ

運用上の注意点
- Paper Trading と本番 DB は分離する（Settings.is_paper による切替）。paper_trading モードでは data/paper_trading.db を使用します。
- Monitoring 系は本番の monitoring DB（Settings.sqlite_path）を参照します。監視は環境にかかわらず本番の監視 DB を使う設計です。
- PID / stop / kill flag:
  - 実行エンジンは data/execution.pid を作成し、監視はこの PID ファイルを参照してプロセス生存をチェックします。
  - 停止要求は data/stop_requested.flag を作成することで行えます（run_execution / run_monitoring が検知して終了）。
  - kill.flag は KillSwitch により書き込まれ、外部的に ExecutionEngine の停止を要求するために利用されます。
- OpenAI 利用:
  - API 呼び出しはリトライやバックオフを実装していますが、APIキーとレート制限に注意してください。
  - レスポンスのバリデーションは厳密に行われ、不備の場合はそのチャンクをスキップするフェイルセーフ設計です。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルとインデックスを作成し、既存カラムがない場合は ALTER で追加する簡易マイグレーションを行います。

---

追加情報・貢献
- ドキュメントや実装に不明点がある場合は issue を作成してください。
- 実運用で使う場合はロギング設定・永続化・監視／アラートの設定を十分に行い、テスト用の paper_trading 環境で挙動を確認してください。

この README はコードベースの静的解析に基づいて作成しています。実際の開発ブランチや配布版では README の内容をプロジェクト固有の要件に合わせて更新してください。