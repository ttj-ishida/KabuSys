# KabuSys

日本株自動売買システム（KabuSys）の簡易ドキュメント / README。  
このリポジトリは取引エンジン・監視・ポートフォリオ構築・リサーチ・AI・ユーティリティ等を含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステムです。主な役割は以下の通りです。

- ExecutionEngine：ブローカーと連携して注文を送信・管理（本番 / ペーパートレード対応）
- Monitoring：システム状態、注文状況、リスク監視、アラート送信
- Portfolio：銘柄選定・重み計算・ポジションサイズ計算（PortfolioConstruction.md ベースのロジック）
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI モジュール：ニュースセンチメント（OpenAI）を用いたスコアリング、レジーム判定
- Tools：ペーパートレーディング検証レポート生成など
- Utils：プロセス優先度設定などのユーティリティ

設計上の特徴：
- DuckDB / SQLite をデータ層に使用（prices_daily, raw_financials, raw_news 等を想定）
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV に応じて切替）
- 外部 API 呼び出し（OpenAI, ブローカー, LINE など）は明示的に分離しフェイルセーフ設計

---

## 主な機能一覧

- Execution
  - ExecutionEngine（起動 / セッション管理 / 停止フラグ対応）
  - BrokerClientFactory による本番 / モック切替（KABUSYS_ENV=paper_trading でモック）
  - 起動時のリコンシリエーション（Reconciler）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視
  - KillSwitch：条件に応じた停止フラグ（kill.flag）書き込み
  - AlertManager：LINE Push による通知とクールダウン制御
  - MonitoringEngine：各モニタを束ねるポーリングエンジン
  - Streamlit ダッシュボード（監視用の簡易 GUI）
- Portfolio
  - 候補選定、等配分・スコア配分、スコアが全て 0 のフォールバック
  - セクター制限の適用、レジーム乗数（bull/neutral/bear）
  - ポジションサイズ計算（リスクベース / 等配分 / スコア配分）
- Research
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - 将来リターン・IC・統計サマリ
- AI
  - news_nlp: raw_news を集約して OpenAI へ投げ、銘柄ごとのスコアを ai_scores に保存
  - regime_detector: ETF ma200 乖離 + マクロニュースセンチメントを合成して market_regime を算出
- Tools
  - paper_verification_report：ペーパートレード DB を集計して検証レポートを標準出力へ出力

---

## セットアップ手順（概略）

前提
- Python 3.10+ を推奨（typing の Union 型解析や新しい構文を想定）
- 必要なライブラリ（最低限の例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボード利用時）
  - （ブローカークライアント実装に応じた追加依存）

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成して依存をインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install duckdb psutil openai requests streamlit
   - 実プロジェクトでは requirements.txt を用意して pip install -r でインストールする想定です
3. データディレクトリ作成
   - mkdir -p data
4. 環境変数 / .env の準備
   - ルートに `.env` / `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 必須例（.env.example を参照する想定）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development  # development | paper_trading | live
     - PAPER_FILL_MODE=instant
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LOG_LEVEL=INFO
5. データベース初期化
   - Monitoring 用 SQLite は起動スクリプトで自動的に init_monitoring_db() が呼ばれマイグレーションされます
   - DuckDB データは外部プロセスや ETL パイプラインで用意してください（prices_daily, raw_financials, raw_news 等のテーブルが必要）

注意:
- process priority 設定（psutil を用いる）により管理者権限が必要な場合があります
- OpenAI / ブローカー API キーは環境変数で安全に管理してください

---

## 使い方（起動・主な操作）

※ 各スクリプトはパッケージモードで実行できます（プロジェクトルートで実行）。

1. ExecutionEngine を起動する
   - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替
   - コマンド例:
     - KABUSYS_ENV=development python -m kabusys.run_execution
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 特記事項:
     - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に書き込みます
     - 起動時に data/execution.pid が作成されるので、プロセス検出や stale PID の検出に使われます
     - data/stop_requested.flag が存在すると起動を中止または実行中に停止します

2. Monitoring（ポーリング）を起動する
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）
   - 実行例:
     - python -m kabusys.run_monitoring
   - 特記事項:
     - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path, デフォルト data/monitoring.db）を使用します（監視は常に本番データを対象とするため）
     - data/stop_requested.flag を作成すると監視ループが終了します

3. Streamlit ダッシュボード（監視 UI）
   - 実行例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only モードで SQLite を開いてダッシュボード表示します

4. ペーパートレード検証レポート生成
   - 実行例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション --db で DB パスを明示可能（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

5. AI モジュール呼び出し（ライブラリ API）
   - ニュースセンチメント付与:
     - from kabusys.ai import score_news
     - score_news(conn, target_date, api_key=None)  # api_key が None の場合は OPENAI_API_KEY を参照
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=None)

6. 強制停止 / キルフラグ
   - KillSwitch は条件に応じて data/kill.flag を書き込みます（ExecutionEngine 側で検知し停止する設計）
   - 監視/実行の即時停止には data/stop_requested.flag を作成してください（両スクリプトともこのフラグを監視し終了します）
   - kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）で管理されます

---

## 環境変数（主要なもの）

主要な環境変数（Settings で参照される）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能利用時に必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- PAPER_FILL_MODE (instant | partial | never | reject) — ペーパートレードの約定挙動
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — "1" で起動時に kill.flag を自動クリア
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視のしきい値（%）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

設定は .env / .env.local / OS 環境変数の順で取り込まれます（.env は自動読み込み。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・ディレクトリのツリー（src/kabusys 配下）。実際のプロジェクトには他のファイルやドキュメントが含まれる想定です。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — ペーパートレード検証レポート CLI
    - ai/
      - __init__.py
      - news_nlp.py                — ニュースセンチメント（OpenAI）
      - regime_detector.py         — レジーム判定（ma200 + マクロセンチメント）
    - monitoring/
      - __init__.py
      - monitoring_db.py           — SQLite ベースの永続層（テーブル作成、CRUD）
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
      - (broker_factory, execution_engine, order_repository などが存在する想定)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - monitoring/..., research/..., ai/... （上記参照）
- data/  — 実行時に使用する SQLite / DuckDB / PID / フラグファイル を格納する想定ディレクトリ

---

## 追加メモ / 運用上の注意

- DB 権限・バックアップ：SQLite / DuckDB ファイルは単一ファイルのため、バックアップやロックに注意してください（複数プロセスの同時書き込みは競合を招く可能性があります）。
- 権限：プロセス優先度や CPU affinity の設定は権限不足で失敗する場合があります（ログで警告されます）。
- フェイルセーフ設計：OpenAI API やブローカー API の失敗時は例外を極力吸収またはフォールバック値を用いる設計です。ログと risk_logs を確認してください。
- ログ：標準の logging を利用しています。LOG_LEVEL で出力量を調整してください。
- ペーパートレード：KABUSYS_ENV=paper_trading により本番口座と完全に分離された DB（PAPER_TRADING_SQLITE_PATH）に記録されます。実システム移行時は設定を慎重に確認してください。

---

この README はコードベースの抜粋から作成しています。実運用・開発の際は README に加えて以下の追加ドキュメントを用意することを推奨します：

- インストール用 requirements.txt / Dockerfile / systemd ユニットのサンプル
- API キー・シークレット管理方針
- 運用手順（起動・停止・ログローテーション・バックアップ）
- テスト手順および CI 設定

ご要望があれば、起動例（systemd 用ユニットファイル例、Docker Compose 構成、CI テストの雛形など）も作成します。