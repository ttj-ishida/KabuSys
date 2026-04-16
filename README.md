# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ兼ミニプロダクション実装）

このリポジトリは、シグナル → 発注 → 監視 → レポートまでを含むシンプルな自動売買基盤の一部実装です。戦略検証用のリサーチ / ファクタ計算、ポートフォリオ構築、発注エンジン、監視・アラート、Paper Trading 用ツールや Streamlit ダッシュボードなどを含みます。

主な設計方針
- DuckDB / SQLite をデータストアに利用（ローカルファイルベース）
- 本番（live）と Paper Trading（paper_trading）を分離可能
- 外部 API（kabuステーション、J-Quants、OpenAI 等）は設定により切替
- ルックアヘッドバイアス防止を重視（関数は date を引数で受け取る等）

対応 Python バージョン
- Python 3.10 以上を想定（型注釈に PEP 604 を利用）

---

## 機能一覧

- execution
  - ExecutionEngine：発注エンジン（ブローカークライアント経由で発注、OrderManager 等と連携）
  - Reconciler：再起動時の注文・ポジション突合（自動復旧）
  - RiskManager / OrderRepository / OrderManager 等の発注管理基盤

- monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / PID チェック
  - TradeMonitor：滞留注文・約定異常（価格逸脱）検出
  - RiskMonitor：ドローダウン・ポジション上限監視と dashboard 更新
  - KillSwitch：リスク条件から ExecutionEngine 停止用の kill.flag 書込み
  - AlertManager：LINE Push によるアラート発行（クールダウン管理）
  - MonitoringEngine：上記 Monitor を束ねるポーリングループ
  - streamlit_dashboard：監視 DB を可視化する Streamlit ダッシュボード

- portfolio
  - 銘柄選定・ウェイト算出（等配分・スコア配分）
  - セクター制限・レジーム乗数（calc_regime_multiplier）
  - 株数算出（position sizing、単元株丸め・aggregate cap）

- research
  - factor_research：Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を利用）
  - feature_exploration：将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ

- ai
  - news_nlp：OpenAI を用いたニュースセンチメント集計 → ai_scores テーブルへ書込
  - regime_detector：MA とマクロニュース（LLM）を合成して市場レジーム判定 → market_regime テーブルに書込

- tools
  - paper_verification_report：Paper Trading の検証レポート生成（稼働率 / 注文成功率 / レイテンシ等）

- utils
  - process_priority：プロセス優先度 / CPU affinity 設定ラッパー（Windows / POSIX 対応）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必須例（実行環境に応じて調整してください）:
     - pip install duckdb psutil requests openai streamlit
   - 実際のプロジェクトでは requirements.txt を用意してください。

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を作成すると自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 代表的な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（strategy / research 用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（broker）
     - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector を使用する場合）
     - KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

5. データディレクトリ
   - デフォルトでは data/ 配下に DB・PID・フラグファイルを作成します。適宜権限を確認してください。

---

## 使い方

注意：ここでは src 配下をモジュールパスとして利用する前提でコマンド例を示します（プロジェクトルートで実行）。

- 実行用エンジン（ExecutionEngine）を起動
  - 目的: 発注・セッション実行
  - コマンド:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が用いられ、データは paper_trading.db に記録され本番 DB と分離されます。
    - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
    - PID ファイルは data/execution.pid（Settings.pid_file_path）に書き込まれます。
    - プロセス優先度は開始時に "high" に設定されます（psutil を使用、失敗時は警告ログのみ）。

- 監視プロセス（MonitoringEngine / SystemMonitor のポーリング）を起動
  - コマンド:
    - python -m kabusys.run_monitoring
  - 挙動:
    - デフォルト 60 秒間隔で各種チェックを実行。MONITOR_POLL_INTERVAL で変更可能（整数秒）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用して monitoring DB に書き込みます。
    - data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポートを生成
  - コマンド例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - オプションで --db PATH を指定可能（PAPER_TRADING_SQLITE_PATH が優先されます）
  - 出力: ターミナルへ検証指標（稼働率、注文成功率、レイテンシ等）と PASS/FAIL 判定を表示

- Streamlit ダッシュボードで監視データを可視化
  - コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 機能: Overview / Positions / Orders / System タブ。監視 DB を read-only で開くため、MonitoringEngine 実行中に閲覧できます。

- AI 関連（ニューススコアリング・レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY（もしくは api_key 引数）が必要です。API エラー時はフェイルセーフで継続する設計（多くの場合 0.0 を使用して処理続行）。

- kill / stop フラグの利用
  - ExecutionEngine 停止トリガ:
    - data/kill.flag を作成すると KillSwitch 経由で ExecutionEngine の停止を促します（理由文字列をファイルに記録）。
    - run_execution は data/stop_requested.flag を監視して安全に終了します。
  - 手動解除:
    - data/kill.flag を削除するか、KillSwitch.clear() を呼ぶことでクリアできます（手動でファイル削除しても可）。

---

## 設定（Settings）について

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env を読み込みます。
  - OS 環境変数は保護され、.env.local は .env の上書きとして読み込まれます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 主な Settings プロパティ
  - env: KABUSYS_ENV（development | paper_trading | live）
  - is_paper / is_live / is_dev
  - sqlite_path, paper_sqlite_path, duckdb_path
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
  - paper_fill_mode: instant / partial / never / reject（Paper Trading の約定モード）

---

## 主要ファイル・ディレクトリ構成

（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数 / Settings 管理（.env 自動ロード等）
  - run_execution.py                     — ExecutionEngine 起動スクリプト
  - run_monitoring.py                    — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py       — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py                        — ニュースNLP（OpenAI）による ai_scores 書込
    - regime_detector.py                 — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py                   — monitoring DB 操作用ユーティリティ（SQLite）
    - system_monitor.py                  — システム状態 / データ鮮度監視
    - trade_monitor.py                   — 注文滞留 / 約定異常検出
    - risk_monitor.py                    — ドローダウン / ポジション上限監視
    - kill_switch.py                     — kill.flag 書込みユーティリティ
    - alert_manager.py                   — LINE Push 通知ラッパー
    - monitoring_engine.py               — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py             — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py               — 銘柄選定 / 等配分・スコア配分
    - position_sizing.py                 — 株数決定ロジック（丸め・aggregate cap）
    - risk_adjustment.py                  — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py                 — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py             — 将来リターン / IC / 統計サマリ
  - execution/
    - reconciler.py                      — 起動時の注文・ポジション突合
    - order_manager.py                   — 発注 API の上位ラッパー（状態遷移管理）
    - （その他 OrderRepository 等のモジュールが存在）
  - utils/
    - process_priority.py                — プロセス優先度 / CPU affinity 管理

---

## 運用上の注意 / ベストプラクティス

- 環境分離:
  - Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
  - 本番運用時は KABUSYS_ENV=live を設定し、適切なバックアップ・監視を行ってください。

- OpenAI の利用:
  - API 呼び出しにはコスト・レイテンシの問題があるため、実行頻度やバッチサイズに注意してください。
  - API 失敗時は多くの処理がフォールバック（0.0 やログ）で継続するよう設計されていますが、重要処理の場合は結果確認を推奨します。

- 権限:
  - process priority の変更や CPU affinity の設定は管理者権限が必要な場合があります。失敗時は警告ログが出ますが運用は続行します。

- ファイルフラグによる制御:
  - data/stop_requested.flag, data/kill.flag, data/execution.pid 等のファイルを用いてプロセスの起動・停止を管理します。CI / 運用スクリプトからこれらを操作することで安全に停止できます。

---

以上。さらに詳細なドキュメント（API リファレンス、設計ドキュメント、運用手順など）を追加したい場合は、項目ごとに追記可能です。必要な箇所（例えば .env.example、依存関係の固定、デプロイ手順など）があれば指示してください。