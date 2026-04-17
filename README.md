# KabuSys

日本株向け自動売買システムのコードベース。ポートフォリオ構築、発注/再同期、監視、Paper Trading の検証、ニュース NLP（OpenAI）を含むモジュール群を提供します。

以下は本リポジトリで提供される主な機能、セットアップ方法、使い方、ディレクトリ構成の説明です。

注意: 実行には外部ライブラリ（duckdb, psutil, openai, requests, streamlit など）が必要です。実運用での利用は適切な権限・環境で行ってください。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた自動売買基盤の部品群です。

- 戦略（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定・重み計算・株数決定）
- 発注実行（ExecutionEngine、OrderManager、Broker クライアント抽象）
- リコンシリエーション（再起動後の同期）
- 監視（System/Trade/Risk モニタ、Kill Switch、LINE 通知）
- Paper Trading 用ツール（検証レポート・専用 DB）
- AI モジュール（ニュースのセンチメント評価、レジーム判定）
- DuckDB / SQLite ベースのデータ操作ユーティリティ
- Streamlit ダッシュボードによる監視ビュー

---

## 機能一覧（ハイレベル）

- portfolio:
  - select_candidates / calc_equal_weights / calc_score_weights：候補選定と重み算出
  - calc_position_sizes：株数決定（リスクベース、等配分、スコア配分など）
  - apply_sector_cap / calc_regime_multiplier：セクター上限・レジーム乗数

- execution:
  - ExecutionEngine / OrderManager / Reconciler：発注・状態管理・再同期ロジック
  - Broker 抽象により paper_trading（モック）と live の切り替えをサポート

- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor：CPU・メモリ・ディスク、データ鮮度、滞留注文、約定異常、ドローダウンなどを監視
  - MonitoringDB：SQLite を用いた監視ログ永続化とマイグレーション
  - KillSwitch：しきい値超過時に data/kill.flag を生成して ExecutionEngine を停止
  - AlertManager：LINE Messaging API への一方向プッシュ通知（クールダウン機能付き）
  - MonitoringEngine：各モニタを束ねるポーリングループ
  - streamlit_dashboard.py：Streamlit による監視ダッシュボード表示

- ai:
  - news_nlp.score_news：ニュース集合を OpenAI に渡して銘柄ごとにセンチメントスコアを生成して ai_scores テーブルに保存
  - regime_detector.score_regime：ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して市場レジームを判定・保存

- tools:
  - paper_verification_report.py：Paper Trading の検証レポートを生成（稼働率・成功率・レイテンシ等）

- utils:
  - process_priority：プロセス優先度設定 / CPU affinity 設定ユーティリティ
  - config.Settings：環境変数 / .env ロードと設定アクセス

---

## セットアップ手順

1. Python 仮想環境作成（例）
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - requirements.txt があれば:
     - pip install -r requirements.txt
   - 無ければ少なくとも以下をインストールしてください:
     - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに .env を配置（任意）
   - .env.example を参考に必要な環境変数を設定します。
   - 自動読み込み: デフォルトで .env / .env.local をプロジェクトルートから自動ロードします。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 主要環境変数（代表例）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager による通知用（任意）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

5. データディレクトリ
   - data/ 以下に DB や PID / フラグファイルを配置します（自動作成されることが多い）。
   - 停止フラグ: data/stop_requested.flag（run_* スクリプトが監視する停止フラグ）
   - kill フラグ: data/kill.flag（KillSwitch が書き込む）

---

## 使い方

基本的な起動方法とツールの例を示します。

- 監視ループ（SystemMonitor 単独スクリプト）
  - 実行:
    - python -m kabusys.run_monitoring
  - オプション / 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。1 未満や不正値はデフォルト 60 秒にフォールバック。
  - 備考:
    - 監視は Settings の sqlite_path を常に本番パスとして使用します（KABUSYS_ENV に依存しない）。
    - プロセス優先度を "high" に設定する処理を含みます（psutil で可能な場合）。

- Execution（注文エンジン）
  - 実行:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離します。
    - 起動時に既に data/stop_requested.flag が存在すると起動せず終了します。
    - エンジンはデーモンスレッドで run_session を実行し、stop flag を検出すると停止します。
  - PID / stop フラグ:
    - PID ファイル: data/execution.pid（Settings.pid_file_path）
    - stop flag: data/stop_requested.flag

- Streamlit ダッシュボード
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - 監視 DB（SQLite）を読み取り専用で開き、ダッシュボード（Overview/Positions/Orders/System）を表示します。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 出力:
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを表示し PASS/FAIL を判定します。

- AI モジュール（ニュース NLP / レジーム判定）
  - 必要: OPENAI_API_KEY 環境変数（または関数引数）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を集計し LLM に渡して ai_scores に書き込みます。
    - バッチサイズ・トリム、リトライ、レスポンス検証を実装しています。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF(1321) の MA200 乖離 + マクロニュース LLM センチメントを合成し market_regime に保存します。
  - 注意:
    - API のレートリミットやネットワークエラーに対して指数バックオフリトライを行いますが、失敗時は安全側のフォールバック（例: macro_sentiment=0.0）で継続します。

- 設定アクセス
  - アプリケーション内では kabusys.config.Settings / settings を通して環境変数を参照します。
  - 自動で .env / .env.local をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

---

## 運用上の重要ポイント

- 環境切替:
  - KABUSYS_ENV により処理モードを切替（development / paper_trading / live）。
  - Paper Trading は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と分離します。

- フラグ・PID ファイル:
  - 起動中に data/stop_requested.flag を作成すると run_* スクリプトはループを終了します。
  - KillSwitch は条件が満たされると data/kill.flag を作成し ExecutionEngine に停止シグナルを出します（flag の存在は再書き込みを行わない）。

- モニタリング DB:
  - init_monitoring_db は必要テーブルを作成し、後方互換のための簡易マイグレーション（カラム追加）も行います。
  - MonitoringDB による write 操作はコミットされます。

- 通知:
  - AlertManager は LINE Push API を利用。token / user_id が未設定の場合は送信をスキップします。
  - 同一カテゴリ/レベルに対してクールダウン（デフォルト 30 分）を適用します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env ロードと Settings
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - data/ (想定)                   — DB/フラグ/PID 等（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定・制限チェック
    - risk_adjustment.py           — セクター制限・レジーム乗数
  - execution/
    - order_manager.py             — 発注の高レベル API
    - reconciler.py                — 起動時リコンシリエーション
    - (そのほか broker/ order_repository 等)
  - monitoring/
    - monitoring_db.py             — SQLite スキーマ定義・MonitoringDB
    - system_monitor.py            — システム・データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 出力ロジック
    - alert_manager.py             — LINE 通知
    - monitoring_engine.py         — 各 Monitor を束ねる
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - research/
    - factor_research.py           — モメンタム/バリュー/ボラティリティ計算（DuckDB）
    - feature_exploration.py       — 将来リターン・IC 等の解析ユーティリティ
  - ai/
    - news_nlp.py                  — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py           — レジーム判定（MA200 + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity

（リポジトリによっては他サブモジュール・ファイルが存在します）

---

## 開発向けの補足

- ログレベル: Settings.log_level から取得できます（DEBUG/INFO/WARNING/...）。スクリプト実行時に logging.basicConfig(level=logging.INFO) 等で設定されます。
- DB 操作: DuckDB は分析用テーブル（prices_daily, raw_financials 等）を想定。research モジュールは DuckDB 接続を受け取り SQL と Python を組み合わせて計算します。
- テスト可能性: OpenAI 呼び出しなどは個別関数（_call_openai_api 等）をモックできるよう設計されています。
- 安全設計: AI 呼び出し失敗時はフェイルセーフ（0 フォールバックや処理スキップ）する実装が多く採用されています。

---

必要な追加情報や README のカスタマイズ（例: 実際の requirements.txt の内容やデプロイ手順、CI/CD 設定など）を希望される場合は、環境（OS、Python バージョン、使いたい Broker 実装など）を教えてください。