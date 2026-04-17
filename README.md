# KabuSys

日本株用の自動売買システム（ライブラリ/実行スクリプト群）です。  
本リポジトリはトレード実行、モニタリング、ポートフォリオ構築、リサーチ、AI を用いたニュース解析などを含むコンポーネントで構成されています。

- 対象 Python バージョン: 3.10+
- 主な依存ライブラリ（例）: duckdb, psutil, openai, pyyaml（任意）
  - 実行環境に応じて必要なパッケージをインストールしてください。

---

## プロジェクト概要

KabuSys は以下の機能群を備えたモジュール群です。

- ExecutionEngine: 発注ロジックとブローカークライアントを組み合わせて発注処理を行う（本番 / ペーパートレード切替あり）。
- Monitoring: システム状態、発注状態、リスク（ドローダウン・ポジション上限）を監視し、アラートや Kill Switch を管理。
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算、セクター制限、レジーム調整などの純粋関数群。
- Research: DuckDB を利用したファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ。
- AI: OpenAI を使ったニュース NLP（センチメント）や市場レジーム判定（gpt-4o-mini 等）。
- ツール: ペーパートレード検証レポート生成などのユーティリティスクリプト。
- 設定管理: .env のウィザード（config_setup）および起動前の設定検証（validate_config）。

---

## 主な機能一覧

- 実行（run_execution.py）
  - 本番 / ペーパートレード切替 (KABUSYS_ENV)
  - Paper 環境では MockBrokerClient を用い、paper_trading DB に記録
  - PID ファイル管理、停止フラグ（data/stop_requested.flag）に対応
- 監視（run_monitoring.py / monitoring/*）
  - CPU/メモリ/ディスク使用率、Execution プロセスの生存チェック、データ鮮度チェック
  - 注文滞留・約定価格異常の検出
  - リスク監視（ドローダウン、ポジション上限）と Kill Switch の発動
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
  - 監視ログは SQLite（defaults: data/monitoring.db）へ永続化
- ポートフォリオ（portfolio/*）
  - 銘柄候補選定、等重／スコア加重配分、ポジションサイズ決定（単元株丸め・資金制約考慮）
  - セクター上限適用、レジーム乗数
- リサーチ（research/*）
  - DuckDB と prices_daily / raw_financials を使ったファクター算出
  - 将来リターン計算、IC（Information Coefficient）など
- AI（ai/*）
  - ニュース記事をまとめて LLM に送信、銘柄別センチメント ai_scores に永続化
  - マクロニュースと ETF MA 乖離を組み合わせた市場レジーム判定
- ツール（tools/）
  - paper_verification_report: ペーパートレード DB から期間集計レポートを生成

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトし、Python 仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストールします（例）:

   ```bash
   pip install duckdb psutil openai
   # YAML 検証や一部ツール利用に PyYAML が必要な場合:
   pip install pyyaml
   ```

   ※ 実際の requirements.txt がある場合はそれを使用してください。

3. 環境変数の設定
   - 対話式ウィザードで .env を作成できます:

     ```bash
     python -m kabusys.config_setup
     ```

   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（例とデフォルト）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - OPENAI_API_KEY — AI モジュール利用時に必要
     - LOG_LEVEL — INFO 等
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）※ run_monitoring 用
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（開発用）

   - 自動 .env ロード
     - プロジェクトルートに .env / .env.local があれば自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。

4. 設定の検証（起動前確認）:

   ```bash
   python -m kabusys.validate_config
   # 警告を致命扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

基本的な起動コマンド例。

- ExecutionEngine を起動する（デフォルト: KABUSYS_ENV に依存）
  - ペーパートレードでは paper_trading 用 DB に分離され、MockBrokerClient が使われます。

  ```bash
  python -m kabusys.run_execution
  ```

  実行中の停止はプロジェクトルート data/stop_requested.flag を作成することで行えます（スクリプトは起動時に停止フラグが既にある場合は起動せず終了します）。PID は data/execution.pid に書き込まれます。

- Monitoring を起動する
  - Monitoring は KABUSYS_ENV にかかわらず production sqlite_path（SQLITE_PATH）を使用して監視ログを保存します。

  ```bash
  python -m kabusys.run_monitoring
  # ポーリング間隔を環境変数で上書き:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート生成

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを明示:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / リサーチのプログラム的利用（例）

  ```python
  from kabusys.ai import score_news
  # DuckDB 接続を作成して score_news(conn, target_date, api_key=...)
  ```

- .env の自動ロードを無効にしたいテスト等の場合:

  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

注意点 / 実行時の挙動
- run_execution と run_monitoring は起動直後にプロセス優先度を "high" に設定しようとします（psutil を利用）。OS によっては権限不足で失敗することがありますが、警告でスキップされます。
- run_monitoring は監視用 DB（SQLITE_PATH）を使用します。run_execution は KABUSYS_ENV=paper_trading の場合 PAPER_TRADING_SQLITE_PATH に接続します（本番 DB と分離）。
- Kill Switch は data/kill.flag を書き込み、ExecutionEngine 停止をトリガーします。kill.flag の自動クリア設定などは .env で制御可能です。

---

## よく使う環境変数一覧（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development|paper_trading|live) — デフォルト: development
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
- OPENAI_API_KEY — AI モジュールで必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
- LOG_LEVEL — INFO 等
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

---

## ディレクトリ構成（抜粋）

以下は主要モジュールの概観です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py
    - .env 読み込み、Settings クラス（環境変数ラッパー）
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（PID / stop flag 管理）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - ai/
    - news_nlp.py — ニュースを LLM でスコア化し ai_scores に書き込む
    - regime_detector.py — マクロセンチメント + ETF MA でレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite を使った永続化レイヤ
    - system_monitor.py — CPU/メモリ/データ鮮度 / PID チェック
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の読み書き
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート配信ロジック、未表示ファイル内）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...（発注周り）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定、資金制約、単元株丸め
    - risk_adjustment.py — セクター制限、レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

- data/
  - monitoring / paper_trading DB 等が置かれる想定（デフォルト: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
  - stop_requested.flag / kill.flag / execution.pid などフラグ / PID ファイル

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では、LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は live 時に追加の注意を出します。
- kill.flag / stop_requested.flag / execution.pid 等のフラグファイルは手動で操作できます。運用手順は運用ルールに従ってください。
- OpenAI を用いる機能は API キーが必要であり、コストとレート制限に注意してください。AI モジュールはリトライ・フォールバック実装を備えていますが、運用上の配慮は必要です。
- psutil によるプロセス優先度変更や CPU affinity の設定は OS 権限に依存します。権限がない場合は警告を出してスキップします。

---

## 追加情報 / 開発向け

- DuckDB 接続を渡して研究 / ファクター計算を行う実装になっているため、データパイプラインで prices_daily / raw_financials などのテーブルを準備すると研究コードを実行できます。
- 単体関数群（portfolio/*.py, research/*.py）は副作用を持たない純粋関数設計が基本です。単体テストが書きやすくなっています。
- .env.sample や config/*.yaml の生成スクリプトが存在する場合は利用してください（validate_config は config/*.yaml の存在とパースもチェックします）。

---

この README はコードベースの主要点をまとめたものです。詳細な実装や API の使い方は各モジュールのドキュメント（ソース内の docstring）を参照してください。必要であれば、起動手順の例や運用手順書のテンプレートを作成します。