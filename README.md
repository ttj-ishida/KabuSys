# KabuSys

日本株向けの自動売買フレームワーク（モジュール群）のリポジトリ用 README。  
この README はコードベース（src/kabusys 以下）を元に作成しています。

---

## 概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。  
主な目的は以下です。

- 戦略（ファクター計算・特徴量解析）とポートフォリオ構築
- 発注エンジン（本番 / ペーパートレード切替）
- 監視（システム状態、注文状態、リスク監視）と Kill Switch
- AI を用いたニュースセンチメント / レジーム検出
- 検証・レポート生成（ペーパートレード検証レポート など）

設計上は「実行時の安全性（フェイルセーフ）」「ルックアヘッドバイアス回避（日時参照の明示）」
「DB（SQLite / DuckDB）を用いた永続化」「モジュールの分離性」を重視しています。

---

## 主な機能

- ExecutionEngine 起動スクリプト（`run_execution.py`）
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード用 DB（デフォルト: `data/paper_trading.db`）へ記録して本番と分離
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視
- Monitoring（`run_monitoring.py`）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、監視ログを SQLite に保存
  - Kill Switch（`data/kill.flag`）書き込みで ExecutionEngine の停止を要求
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- 監視 DB 永続化層（`monitoring_db.py`）
  - `system_status`, `trade_logs`, `positions`, `risk_logs`, `dashboard` 等のテーブル管理と読み書きユーティリティ
- ポートフォリオ構築（`portfolio/`）
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイズ算出、セクターキャップ・レジーム乗数
- リサーチ（`research/`）
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI モジュール（`ai/`）
  - `news_nlp.py`: OpenAI を使ったニュースセンチメント集計 → `ai_scores` へ書込
  - `regime_detector.py`: ETF の MA 乖離 + マクロニュースに基づき市場レジームを判定して `market_regime` に書込
  - OpenAI へのコールはリトライ／バックオフとレスポンス検証を行う
- CLI 補助ツール
  - `.env` 対話ウィザード（`python -m kabusys.config_setup`）
  - 設定検証ツール（`python -m kabusys.validate_config [--strict]`）
  - ペーパートレード検証レポート（`python -m kabusys.tools.paper_verification_report`）

---

## 前提 / 推奨環境

- Python >= 3.10（型ヒントで `X | Y` を使用しているため）
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (OpenAI Python SDK)
  - pyyaml（config YAML 検証時にオプションで使用）
- SQLite は標準ライブラリで使用
- デフォルトの DB / ファイルパス:
  - DuckDB: `data/kabusys.duckdb`
  - SQLite (監視): `data/monitoring.db`
  - Paper trading SQLite: `data/paper_trading.db`
  - ログディレクトリ: `logs/`
  - PID/flag: `data/execution.pid`, `data/kill.flag`, `data/stop_requested.flag`

（リポジトリに requirements.txt がない場合は上記パッケージを pip で個別にインストールしてください）

例:
```
python -m pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをチェックアウト
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - python -m pip install -r requirements.txt  （存在する場合）
   - または個別に: python -m pip install duckdb psutil openai pyyaml
4. データ / ログ ディレクトリを作成（通常は実行時に自動作成されますが、手動で用意しておくと良い）
   - mkdir -p data logs
5. 環境変数を設定（.env を作る推奨）
   - 対話式ウィザード: python -m kabusys.config_setup
   - 生成後、設定を検証: python -m kabusys.validate_config
6. OpenAI を利用する場合は `OPENAI_API_KEY` を .env または環境変数に設定

注意: `.env` は決して Git にコミットしないでください（ウィザードにも注記あり）。

---

## 主要な環境変数（要点）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
  - `paper_trading` の場合、Mock ブローカーと専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- PAPER_FILL_MODE: ペーパートレードの fill モード（"instant" | "partial" | "never" | "reject"、デフォルト "instant"）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI を利用する AI モジュール用
- LOG_LEVEL: ログレベル (DEBUG/INFO/...)
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番での Kill Flag 自動クリア（0 推奨）

---

## 使い方（起動例）

- 環境セットアップ / 検証
  - .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]

- ExecutionEngine を起動（本番 / ペーパー切替は KABUSYS_ENV）
  - python -m kabusys.run_execution
  - 実行前に `data/stop_requested.flag` が存在すると起動しない
  - 実行中は `data/execution.pid` に PID を保存
  - 停止は `data/stop_requested.flag` を作成することで通知（run_execution はループ内で検知して優雅に停止）

- Monitoring を起動（監視プロセス）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）
  - Monitoring はどの KABUSYS_ENV でも本番 sqlite_path（`SQLITE_PATH`）を使用して監視ログを書きます

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI / リサーチ関数（ライブラリ利用）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - Research API: kabusys.research.calc_momentum/… を DuckDB 接続経由で利用

- 設定の強制クリア（Kill Flag）
  - Kill Switch による停止要求は `data/kill.flag` に理由を書き込みます
  - ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定していると自動でクリアされる（本番は推奨されません）
  - KillFlag の手動クリアは `KillSwitch.clear()` を呼ぶか `rm data/kill.flag`

---

## 停止フラグ / Kill Switch の仕組み

- run_execution と run_monitoring はそれぞれプロジェクト内の `data/stop_requested.flag` を監視して優雅に停止します。
  - `data/stop_requested.flag` を作成すると Monitoring/Execution は次回のチェックで停止します。
- Kill Switch（監視→Execution 停止要求）は `data/kill.flag` を書き込むことで実行エンジンへ停止を要求します。
  - KillSwitch はリスク（ドローダウン超過 / ポジション上限超過）により `kill.flag` を書き込みます。
  - ExecutionEngine 側は `kill.flag` を検知して停止処理（注文キャンセル等）を行う実装を想定しています。

---

## ロギング

- 共通のログセットアップユーティリティ: `kabusys.utils.logging_setup.setup_logging(app_name=...)`
  - 標準出力（stdout）と日次ローテートされたファイルログ（logs/<app_name>.log）をルートロガーに設定
  - ログディレクトリは `LOG_DIR` 環境変数または `logs/`（デフォルト）
  - デフォルトで 30 日分のログを保持

---

## 開発 / テストに便利な機能

- `MonitoringEngine.run_once()`：単発で各 Monitor を実行して挙動を確認するためのテスト用 API
- AI の API 呼出し箇所は内部でラップされているため（`_call_openai_api` 等）、テスト時はパッチやモックで差し替え可能
- `kabusys.config` は `.env` の自動読み込み機能を持ちますが、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化できます
- `validate_config` は設定の事前検証（必須 env の有無、パス存在チェック、YAML パースなど）を行います

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル / ディレクトリ構成の要約です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定読み込み / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング
    - regime_detector.py      — 市場レジーム判定
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - (その他: execution/, data/, strategy/ などのサブパッケージが想定される)

---

## 注意事項 / 運用上の留意点

- 本番運用（KABUSYS_ENV=live）の場合は .env 設定・ LINE 通知等を十分に確認してください（validate_config は `--strict` オプションで警告も FAIL 扱いにできます）。
- `.env` や API キーは絶対にリポジトリにコミットしないでください。
- Monitoring は本番 sqlite_path を参照して監視ログを保存します。ペーパートレード DB は明確に分離してください。
- OpenAI など外部 API 呼出しはリトライ・バックオフやレスポンス検証を行いますが、API 失敗時はフェイルセーフ（スコアをスキップ or 0.0 フォールバック）にしています。
- プロセス優先度や CPU affinity 設定は OS に依存します。`psutil` の権限エラーはワーニングで無視されます。

---

必要であれば、この README をベースに以下の追加を行えます：
- `requirements.txt` の推奨パッケージ一覧
- systemd / supervisor / docker compose の起動例
- より詳細な API ドキュメント（関数ごとの引数/戻り値一覧）
- テスト手順（ユニットテスト / 結合テストの実行方法）

要望があれば、上記のいずれかを追記して README を拡張します。