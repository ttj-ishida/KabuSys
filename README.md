# KabuSys — README

KabuSys は日本株向けの自動売買／リサーチ基盤のコードベースです。本リポジトリには以下の主要機能（監視・発注エンジン、ポートフォリオ構築、ファクター計算、AI ベースのニュース分析、ユーティリティ群）が含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

- オンライン／ペーパートレード双方に対応した ExecutionEngine（発注エンジン）。
- システム監視 (Monitoring) — 稼働率、プロセス死活、データ鮮度、注文ログ等を定期的に記録・アラート。
- ポートフォリオ構築ライブラリ（候補選定、重み計算、ポジションサイズ計算、セクター制約など）。
- リサーチ用モジュール（ファクター計算、将来リターン・IC 計算、統計サマリ）。
- AI モジュール：ニュースのセンチメント解析（OpenAI）や市場レジーム判定。
- 各種 CLI ツール：環境設定ウィザード、設定検証、ペーパートレード検証レポート生成など。
- 永続化: DuckDB（分析用）と SQLite（監視／発注ログなど）を併用。

---

## 主な機能一覧

- 実行環境管理
  - KABUSYS_ENV によるモード切替: `development` / `paper_trading` / `live`
  - paper_trading では MockBrokerClient を使用し、専用の Paper DB に記録（production DB と分離）

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスクの収集、Execution プロセス監視、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じて kill.flag を書き込み ExecutionEngine 停止をトリガー
  - 監視ログの永続化（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard 等

- 発注エンジン（Execution）
  - BrokerFactory による実際の証券 API またはモックの切替
  - OrderManager / RiskManager / Reconciler による発注と整合性管理
  - PID / stop フラグによる起動・停止制御

- ポートフォリオ構築
  - シグナル選別、等配分・スコア加重配分、リスクベースの株数計算、セクター上限適用、レジーム乗数

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン・IC 計算、ファクター統計サマリ

- AI（OpenAI）
  - ニュース記事を集約して LLM でセンチメントを付与し ai_scores に格納
  - マクロニュース + ETF MA を用いた市場レジーム判定

- ユーティリティ
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env ウィザード / 設定検証 CLI
  - ペーパートレード検証レポート生成ツール

---

## 前提 / 依存関係

- Python 3.10+
  - （型ヒントに `X | Y` を使用しているため 3.10 以上を推奨）
- 必要な外部パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - （オプション）PyYAML（config/*.yaml の構文検証用）

pip install 例（requirements.txt がある場合はそれを使用してください）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン／展開
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動でプロジェクトルートに `.env` を作成。`.env.example` を参照してください（存在しない場合は README の下の「推奨 .env 例」を参照）。
   - 自動的に .env を読み込む: デフォルトで、プロジェクトルートの `.env` と `.env.local` が読み込まれます。自動読み込みを無効化する場合:
     ```
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1 python ...
     ```

4. 設定検証（起動前確認）:
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も FAIL 扱いになります。

5. 必要なディレクトリ作成:
   - data/ （デフォルトの DB / フラグファイル用）
   - logs/ （ログ出力用） — logging_setup が自動作成しますが、権限等で失敗する場合は手動作成してください。

---

## 環境変数（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 選択・一般:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - LOG_LEVEL — デフォルト: INFO
  - LOG_DIR — デフォルト: logs/
  - OPENAI_API_KEY — OpenAI を使う機能で必要
  - PAPER_FILL_MODE — paper_trading の約定動作 (instant|partial|never|reject)、デフォルト: instant

- 監視周り:
  - MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒）。デフォルト: 60
  - PID_FILE_PATH — Execution PID ファイルのパス（Settings で参照）
  - KILL_FLAG_PATH — KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" で自動クリア、デフォルト: "0"）

---

## 使い方（実行例）

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（本番想定の monitoring）:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 停止方法: プロジェクト `data/stop_requested.flag` ファイルが存在するとループを抜けます（手動で作成するか、運用ツールでトリガ）。

- ExecutionEngine 起動（発注エンジン）:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ `data/paper_trading.db` に記録されます（本番 DB と分離）。
  - 停止方法:
    - `data/stop_requested.flag` が存在すると起動を中止または実行中に停止します。
    - KillSwitch（監視ロジック）が `KILL_FLAG_PATH`（デフォルト data/kill.flag）に理由を書き込むと、ExecutionEngine 側で検出して順次停止します。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。別パス指定は `--db` または環境変数 PAPER_TRADING_SQLITE_PATH。

- ライブラリとしての利用（例: research / portfolio）:
  - Python 内からインポートして利用します（DuckDB 接続などを渡す設計）。
  ```
  from kabusys.research import calc_momentum
  # duckdb_conn を作成して calc_momentum(duckdb_conn, target_date) を呼ぶ
  ```

---

## 停止・フラグの取り扱い（要点）

- run_monitoring.py / run_execution.py はプロジェクトルートの `data/stop_requested.flag` の存在を見て安全に終了します（手動停止用）。
- KillSwitch はルールにより `data/kill.flag`（デフォルト）を作成し、ExecutionEngine に「安全停止」を促します（ドローダウン超過などの自動停止）。
- ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` 設定に応じて kill.flag を自動でクリアするか決められます（本番では 0 推奨）。

---

## ディレクトリ構成

主要なファイル／ディレクトリ（src/kabusys 以下）:

- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- config.py — Settings クラス（.env / 環境変数の読み込みと検証）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM スコアリング
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — 監視用 SQLite 永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - trade_monitor.py — 注文ログ監視（滞留・異常）
  - kill_switch.py — Kill Switch 書き込みロジック
  - monitoring_engine.py — 各 Monitor を束ねる実行ロジック
  - alert_manager.py —（アラート送信の抽象）
- execution/
  - execution_engine.py, order_manager, order_repository, reconciler, risk_manager, broker_factory など（発注系ロジック）
- portfolio/
  - portfolio_builder.py — 候補選定・重み
  - position_sizing.py — 株数決定
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — forward returns / IC / summary 等
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート出力
- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity
- data/ （運用時に使用するデータ・フラグ・DB ファイル）
- logs/ （ログ出力先、デフォルト daily ローテーション）

（上記はソース構成の要約です。詳細は各モジュールの docstring を参照してください。）

---

## 推奨 .env 例（抜粋）

.env は秘密情報を含むため Git にコミットしないでください。

例（参考）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx...
KILL_FLAG_CLEAR_ON_START=0
```

---

## 運用上の注意

- production（KABUSYS_ENV=live）ではログレベル・通知設定・kill flag の扱い等を十分に確認してください。
- Paper trading は本番 DB と完全分離されるよう設計されていますが、設定ミスは重大な事故につながるため `validate_config` を必ず実行してください。
- OpenAI を使用する機能は API コストとレイテンシが発生します。API キー管理とレート制御を適切に行ってください。
- ログディレクトリ作成権限や DB ファイルのパーミッションに注意してください。logging_setup は作成に失敗した場合ファイル出力を無効化してコンソール出力のみで継続します。

---

README はコードベースの主要点をまとめたものです。各モジュールの詳しい挙動（引数や戻り値の仕様、内部の閾値など）は該当ファイルの docstring を参照してください。必要であれば、各コンポーネントの運用手順やデプロイ手順のテンプレートも作成します。どの情報がさらに必要か教えてください。