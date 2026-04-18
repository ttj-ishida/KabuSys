# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ内ドキュメントです。  
この README はソースコード（src/kabusys 以下）を元に、プロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

※ 本 README はコードベースの理解を補助する目的で作成しています。実運用前に必ず `python -m kabusys.validate_config` 等で設定検証を行ってください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤で、主に以下の役割を持ちます。

- 戦略（ファクター計算・特徴量探索）を行う Research モジュール
- ポートフォリオ構築（候補選定・重み計算・株数算出）
- ExecutionEngine による発注処理（本番 / ペーパートレード対応）
- Monitoring によるシステム状態・注文状態・リスク監視とキルスイッチ制御
- AI モジュール（ニュースセンチメント、レジーム判定）による外部情報の取り込み
- 運用ツール（ペーパートレード検証レポート生成 等）
- .env ウィザード・設定検証用 CLI

設計方針の一部:
- DuckDB を分析用 DB、SQLite を監視/発注ログ用に利用
- Paper Trading は本番 DB と分離（デフォルトで `data/paper_trading.db`）
- OpenAI 経由の処理は失敗に寛容（フォールバックやリトライ実装あり）
- 全体的に「フェイルセーフ」を重視（部分的失敗が全体を止めない）

---

## 主な機能一覧

- Execution
  - ExecutionEngine による発注ワークフロー（kabuステーション API を利用）
  - Paper Trading モード（MockBrokerClient、専用 SQLite への記録）
  - リスク管理（RiskManager）や注文管理（OrderManager）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在 / データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、kill.flag の評価
  - MonitoringEngine: 各種モニタを束ねてポーリング、アラート通知連携

- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア重み）
  - ポジションサイズ算出（リスクベース・重みベース）
  - セクター集中回避、レジーム乗数

- Research
  - ファクター計算（モメンタム／バリュー／ボラティリティ）
  - 将来リターン計算、IC 計算、ファクター統計サマリ

- AI
  - news_nlp: OpenAI を使ったニュースセンチメントスコア算出（ai_scores テーブルに書込）
  - regime_detector: ETF (1321) の MA200 とマクロニュースから市場レジーム判定

- ユーティリティ
  - .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

---

## 必要条件（推奨）

- Python 3.10+
  - 型ヒントで PEP 604 の `X | Y` を使用しているため少なくとも 3.10 以上を推奨します。
- 必要パッケージ（最低限）
  - duckdb
  - psutil
  - openai
- 任意（機能による）
  - pyyaml（config/*.yaml の構文チェックに使用）
- その他
  - kabuステーション API や J-Quants API を使う場合はそれぞれの接続情報・資格情報が必要

具体的なインストール例（仮）:
- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate
- パッケージインストール（プロジェクトに requirements.txt が無い場合は個別インストール）
  - pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローンしてソースを取得する
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で `.env` を作成する場合、最低限以下の環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY（AI 機能を使う場合）
5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 必須環境変数の未設定やファイルパスの問題を検出します。
6. データディレクトリ作成
   - デフォルトでは data/ 以下に DB や PID/flag を配置します。必要に応じてディレクトリを作成してください（logging_setup が自動作成する場合もあります）。

補足:
- 環境変数の自動ロード:
  - プロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数が優先）
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
  - 読み込み順: OS 環境 > .env.local（上書き） > .env（初期設定）

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）

- データベース / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）

- ログ
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR（デフォルト: logs/）

- Monitoring
  - MONITOR_POLL_INTERVAL（秒、デフォルト: 60。run_monitoring で使用）

- Paper Trading
  - PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: instant）

- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY

- その他
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で消す（1）か否か（0, デフォルト0）

---

## 使い方（実行例）

注意: 各スクリプトはモジュールとして実行します（プロジェクトルートから）。

1. ExecutionEngine を起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
   - 環境変数設定例（ペーパートレード）:
     - export KABUSYS_ENV=paper_trading
     - export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - 起動:
     - python -m kabusys.run_execution
   - 特記事項:
     - run_execution は PID ファイルを生成し、data/stop_requested.flag の検出でエンジン停止をトリガーします。
     - PAPER_TRADING 時は MockBrokerClient を使用し、本番 DB とは分離されます。

2. Monitoring を起動（監視ループ）
   - ポーリング間隔上書き:
     - export MONITOR_POLL_INTERVAL=30
   - 起動:
     - python -m kabusys.run_monitoring
   - 特記事項:
     - Monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path（Settings.sqlite_path）を使って監視ログを保存します。
     - run_monitoring は data/stop_requested.flag によってループを終了します。

3. .env ウィザード（初期設定）
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL とする: python -m kabusys.validate_config --strict

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - --db PATH を指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を使います。

6. AI / レジーム判定等（コード呼び出し）
   - news_nlp.score_news(conn, target_date, api_key=None) — OpenAI キーは環境変数 OPENAI_API_KEY か引数で指定
   - regime_detector.score_regime(conn, target_date, api_key=None)

ログ:
- ログはコンソール（stdout）と日次ローテートされるファイル（logs/<app_name>.log）に出力されます。ログディレクトリは LOG_DIR またはデフォルト `logs/`。

kill / stop 方法:
- ExecutionEngine の停止は `data/kill.flag`（KillSwitch）や `data/stop_requested.flag` を用いて外部から指示できます。
- kill.flag は KillSwitch によって書き込まれると ExecutionEngine 側で検出され停止される設計です。

---

## 開発・運用上の注意

- データ鮮度・ルックアヘッド
  - Research / AI モジュールはルックアヘッドバイアスを避けるよう設計されています（内部で date.today()/datetime.today() を直接参照しない等）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は起動時に必須テーブルを冪等に作成し、簡単なマイグレーション（カラム追加）も行います。
- 権限・実行優先度
  - 実行スクリプトは起動時に set_process_priority("high") を呼び出そうとします。権限不足で設定できない場合は警告に留まります。
- フォールトトレランス
  - OpenAI 等外部 API 呼び出しはリトライ・フォールバック処理が組み込まれています。致命的な失敗でない限りシステム全体を停止させない設計です。
- 本番環境（KABUSYS_ENV=live）では kill_flag や LINE 通知設定などを慎重に扱ってください。validate_config は live 時のガードチェックを行います。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       — （コード内参照: 注文監視）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （コード内参照: アラート送信ロジック）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                    — (実行時に利用する DB / flag / pid がここに置かれる想定)
  - logs/                    — ログファイル出力先（デフォルト）

（上記はリポジトリに含まれる主なモジュールの概要です。詳細は各ファイル内の docstring / コメントを参照してください。）

---

## 参考コマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- Monitoring 起動:
  - export MONITOR_POLL_INTERVAL=60
  - python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README は現行ソースコードのコメント・実装に基づいて作成しています。詳しい API 仕様や戦略ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）が別途ある場合は、そちらも合わせて参照してください。質問や追記したい項目があればお知らせください。