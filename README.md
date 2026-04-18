# KabuSys

日本株向け自動売買システムのコアライブラリ群と運用ユーティリティ群です。  
このリポジトリは発注エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント）などのモジュールを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントをモジュール化したライブラリ兼運用ツール群です。主な役割は以下の通りです。

- ExecutionEngine：発注ロジック、注文管理、リスク管理を統合して取引セッションを実行
- Monitoring：システム稼働状況・注文状況・リスク（ドローダウン・ポジション上限等）を定期監視し、Kill Switch を発動
- Portfolio construction：候補選定、重み付け、ポジションサイジング、セクター制約等の純粋関数
- Research：DuckDB 上の価格・財務データからファクター計算・統計解析
- AI：OpenAI API を利用したニュースセンチメント評価・市場レジーム判定
- ユーティリティ：設定 (.env) のウィザード、設定検証、ログ設定、プロセス優先度設定など

設計方針としては、環境変数・ローカル DB（SQLite / DuckDB）中心の実装で、外部 API 呼び出し（kabuステーション / J-Quants / OpenAI）を必要に応じて行います。Paper Trading モードでは本番 DB とは分離された専用 SQLite DB を使用します。

---

## 機能一覧

主要な機能を列挙します。

- Execution
  - BrokerClientFactory を通じたブローカークライアント生成（本番 / Mock）
  - OrderManager / OrderRepository による注文管理
  - RiskManager による資金・ポジション制約チェック
  - ExecutionEngine によるセッション実行・PID ファイル管理・停止フラグ対応
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス稼働確認
  - TradeMonitor：注文滞留や約定異常の検出（trade_logs を参照）
  - RiskMonitor：ドローダウン、ポジション数上限監視とリスクログ記録
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記を定期実行してアラート送信（AlertManager 経由）
- Portfolio
  - 候補選定、スコア重み・等分配、ポジションサイズ計算（単元株丸め・aggregate cap）
  - セクター上限の適用、レジーム乗数（bull/neutral/bear）
- Research
  - ファクター計算（Momentum/Volatility/Value 等）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出し ai_scores に書込
  - regime_detector: ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書込み
- ツール
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## 必要要件（例）

- Python 3.9+（コードは型ヒントに Union 演算子などを使用）
- 推奨パッケージ（最低限・用途に応じて追加）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証に利用）
- （任意）仮想環境（venv / poetry / pipenv 等）

requirements.txt がない場合は、必要に応じて上記をインストールしてください。

例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
     - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - あるいは手動で .env を作成（.env.example を参考に）

5. 設定検証（起動前確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリの準備
   - デフォルトの DB / PID / フラグファイルは `data/` 配下に置かれる想定です（Settings によりパスは変更可）。
   - ログは `logs/` 配下にアプリ名ごとの日次ローテートログが出力されます。

---

## 環境変数（主なもの）

自動ロード:
- プロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動読み込みします。
- OS 環境変数は上書きされません（`.env.local` は上書き可）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

主要な環境変数（デフォルトや用途を併記）:
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使い `PAPER_TRADING_SQLITE_PATH` を利用
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 用）
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START — 0/1（デフォルト: 0）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API を利用するモジュールで使用
- PAPER_FILL_MODE — paper_trading の MockBrokerClient の約定挙動:
  - instant / partial / never / reject（デフォルト: instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視データは共通に保存）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、`paper_sqlite_path` を使い本番データと分離されます。

---

## 使い方（代表コマンド）

※ すべてリポジトリのルートから実行することを想定しています。`python -m ...` 形式でモジュールを実行します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し `data/paper_trading.db` に記録（本番 DB と完全分離）
    - 起動時に `data/stop_requested.flag` が存在すると起動せず終了
    - 実行中は PID ファイル（デフォルト data/execution.pid）を管理
    - 停止は `data/stop_requested.flag` を作成するか、kill.flag（Settings.kill_flag_path）が書かれると停止シグナルを受ける

- Monitoring を起動（SystemMonitor のポーリングループ）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（秒、デフォルト 60）
  - python -m kabusys.run_monitoring

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（優先度: --db > PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI 関連（プログラム的に呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 運用上のファイル / フラグ

- data/stop_requested.flag
  - run_execution / run_monitoring のループを停止するために使用されるフラグ（存在を検知して終了）
- data/execution.pid
  - ExecutionEngine の PID ファイル（デフォルト）
- data/kill.flag
  - KillSwitch が条件を満たすと書き込まれる（ExecutionEngine を停止するために外部プロセスが検出・処理する）
- logs/<app_name>.log
  - 日次ローテーションでログ出力（デフォルト logs ディレクトリ、30 日分保持）

---

## ディレクトリ構成

以下は `src/kabusys` にある主なファイル・ディレクトリと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ初期化（version）
  - config.py — Settings クラス（環境変数読み込み・デフォルト・検証）
  - config_setup.py — .env 対話ウィザード CLI
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・制約・単元丸め
    - risk_adjustment.py — セクター制限・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py — 注文滞留・約定異常検出（省略ファイルは実装参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信（実装に依存）
  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig, run_session 等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注関連
  - research/
    - factor_research.py — モメンタム / バリュー / ボラティリティ等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース -> 銘柄センチメント（OpenAI）
    - regime_detector.py — マクロニュース + ETF MA200 で市場レジーム判定
  - utils/
    - logging_setup.py — 統一的なログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

---

## 注意事項 / 運用上の注意

- 本番（KABUSYS_ENV=live）での実行前には .env を慎重に確認してください。validate_config の警告を無視しないことを推奨します。
- OpenAI API を使用する機能（news_nlp, regime_detector）は API 利用料金・レート制限に注意してください。失敗時はフォールバック挙動（スコア 0.0 等）がありますが、API キーの漏洩に注意してください。
- Paper Trading モードは本番 DB とは分離されていますが、設定ミスで本番 DB を参照しないよう .env のパスを確認して下さい。
- run_monitoring / run_execution はファイルフラグで停止を判定します。CI やプロセスマネージャ（systemd / supervisor）で実行する際は、そのプロセス監視方針に合わせてください。
- ログディレクトリの作成に失敗した場合はコンソール出力のみになります。適切なパーミッションを設定してください。

---

## 開発・拡張のヒント

- DuckDB を使ったデータ処理は SQL + Python の混合設計です。分析クエリは research/ に実装されています。
- モジュールはできるだけ副作用を避けた純粋関数（portfolio / research）と I/O 層（monitoring_db 等）に分離しています。ユニットテストが書きやすい設計です。
- OpenAI の呼び出しはテスト容易性のためラップしてあり、ユニットテストでは該当関数をモックできます（例: news_nlp._call_openai_api を patch）。

---

必要であれば README に含めるサンプル .env テンプレートや systemd ユニット例、Dockerfile、CI ワークフローのサンプルも作成します。どの追加情報が必要か教えてください。