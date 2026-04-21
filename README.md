# KabuSys

日本株向け自動売買・調査プラットフォームの一部を実装した Python パッケージ（サブモジュール群）。  
このリポジトリには実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI ニュース分析などのユーティリティが含まれます。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群から成ります。

- ExecutionEngine：発注・注文管理・リコンシリエーション・リスク管理を担うランタイム（run_execution）。
- Monitoring：システム稼働・注文状態・リスクを定期チェックする監視サービス（run_monitoring）。
- Portfolio：銘柄選定、重み計算、ポジションサイズ決定、リスク調整（純粋関数群）。
- Research：DuckDB 上でのファクター計算・特徴量探索ツール（モメンタム、ボラティリティ、バリュー等）。
- AI モジュール：ニュース記事を LLM（OpenAI）でスコアリング、マーケットレジーム判定。
- ツール：設定ウィザード、設定検証、ペーパートレード検証レポート等。

設計方針の一例：
- 環境変数 / .env による設定管理（自動ロードあり）。
- Paper trading（検証）と live（本番）は DB を分離。
- DuckDB を分析用に、SQLite を監視 / 発注ログ用に使用。
- LLM 呼び出し部分はリトライやバリデーション等の堅牢化を実装。

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - Broker クライアントの抽象化（Mock を利用して分離）
  - OrderManager / RiskManager / Reconciler 組立てとセッション実行
  - 停止フラグ（data/stop_requested.flag）で安全に停止

- 監視サービス（run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を統合したポーリングループ
  - kill.flag による ExecutionEngine 停止トリガ（KillSwitch）
  - ポーリング間隔を環境変数でオーバーライド（MONITOR_POLL_INTERVAL）

- 監視 DB（monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard の自動作成・マイグレーション
  - MonitoringDB クラスを通じた読み書き API

- ポートフォリオ構築（portfolio）
  - 候補選定（select_candidates）
  - 等分配 / スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- リサーチ（research）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC・統計サマリ（calc_forward_returns, calc_ic, factor_summary）

- AI（ai）
  - news_nlp.score_news：raw_news を集約して OpenAI で銘柄ごとにスコアリング、ai_scores に書き込み
  - regime_detector.score_regime：ETF / マクロを合成して market_regime を判定・書き込み

- 設定支援ツール
  - config_setup.py：対話式 .env 生成ウィザード
  - validate_config.py：環境変数・config/*.yaml の事前検証
  - tools/paper_verification_report.py：ペーパートレード DB を集計して PASS/FAIL レポート生成

---

## セットアップ手順

想定環境：Python 3.10+（パッケージの import から typing の | 記法が利用されているため少なくとも 3.10 以上を推奨）

1. リポジトリを取得する
   - git clone ... 等でソースを取得

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - もしくは最低限必要なパッケージ:
     - pip install duckdb psutil openai

   注意: 実際の運用では additional パッケージ（PyYAML 等）が必要になる箇所があります。validate_config は YAML 検査のため PyYAML を利用します。

4. .env の作成
   - 対話式ウィザードを使うと簡単です:
     - python -m kabusys.config_setup
   - 手動で作成する場合、最低限必須（validate_config 参照）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - その他（必要に応じて）: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, OPENAI_API_KEY 等

   自動ロード挙動:
   - プロジェクトルートに .env / .env.local があれば自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. ログディレクトリ
   - デフォルトは `logs/`。LOG_DIR 環境変数で変更可能。
   - ログは日次ローテート（30日保持）設定。

---

## 使い方

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）になります。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合:
    - MockBroker を使用して `data/paper_trading.db` に記録（本番 DB と完全分離）
  - 停止制御:
    - スクリプトはプロジェクトルート/data/stop_requested.flag を検知すると停止します。
    - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）に書き込まれます。

- 監視サービス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - デフォルト 60 秒
    - 環境変数で上書き: MONITOR_POLL_INTERVAL=30 など（1 秒以上の整数）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境が何であれ）。
  - 監視が KillSwitch を評価して `data/kill.flag` を書き込むと ExecutionEngine 側で停止トリガとして利用されます。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI スコアリング / レジーム判定（プログラム呼び出し例）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーは引数または環境変数 OPENAI_API_KEY を利用します。

- 監視 DB 初期化
  - run_execution / run_monitoring の起動時に自動で init_monitoring_db が呼ばれます。
  - 手動で初期化したい場合は MonitoringDB の init_monitoring_db を利用してください。

---

## 主要な環境変数（代表）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を消すか（0/1）

---

## 停止・フラグ関連

- data/stop_requested.flag
  - run_execution と run_monitoring が参照する「停止要求」フラグファイル。存在を確認して安全にループを抜けます。

- data/kill.flag
  - KillSwitch が書き込むファイル。主に ExecutionEngine を停止させるために使用されます。
  - KillSwitch.evaluate(...) がトリガー条件を満たすと書き込まれます。
  - Settings.kill_flag_clear_on_start = 1 のときは起動時にクリアされる挙動があります（本番での自動クリアは危険なので注意）。

---

## 主要モジュール・ディレクトリ構成

（抜粋・概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み / .env 自動ロード / Settings クラス
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring 起動スクリプト

  - ai/
    - news_nlp.py
      - news の LLM スコアリング（score_news）
    - regime_detector.py
      - マーケットレジーム判定（score_regime）

  - monitoring/
    - monitoring_db.py
      - DB スキーマ作成 / MonitoringDB（読み書き API）
    - system_monitor.py
      - システム稼働・データ鮮度監視
    - trade_monitor.py
      - （注文の滞留／異常検出等を行うモジュール）
    - risk_monitor.py
      - ドローダウン／ポジション上限監視
    - kill_switch.py
      - kill.flag の生成・操作
    - monitoring_engine.py
      - 各 Monitor を束ねる実行ループ

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py

注: この README は主要ファイルの抜粋に基づく要約です。個別モジュールやクラスの詳細はソース内ドキュメント（docstring）を参照してください。

---

## よくある操作例（コマンド）

- .env を作る（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視サービス起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

---

## トラブルシューティング / 注意事項

- .env は絶対にリポジトリへコミットしないでください（config_setup でも注意書きあり）。
- OpenAI 利用部分は API キー必須。API 呼び出しは再試行や失敗時のフォールバックを実装していますが、API 利用料発生に注意してください。
- run_monitoring は常に Settings.sqlite_path（本番監視 DB）を参照します。paper_trading の監視も本番 DB を使う点に注意。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と完全に分離します。
- プロセス優先度や CPU affinity の設定は OS 権限に依存します。psutil による設定が失敗しても警告を出して継続します。

---

以上がこのコードベースの概要・セットアップ・使用方法です。各モジュールの詳細や追加の CLI が必要であれば README に追記しますので、必要な箇所を教えてください。