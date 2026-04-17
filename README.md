# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 実行スクリプト群）

この README はリポジトリ内の主要モジュールを元に作成しています。各種ツール・監視・実行エンジン・研究用モジュールを含み、ローカル開発／ペーパートレード／本番（live）を想定した設定管理を備えます。

---

## プロジェクト概要

KabuSys は以下のような責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）と注文管理（発注は kabuステーション または MockBroker）
- 監視（System / Trade / Risk）と Kill Switch（フラグファイルによる停止）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算・セクターキャップ等）
- 研究用／分析用モジュール（DuckDB を用いたファクター計算・特徴量解析）
- AI 連携（OpenAI を用いたニュース NLP / 市場レジーム判定）
- 設定管理（.env 自動読み込み、対話式ウィザード、設定検証ツール）
- 各種ユーティリティ（プロセス優先度設定 等）

設計上のポイント：
- 本番 DB（monitoring.db）とペーパートレード DB（paper_trading.db）は分離されています。
- 時刻や日付の扱いでルックアヘッドバイアスを避ける方針（関数は date / target_date を引数で受け取る等）。
- フェイルセーフ：外部 API の失敗時は安全なデフォルト（例: macro_sentiment=0）やスキップで継続する設計。

---

## 機能一覧（抜粋）

- 実行系
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - ペーパートレード時は MockBroker を使用し DB を分離

- 監視系
  - SystemMonitor: CPU / メモリ / ディスク / プロセスの監視、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - MonitoringEngine: 各モニタを束ねたポーリングループ（python -m kabusys.run_monitoring）
  - KillSwitch: 条件に応じて data/kill.flag を書き込みエンジン停止をシグナル

- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等金額/スコア加重の重み計算
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数の適用（calc_regime_multiplier）
  - 株数算出（リスクベース・等配分・スコア配分）、単元株丸め、集約キャップ調整

- 研究・分析
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）等
  - DuckDB を用いた集計・分析を想定

- AI 連携
  - ニュース NLP（OpenAI）で銘柄ごとにセンチメントを計算・ai_scores へ書込
  - 市場レジーム判定（ETF の MA200 乖離 + マクロニュースの LLM スコア合成）

- 設定管理 / ツール
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ペーパートレード検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提: Python 3.9+（型アノテーション等を利用しています）

1. リポジトリをチェックアウトし、仮想環境を作成・有効化します。
   - 例（Unix/macOS）:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要なパッケージをインストールします（最低限）:
   - duckdb
   - psutil
   - openai (AI 機能を利用する場合)
   - PyYAML（設定検証で YAML 検証を行う場合に推奨）

   例:
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください。）

3. .env を作成します（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   - 対話ウィザードで JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等の必須値を設定してください。

   自動読み込み:
   - Settings モジュールはプロジェクトルートの .env を起動時に自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 設定の検証:
   - python -m kabusys.validate_config
   - 問題があればメッセージに従って修正してください。
   - --strict オプションで警告も失敗扱いにできます。

5. 初回起動前に data ディレクトリを作成しておくと安全です（DB ファイルの親ディレクトリなど）:
   - mkdir -p data

---

## 使い方（主要コマンド例）

- 環境ウィザード（.env を作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- Execution Engine（注文実行）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番とは分離）。
  - 実行中の PID は data/execution.pid に書き込まれます。停止は data/stop_requested.flag / data/kill.flag の設置で制御されます。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。
  - 監視は KABUSYS_ENV に関係なく本番 sqlite_path（デフォルト: data/monitoring.db）を使用します（監視データは本番 DB に保存）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを明示: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI 機能（プログラム呼び出し）
  - openai API を利用する関数は引数で api_key を受け取れます。引数未指定の場合は環境変数 OPENAI_API_KEY を参照します。
  - 例:
    - kabusys.ai.score_news(conn, target_date, api_key="sk-...")
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key="sk-...")

---

## 主要な環境変数（よく使うもの）

- KABUSYS_ENV
  - 値: development | paper_trading | live
  - 動作モードに影響（paper_trading は MockBroker / separate DB、live は本番）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用）
- LOG_LEVEL（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（0/1、起動時に kill.flag をクリアするか）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL（run_monitoring 用ポーリング秒数、デフォルト 60）
- OPENAI_API_KEY（AI モジュール利用時に必要）

注意:
- run_monitoring は「監視用 DB」を常に本番 sqlite_path に接続します（KABUSYS_ENV に依存しない）。一方、run_execution は paper_trading 時に paper_sqlite_path を使用します。

---

## 停止・Kill Switch の仕組み

- data/stop_requested.flag
  - run_execution / run_monitoring のループを外部から停止したい場合に利用されます（存在するとループが安全に終了します）。ファイルパスは各スクリプト内で定義されています。

- data/kill.flag
  - KillSwitch が条件（例: ドローダウン閾値超過）を満たすと作成され、ExecutionEngine に停止を促します。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされます（本番では 0 を推奨）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py     — 市場レジーム判定（MA200 + LLM）

  - monitoring/
    - monitoring_db.py       — SQLite ベースの監視ログ永続化
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — （アラート管理：未表示の実装あり）

  - execution/
    - （注文管理・ExecutionEngine 等の実装群）※今回の抜粋では参照あり

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定ロジック
    - risk_adjustment.py     — セクター制限・レジーム乗数

  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー 等

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/
  - （実行時に生成される DB / フラグ / pid 等。既定パス: data/*.db, data/*.flag, data/*.pid）

---

## 開発・運用時の注意点

- DB マイグレーション: monitoring_db.init_monitoring_db() は冪等で一部のカラム追加（ALTER TABLE）を行います。
- DuckDB と SQLite を併用：DuckDB は分析用、SQLite は監視・注文記録用の軽量永続化に使用されています。
- API キー管理: .env を絶対に Git にコミットしないでください。
- テスト: MonitoringEngine.run_once() 等を使うと単発実行のテストが容易です。
- 権限: set_process_priority() は権限が必要な操作を行う可能性があります。権限不足時は警告を出してスキップします。

---

## 参考コマンドまとめ

- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate

- 依存インストール（例）:
  - pip install duckdb psutil openai PyYAML

- .env 作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードのスナップショットに基づいて作成しています。実際の運用では各モジュール内のドキュメント・ログ出力を参照し、環境設定 (.env / config/*.yaml) を適切に整備した上で稼働させてください。必要であれば各モジュールの詳細マニュアル（API、設定項目の説明、監視閾値のチューニングガイド等）も作成できます。