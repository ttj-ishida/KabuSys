# KabuSys — README

以下はこのコードベース（KabuSys）の概要、機能、セットアップ手順、使い方、ディレクトリ構成の簡易ドキュメントです。

目的
- 日本株向けの自動売買 / リサーチ / モニタリング用ライブラリ兼実行フレームワーク。
- 発注ロジック、ポートフォリオ構築、リサーチ（ファクター計算）、AI（ニュース・レジーム判定）、監視（モニタリング・Kill Switch）などを含む。

主な特徴（機能一覧）
- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - 本番 / ペーパートレード（KABUSYS_ENV=paper_trading）を切替可能。ペーパートレード時は MockBrokerClient を使用して data/paper_trading.db へ記録（本番 DB と分離）。
    - プロセス優先度設定（高優先で実行）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止。
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor とそれらを束ねる MonitoringEngine
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL 環境変数で間隔指定、デフォルト 60 秒）
  - SQLite（監視ログ）／DuckDB（分析用）への永続化
  - Kill Switch（リスク条件で data/kill.flag を書き込む）
- ポートフォリオ構築
  - 候補選定、重み付け（等重・スコア重み）、ポジションサイズ計算（ロット丸め・リスクベース割当）
  - セクター集中制限やレジーム乗数適用
- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計算、統計サマリー
- AI（OpenAI 統合）
  - ニュース NLP（news_nlp）: raw_news を LLM に渡して銘柄ごとにセンチメントスコアを生成して ai_scores テーブルへ書き込み
  - レジーム判定（regime_detector）: ETF MA とマクロニュースの LLM スコアを合成して daily regime を判定・保存
- ツール
  - 環境設定ウィザード（config_setup.py）で .env を対話式作成
  - 設定検証 CLI（validate_config.py）で .env / config/*.yaml のチェック
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

前提 / 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能利用時に必要）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant | partial | never | reject。デフォルト: instant）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（本番で kill.flag を起動時に自動クリアするか、0/1）

セットアップ手順（概要）
1. リポジトリを取得
   - git clone ... (パッケージルートに README と src/ 等がある想定)
2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必須: duckdb, psutil
   - AI 機能を使う場合: openai（v1 SDK）など
   - 設定検証で YAML を使いたい場合: PyYAML
   例:
     pip install duckdb psutil openai pyyaml
   ※ 実際の requirements.txt があればそれを使ってください。
4. .env 作成（推奨）
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - 自動ロード: パッケージ起動時にプロジェクトルートの .env / .env.local が自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     python -m kabusys.validate_config --strict

実行方法（使い方）
- ExecutionEngine（発注実行）を起動
  - 本番/ペーパー切替は KABUSYS_ENV で制御
  - 起動:
    python -m kabusys.run_execution
  - 動作:
    - 起動時にプロセス優先度を "high" に設定
    - paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
    - 起動中に data/stop_requested.flag が作られると安全停止
  - PID/停止:
    - 実行時に data/execution.pid が使用されます（Settings.pid_file_path）
    - Kill Switch（data/kill.flag）により外部から停止指示を行えます

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を設定可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（監視 DB）を使い、duckdb は Settings.duckdb_path を使用
  - Monitoring は設定された KABUSYS_ENV に関わらず「本番 sqlite_path」を使って監視データを書きます（監視は本番 DB を参照する設計）
  - 停止フラグ: run_monitoring.py は data/stop_requested.flag を監視してループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime を呼び出す際は OPENAI_API_KEY を設定してください
  - OpenAI 呼び出しはリトライやバリデーションを備えていますが、API キー未設定だと例外が発生します

停止・Kill Switch（運用上の注意）
- 外部から ExecutionEngine を安全に停止するには data/kill.flag を書き込んでください（KillSwitch が検出すると停止シグナルを発行）。
- run_execution.py / run_monitoring.py はそれぞれ data/stop_requested.flag の存在を監視し、見つかれば終了します。
- Settings にて KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨。

主要コマンドまとめ
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定の読み込みと Settings クラス（.env 自動ロードロジック含む）
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュース NLU（OpenAI 連携、ai_scores 書込み）
    - regime_detector.py — マーケットレジーム判定（ETF MA + LLM マクロセンチメント）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite のスキーマ初期化 + 永続化層（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書込み / 評価
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信管理。ファイルは未表示部分）
  - execution/  (発注・注文管理関連)
    - order_repository.py, order_manager.py, execution_engine.py, reconciler.py, risk_manager.py, broker_factory.py, ...（実行ロジック全般）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数計算（ロット丸め、aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
    - __init__.py
  - monitoring/  （上記）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ （実行時に使うフラグや DB が置かれる想定）
    - stop_requested.flag, kill.flag, execution.pid, monitoring.db, paper_trading.db, kabusys.duckdb など

実装上の重要ポイント（運用メモ）
- Settings（config.py）は .env 自動ロードを行う（プロジェクトルートが検出できる場合）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能。
- run_monitoring.py の監視間隔は MONITOR_POLL_INTERVAL で上書き可能。0 以下や不正な値はデフォルト 60 秒にフォールバックする。
- Monitoring データベースは monitoring_db.init_monitoring_db() で必要テーブルを冪等に作成・マイグレーションする。
- AI 呼び出しは OpenAI の JSON モードを使い、レスポンスのバリデートやリトライ（429/タイムアウト/5xx）を行う。API キーは必須（引数で渡すか環境変数 OPENAI_API_KEY）。
- ExecutionEngine は paper_trading と本番 DB を分離しているため、ペーパートレードであれば本番 DB を汚さない設計になっている。
- process_priority.set_process_priority() により起動直後にプロセス優先度を上げる（プラットフォーム差分吸収済み、失敗は警告でスキップ）。

ライセンス・貢献
- （このリポジトリのライセンス情報や貢献方法があればここに記載してください）

問題・拡張案
- stocks マスタに lot_size を保持して銘柄ごとに単元を扱う拡張（position_sizing の TODO）
- price 欠損時のフォールバック価格戦略（risk_adjustment の TODO）
- alert_manager の通知チャネル拡張（LINE / Slack 等）

お問い合わせ
- 実装上の詳細や運用フローに関する質問があればリポジトリの issue や担当者に問い合わせてください。

以上。README に載せてほしい追加項目や実行例（.env の具体例、SQL スキーマサンプル、デバッグ手順など）があれば教えてください。