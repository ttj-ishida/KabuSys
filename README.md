# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成、ポートフォリオ構築、発注実行、監視、研究用ユーティリティ、ならびに AI を用いたニュース評価機能を含む自動売買基盤です。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群で構成されています。

- 市場データ（DuckDB）を用いたファクター計算・研究（research）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 発注実行エンジン（ExecutionEngine）と注文管理（execution）
- 監視コンポーネント（システム状態・注文滞留・リスク監視）
- Paper Trading（本番 DB と分離して動作可能）
- OpenAI を利用したニュース NLP / レジーム判定（AI）
- 設定ウィザード（.env 生成）と起動前検証ツール
- 運用支援ツール（ペーパートレード検証レポート等）

設計方針としては「フェイルセーフ」「ルックアヘッドバイアスを避ける」「DB分離（paper/live）」などが徹底されています。

---

## 主な機能一覧

- research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算 / IC（情報係数）計算 / 統計サマリー
- portfolio
  - 候補選定（スコア順）、等分配・スコア加重、リスク調整（セクター制限、レジーム乗数）
  - ポジションサイズ計算（ロット丸め、aggregate cap スケーリング）
- execution
  - 発注エンジン（実口座・ペーパートレード分離）
  - 注文リポジトリ / リコンシリエーション / リスク管理
- monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス有無/データ鮮度監視
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視（kill switch 連動）
  - MonitoringEngine：各モニタの統合ループ、アラート送信（LINE 等）
- ai
  - news_nlp：raw_news を LLM（OpenAI）でスコアリングして ai_scores に保存
  - regime_detector：ETF ma200 乖離 + マクロニュースで日次レジーム判定
- utils
  - process_priority：プロセス優先度 / CPU affinity 設定
- tools
  - paper_verification_report：ペーパートレード DB から PASS/FAIL 判定レポートを生成
- 設定関連
  - config_setup.py：対話式 .env 作成ウィザード
  - validate_config.py：起動前に環境・設定ファイルを検証

---

## セットアップ手順

前提：Python 3.9+（コードで typing アノテーションなどを使用）。必要パッケージはプロジェクトの依存に合わせてインストールしてください（例: duckdb, psutil, openai, PyYAML が必要な機能あり）。

1. リポジトリをクローンし、作業ディレクトリに移動
   - git clone ...
   - cd <project_root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -r requirements.txt
   - ※ requirements.txt がない場合は、少なくとも以下を入れてください:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config 検証で YAML をチェックしたい場合）

4. 環境変数 / .env の準備
   - 対話式ウィザードで作成（推奨）:
     - python -m kabusys.config_setup
   - または手動で .env を作成。主に必須な変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 実行環境:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - そのほか（代表例）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知設定）
     - LOG_LEVEL（DEBUG/INFO/…）
     - KILL_FLAG_CLEAR_ON_START（0/1）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱い（exit code 1）

6. DB や data ディレクトリの作成（必要なら）
   - mkdir -p data

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 起動前設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパー両対応）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在すると起動せず終了
    - 実行中に data/stop_requested.flag を作成すると停止処理が行われる
    - 実行中は data/execution.pid が作成される

- Monitoring（定期監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に本番用 sqlite_path を使用（環境に依らず監視 DB は本番パス）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI 機能
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用
  - OpenAI API キーは OPENAI_API_KEY 環境変数、もしくは関数引数で渡す
  - 実行は DuckDB 接続を渡して行う設計（テストやスケジューラから呼び出し）

- その他ユーティリティ
  - process_priority.set_process_priority("high") 等を利用し、起動時にプロセス優先度を設定しています

---

## 重要なファイル／フラグ

- data/kill.flag — KillSwitch による停止フラグ。存在すると ExecutionEngine を停止させる（KillSwitch が生成）。
- data/stop_requested.flag — run_execution / run_monitoring の停止検知用フラグ。存在するとループを終了する。
- data/execution.pid — ExecutionEngine の PID ファイル。SystemMonitor はこの PID を見てプロセス生存チェックを行う。
- DB（デフォルト）
  - DuckDB: data/kabusys.duckdb
  - SQLite（監視）: data/monitoring.db
  - SQLite（ペーパー）: data/paper_trading.db

---

## サンプル .env（最低限）

以下は最小限の例です（実際は secret 値を入力してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

※ .env は絶対に Git にコミットしないでください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（自動 .env ロード機能含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — CPU/MEM/DISK/プロセス/DataFreshness 監視
    - trade_monitor.py — 滞留注文・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成／評価
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - alert_manager.py — （アラート送信ロジック）
  - execution/  (実行関連コンポーネント)
    - order_manager.py, order_repository.py, execution_engine.py, broker_factory.py, reconciler.py, risk_manager.py, order_record.py
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・aggregate cap
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 計算
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 経由）
    - regime_detector.py — マクロ + MA によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - data/ （実行時に生成される想定）
    - *.db, *.flag, *.pid など

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config は live 時に警告を出します。
- kill.flag / stop_requested.flag / execution.pid 周りは運用フローで重要です。意図せずフラグを残すと起動・停止に影響します。
- AI 機能（OpenAI）の呼び出しはレート制限やネットワーク障害を考慮して設計されていますが、APIキーの扱い・コスト管理は運用者の責任です。
- Paper Trading は本番 DB とは分離されます（PAPER_TRADING_SQLITE_PATH を使用）。ペーパートレードでの検証後、本番に移行する際は設定・DB を見直してください。
- monitoring は常に本番 sqlite_path を使用します（環境にかかわらず監視対象は本番 DB で行われる点に注意）。

---

## 開発・テスト

- 単体・統合テストは各モジュールをローカルの DuckDB / SQLite を使って実行できます。
- AI 呼び出し関数は内部でラッパー化されており、テスト時はモック化（unittest.mock.patch）して外部 API を呼ばないようにできます（news_nlp._call_openai_api / regime_detector._call_openai_api など）。
- config モジュールはプロジェクトルート検出ロジックを持つため、パッケージ化後も .env 自動読み込みが適切に働きます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動ロードを無効化できます。

---

必要があれば、README に以下を追記します：
- 具体的な systemd / supervisor の Unit ファイル例（運用起動方法）
- CI 用のテスト実行手順
- 各設定ファイル（config/*.yaml）の例と生成スクリプトの使い方

どの追加情報を優先して欲しいか教えてください。