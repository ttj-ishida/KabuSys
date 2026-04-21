# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ兼運用スクリプト集です。本リポジトリは以下の主要機能を含みます：戦略ファクター計算、ポートフォリオ構築、ポジションサイズ算出、監視（Monitoring）、ExecutionEngine 起動スクリプト、Paper Trading 用の検証ツール、LLM を使ったニュース NLP / 市場レジーム判定など。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群と運用用スクリプトをまとめたものです。主な責務は以下です。

- データ解析（DuckDB ベースのファクター算出、リサーチ機能）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター調整）
- ExecutionEngine 起動（実際の/模擬発注を行うエンジンの起動スクリプト）
- 監視（システム稼働状況、注文ログ、リスク指標のポーリング・アラート）
- Paper Trading 検証用レポート生成
- LLM（OpenAI）を使ったニュースセンチメント算出と市場レジーム判定
- 設定管理・ウィザード・検証ツール

設計上の注意点として、DuckDB を分析用の永続化として使い、SQLite を監視ログ・注文履歴などの軽量永続化に使っています。Paper Trading と本番 DB は分離されます。

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行 / 監視
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db を利用
    - 停止は data/stop_requested.flag / data/kill.flag のフラグファイルで制御
  - Monitoring 起動スクリプト: python -m kabusys.run_monitoring
    - 環境に関わらず本番 sqlite_path を監視 DB として使用
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 監視コンポーネント:
    - SystemMonitor: CPU/メモリ/Disk、プロセス死活、データ鮮度確認
    - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限監視
    - KillSwitch / AlertManager による自動停止・通知（LINE など）

- ポートフォリオ構築
  - 候補選定（score 降順、タイブレークルール）
  - 重み計算（等分配 / スコア加重）
  - セクターキャップ適用（既存保有に基づく除外）
  - ポジションサイズ算出（risk_based / equal / score、lot_size で丸め、aggregate cap によるスケールダウン）

- リサーチ
  - ファクター計算: Momentum / Volatility / Value（DuckDB の prices_daily / raw_financials 参照）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ

- AI（OpenAI）
  - news_nlp: ニュース記事を集約して LLM に投げ、銘柄ごとの sentiment / ai_score を ai_scores テーブルへ保存
  - regime_detector: ETF(1321) の MA200 乖離 + マクロニュース LLM による日次レジーム判定（bull/neutral/bear）

- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
    - レポート指標: 稼働率、注文成功率、送信率、レイテンシ（P95 など）

---

## セットアップ手順（ローカル実行向け）

前提
- Python 3.9+（型ヒントの union / 省略形を含むため 3.9+ を想定）
- OS により psutil のネイティブ依存を満たす必要あり

1. リポジトリをクローン / ソース配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 基本的な依存:
     - duckdb
     - psutil
     - openai
   - 任意（YAML 検証を行う場合）:
     - PyYAML
   例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt）

4. .env の用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参照して手動で作成
   - 重要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - DUCKDB_PATH / SQLITE_PATH（必要に応じて上書き）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱う

6. 必要ディレクトリ:
   - data/ （DB 等を置く）
   - logs/ （ログ出力）
   スクリプトは起動時に自動作成を試みますが、権限などで失敗することがあるため事前に作成しておくと安心です。

---

## 使い方（代表的なコマンド）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとペーパートレード用 DB（デフォルト data/paper_trading.db）を使用し、MockBrokerClient を使います。
  - 起動前に data/kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）を確認してください。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - 停止方法:
    - data/stop_requested.flag を作成すると監視プロセスは次ループで停止します（スクリプト自体に stop フラグ検知あり）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- ライブラリ的利用例（コードから）
  - ファクター計算:
    - from kabusys.research import calc_momentum
    - result = calc_momentum(duckdb_conn, date(2026, 4, 10))
  - ポートフォリオ API:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

---

## 重要な環境変数（主要なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI を利用する処理で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログレベル・ログ出力先
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

（その他は config_setup で対話的に確認できます）

---

## 停止 / Kill スイッチの挙動

- data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止命令を出します（起動中のエンジンはこのファイルを検出して安全停止します）。
- data/stop_requested.flag: run_execution/run_monitoring の外部的な停止フラグ（存在すると起動ループを抜けて終了します）。
- KILL_FLAG_CLEAR_ON_START（.env）: ExecutionEngine 起動時に kill.flag を自動でクリアするか（0/1）。本番では 0 推奨。

---

## ログとファイル配置

- デフォルトログディレクトリ: logs/
  - 各アプリ名（execution, monitoring）の日次ローテートログを出力
- PID ファイル: data/execution.pid（ExecutionEngine の PID を格納）
- DB:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db（KABUSYS_ENV=paper_trading 時）

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py — 環境変数と Settings クラス、自動 .env ロード
- config_setup.py — 対話式 .env ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリング起動スクリプト

- utils/
  - logging_setup.py — 統一的なロギング設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化層
  - system_monitor.py — システム状態 / データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - trade_monitor.py — （注文ログ監視など）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — 通知管理（LINE など）

- execution/
  - execution_engine.py — 実際の ExecutionEngine（起動/セッション管理）
  - broker_factory.py — BrokerClient の生成（本番 or Mock）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注周りの実装

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value の計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリ

- ai/
  - news_nlp.py — ニュースセンチメントの LLM スコアリング＆書き込み
  - regime_detector.py — マクロ + ETF MA200 によるレジーム判定

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

---

## 開発上の注意点 / 補足

- settings（config.Settings）は .env と環境変数を透過的に扱います。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用）。
- Monitoring は run_monitoring が本番 sqlite_path を常に使用する設計です（環境に依存せず監視データは一元化）。
- Paper Trading 実行は settings.is_paper を参照して専用 DB を使用し、本番 DB と分離されます。
- OpenAI 周りは API の rate limit / transient error をリトライ実装で扱っていますが、API キー漏洩に注意してください（.env を Git 管理しないこと）。
- DuckDB へのバッチ書き込みや executemany の空リストに関する互換性に注意する実装上の制約があります（実装内に注記あり）。

---

## よく使うコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要があれば、README にチュートリアル（初回起動例）、.env.example のテンプレート、CI / デプロイ手順、詳しい API ドキュメント（各モジュールの public 関数の使用例）を追加できます。どの情報を優先して追記しますか？