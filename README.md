# KabuSys

日本株自動売買システムのミニマル実装。シグナル生成・ポートフォリオ構築・発注（本番／ペーパートレード分離）・監視・レポート・研究用ユーティリティを含みます。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 発注エンジン（ExecutionEngine）: 本番（kabuステーション）とペーパートレードを分離して実行可能
- 監視（Monitoring）: システム状態・注文状態・リスク（ドローダウン／ポジション過多）をポーリングで監視
- ポートフォリオ構築（Portfolio）: 候補選定、重み付け、ポジションサイズ計算、セクター制約など
- リサーチ（Research）: ファクター計算・特徴量探索・IC計算など DuckDB を使った分析
- AI ユーティリティ（AI）: ニュースの LLM によるセンチメント評価、レジーム判定（OpenAI を利用）
- ツール: ペーパートレード検証レポート生成などの CLI スクリプト
- 設定管理: .env ウィザードと設定検証 CLI

設計方針の一部:
- 本番データベースとペーパートレードデータベースは分離（KABUSYS_ENV に依存）
- 可能な限り副作用を避け、純粋関数として実装される部分（ポートフォリオ・計算系）
- ルックアヘッドバイアスを避けるため、date/time の扱いに注意（各モジュールで言及あり）
- OpenAI 呼び出しは失敗時にフェイルセーフ（スコア 0.0 等）で継続

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使い `data/paper_trading.db` を使用。
  - 起動時に PID ファイルを書き、停止はフラグファイル（data/stop_requested.flag）で制御。

- run_monitoring.py
  - SystemMonitor のポーリングループを実行。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60）。
  - 監視は本番 sqlite_path を使う（環境に依存せず本番 DB を監視）。

- monitoring/*（監視サブパッケージ）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・Execution プロセスの有無を監視
  - TradeMonitor: 滞留注文・約定異常を検出
  - RiskMonitor: ドローダウン／ポジション上限を監視し必要なら kill flag を作成
  - KillSwitch / AlertManager / MonitoringEngine: 監視結果の総合評価と通知・Kill 制御

- portfolio/*
  - 候補選定（select_candidates）、等重・スコア重み付け、ポジションサイズ計算（lot 単位処理や aggregate cap）
  - セクター上限適用、レジーム乗数

- research/*
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- ai/*
  - news_nlp: raw_news を LLM で評価して ai_scores に書き込む（OpenAI 使用）
  - regime_detector: ETF とマクロニュースを組み合わせて market_regime を判定・書込

- tools/paper_verification_report.py
  - ペーパートレード DB を読み取り、稼働率・注文成功率・レイテンシ等の検証レポートを出力

- config_setup.py / validate_config.py
  - .env を対話的に生成/更新するウィザード
  - .env と config/*.yaml の妥当性チェック CLI

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。仮想環境を使うことを推奨します。

   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストールします（プロジェクトに requirements.txt があればそちらを利用）。最低限必要なパッケージ:

   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証時に YAML を検証したい場合）

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. .env を作成します（ウィザード推奨）:

   ```
   python -m kabusys.config_setup
   ```

   生成後に設定が正しいか確認:
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```

   重要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要なオプション/デフォルト:
   - KABUSYS_ENV: development | paper_trading | live (default: development)
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - LOG_LEVEL: INFO
   - OPENAI_API_KEY: OpenAI を使う機能を利用する場合に必要
   - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）

   自動ロード:
   - プロジェクトルート (.git または pyproject.toml を基準) が見つかれば `.env` → `.env.local` の順で自動読み込みされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必要なデータディレクトリを作成（.env の DB パスに応じて）:
   ```
   mkdir -p data
   ```

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（フォアグラウンド）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
  - 起動時に `data/execution.pid`（デフォルト）を書きます
  - 停止は `data/stop_requested.flag` を作成するか Ctrl+C

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で変更:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番用 sqlite_path を使って監視テーブルを初期化します。

- 設定ウィザード・検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（プログラム呼び出し例）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定してください。
  - news_nlp の programmatic 呼び出し例（DuckDB 接続を渡す）:
    ```
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10))
    ```

- Research / factor 計算（例）
  ```
  from kabusys.research import calc_momentum
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  calc_momentum(conn, date.today())
  ```

---

## 停止・フラグ類

- 停止フラグ（run_execution / run_monitoring の終了）
  - data/stop_requested.flag を作成すると各プロセスは検知して安全に終了します。
- Kill Switch（監視が起動している場合）
  - `KillSwitch` が条件を満たすと `data/kill.flag` を書き込みます。ExecutionEngine は起動時にこのフラグを確認して起動を中止できます（KILL_FLAG_CLEAR_ON_START で自動クリア制御）。
- PID ファイル
  - ExecutionEngine は起動時に pid をファイルに書きます（デフォルト: data/execution.pid）。SystemMonitor はこの PID ファイルの有効性を確認します。

---

## ディレクトリ構成（主要ファイルと簡単説明）

- src/kabusys/
  - __init__.py — パッケージ定義、version
  - config.py — 環境変数/.env の読み込み・Settings クラス
  - config_setup.py — .env を対話的に生成するウィザード CLI
  - validate_config.py — .env / config/*.yaml の起動前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（本番／ペーパー分離）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・aggregate cap・lot 単位丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — レジーム判定（ETF + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite による監視用 DB 層（テーブル作成・読み書き）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 滞留注文・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルで Execution を停止させるユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （未表示）通知ロジック
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他:
- data/ — 実行時に生成される DB / flag / pid などのデータ置き場（デフォルト）
- config/ — 設定用 YAML（system_config.yaml 等。validate_config で参照）

---

## 注意事項・運用上のヒント

- .env は絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも警告あり）。
- KABUSYS_ENV の設定により挙動が変わります。特に `live` を設定する前に validate_config で警告を確認してください。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）に課金が発生します。開発時は注意してください。
- DuckDB のテーブルスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）に依存するモジュールが多数あります。研究／AI 機能を使う場合は想定のスキーマでデータを準備してください。
- run_monitoring は MONITOR_POLL_INTERVAL によるポーリングを行います。短すぎると過負荷や不要なログが増えるためデフォルト 60 秒推奨です。
- Paper Trading は production DB と分離されています。KABUSYS_ENV=paper_trading 時は PAPER_TRADING_SQLITE_PATH を確認してください。

---

## 追加情報 / 開発者向け

- 各モジュールは docstring に設計方針や注意点が書かれています。実装や拡張を行う際はそちらを参照してください。
- テストを書く際は .env 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用すると便利です。
- OpenAI 呼び出し部は内部で再試行・パーシングの冗長性を持たせていますが、ユニットテストでは `_call_openai_api` をモックして外部依存を切ることを推奨します。

---

必要であれば README の英語版やセットアップ手順の自動化（Docker / docker-compose / Makefile）テンプレートも作成できます。どの部分を詳しく書き足しましょうか？