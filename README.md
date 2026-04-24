# KabuSys

日本株向けの自動売買・リサーチ基盤（KabuSys）。  
シグナル生成 → ポートフォリオ構築 → 発注（実運用 or ペーパートレード）に加え、監視・アラート、AI を使ったニュース評価、リサーチ用ユーティリティを備えたモジュール型のコードベースです。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つコンポーネント群で構成されています。

- ExecutionEngine：ブローカー連携（実口座 / ペーパートレード）による発注実行
- Monitoring：システム稼働性・データ鮮度・注文状態・リスク（ドローダウン等）を定期監視し、必要に応じてアラート／Kill Switch を発動
- Portfolio モジュール：候補選定、配分重み、ポジションサイズ計算、セクター制約等の純粋関数群
- Research モジュール：DuckDB 上の価格データからファクター計算・特徴量探索を実施
- AI モジュール：OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- ユーティリティ：設定（.env）ウィザード、設定検証、ロギング設定、プロセス優先度設定 等
- Tools：ペーパートレード検証レポート生成等の CLI ユーティリティ

設計方針は「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス排除（date.today()/datetime.today() を直接参照しない）」「フェイルセーフ（API 失敗時はスキップやフォールバック）」などです。

---

## 主な機能一覧

- 実行エンジン（ExecutionEngine）
  - 本番（kabuステーション） / ペーパートレード（MockBroker）対応
  - リスク管理（最大ポジション比率、利用率、ドローダウン等）
- 監視（Monitoring）
  - CPU / メモリ / ディスク使用率、プロセス生存チェック、データ鮮度チェック
  - 注文滞留・約定異常検出、リスクイベント記録、kill.flag の自動作成
  - ログは SQLite（monitoring DB）と DuckDB（分析用）に記録
- ポートフォリオ構築
  - 候補選定（スコア順）・等配分・スコア加重配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ決定（単元株丸め、aggregate cap）
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）等の統計機能
- AI
  - ニュースを LLM（gpt-4o-mini 想定）でスコアリングし ai_scores に保存
  - マクロニュース + ETF MA200 を使った市場レジーム判定
  - API 呼び出しは冗長性（リトライ・バックオフ）を持つ
- ツール
  - ペーパートレード検証レポート生成スクリプト（期間指定可能）
- 設定まわり
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）

---

## 動作環境 / 要件

- Python 3.10+
- 必要パッケージ例（プロジェクトに requirements.txt がない場合）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（kabuステーション API, OpenAI 等、必要に応じて）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリを取得
   ```bash
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. data / logs ディレクトリの作成（多くの実行スクリプトが自動生成しますが、手動でも可）
   ```bash
   mkdir -p data logs
   ```

4. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードで J-Quants トークンや KABU API パスワードなどを入力してください。
   重要: .env は決して Git にコミットしないでください。

5. 設定検証
   ```bash
   python -m kabusys.validate_config       # 警告は表示するが exit 0
   python -m kabusys.validate_config --strict  # 警告も FAIL として exit 1
   ```

6. （任意）OpenAI を使う機能を利用する場合は環境変数 OPENAI_API_KEY を設定

---

## 使い方（主要 CLI / スクリプト）

- ExecutionEngine 起動
  - 本番: KABUSYS_ENV=live（実際に発注）
  - ペーパートレード: KABUSYS_ENV=paper_trading（MockBroker を使用、デフォルト DB: data/paper_trading.db）
  ```bash
  python -m kabusys.run_execution
  ```
  挙動:
  - 起動時にプロセス優先度を "high" に設定
  - SQLite / DuckDB に接続
  - data/stop_requested.flag が存在する場合は起動を中止
  - 実行中に data/stop_requested.flag を生成するとエンジン停止

- Monitoring 起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  オプション / 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。不正値はデフォルトにフォールバック。
  挙動:
  - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは一元管理）
  - stop フラグ（data/stop_requested.flag）検出でループ終了

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config [--strict]
  ```

- ペーパートレード検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定が必要な場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - api_key を省略すると環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError。

---

## 停止・Kill の仕組み

- data/stop_requested.flag
  - 実行中の run_execution / run_monitoring がループを終了するための外部停止フラグ
- Kill Switch（kill.flag）
  - 監視コンポーネントがリスク条件（例: ドローダウン閾値超過、ポジション上限）を検知した場合に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動クリアされる（本番では 0 推奨）
- PID ファイル
  - ExecutionEngine は起動時に pid ファイル（data/execution.pid など）を扱います

---

## ロギング

- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます
- ファイルは日次ローテーションされ、デフォルトで 30 日分保持
- setup_logging(app_name="execution") のように各起動スクリプトから共通の設定が行われます
- ログ出力レベルは環境変数 LOG_LEVEL、引数 level、デフォルト "INFO" の順で決定

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒）
- PAPER_FILL_MODE（paper_trading 時の MockBroker 挙動: instant | partial | never | reject）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START（0/1、本番は 0 推奨）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用、任意）

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                            — 環境変数 / 設定読み込みロジック（自動 .env ロード）
  - config_setup.py                      — .env 対話式ウィザード
  - validate_config.py                   — 起動前設定検証 CLI
  - run_execution.py                      — ExecutionEngine 起動スクリプト
  - run_monitoring.py                     — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py        — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                         — ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py                  — マクロ + ETF MA200 を使ったレジーム判定
  - monitoring/
    - monitoring_db.py                    — monitoring SQLite 操作ラッパー（テーブル作成含む）
    - system_monitor.py                   — システム・データ鮮度監視
    - trade_monitor.py                    — 注文/約定監視（ファイルでは省略されているが存在想定）
    - risk_monitor.py                     — ドローダウン / ポジション数監視
    - kill_switch.py                      — kill.flag 書き込みユーティリティ
    - monitoring_engine.py                — 各 Monitor を束ねるポーリングループ
    - alert_manager.py                    — アラート送信管理（LINE 等、実装箇所）
  - execution/
    - execution_engine.py                 — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py                    — Broker クライアントの生成（Mock / real）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py                — 候補選定・重み計算
    - position_sizing.py                  — 注文株数計算
    - risk_adjustment.py                  — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py                  — ファクター計算（momentum/volatility/value）
    - feature_exploration.py               — 将来リターン・IC 計算等
  - utils/
    - logging_setup.py                    — ログ設定ユーティリティ
    - process_priority.py                 — プロセス優先度 / CPU affinity 設定
  - data/ (ランタイム)
    - monitoring.db (デフォルト: SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - stop_requested.flag
    - kill.flag
    - execution.pid

（上記はコードベースの主要モジュールを抜粋したものです。構成は将来的に変更される可能性があります。）

---

## 開発・運用上の注意

- Python バージョンは 3.10 以上を推奨（型アノテーションの | 演算子などを使用）
- .env は機密情報を含むため、絶対にリポジトリへコミットしないでください
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨
- Monitoring は KABUSYS_ENV にかかわらず、本番 monitoring DB（SQLITE_PATH）を使用する設計です
- OpenAI を使う機能は API 利用料金が発生します。キー・利用制限に注意してください
- DuckDB / SQLite のファイルパス（デフォルトは data/ 以下）は .env でカスタマイズ可能です
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソールのみで継続します

---

## よく使うコマンド一覧

- .env 作成（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン開始
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- 監視ループ開始（ポーリング間隔変更例）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- ペーパートレード検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に含める内容やコマンド例の追加・修正、部署固有の運用ルール（LINE 通知の設定など）を反映したカスタム版が必要であれば教えてください。必要に応じて .env.example のテンプレート作成や、systemd / supervisor 用の起動ユニット例も作成できます。