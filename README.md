# KabuSys

軽量な日本株自動売買システムのコアライブラリ。  
このリポジトリは、監視（Monitoring）、発注実行（Execution）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買に必要な以下の機能をモジュール化して提供します。

- シグナルに基づく銘柄選定・重み付け・株数計算（Portfolio）
- 注文管理・リスク管理・ExecutionEngine（発注エンジン、paper/live 切替対応）
- システム監視・トレード監視・リスク監視（監視エンジン）
- ニュースの LLM（OpenAI）を用いたセンチメントスコアリング / レジーム判定（AI）
- DuckDB / SQLite を用いたデータ処理・ログ永続化
- 簡易的な CLI ユーティリティ（.env ウィザード、設定検証、レポート生成）

設計方針の一部：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV=paper_trading）
- ルックアヘッドバイアス対策のため日付参照は明示的な引数で行う
- フェイルセーフ：外部 API 失敗時はデフォルト値で継続する箇所あり

---

## 主な機能一覧

- CLI / スクリプト
  - .env 対話式ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution エンジン起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

- ポートフォリオ構築
  - 候補選定（スコア降順）、等金額・スコア加重の重み算出
  - セクター上限チェック、レジーム乗数
  - 株数算出（リスクベース / 等配分 / スコアベース）、単元丸め、集約キャップ処理

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ

- AI（OpenAI）
  - ニュースを銘柄別に集約して LLM に投げ、銘柄ごとのセンチメントを ai_scores テーブルへ書込
  - マクロニュース＋ETF MA を使った市場レジーム判定（bull/neutral/bear）

- 監視
  - system_status / trade_logs / risk_logs / positions / dashboard テーブルによるログ化
  - ドローダウンやポジション上限を監視して kill.flag を書き込み（Execution 停止トリガ）
  - モニタリングループは外部フラグで停止可能（data/stop_requested.flag）

---

## セットアップ手順

1. リポジトリをクローン・作業ディレクトリへ移動
   - (任意) 仮想環境を作成・有効化

2. 依存パッケージのインストール（最低限）
   - duckdb, psutil, openai が主要依存です。PyYAML は設定検証時にあれば YAML のパース検証を行います。
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```

3. .env の初期作成（対話ウィザード推奨）
   - 実行:
     ```
     python -m kabusys.config_setup
     ```
   - ウィザードは .env を生成します（.env はリポジトリにコミットしないでください）。

4. 必須環境変数（.env に設定）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合必須）
   - その他（任意）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の MockBroker 振る舞い。instant|partial|never|reject）
     - LOG_LEVEL（例: INFO）

5. 設定検証（任意だが推奨）
   - 実行:
     ```
     python -m kabusys.validate_config
     ```
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリ等の作成
   - 通常スクリプトが起動時に必要ディレクトリを生成しますが、手動で logs/ や data/ を作成しておくと権限問題を避けられます。

注意:
- 自動的に .env を読み込む機能が有効（プロジェクトルートが特定できる場合）。テストで無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方

基本的なコマンド例を示します。

- .env 対話式作成
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 本番 / paper_trading は KABUSYS_ENV に依存します。paper_trading の場合は MockBrokerClient として data/paper_trading.db に記録されます。
  ```
  python -m kabusys.run_execution
  ```
  - 実行中は data/execution.pid に PID を書きます。停止は監視側が kill.flag を書くか（monitoring の KillSwitch）、またはデータディレクトリ内に stop_requested.flag を作成すると検知して終了します。

- Monitoring 起動
  - 監視ループのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。ただし 1 未満の値は無効でデフォルトにフォールバックします。
  - 監視は KABUSYS_ENV に関わらず production sqlite_path（SQLITE_PATH）を使用します（監視ログは本番 DB を使う想定）。
  ```
  python -m kabusys.run_monitoring
  # 例: 30秒間隔で起動
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 停止・Kill フラグ
  - Execution の即時停止トリガは data/kill.flag に理由テキストを書き込むことで発動します（KillSwitch が評価している場合）。
  - 外部的にプロセス全体を停止させたい場合は data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動で kill.flag をクリアします（本番では 0 推奨）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 指定しない場合: デフォルト DB パス data/paper_trading.db を参照
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で提供）。
  - AI 関連関数は kabusys.ai モジュールにあり、DuckDB 接続を渡して呼び出します。
  - 失敗時はフェイルセーフ（デフォルト値やスキップ）で継続する設計です。

ログ:
- setup_logging によって stdout と logs/<app_name>.log（日次ローテーション、30 日保持）に出力します。
- デフォルトログディレクトリ: logs/

注意点:
- run_monitoring は「監視」用途に特化しており、監視用 SQLite は KABUSYS_ENV に依らず本番 sqlite_path を使用します（監視の一貫性確保のため）。
- paper_trading 環境では発注は MockBroker によって行われ、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI を使う場合)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — instant | partial | never | reject（paper_trading 時の Fill 挙動）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1）

---

## ディレクトリ構成

概ねのソース配置は以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード CLI
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (not listed in snippets, assume present)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (not listed in snippets, assume present)
  - execution/
    - execution_engine.py (起動コードから参照)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/ (実行時に生成される想定)
    - monitoring.db (SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/ (デフォルト、ログファイル出力先)

（上記はコードスニペットに基づく抜粋表示です。実際のファイルはリポジトリツリーを参照してください。）

---

## 運用メモ / 注意事項

- 実行ユーザーにより psutil による優先度設定（nice/Windows priority）や CPU affinity の操作で権限が必要な場合があります。失敗した場合は警告を出してスキップします。
- Monitoring は監視ログを本番 sqlite DB に残す仕様になっています。paper_trading の監視も本番監視 DB を参照します（設計上の決定事項）。
- AI（OpenAI）を使う処理は API レート制限 / 一時エラーに対してリトライ実装がありますが、上限到達時は該当チャンクをスキップします。重要な運用では API 利用量とエラーハンドリングを監視してください。
- .env は機密情報（API トークン・パスワード等）を含むため、決して Git 等にコミットしないでください。
- config/*.yaml は設定ファイルのテンプレートや生成スクリプトが用意されている場合があります。validate_config は PyYAML がインストールされていれば YAML のパース検証も行います（未インストール時は警告を出してスキップ）。

---

必要があれば、README に含めるコマンドの詳細や実例（systemd / Supervisor 用のユニットファイル例、Dockerfile、CI 設定例）も作成します。どの情報を追加しますか？