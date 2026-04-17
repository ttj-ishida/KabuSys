# KabuSys

KabuSys は日本株向けの自動売買 / リサーチ / 監視を行う小規模なシステムです。本リポジトリには、発注エンジン（ExecutionEngine）、監視コンポーネント、ポートフォリオ構築ユーティリティ、リサーチ用ファクター計算、LLM を使ったニュースセンチメント評価などが含まれます。

以下はこのコードベースの概要、機能、セットアップ・使い方、ディレクトリ構成の説明です。

## プロジェクト概要
- 目的: 日本株の自動売買支援と、それに付随する監視 / リサーチ機能の提供
- 主な構成要素:
  - ExecutionEngine: ブローカーと連携して注文作成・管理を行うエンジン
  - Monitoring: システム状態・注文状態・リスク監視、アラート送信、kill スイッチ
  - Portfolio: 候補選定・配分・ポジションサイズ決定（純粋関数群）
  - Research: DuckDB 上の価格・財務データに対するファクター計算・解析
  - AI: OpenAI を用いたニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
  - Tools: Paper trading の検証レポート生成スクリプト等
  - Utils / Config: 環境変数読み込み、プロセス優先度設定などのユーティリティ

## 主な機能一覧
- 発注管理（OrderManager）:
  - signal から注文を作成し、ブローカークライアント経由で発注・状態同期を行う
  - Duplicate 検出、リコンシリエーション（Reconciler）機能
- モニタリング:
  - SystemMonitor: CPU / メモリ / ディスク / プロセス状態 / データ鮮度監視
  - TradeMonitor: 注文滞留（stale order）・約定価格異常監視
  - RiskMonitor: ドローダウン監視、ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: 上記 Monitor を束ねたポーリングループ、KillSwitch 評価、Alert 発行
  - AlertManager: LINE Messaging API 経由でアラートを送信（クールダウン管理あり）
  - Streamlit ダッシュボード: 監視情報の可視化（streamlit run で起動）
- Paper Trading / 検証:
  - mock ブローカーで分離された DB に記録（KABUSYS_ENV=paper_trading）
  - tools/paper_verification_report: 検証レポート生成（稼働率、注文成功率、レイテンシ等）
- リサーチ:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
- AI:
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとの ai_score を保存
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成しレジーム判定

## セットアップ手順（ローカル）
1. Python と仮想環境
   - 推奨: Python 3.10+
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（例）
   - 必須（ファイル内参照）: duckdb, psutil, requests, openai, streamlit
   - インストール例:
     - pip install duckdb psutil requests openai streamlit
   - （実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt を推奨）

3. プロジェクトをクローン / 配置
   - git clone <repo>
   - 作業ディレクトリはプロジェクトルートを想定（.env 自動ロード等に影響）

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data
   - デフォルト DB/ファイルパス:
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
     - PID/flag: data/execution.pid, data/kill.flag, data/stop_requested.flag

5. 環境変数 / .env
   - Settings クラスは環境変数を参照します。プロジェクトルートに .env / .env.local を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (news_nlp / regime_detector 用)
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - PAPER_FILL_MODE: instant | partial | never | reject (paper_trading 用、デフォルト: instant)
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - SQLITE_PATH: data/monitoring.db（監視 DB）
     - DUCKDB_PATH: data/kabusys.duckdb
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, CPU/Memory/Disk thresholds など
   - .env の書式は shell 形式（export KEY=val, コメント行 # をサポート）で、クォートやエスケープも処理します。
   - 簡単な .env 例:
     - KABUSYS_ENV=development
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=your_password
     - JQUANTS_REFRESH_TOKEN=your_token

6. DB 初期化
   - run_monitoring.py / run_execution.py は起動時に必要なテーブルを作成（init_monitoring_db）します。手動で作る必要は通常ありません。

## 使い方（主要コマンド）
- 監視ループ起動
  - デフォルト poll interval 60 秒（MONITOR_POLL_INTERVAL 環境変数で上書き可）
  - python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を参照します（環境にかかわらず本番 DB を使う設計）

- ExecutionEngine 起動
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_sqlite_path に記録（本番 DB と分離）
  - python -m kabusys.run_execution
  - 起動直後に data/stop_requested.flag が存在すると起動せず終了
  - プロセス優先度を High に設定します（可能な環境で）

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db で閲覧する SQLite DB を指定可能（既に起動中の MonitoringEngine が DB を作っている想定）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定

- AI / レジーム判定 / ニューススコア
  - kabusys.ai.score_news（内部 API）を利用。OpenAI API キーは OPENAI_API_KEY 環境変数または関数引数で指定
  - kabusys.ai.regime_detector.score_regime で market_regime テーブルへ書き込み

- 停止 / Kill Switch
  - 実行中プロセスの外部停止はフラグファイルを用います:
    - data/stop_requested.flag: 実行スクリプト（run_execution/run_monitoring）が検出して安全に終了
    - KillSwitch は内部的に data/kill.flag を書き込み、ExecutionEngine に停止を要求する
  - KillSwitch の評価条件は RiskMonitor の出力（ドローダウン超過、ポジション上限超過等）

## 注意事項 / 運用メモ
- 環境分離:
  - paper_trading モードは paper_trading 用 SQLite DB を使い、本番 DB と完全に分離するよう設計されています。
- DB マイグレーション:
  - init_monitoring_db は冪等でテーブル作成を行い、既存 DB に対する簡単なカラム追加（migration）ロジックも含みます。
- LLM 呼び出し:
  - OpenAI 呼び出しはリトライ処理、レスポンス検証、スコアクリッピング等の安全策を導入していますが、API キーの管理・利用には注意してください。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出します。管理者権限やプラットフォームによっては失敗する場合があります（警告ログのみ）。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数読み込み、自動 .env ロード（プロジェクトルート検出）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 切替あり）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
  - ai/
    - news_nlp.py: ニュースを OpenAI でスコア化して ai_scores に書き込む
    - regime_detector.py: MA200 + マクロニュースでレジーム判定
  - monitoring/
    - monitoring_db.py: SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py: CPU/メモリ/ディスク、プロセス・データ鮮度チェック
    - trade_monitor.py: 注文滞留・約定異常チェック
    - risk_monitor.py: ドローダウン / ポジション上限チェック
    - kill_switch.py: kill.flag の書き込み・管理
    - alert_manager.py: LINE push 通知
    - monitoring_engine.py: 各 Monitor をまとめる（run / run_once）
    - streamlit_dashboard.py: Streamlit ベースのダッシュボード
  - execution/
    - order_manager.py: 発注ロジックの外向き API
    - reconciler.py: 起動時リコンシリエーション（注文・ポジション突合）
    - order_repository.py, order_record.py, broker_factory.py, execution_engine.py ...（発注周りの実装）
  - portfolio/
    - portfolio_builder.py: 候補選定、配分（等金額・スコア重み）
    - position_sizing.py: 株数計算（risk_based / equal / score）
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py: 将来リターン計算、IC, ランク等
  - tools/
    - paper_verification_report.py: Paper trading の検証レポート生成スクリプト
  - utils/
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (実行時に使用する想定のディレクトリ。リポジトリには含まれないことが多い)
    - monitoring.db (SQLite)
    - paper_trading.db (paper_trading 用 SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid, kill.flag, stop_requested.flag

※ 実際のリポジトリには上記以外のファイルも存在する可能性がありますが、ここでは主要なモジュールを抜粋しています。

## よく使うコマンドまとめ
- 仮想環境作成:
  - python -m venv .venv && source .venv/bin/activate
- 依存インストール:
  - pip install duckdb psutil requests openai streamlit
- 監視開始:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒間隔を変更（例: MONITOR_POLL_INTERVAL=30）
- エンジン開始:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

---

この README はコードベースの主要動作と運用上のポイントをまとめたものです。詳細な API や設計仕様（StrategyModel.md や PortfolioConstruction.md 等）は別ドキュメントを参照してください。必要であれば README に加えてセットアップの自動化（Dockerfile / docker-compose / requirements.txt など）や運用手順書を追加します。どの情報を優先して追記しましょうか？