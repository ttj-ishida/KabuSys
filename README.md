# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）。  
戦略用のファクター計算・ポートフォリオ構築、Execution エンジン、監視（Monitoring）、AI 補助（ニュース NLP / レジーム判定）、および運用支援ツールを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は、以下のようなコンポーネントを持つ自動売買プラットフォームの基盤です。

- データ解析 / 研究用モジュール（DuckDB を利用）
- ファクター・シグナル生成 / ポートフォリオ構築（純粋関数群）
- Execution エンジン（発注・Order 管理・リスク管理・Reconciler 等）
- 監視モジュール（System / Trade / Risk の監視、Kill Switch）
- AI モジュール（OpenAI を用いたニュースセンチメント / レジーム判定）
- 運用支援 CLI（.env ウィザード、設定検証、Paper Trading の検証レポート生成）

設計方針の例:
- 実行スクリプトは logging 設定やプロセス優先度設定を共通化
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db）
- ルックアヘッドバイアスに注意した時系列処理（target_date ベースで計算）
- フェイルセーフ（API 失敗時はフォールバックして継続）

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- Execution エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録
  - 停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御
- Monitoring 起動: python -m kabusys.run_monitoring
  - SystemMonitor をポーリングして system_status / risk_logs / trade_logs を更新
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.score_news: ニュース記事のセンチメントを OpenAI で評価し ai_scores に保存
  - kabusys.ai.regime_detector.score_regime: 市場レジーム判定（ma200 + マクロ記事の LLM 評価）
- 研究用モジュール:
  - kabusys.research.calc_momentum / calc_volatility / calc_value など
  - feature_exploration: 将来リターン、IC、統計サマリー
- ポートフォリオ構築:
  - 銘柄選定 / 重み付け / ポジションサイズ計算 / セクター制限 / レジーム乗数

---

## 要件

- Python 3.10 以上（型注釈のパイプ演算子などを使用）
- 主な依存パッケージ（用途）:
  - duckdb (分析 DB)
  - psutil (プロセス・リソース情報)
  - openai (OpenAI API クライアント) — AI 機能を使う場合
  - PyYAML（任意、validate_config の YAML 検証を行う場合）
- ほか標準ライブラリを多数使用

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ requirements.txt は本リポジトリに含まれていません。用途に応じて必要なパッケージを追加してください。

---

## セットアップ手順

1. リポジトリをクローン（またはソースを用意）
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数ファイル（.env）を作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - 重要な環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能を使用する場合）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。開発用）
4. 設定の検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. ディレクトリの確認（logs/ と data/ は起動時に作成されることが多い）
   - ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力
   - SQLite / DuckDB のファイルパスは .env で上書き可能

注意:
- 自動で .env をロードする機能がある（config.py）。テスト等で無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 本番運用時は KABUSYS_ENV=live にして、LINE 通知設定などを確認してください。

---

## 使い方（起動・主要コマンド）

- Execution エンジン起動（デーモン/プロセスとして実行する想定）:
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動時にプロセス優先度を "high" に設定します（可能な場合）。
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB に書き込みます。
  - 停止は data/stop_requested.flag を作成するか、Execution 側の kill flag（data/kill.flag）で制御します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）

- Monitoring 起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - SystemMonitor をポーリングして監視ログを SQLite に記録します。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数指定（デフォルト 60）。
  - 監視は MonitoringEngine の run の動作（例: AlertManager があれば通知発行）に従います。
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視データは本番 DB に集約）。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```bash
  # デフォルト DB を使う:
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ライブラリとして利用（例）:
  ```python
  from kabusys.portfolio import select_candidates, calc_equal_weights
  from kabusys.research import calc_momentum
  # DuckDB 接続を作成して calc_momentum(conn, date(...))
  ```

---

## 環境変数（主要なものとデフォルト）

- KABUSYS_ENV: execution 環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト、Monitoring 用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: INFO（デフォルト）
- LOG_DIR: logs（デフォルト）
- OPENAI_API_KEY: OpenAI を使う場合に指定
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリア（1: 有効 / 0: 無効）

詳細は `kabusys.config.Settings` のプロパティを参照してください。

---

## 運用上の注意

- Monitoring は監視データを sqlite に永続化します。初回起動時にテーブルが自動生成されます（init_monitoring_db）。
- Execution と Monitoring の停止・制御はフラグファイルで行います:
  - data/stop_requested.flag: 起動スクリプトが起動時に参照し、存在すると起動を抑止またはループを終了します。
  - data/kill.flag: KillSwitch によって書かれ、Execution 停止の合図となります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では推奨されません。
- AI 機能を有効にする場合は OPENAI_API_KEY を設定してください。API エラー時はフェイルセーフでスコアをスキップまたは 0 にフォールバックする実装です。
- ログは stdout とファイル（logs/<app_name>.log）に出力されます。ログディレクトリ作成に失敗した場合はコンソールのみとなります。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env ウィザード CLI
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — Execution 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — レジーム判定（ma200 + LLM）
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (想定)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルの抜粋です。詳細はソースを参照してください。）

---

## 開発者向けメモ

- DuckDB 接続を受け取って純粋関数的に計算するモジュール（research/**）はテストが容易です。
- monitoring/monitoring_db.py は DB マイグレーション（列追加）ロジックを含み、冪等に設計されています。
- AI 呼び出しはリトライ・バックオフ・レスポンス検証の手当てがされており、部分失敗時の DB 書換えロジックも注意されています。
- unit tests 用に OpenAI 呼び出しは内部で差し替え可能な設計（テスト時はモック推奨）。

---

## 参考コマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

質問や追加のドキュメント（API 仕様、各モジュールの詳細説明、運用手順書など）が必要であれば教えてください。README の内容を用途（開発者向け / 運用者向け / API リファレンス）に合わせて拡張できます。