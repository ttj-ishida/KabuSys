# KabuSys

日本株向けの自動売買 / 研究プラットフォームのサンプル実装です。  
このリポジトリは戦略やポートフォリオ構築、モニタリング、実行エンジン、AI を用いたニュース評価などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群で構成されています。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重みづけ、ポジションサイズ計算）
- 実行エンジン（発注・リスク管理・再整合）
- 監視（System / Trade / Risk のポーリングとアラート / Kill Switch）
- Paper Trading を想定した分離された DB と MockBroker のサポート
- OpenAI を使ったニュースセンチメント（AIモジュール）
- 設定ウィザード・構成検証・検証レポート等のユーティリティ

設計方針として、
- ルックアヘッドバイアスを避ける（date.today()/datetime.today() を直接参照しない設計）
- 本番 / ペーパー（paper_trading）を明確に分離
- フェイルセーフ（API 失敗時は安全側へフォールバック）
などが取られています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml のチェック）: python -m kabusys.validate_config
- 実行エンジン起動スクリプト（ExecutionEngine）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading DB に記録
- 監視ループ起動スクリプト（SystemMonitor ポーリング）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL で間隔上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築ユーティリティ
  - 候補選定・等金額/スコア加重配分・ポジションサイズ計算
  - セクター上限適用・レジーム乗数
- リサーチ / ファクター計算（Momentum, Volatility, Value 等）
- AI モジュール
  - kabusys.ai.news_nlp: ニュースを LLM でスコアリングして ai_scores に書き込む
  - kabusys.ai.regime_detector: MA200 とマクロニュースで日次レジーム判定
- 共通ユーティリティ
  - ロギングセットアップ（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
- 監視 DB（SQLite）永続化層（system_status / trade_logs / positions / risk_logs / dashboard）

---

## セットアップ手順

前提:
- Python 3.10 以上（type hint の構文などを使用）
- OS に応じた依存ライブラリのサポート（psutil 等）

1. リポジトリをクローン / 配置
   - 本 README はパッケージルート（src/ を含む構成）を前提とします。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 必須: duckdb, psutil, openai
   - 推奨: PyYAML（config/*.yaml のパース検証に使用）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   （requirements.txt がある場合は `pip install -r requirements.txt`）

4. 環境変数 (.env) の準備
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
   - 重要な必須環境変数
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - よく使うオプション（デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI モジュールを使う場合に必要

   - 自動読み込みについて:
     - パッケージはプロジェクトルート（.git または pyproject.toml がある階層）を探索し .env/.env.local を自動で読み込みます。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 設定の検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

6. data/logs ディレクトリなどが自動作成されます。ファイル権限に注意してください。

---

## 使い方（代表的なコマンド）

- 実行エンジン（Execution）
  - 本番 / ペーパートレードの動作を開始:
    ```
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite に記録し、本番 DB と完全分離されます。
    - 実行中に停止指示を出すにはプロジェクトルートの data/stop_requested.flag を作成します（run_execution/run_monitoring はこのファイルを監視して終了します）。
    - 実行中の PID は data/execution.pid に書き込まれます。

- 監視ループ（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60）。
  - 監視は常に本番 sqlite_path（settings.sqlite_path）を使用します（監視は環境に依存しない想定）。
  - 停止フラグ: data/stop_requested.flag

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能。

- AI モジュール（プログラムから呼ぶ）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - ニューススコア付与:
    ```
    from kabusys.ai import score_news
    # conn は duckdb 接続 (duckdb.connect(...))
    score_news(conn, target_date, api_key=None)
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=None)
    ```

---

## 主要な設定項目（.env の例）

例（.env）:
```
# 実行環境
KABUSYS_ENV=development

# J-Quants / kabuステーション
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# ログ
LOG_LEVEL=INFO
LOG_DIR=logs

# Kill switch 挙動
KILL_FLAG_CLEAR_ON_START=0

# OpenAI
OPENAI_API_KEY=sk-...
```

---

## 注意点 / 運用メモ

- Paper Trading（KABUSYS_ENV=paper_trading）では発注はモック化され、データは data/paper_trading.db に書かれます。本番 DB と分離されるため安全に検証できます。
- 監視コンポーネントは監視 DB（SQLite）に状態を永続化します。監視は常に本番 sqlite_path を参照します（監視設定は環境に依存しない想定）。
- Kill Switch:
  - KillSwitch は監視結果から条件を満たした場合 data/kill.flag を書き込み、ExecutionEngine 側がこれを検知して停止します。
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアは危険）。
- ロギング:
  - デフォルトで stdout と日次ローテートのファイル（logs/<app_name>.log）に出力します。LOG_DIR で変更可能。
- OpenAI:
  - LLM 呼び出しは外部 API への依存があり、429/ネットワーク/5xx をリトライする実装を備えていますが、API キー・レート制限・課金に注意してください。
- テスト / 開発:
  - 自動環境変数読み込みはプロジェクトルートを .git / pyproject.toml から推定して行います。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル）

（パッケージルート: src/kabusys/ 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義・永続化 API
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 発注ログに対する監視（滞留・約定異常等）※（実装参照）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - alert_manager.py       — （アラート送信管理: LINE 等）（実装参照）
    - monitoring_engine.py   — 各モニター束ねるループ

  - execution/
    - execution_engine.py    — 実行エンジン本体（run_session 等）
    - broker_factory.py      — ブローカークライアント生成（Mock or live）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py     — Momentum / Volatility / Value 等
    - feature_exploration.py — IC / 統計サマリ等
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
    - __init__.py

  - utils/
    - logging_setup.py       — 共通ロギング初期化
    - process_priority.py    — プロセス優先度設定（Windows / POSIX 対応）
    - __init__.py

- data/
  - (実行時に作成されるファイル)
  - stop_requested.flag      — 停止要求フラグ（run_* スクリプトで参照）
  - kill.flag                — KillSwitch による停止指示
  - execution.pid            — 実行エンジン PID
  - monitoring.db / paper_trading.db / kabusys.duckdb（デフォルトパスに対応）

---

## 開発者向けメモ

- DuckDB 接続を渡す設計により、リサーチ関数は副作用が少なくテストしやすいです。
- 多くの関数は「フェイルセーフ」で例外を内包し、監視やバッチ処理が単一失敗で停止しないよう配慮されています。
- 設定検証とウィザードを用意しているため、運用前に `python -m kabusys.validate_config` を実行して設定の整合性を確認してください。
- AI 関連機能は OpenAI の SDK 変更に追従する必要があるため、ユニットテストでは API 呼び出しをモックすることを推奨します（コード中でもモック用フックを明示しています）。

---

これで README の基本は以上です。追加で次の内容が必要であれば教えてください:
- より詳細な運用手順（systemd / Supervisor / Windows サービス 用の起動例）
- テスト手順・カバレッジ
- デプロイ手順（Docker / CI）