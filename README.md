# KabuSys

日本株自動売買システムの軽量ライブラリ群 / 実行ユーティリティ群です。本リポジトリはトレード実行（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・リサーチ・AI（ニュース NLP / レジーム判定）などの主要コンポーネントをモジュール単位で提供します。

以下は本コードベースの概要・機能・セットアップ・利用方法・ディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的: 日本株の自動売買システムのコア機能（発注管理、リコンシリエーション、監視、ポートフォリオ構築、ファクター計算、ニュースセンチメント評価など）を提供する。
- 設計方針:
  - DB 層は SQLite（監視・注文ログ）と DuckDB（価格データ・リサーチ）を併用。
  - 多くのモジュールは副作用を避ける純粋関数で実装（ポートフォリオ計算やファクター等）。
  - Paper Trading 環境は本番 DB と分離して動作可能。
  - OpenAI API を利用した NLP 処理はフェイルセーフ（API失敗時はスコアを0にフォールバック、部分的失敗に耐える）。

---

## 主な機能一覧

- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 滞留注文（stale order）・約定異常価格検出
  - RiskMonitor: ドローダウン監視、ポジション数上限チェック、ダッシュボード更新
  - KillSwitch: 条件により `data/kill.flag` を書いて Execution を停止
  - AlertManager: LINE Push によるアラート送信（クールダウン付き）
  - Monitoring DB（SQLite）初期化・読み書きユーティリティ
  - Streamlit ベースの簡易ダッシュボード（読み取り専用）

- 実行（execution）
  - OrderManager: 注文状態遷移と DB 保存（重複防止）
  - Reconciler: 再起動時のブローカー照合・ポジション差分検出
  - ExecutionEngine（参照あり）: 発注セッション実行（コード内に起動スクリプトあり）
  - BrokerClientFactory: 本番/モック切替（KABUSYS_ENV=paper_trading 時に MockBroker を利用）

- ポートフォリオ（portfolio）
  - 候補選定、等金額・スコア加重配分
  - セクターキャップの適用、レジームに応じた乗数
  - 株数計算（リスクベース、ウエイトベース）、単元株丸め、aggregate cap の処理

- リサーチ（research）
  - ファクター計算（モメンタム／バリュー／ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - DuckDB を用いた SQL+Python の処理

- AI（ai）
  - ニュース NLP（OpenAI）による銘柄ごとのセンチメントスコア生成（ai_scores へ書き込み）
  - 市場レジーム判定（ETF ma200 とマクロニュースセンチメントの合成）
  - API 呼び出しはリトライとバックオフ、応答バリデーションを実装

- ツール（tools）
  - Paper Trading 検証レポート生成（データ抽出・指標算出・Pass/Fail 判定）
  - その他のユーティリティ群

---

## セットアップ手順（開発 / 実行前準備）

1. 前提
   - Python 3.10+ を推奨（typing 機能使用のため）。
   - SQLite は標準ライブラリで利用可能。
   - DuckDB、psutil、requests、openai、streamlit 等が必要。

2. パッケージインストール（例）
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要パッケージを個別に入れる場合:
     - pip install duckdb psutil requests openai streamlit

3. 環境変数 / .env
   - `.env` / `.env.local` をプロジェクトルートに置くと自動読み込みされます（デフォルト動作）。
     - 読み込み優先度: OS 環境変数 > .env.local > .env
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主な必須 / 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須な箇所で要求されます）
     - KABU_API_PASSWORD — kabuステーション API 用
     - OPENAI_API_KEY — OpenAI を使う機能（ai.news_nlp / ai.regime_detector）で必要
     - KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - PAPER_FILL_MODE — paper trading のフィルモード（instant/partial/never/reject）

   - .env のパースは export KEY=val、クォート、コメントなど一般的な形式に対応しています。

4. データディレクトリ
   - 多くのデフォルトファイルは `data/` 配下を想定します。必要に応じて作成してください（監視 PID / フラグ / DB）。
   - 例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag

---

## 使い方（主要スクリプト・API）

- 監視ループ起動
  - スクリプト: src/kabusys/run_monitoring.py
  - 実行:
    - python -m kabusys.run_monitoring
    - 環境変数でポーリング間隔を上書き: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 備考:
    - モニタリングは KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。
    - 起動時にプロセス優先度を "high" に設定する試みを行います（権限のない環境では警告のみ）。

- ExecutionEngine 起動
  - スクリプト: src/kabusys/run_execution.py
  - 実行:
    - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と完全に分離）。
    - 停止はプロジェクトルートの `data/stop_requested.flag` を作成することで行います（スクリプトは起動時にフラグがあれば起動しない）。

- Paper Trading 検証レポート
  - スクリプト: src/kabusys/tools/paper_verification_report.py
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB を明示する: --db path/to/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（avg, max, p95）などの検証レポートを標準出力に表示し PASS/FAIL 判定を行います。

- Streamlit ダッシュボード（監視可視化）
  - スクリプト: src/kabusys/monitoring/streamlit_dashboard.py
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で Monitoring DB を参照しダッシュボード表示を行います。

- AI 関連（プログラムからの呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...") で指定日のニュースをスコア化し ai_scores テーブルに書き込みます。
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...") で market_regime テーブルへ書き込みます。
  - 注意: OPENAI API キーまたは api_key 引数が必要です。API 失敗時は安全側にフォールバックしますが、キー未設定の場合は ValueError が発生します。

- ライブラリとしての利用（例）
  - ポートフォリオ構築:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

---

## 重要な挙動・注意点

- 環境判定
  - Settings.env は KABUSYS_ENV で制御。許容値は `development`, `paper_trading`, `live`。
  - paper_trading モードは発注のモック化と DB 分離を行います。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等的にテーブル作成と軽微なスキーマ追加（カラム追加）を実施します。既存の monitoring DB に対して後方互換的なマイグレーションを行います。

- PID / Stop / Kill フラグ
  - 実行エンジンは `data/execution.pid` を生成してプロセス存続を示すことが想定されています（PID ファイルが stale の場合は自動削除しアラート記録）。
  - `data/kill.flag` は KillSwitch が書き込む停止トリガー。`KillSwitch.clear()` で削除可能。
  - `data/stop_requested.flag` は run_monitoring / run_execution の外部停止要求フラグ（これが存在するとループを抜ける/起動を中止します）。

- OpenAI / ネットワーク呼び出し
  - API 呼び出しにはリトライ（指数バックオフ）とレスポンスバリデーションを導入していますが、APIキー漏洩や課金に注意してください。

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - utils/
    - __init__.py
    - process_priority.py           — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py              — Monitoring DB（SQLite）CRUD
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: execution_engine, broker_factory, order_repository 等を参照)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/                            — 実行時に用いる data/ 配下のファイル（DB・PID・フラグ等）

（上記は主要ファイルの一覧です。細かなモジュールはソース内にコメントで説明があります。）

---

## よく使うコマンドまとめ

- 依存ライブラリのインストール
  - pip install duckdb psutil requests openai streamlit

- 監視起動（デフォルト 60 秒間隔）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 開発者向けメモ

- Settings は自動で .env / .env.local を読み込みます（プロジェクトルートの検出は .git または pyproject.toml が基準）。
- .env のパースは export 形式やクォート、インラインコメント等に対応しています（細かい振る舞いは config._parse_env_line を参照）。
- 多くの DB 操作は冪等性（再実行可能）を想定して作られています。
- 外部 API（kabu ステーション・OpenAI・J-Quants）は環境変数設定とエラーハンドリングを前提にしています。

---

問題があれば、どのコマンドを実行したいか／どの機能を使いたいか教えてください。必要に応じて .env.example のテンプレートや実行例、トラブルシュート手順も作成します。