# KabuSys — 日本株自動売買システム (README)

本リポジトリは日本株向けの自動売買・研究・監視コンポーネント群を収めたパッケージです。  
ここに含まれるのは ExecutionEngine（発注系）、Monitoring（監視系）、Research（ファクター計算／解析）、AI 補助（ニュース NLP / レジーム判定）、およびポートフォリオ構築ユーティリティ等です。

---

## プロジェクト概要

- 実運用を想定した自動売買フレームワーク（発注・リスク管理・監視・アラート）と研究用モジュール（ファクター計算、特徴量解析）を提供します。
- DuckDB を分析用DBとして利用し、SQLite を監視・トレードログ用 DB として利用します。
- ペーパートレード用の分離された DB と MockBroker をサポートし、本番 DB と完全に分離して検証可能です。
- OpenAI（gpt-4o-mini）を用いるニュース NLP / マクロセンチメント機能を備え、AI によるスコアリングやレジーム判定を行います。
- モジュール設計はパイプラインとユーティリティ関数を中心に純粋関数（副作用の少ない実装）で構成されています。

---

## 主な機能一覧

- Execution
  - 実際のブローカー接続（kabuステーション）またはペーパートレード用 MockBroker を使用した ExecutionEngine（発注、OrderManager、Reconciler、RiskManager 等）。
  - 起動・停止用の PID / Stop フラグ連携。
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文（stale）や約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、Dashboard 更新
  - KillSwitch: 条件により data/kill.flag を書いて Execution を停止
  - Monitoring DB 層（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard 等の永続化
  - MonitoringEngine: 上記をまとめてポーリング実行し、AlertManager を通じて通知
- Portfolio / Position Sizing
  - 候補選定（スコア順）、等分配・スコア重み配分、リスクベースの株数算出、セクターキャップ適用、レジーム乗数
- Research
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等
- AI
  - news_nlp: ニュース記事を集約して OpenAI に投げ、銘柄別センチメント ai_score を ai_scores テーブルへ書き込み
  - regime_detector: ETF の MA200 乖離とマクロセンチメントを合成して日次レジームを判定し DB に書き込み
- Tools
  - paper_verification_report: ペーパートレード DB を解析して運用検証レポートを生成

---

## セットアップ手順（開発 / 実行環境）

前提: Python 3.10+ を推奨します（typing 構文や型ヒントが利用されています）。

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール（最小セット）
   - pip install duckdb psutil openai
   - 監視用の YAML 検証を行う場合は PyYAML を追加: pip install pyyaml
   - テストや他のオプション機能がある場合は適宜追加

   （本リポジトリに requirements.txt がない場合は上記を参考にしてください）

3. プロジェクトルートに移動（.env 自動ロードはプロジェクトルートの検出に .git / pyproject.toml を使用）
   - KabuSys は起動時にプロジェクトルートを探索して .env / .env.local を自動ロードします。自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. .env の作成（対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します（機密情報を含むため .env を Git にコミットしないでください）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります: python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - デフォルトで使用されるディレクトリ: data/
   - 例: mkdir -p data

---

## 環境変数（主要項目）

- 必須（実運用 / 一部機能）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境指定
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading の場合、MockBroker が使用され、デフォルトで data/paper_trading.db に記録します（本番 DB と分離）。
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 SQLite、デフォルト: data/paper_trading.db)
- ログ・動作
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - PID_FILE_PATH, KILL_FLAG_PATH（監視・停止フラグ関連）
  - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒数 — run_monitoring 用環境変数）
  - PAPER_FILL_MODE（"instant" | "partial" | "never" | "reject"）

---

## 使い方（主要な起動コマンド / スクリプト）

- 環境構築（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH の DB に記録（本番 DB と完全分離）。
    - 起動時に data/execution.pid（デフォルト）へ PID を書きます。停止は data/stop_requested.flag を作成するか、KillSwitch による data/kill.flag により検出されます。
    - プロセス優先度を "high" に設定しようとします（psutil による設定、権限によっては失敗して警告）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず production sqlite_path を使用（monitoring 用 DB は本番 DB を想定）。
    - 停止は data/stop_requested.flag を作成することで行います。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を指定: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI / Research 関数（PythonAPIとして呼び出し）
  - news NLP スコア付け:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=...)  のように呼び出して ai_scores テーブルへ書き込み
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...) で market_regime テーブルへ書き込み
  - ファクター計算等は kabusys.research 下の関数を利用可能（DuckDB 接続を渡して実行）

- 停止・Kill Switch
  - KillSwitch（監視側）が条件を検出すると data/kill.flag を書き込み、ExecutionEngine は検出して停止します。
  - 手動で停止したい場合は data/stop_requested.flag を作るか実行プロセスへ KeyboardInterrupt を送ってください。

---

## 運用上の注意

- .env や API キーなど機密情報は絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを強く推奨します（自動クリアは危険）。
- Monitoring は run_monitoring の docstring にある通り、監視用 DB は環境にかかわらず本番 sqlite_path を参照します。ペーパートレードと監視 DB を分離したい場合は設定を調整してください。
- OpenAI API を使用する機能は、API キーの料金やレート制限に注意してください。429 / ネットワークエラー時にはリトライ実装がありますが、過度の呼び出しは避けてください。
- psutil によるプロセス優先度設定や CPU affinity の設定はプラットフォーム依存・権限依存です。設定に失敗した場合は警告を出してスキップします。

---

## 主要なディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイルとディレクトリの概要です。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings クラス（.env 自動ロード）
  - config_setup.py             — .env 作成ウィザード（対話式）
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ループ起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
  - execution/                  — 発注周り（OrderManager, OrderRepository, Engine 等）
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層（table 作成 / マイグレーション）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py          — （アラート送信ロジック、未掲示の実装ファイル）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — レジーム判定（MA + マクロセンチメント合成）
  - data/                       — 実行時に使用する data ファイル（data/kabusys.duckdb, data/monitoring.db, paper_trading.db 等）
  - tools/
    - paper_verification_report.py

（上記は主要モジュールの抜粋です。詳細はソースを参照してください）

---

## よく使うコマンド（まとめ）

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

## 補足 / 開発者向けメモ

- DuckDB 接続を受け取り SQL+Python で計算する設計が多く、研究目的の再利用性を重視しています。
- AI 呼び出し部分は外部 API（OpenAI）に依存します。ユニットテスト時は _call_openai_api をモックする設計になっています。
- monitoring_db.init_monitoring_db は冪等でマイグレーション（カラム追加）を行うので、既存 DB でも安全に呼べます。
- ペーパートレード用 DB / 本番 DB は分離する設計になっているため、誤発注リスクを低減できます。

---

必要であれば、この README に「セットアップの自動化用スクリプト例（docker-compose / systemd ユニット定義等）」や「.env.example のサンプル」「よくあるトラブルシューティング」を追加できます。どの情報を追記したいか教えてください。