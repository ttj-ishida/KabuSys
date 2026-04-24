# KabuSys

日本株自動売買システムの一部を実装した Python パッケージ。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算／特徴量探索）、AI（ニュース NLP / レジーム判定）などのモジュール群と、環境設定ウィザード／検証ツールが含まれます。

> バージョン: 0.1.0

---

## 概要（Project overview）

KabuSys は日本株の自動売買運用を想定したモジュール群です。主な責務は以下の通りです。

- ExecutionEngine: 発注・注文管理・リスク管理を行う実行エンジン（本番／ペーパートレード対応）
- Monitoring: システム状態・注文状態・リスク（ドローダウン等）を監視し、アラート・Kill Switch を管理
- Portfolio: 候補選定、重み付け、株数決定（ポジションサイジング）などの純粋関数群
- Research: DuckDB 上の時系列データからファクターを計算・分析するモジュール
- AI: OpenAI を使ったニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）
- ツール: .env ウィザード、設定検証、Paper Trading 検証レポート生成 など

設計方針として、DB（DuckDB / SQLite）や外部 API 呼び出しを明示的に切り分け、ユニットテストや部分実行がしやすい純粋関数を多用しています。

---

## 機能一覧（Features）

- 環境設定ウィザード（.env 作成・更新） — python -m kabusys.config_setup
- 設定検証 CLI（.env + config/*.yaml のチェック） — python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替） — python -m kabusys.run_execution
  - paper_trading 環境では MockBroker を使用し data/paper_trading.db に記録
- Monitoring 起動スクリプト（定期ポーリング） — python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で上書き可（MONITOR_POLL_INTERVAL）
  - System / Trade / Risk の各モニタと Kill Switch を統合
- AI: OpenAI（gpt-4o-mini）を使ったニュースセンチメント（kabusys.ai.score_news）とレジーム判定（kabusys.ai.regime_detector.score_regime）
- Research: モメンタム・ボラティリティ・バリューファクター計算、将来リターン・IC 計算等
- Portfolio: 候補選定、等重・スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Tools: Paper Trading の検証レポート生成 — python -m kabusys.tools.paper_verification_report

---

## 前提／依存（Requirements）

推奨: Python 3.10 以上（コードは型ヒントで 3.10+ を想定）

主な Python パッケージ依存（抜粋）:
- duckdb
- psutil
- openai
- PyYAML（config 検証時に任意で使用）

仮想環境作成例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai pyyaml
```

（実プロジェクトでは requirements.txt / Poetry を利用してください）

---

## セットアップ手順（Setup）

1. レポジトリをクローンして仮想環境を作成、依存をインストール
2. .env の作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他（代表例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - OPENAI_API_KEY: AI 機能を使う場合に必要
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
3. 設定検証（オプション）:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL として扱う場合
   python -m kabusys.validate_config --strict
   ```
4. 必要に応じて data/ や logs/ ディレクトリを作成（logging_setup が自動で作成する場合あり）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (required)
- KABU_API_PASSWORD (required)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV: development | paper_trading | live (default: development)
  - paper_trading の場合、発注は MockBrokerClient により data/paper_trading.db に記録
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- MONITOR_POLL_INTERVAL (監視ループの秒間隔、default: 60)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（監視・停止制御に利用）
- PAPER_FILL_MODE (paper_trading の MockBroker の fill_mode、instant|partial|never|reject)

.env は機密情報を含むため、絶対に Git にコミットしないでください。

---

## 使い方（Usage）

起動スクリプト（CLI 形式）:

- ExecutionEngine を起動（本番／ペーパートレードは KABUSYS_ENV による）:
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - ExecutionEngine は PID ファイルを生成します（Settings.pid_file_path 参照）。
  - ペーパートレード環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用。

- Monitoring を起動（ポーリング）:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で設定可能（デフォルト 60 秒）。
  - 停止は data/stop_requested.flag を作成することで検知して終了します。

- 環境設定ウィザード（.env を対話的生成）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

プログラムから利用する（ライブラリ API）:

- AI（ニューススコア）:
  ```py
  from kabusys.ai import score_news
  # conn: duckdb connection, target_date: datetime.date
  count = score_news(conn, target_date, api_key="xxxxx")
  ```

- レジーム判定:
  ```py
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="xxxxx")
  ```

- Research / Portfolio 関数群:
  - kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.portfolio.select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

ログ:
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一設定され、コンソール（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力されます。

停止・KillSwitch:
- 2 種類のフラグファイルが利用されます:
  - data/stop_requested.flag: 実行中スクリプト（run_execution/run_monitoring）に対する外部停止要求（存在を検知して終了）
  - data/kill.flag: Monitoring の KillSwitch が書き込むファイル（主にリスクトリガー等で ExecutionEngine を停止させるためのシグナル）。パスは Settings.kill_flag_path で設定可能

---

## ディレクトリ構成（Directory structure）

（主要ファイル / ディレクトリのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・Settings 管理、自動 .env ロード
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py — マーケットレジーム判定（LLM + MA200）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文ログ監視）※実装ファイルが存在
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — Kill Switch（flag 書き込み）
    - monitoring_engine.py — 各 Monitor を統合するポーリングエンジン
    - alert_manager.py — （アラート送信用、LINE 連携等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・aggregate cap ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

data/ および logs/ は実行時に使用されるランタイム領域（DB, flag, pid, ログなど）。

---

## トラブルシューティング（よくある問題）

- 必須環境変数未設定:
  - validate_config でエラーになります。JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD は必須。
- DuckDB / SQLite ファイルの親ディレクトリがない:
  - validate_config は警告を出します。logs/ や data/ は起動時に自動作成されることもありますが、権限に注意してください。
- OpenAI API の呼び出しエラー:
  - OPENAI_API_KEY を設定してください。429 やタイムアウトはモジュール側でリトライ実装がありますが、上限を超えると一部スコアが落ちます（フェイルセーフで継続）。
- 権限不足でプロセス優先度設定に失敗:
  - utils.process_priority は権限や OS によりスキップするよう安全に実装されています（警告ログが出ます）。

---

必要に応じて README を拡張して、具体的な ExecutionEngine の設定項目（risk config 等）や、利用する外部サービス（kabuステーション、J-Quants、LINE）の設定手順・鍵の管理方法を追記してください。README の追記や特定コマンドのサンプルが必要であれば、どの箇所を詳しく書くか教えてください。