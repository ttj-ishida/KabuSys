# KabuSys

日本株自動売買システムの一部（コアライブラリ・監視・検証ツール群）。

このリポジトリには、注文実行エンジン、監視（Monitoring）コンポーネント、ポートフォリオ構築ユーティリティ、リサーチ／AI モジュール、ならびに運用支援スクリプトが含まれます。

---

## プロジェクト概要

KabuSys は日本株自動売買を支援するモジュール群です。主な責務は以下のとおりです。

- 注文作成・送信・状態管理（Execution）
- 再起動後のリコンシリエーション（Reconciler）
- 実行系の安全監視（Monitoring）
- ポートフォリオ構築・配分・ポジション決定ロジック（Portfolio）
- ファクター計算・特徴量探索（Research）
- ニュースを用いた LLM ベースのセンチメント評価（AI）
- Paper Trading 用の検証レポート生成ツール
- 監視ダッシュボード（Streamlit）

設計方針として、可能な限りフェイルセーフ（APIエラー時はスキップ、ロールバック等）を重視し、ルックアヘッドバイアスを避ける実装になっています。

---

## 主な機能一覧

- Execution
  - OrderManager: 注文作成・送信・状態遷移管理
  - BrokerClientFactory 経由で実環境／モック切替（KABUSYS_ENV）
  - Reconciler: 再起動時の注文・ポジション突合

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限チェック、リスクイベントログ化
  - KillSwitch: flag ファイルを書いて ExecutionEngine を停止
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringEngine: 上記を束ねてポーリング実行
  - streamlit_dashboard: 監視用ダッシュボード（read-only SQLite 接続）

- Portfolio
  - 候補選定（スコア降順）、等重／スコア重み、リスクベース配分（position sizing）
  - セクター制限、レジーム乗数の適用

- Research
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）で評価して ai_scores に書き込む
  - regime_detector: ma200 とマクロニュースの LLM 評価を合成して市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポートを生成

---

## セットアップ手順（ローカル開発 / 運用向け）

前提: Python 3.10+（PEP 604 の `X | Y` 型表記を使用）、pip が利用可能であること。

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（例）。
   - pip install duckdb psutil requests openai streamlit

   （本プロジェクトの実際の requirements.txt がある場合はそちらを使用してください。）

3. プロジェクトルートに `.env`（または `.env.local`）を配置して環境変数を設定できます。
   - 自動ロードは、config.py がプロジェクトルート（.git か pyproject.toml）を検出した場合に行われます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 重要な環境変数（例）
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート送信用
   - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB DB パス（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading 時の fill 動作（instant|partial|never|reject）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など

5. データディレクトリ（data/）や DB ファイルの配置・書き込み権限を確認してください。
   - 例: mkdir -p data

注意: psutil によるプロセス優先度設定は OS に依存するため、権限不足で失敗することがあります（警告が出るのみで動作継続します）。

---

## 使い方（主要な起動コマンド）

- 実行エンジンの起動（本番/紙取引は KABUSYS_ENV で切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

  説明:
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil）。
  - paper_trading の場合、BrokerClientFactory が MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。

- 監視ループ起動（SystemMonitor 単体）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（秒、デフォルト 60）。

- Streamlit ダッシュボード（監視 DB を read-only で表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI/レジーム判定（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

  ※ 上記は DuckDB 接続（duckdb.DuckDBPyConnection）を渡して使用します。

---

## 環境設定のヒント / 運用上の注意

- .env の読み込み
  - config.Settings モジュールはプロジェクトルートを自動検出し `.env` / `.env.local` を読み込みます（OS 環境変数より優先度が低い）。
  - OS 環境変数を上書きしたくない場合は .env を編集してください。

- Paper Trading の分離
  - KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使って記録します。本番の monitoring.db と完全に分離される設計です。

- OpenAI 呼び出し
  - API 呼び出し（news_nlp / regime_detector）はリトライ・バックオフの実装があり、失敗時は安全側のフォールバック（例: macro_sentiment=0.0）を行います。
  - OPENAI_API_KEY を環境変数で設定してください。

- Kill Switch
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）に理由テキストを書き込むことで ExecutionEngine の停止を促します。
  - ExecutionEngine 側でこのファイルの存在をチェックして停止する実装が期待されます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db() は起動時にテーブルを作成し、必要に応じて既存テーブルへカラム追加（migrations）を行います（冪等）。

---

## ディレクトリ構成（主要ファイル）

概略:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリングスクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - broker_factory.py (実装参照)
    - execution_engine.py (実装参照)
    - order_manager.py          — OrderManager（状態遷移・送信）
    - order_repository.py       — SQLite を使った注文永続化
    - reconciler.py             — 再起動時の同期処理
    - risk_manager.py (実装参照)
    - order_record.py (実装参照)
    - ...
  - monitoring/
    - monitoring_db.py          — monitoring DB（SQLite）読み書き層
    - system_monitor.py         — システム・データ鮮度監視
    - trade_monitor.py          — 注文滞留・約定異常監視
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag 作成・管理
    - alert_manager.py          — LINE アラート送信
    - monitoring_engine.py      — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py    — 監視ダッシュボード
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 発注株数計算・スケーリング
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — momentum/value/volatility 計算
    - feature_exploration.py   — 将来リターン・IC・統計
  - ai/
    - news_nlp.py              — ニュースを LLM でスコアリング
    - regime_detector.py       — マクロ + MA200 によるレジーム判定
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (デフォルトの DB・PID・フラグの保存先)
    - kabusys.duckdb (default DUCKDB_PATH)
    - monitoring.db (default SQLITE_PATH)
    - paper_trading.db (default PAPER_TRADING_SQLITE_PATH)

（注）上記以外に、実際の Broker / Engine 実装ファイルが存在します。各ファイルには docstring と詳細な設計注記が付与されています。コード内のコメントは設計目的・フェイルセーフの挙動を説明しています。

---

## よくある質問 / トラブルシュート

- 「.env が読み込まれない」
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env を配置してください。
  - 自動読み込みを無効化した場合（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）には手動で環境変数を設定してください。

- 「psutil の優先度設定でエラーが出る」
  - 権限が不足していると AccessDenied になり設定はスキップされます。警告ログだけ出力されますが処理自体は継続します。

- 「OpenAI 呼び出しで頻繁に失敗する」
  - ネットワーク・レート制限に対しては指数バックオフでリトライしますが、API キーや使用量制限を確認してください。

- 「監視 DB に接続できない（streamlit）」
  - MonitoringEngine を起動していない場合は DB が作成されていない可能性があります。また streamlit からは read-only URI（?mode=ro）で接続しているため、ファイルパスと権限を確認してください。

---

## ライセンス / 貢献

この README はコードベースのドキュメント用であり、実際のライセンスやコントリビュート手順はリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば、以下の内容を追加で作成できます：
- 詳細な設定ファイル (.env.example) のテンプレート
- systemd / supervisor 向けのユニットファイル例（監視・実行の永続化）
- 開発用テスト手順・ユニットテストの説明

どの追加ドキュメントが必要か教えてください。