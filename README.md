# KabuSys

日本株向け自動売買システムの軽量実装。バックテスト／ポートフォリオ構築の関数群、注文実行エンジン（paper/live 切替対応）、監視・アラート、AI を使ったニュースセンチメント・レジーム判定などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネント群で構成されています。

- ExecutionEngine: ブローカークライアントを通じた発注・注文管理（paper_trading 時は MockBroker を使用して本番 DB と分離）
- Monitoring: システム稼働状態・注文状況・リスク（ドローダウン/ポジション上限）を定期チェックし、必要に応じて kill flag を発行
- Portfolio: 候補選定・重み計算・ポジションサイズの算出などの純粋関数（DB 非依存）
- Research: DuckDB を用いたファクター計算、特徴量解析ユーティリティ
- AI: OpenAI を利用したニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）
- Tools: ペーパートレード検証レポート生成などの補助スクリプト
- Config: 環境変数/.env の読み込み・ウィザードと検証ツール

設計方針の一部:
- 可能な限り副作用を限定した純粋関数を採用（Portfolio, Research 等）
- 実行時の設定は環境変数/.env で管理
- Paper trading と Live を明確に分離（paper 用 DB など）

---

## 主な機能一覧

- 実行エンジン（ExecutionEngine）
  - 本番/ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - リスク管理（RiskManager）、注文管理（OrderManager）、再整合処理（Reconciler）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度監視
  - TradeMonitor: 注文の滞留/約定異常検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: これらを束ねたポーリングループ
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重配分、リスクベースのポジション計算、セクター上限適用
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン・IC 計算・統計サマリ
- AI関連
  - news_nlp: OpenAI（gpt-4o-mini）でニュースから銘柄別センチメントを算出して ai_scores に保存
  - regime_detector: ETF(1321)の MA200 とマクロニュースセンチメントを合成して 'bull'/'neutral'/'bear' 判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析し PASS/FAIL レポート出力
- 設定支援
  - config_setup: .env の対話式生成/更新ウィザード
  - validate_config: 環境変数・config/*.yaml の基本検証

---

## 必要環境（想定）

- Python 3.10+（| ユニオン型・型注釈の構文を使用）
- 主な依存パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合）
- （任意）SQLite は標準ライブラリで使用

依存関係はプロジェクトに requirements.txt があればそちらを使用してください。なければ手動で以下をインストールします例:

pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーへ移動

2. 仮想環境（推奨）を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （もし用意されていれば）
   - または手動:
     - pip install duckdb psutil openai pyyaml

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 他の代表的な設定:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL（DEBUG/INFO/...）
     - OPENAI_API_KEY（AI 機能利用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
   - 参考: config_setup.py に定義された項目を使用

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります

6. データディレクトリ等の作成（自動作成されることが多いが明示的に作る場合）
   - mkdir -p data logs

---

## 使い方（実行例）

- ExecutionEngine を起動（常駐実行）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に書き込みます（本番 DB と分離）。
    - エンジン起動時は data/stop_requested.flag を検査し、存在する場合は起動しません。
    - エンジンは data/execution.pid に PID を書きます（設定により異なる）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（環境にかかわらず監視 DB は本番 DB パスを参照する設計）。

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db が使用されます）

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を使用
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ログ
  - ログ出力先はデフォルト logs/。LOG_DIR 環境変数や setup_logging の引数で変更可能。
  - 各起動スクリプトは setup_logging(app_name=...) を呼ぶため logs/<app_name>.log が生成されます。

---

## 重要なファイル／フラグ

- data/kill.flag
  - KillSwitch が書き込み、ExecutionEngine に停止シグナルを送るためのファイル。
  - ExecutionEngine 側で設定に応じてクリア動作（KILL_FLAG_CLEAR_ON_START）がありますが、本番では自動クリアを無効化することを推奨します。

- data/stop_requested.flag
  - run_monitoring/run_execution が監視している停止フラグ（停止要求）。このファイルが存在すると監視/エンジンはループを抜けます。

- data/execution.pid
  - ExecutionEngine が書き込む PID ファイル（既定）。

- DB ファイル:
  - DUCKDB_PATH（分析用 DuckDB）
  - SQLITE_PATH（監視 DB — monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite）

---

## ディレクトリ構成

（重要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/.env の読み込み・Settings
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI + MA200）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数算出・スケールダウンロジック
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Volatility/Value 等
    - feature_exploration.py   — 将来リターン / IC / 統計サマリ
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ／永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
  - execution/                  — エンジン本体と注文周り（BrokerFactory 等）
  - utils/
    - logging_setup.py         — 共通ロギング設定
    - process_priority.py      — プロセス優先度・CPU affinity 設定

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の注文約定挙動）

- DB/ログ
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
  - LOG_LEVEL（DEBUG/INFO/...）
  - LOG_DIR（logs の場所）

- AI
  - OPENAI_API_KEY

- 監視/Kill
  - KILL_FLAG_CLEAR_ON_START（0/1。1 = 起動時に kill.flag を自動クリア）

- 監視間隔
  - MONITOR_POLL_INTERVAL（run_monitoring 用、秒）

---

## トラブルシューティング（よくある注意点）

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行われるため、パス構成に注意してください。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- OpenAI を利用する機能を呼ぶ場合は OPENAI_API_KEY を設定してください。キー未設定だと該当機能は ValueError を送出します（実装によりフェイルセーフで 0.0 を返す箇所もありますが、原則として API キーは必須）。
- Paper trading を使う際は PAPER_TRADING_SQLITE_PATH を使うことで本番 monitoring.db と分離できます。
- DuckDB や PyYAML が未インストールのとき、該当機能（research の一部や validate_config の YAML 検証）が動作しないか警告になります。
- ログディレクトリ作成に失敗するとファイルロギングは無効化されコンソールのみになります。パーミッションなどを確認してください。

---

README は以上です。実装の詳細な仕様やアルゴリズム（PortfolioConstruction.md 等）はリポジトリ内の設計ドキュメントを参照してください。必要であれば利用手順の具体的なユースケース（本番デプロイ手順、systemd / supervisor での運用例、docker 化の指針など）も追記できます。どの情報を追加したいか教えてください。