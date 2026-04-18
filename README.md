# KabuSys

日本株向け自動売買/リサーチ基盤のサブセット実装ドキュメント（README）。  
このリポジトリには、実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ニュース解析、ユーティリティ等のモジュールが含まれます。

---

## プロジェクト概要

KabuSys は日本株の自動売買やリサーチ処理を支援するライブラリ／スクリプト群です。  
主な役割は次の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード切替対応）
- Monitoring：システム状態・注文状況・リスクを継続監視してアラート／Kill Switch を運用
- Research：DuckDB 上の株価・財務データを用いたファクター計算や特徴量解析
- AI：ニュース記事を OpenAI に送信してセンチメント評価を行い DB に格納
- Portfolio：候補選定・配分・ポジションサイズ計算・セクター制限などの純粋関数群
- ツール類：設定ウィザード、設定検証、Paper Trading 検証レポート生成など

設計上のポイント：
- .env による環境変数で設定を管理（`config_setup.py` により対話式生成可能）
- DuckDB / SQLite を用いたデータ格納（デフォルトは `data/` 配下）
- ロギングは統一された `kabusys.utils.logging_setup.setup_logging` を通じて行う
- ペーパートレード時は本番 DB と分離して `data/paper_trading.db` を使用可能

---

## 主な機能一覧

- 実行（Execution）
  - ブローカークライアント抽象化（本番 or Mock）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine 起動
  - PID ファイル管理・停止フラグによる安全停止

- 監視（Monitoring）
  - CPU/メモリ/ディスク/プロセス稼働監視（`MonitoringDB` に永続化）
  - 注文滞留・約定異常・データ鮮度の監視
  - リスク（ドローダウン、ポジション上限）の定期チェックと Kill Switch 書き込み
  - アラート発行フック（AlertManager 経由）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value の計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（ニュース解析・レジーム判定）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントスコア算出
  - マクロニュース + ETF MA による市場レジーム判定
  - API 呼び出しはリトライ・バックオフ、部分書き込みによる耐障害性あり

- ポートフォリオ構築
  - 候補選定（スコア/順位）、等重/スコア重み付け
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め・aggregate cap）

- ツール
  - .env 対話式ウィザード：`python -m kabusys.config_setup`
  - 設定検証 CLI：`python -m kabusys.validate_config`
  - Paper Trading 検証レポート生成：`python -m kabusys.tools.paper_verification_report`

---

## セットアップ手順（開発者向け）

前提
- Python 3.10+（型注釈に `X | Y` を使用）
- Git、インターネットアクセス（OpenAI を使う場合）

1. リポジトリをクローン・移動
   - git clone ... ; cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合は `pip install -r requirements.txt`
   - ない場合は最低限次を入れてください：
     - pip install duckdb psutil openai
     - PyYAML を使うなら： pip install pyyaml

4. .env を作成
   - 対話式ウィザード： `python -m kabusys.config_setup`
   - もしくは `.env.example` を編集して `.env` を作成（このリポジトリに例がある場合）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL として扱う場合： `python -m kabusys.validate_config --strict`

6. データディレクトリ
   - デフォルトでは `data/` 下に DB ファイルやフラグファイルが作られます。必要に応じてパスは `.env` で上書きできます。

必須／重要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合）
- KABUSYS_ENV（development / paper_trading / live）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR など

---

## 使い方（主要スクリプト）

- 監視ループを起動（Monitoring）
  - デフォルトのポーリング間隔は 60 秒
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 実行:
    - python -m kabusys.run_monitoring
  - 監視ループはプロジェクトルートの `data/stop_requested.flag` を監視しており、存在すると終了します。
  - Monitoring は実行環境に関わらず `Settings.sqlite_path`（本番パス）を使用します。

- 実行エンジンを起動（Execution）
  - 起動:
    - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（`PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`）に記録します（本番 DB と分離）。
  - 停止制御:
    - `data/stop_requested.flag` があると起動を抑止／実行中に検知すると停止処理を行います。
    - 実行中は `data/execution.pid` が作成されます。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告をエラー扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
  - 関数 API を直接呼び出して DuckDB 接続と target_date を渡す設計（バッチ処理に向く）

ログ
- デフォルトのログディレクトリ: logs/
- ログファイル名: `<app_name>.log`（例: execution.log, monitoring.log）
- 環境変数で上書き可能: LOG_DIR, LOG_LEVEL

停止制御
- 共通停止フラグ: `data/stop_requested.flag`
- Execution 停止トリガ（Kill Switch）: `data/kill.flag` を書き込むことで ExecutionEngine を停止させる設計。KillSwitch の評価は Monitoring 側で実施。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings 管理
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 設定検証 CLI
- run_monitoring.py              — Monitoring ポーリングループ起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト

submodules / パッケージ:
- ai/
  - news_nlp.py                   — ニュースセンチメント（OpenAI 呼び出し）
  - regime_detector.py            — レジーム（bull/neutral/bear）判定
- monitoring/
  - monitoring_db.py              — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py             — CPU/メモリ/プロセス/データ鮮度監視
  - trade_monitor.py              — 注文ログ監視（存在するファイルに実装あり）
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — Kill Switch 管理（kill.flag）
  - monitoring_engine.py          — 各 Monitor を束ねるランナー
  - alert_manager.py              — （アラート送信実装を差し込む場所）
- execution/
  - execution_engine.py           — ExecutionEngine 本体（EngineConfig 等）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py          — 候補選定 / 重み計算
  - position_sizing.py            — 発注株数計算
  - risk_adjustment.py            — セクターキャップ / レジーム乗数
- research/
  - factor_research.py            — Momentum / Volatility / Value 計算（DuckDB）
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py  — Paper Trading レポート生成
- utils/
  - logging_setup.py              — 共通ロギング設定
  - process_priority.py           — プロセス優先度／CPU affinity 設定
- data/ (実行時に生成・使用)
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite; ペーパートレード用)
  - kabusys.duckdb (DuckDB)
  - execution.pid, stop_requested.flag, kill.flag

（上記は主要ファイルを抜粋。詳細はソースツリーを参照してください）

---

## 注意事項 / 運用メモ

- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml）が見つかれば `.env` / `.env.local` を自動で読み込みます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 実行環境（KABUSYS_ENV）:
  - development / paper_trading / live の 3 種類
  - `live` 設定時は注意（validate_config で警告が出ます）

- DuckDB / SQLite:
  - Research や AI は DuckDB 接続を受けて処理を行うため、prices_daily / raw_news / raw_financials 等のテーブルが必要です。
  - Monitoring 用のテーブルは `init_monitoring_db` で自動作成（マイグレーション処理も含む）

- OpenAI 利用:
  - API 呼び出しはリトライ・バックオフを実装していますが、API コストやレイテンシを考慮してバッチサイズやトークン制限を調整してください。
  - API キーは環境変数 `OPENAI_API_KEY` に設定するか、関数引数で渡します。

- ロギング:
  - 起動スクリプトは最初にプロセス優先度を `high` に設定し（可能な場合）、ログ初期化を行います。
  - ログファイル出力に失敗した場合はコンソール出力のみで継続します。

---

もし README に追記したい項目（例: サンプル .env、requirements.txt、運用手順の詳細、テーブルスキーマの説明や API インターフェース仕様）があれば教えてください。必要に応じて追加のセクションを作成します。