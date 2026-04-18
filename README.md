# KabuSys

日本株向け自動売買システムのコアライブラリ群（ライブラリ＋起動スクリプト群）。

この README はリポジトリ内の主要スクリプト・モジュールの使い方、セットアップ手順、ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネント群で構成されます。

- 監視（Monitoring）：システム状態、データ鮮度、取引ログ、リスクイベントを定期チェックし、必要に応じてアラートや Kill Switch（停止フラグ）を発動します。
- 実行（Execution）：ブローカークライアント経由で発注を行う ExecutionEngine。`paper_trading` 環境では MockBroker を使い、本番 DB と分離された専用 SQLite に記録します。
- ポートフォリオ構築（Portfolio）：銘柄選定、配分、単元丸め、セクター制限、レジーム乗数などの純粋関数実装。
- リサーチ（Research）：DuckDB 上の価格・財務データからファクター計算、将来リターン、IC 等の統計解析を実行。
- AI 支援（AI）：OpenAI を用いたニュースセンチメント・市場レジーム判定（必要時に API キーが必要）。
- ユーティリティ：ロギング設定、プロセス優先度設定、設定ファイル読み込みウィザード、設定検証 CLI 等。

主に次の起動スクリプト／ CLI を提供します。
- python -m kabusys.run_monitoring — システム監視ループを開始
- python -m kabusys.run_execution — ExecutionEngine を起動
- python -m kabusys.config_setup — .env を対話式に作成／更新
- python -m kabusys.validate_config — 環境設定の事前検証
- python -m kabusys.tools.paper_verification_report — ペーパートレード検証レポート生成

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）／対話式ウィザードで .env を生成
- 起動スクリプト
  - run_execution: ExecutionEngine の起動（KABUSYS_ENV により挙動切替）
  - run_monitoring: SystemMonitor をポーリング実行（MONITOR_POLL_INTERVAL で間隔変更可）
- モニタリング
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - 稼働率・CPU/メモリ/ディスク監視、データ鮮度チェック、滞留注文・約定異常検出
  - Kill Switch（data/kill.flag）による ExecutionEngine 強制停止
- リスク管理
  - ドローダウン監視、ポジション数上限監視、リスクイベントの重複抑止
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重、リスクベース発注株数計算、セクターキャップ、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等ファクター算出、将来リターン・IC 計算、統計サマリ
- AI 機能（OpenAI）
  - ニュースの銘柄別センチメントスコア算出（ai_scores へ書き込み）
  - マクロニュース＋ETF MA200 を使った市場レジーム判定（market_regime へ書き込み）
- ツール
  - Paper Trading 用検証レポート生成（稼働率、成功率、レイテンシ等の指標と PASS/FAIL 判定）
- ロギング、プロセス優先度、CPU affinity 設定ユーティリティ

---

## 事前準備（セットアップ手順）

前提
- Python 3.10 以上（typing の記法等を利用）
- システムに duckdb, psutil, openai 等の依存が必要（OpenAI を使う機能は任意）

例: 仮想環境の作成と依存インストール（必要なパッケージはプロジェクトの requirements.txt に記載されている想定）
```bash
git clone <repo-url>
cd <repo-root>

python -m venv .venv
source .venv/bin/activate

# 例（requirements.txt がある場合）
pip install -r requirements.txt

# もし requirements.txt がない場合の主要依存例:
pip install duckdb psutil openai PyYAML
```

.env の作成（対話ウィザード推奨）
```bash
python -m kabusys.config_setup
```
ウィザードが .env を生成します。生成後は設定検証を行ってください:
```bash
python -m kabusys.validate_config
# 警告も失敗にしたい場合:
python -m kabusys.validate_config --strict
```

重要な環境変数（主要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を利用し、データは data/paper_trading.db に保存（本番 DB と分離）
- OPENAI_API_KEY — OpenAI を使う機能（ニュース NLP、レジーム判定）で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR — ログ出力設定
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

ファイルフラグ
- data/kill.flag — Kill Switch により書き込まれる停止フラグ。存在すると ExecutionEngine に停止シグナルを送る。
- data/stop_requested.flag — run_monitoring/run_execution はこのファイルを見て自発終了する（デバッグ用の停止フラグ）。
- data/execution.pid — ExecutionEngine が PID を書き込む（run_execution が使用）。

---

## 使い方（主要コマンド例）

1. 環境確認（作成した .env を検証）
```bash
python -m kabusys.validate_config
```

2. 実行（ExecutionEngine）
- 通常（本番／paper_trading は KABUSYS_ENV に依存）:
```bash
python -m kabusys.run_execution
```
- 注意: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。

3. 監視（Monitoring）
```bash
# 環境変数でポーリング間隔を上書き可能（秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- run_monitoring は常に本番 sqlite_path を使って監視ログを記録します（KABUSYS_ENV に依らず）。
- 停止: data/stop_requested.flag を作成するとループが検出して終了します（または Ctrl+C）。

4. .env の対話作成
```bash
python -m kabusys.config_setup
```

5. Paper Trading 検証レポート
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# または別 DB を指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

6. AI 機能（ニュース NLP / レジーム判定）
- OPENAI_API_KEY を設定してから、アプリケーション内 API を呼びます（CLI は提供されていません）。例:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 実装上の挙動上の注意点

- run_execution と run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（psutil に依存、権限や OS により失敗する場合はログ警告）。
- monitoring は SQLite（監視ログ）と DuckDB（分析用）を併用します。init_monitoring_db は冪等的にテーブルを作成・マイグレーションします。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われますが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI を利用する機能は API の失敗に対してリトライやフォールバックを実装しており、API 未設定時は例外を投げる（あるいはフォールバック値を使って続行）する設計です。
- Paper Trading と Live の DB は分離される設計になっています（誤って本番 DB にデータを書き込まないよう注意）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋、リポジトリの src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - config.py                     — Settings (.env 読み込み・アクセスラッパ)
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 設定検証 CLI
  - utils/
    - logging_setup.py            — ロギング初期化ユーティリティ
    - process_priority.py         — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, ...）
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — （取引関連の監視ロジック: 滞留注文等）
    - risk_monitor.py             — ドローダウン・ポジション制限監視
    - kill_switch.py              — kill.flag 書き込みユーティリティ
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - alert_manager.py            — （通知管理: LINE 等。実装参照）
  - execution/                     — Execution に関する複数モジュール（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 発注株数決定・スケーリング
    - risk_adjustment.py          — セクター上限・レジーム乗数
  - research/
    - factor_research.py          — ファクター計算（momentum, volatility, value）
    - feature_exploration.py      — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py                 — ニュースを用いた銘柄別センチメント（OpenAI）
    - regime_detector.py          — 市場レジーム判定（ETF + マクロニュース + OpenAI）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - data/                         — デフォルトで使用する DB / flag / pid の親ディレクトリ（git 管理対象外にすること）

補足: 各モジュールの詳細はソース内の docstring に設計思想・前提が記載されています。実運用前に該当箇所を確認してください。

---

## ロギング・ファイル配置

- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: execution.log, monitoring.log）
- ローテーション: 日次（TimedRotatingFileHandler）、30 日分保持
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御

---

## よくある運用オペレーション

- 強制停止（安全な停止）:
  - ExecutionEngine の停止は kill.flag を生成（KillSwitch が検出）すると実行されます。
  - 管理者が即時停止させたい場合は data/kill.flag に内容を書いてください（KillSwitch.write が行う内容と同様）。
  - run_monitoring/run_execution の自発終了は data/stop_requested.flag を作成することで行えます。

- Paper Trading 検証:
  - ペーパートレード動作確認後、 tools/paper_verification_report により期間別の PASS/FAIL を判定できます。

---

必要に応じて README を拡張して、セットアップのコマンド例、CI 設定、Dockerfile、詳細な DB スキーマ説明、各コンポーネントの API 使用例（OpenAI 呼出しのサンプル）などを追記してください。README の追加項目が必要であれば、どの部分を詳しく書くか教えてください。