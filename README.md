# KabuSys

KabuSys は日本株の自動売買（Execution）・監視（Monitoring）・リサーチ（Research）・AI（ニュースセンチメント・レジーム判定）などを含む小規模な自動売買フレームワークです。本リポジトリは純粋関数的なポートフォリオ構築、注文管理・リコンシリエーション、監視エンジン、Streamlit ダッシュボード、Paper Trading 検証ツール、OpenAI を使ったニュース NLP/レジーム判定機能などを提供します。

## 主な機能
- Execution
  - 注文作成・発注・状態管理（OrderManager、ExecutionEngine）
  - ブローカー抽象化（本番／モックの切替）
  - 起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager 等）
- Monitoring
  - システム状態（CPU/メモリ/ディスク）、Execution プロセス生存、データ鮮度監視（SystemMonitor）
  - 注文滞留・約定異常監視（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - Kill Switch（条件に応じて停止フラグを書き込み Execution を停止）
  - LINE によるアラート通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio（銘柄選定・配分・サイズ決定）
  - 候補選定、等金額／スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマン）等の統計ユーティリティ
- AI
  - ニュース記事を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に保存（news_nlp）
  - マクロニュース＋ETF MA200 乖離を合成した市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repository-url>

2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb psutil requests openai streamlit

   （requirements.txt がない場合は上記の主要依存をインストールしてください）

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置できます。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_FILL_MODE (instant | partial | never | reject) — デフォルト: instant
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用
     - LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

   例 .env スニペット:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリ作成
   - mkdir -p data

---

## 使い方（主要スクリプト）

- Monitoring（ポーリング監視ループ）
  - 目的: システム状態や注文状況を定期的にチェックしてログ/アラート/kill flag を扱う
  - 起動:
    - python -m kabusys.run_monitoring
  - オプション / 挙動:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（monitoring 用 DB は常に設定の SQLITE_PATH）。
    - 停止はプロジェクトの data/stop_requested.flag を作成することで行えます。

- Execution（発注エンジン）
  - 目的: ブローカーとやりとりして注文を実行・管理する
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper Trading 用の別 SQLite（PAPER_TRADING_SQLITE_PATH）にデータを書きます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
    - 実行中は data/execution.pid に PID を書く実装になっています（PID ファイル経由で生存チェックを行います）。

- Streamlit ダッシュボード（監視）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、ダッシュボード表示を行います。

- Paper Trading 検証レポート生成
  - スクリプト:
    - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、Pass/Fail 判定を標準出力に表示します。

- AI 機能（ニュース NLP / レジーム判定）
  - 必要: OPENAI_API_KEY（引数で渡すことも可能）
  - 関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - モデル: gpt-4o-mini を想定（JSON Mode を使用）。API エラーはリトライやフェイルセーフ（失敗時には中立値を採用）を備えています。

---

## 停止・強制停止機構
- data/stop_requested.flag
  - run_monitoring と run_execution はこのファイルの存在を検知してループを止めます（運用側からの優しい停止）。
- Kill Switch（kill.flag）
  - RiskMonitor → KillSwitch の評価で条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine 側で検知して停止します。
  - KillSwitch は書き込み時に理由を記載します。

---

## 設定（Settings）
設定の処理は kabusys.config.Settings クラスで行われます。主なプロパティ:
- jquants_refresh_token, kabu_api_password（必須）
- kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
- line_channel_access_token, line_user_id
- duckdb_path（デフォルト: data/kabusys.duckdb）
- sqlite_path（監視用デフォルト: data/monitoring.db）
- paper_sqlite_path（Paper Trading 用デフォルト: data/paper_trading.db）
- pid_file_path, kill_flag_path, kill_flag_clear_on_start
- paper_fill_mode（instant|partial|never|reject）
- KABUSYS_ENV（development | paper_trading | live）
- LOG_LEVEL

.env の自動読み込みについて:
- プロジェクトルート（.git または pyproject.toml を基準）から .env（デフォルト）と .env.local（存在すれば上書き）を自動で読み込みます。
- OS の環境変数は保護され、.env で上書きされません（.env.local は override=True ですが protected keys は上書きしない）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 設定 / 環境変数ローダ
  - run_monitoring.py — Monitoring 用起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・永続化層
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション監視
    - kill_switch.py — kill.flag の作成・管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, ...
    - broker_factory.py, execution_engine.py, order_record.py, ...
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI 呼び出し）
    - regime_detector.py — レジーム判定（ETF + マクロニュース）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - data/ (ランタイム用：PID/flag/DB ファイル置き場を想定)
    - stop_requested.flag, kill.flag, execution.pid, monitoring.db, paper_trading.db, kabusys.duckdb, ...

---

## 運用上の注意
- 監視（Monitoring）は監視用 DB（SQLITE_PATH）へログを書き込みます。monitoring は本番 sqlite_path を使用する設計になっているため、環境切替に注意してください。
- Paper Trading（KABUSYS_ENV=paper_trading）では実際のブローカーアクセスをモック化しており、paper_trading DB（PAPER_TRADING_SQLITE_PATH）に全データを書きます。本番 DB を汚さないように分離されています。
- OpenAI を利用する機能は API キーが必須です。API レスポンスの JSON パース失敗や API エラーに対してはリトライや安全側のフォールバック（中立値）を行う実装になっていますが、API 利用料・レート制限等の管理は運用者側で注意してください。
- process priority / cpu affinity の設定は psutil を用いていますが、権限不足時や未対応環境では警告を出して実行を継続します。

---

## 参考コマンドまとめ
- 開発用 venv 作成:
  - python -m venv .venv && source .venv/bin/activate
- 依存インストール:
  - pip install duckdb psutil requests openai streamlit
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

必要であれば、導入用の .env.example や Docker / systemd ユニットのサンプル、依存関係をまとめた requirements.txt 形式のファイルも作成できます。どの追加ドキュメントを作成しましょうか？