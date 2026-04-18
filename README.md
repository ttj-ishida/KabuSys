# KabuSys

日本株自動売買システム（KabuSys）リポジトリの README。  
このドキュメントはリポジトリ内のスクリプト・モジュール群を元に作成しています。セットアップ手順、主要機能、使い方、ディレクトリ構成などを日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤（バックエンドライブラリ群と運用スクリプト）です。主な責務は次の通りです。

- シグナル／ポートフォリオ構築（ポートフォリオ選定、配分、ポジションサイズ計算）
- ExecutionEngine（注文管理、リスク管理、注文リコンシリエーション）
- 監視（System / Trade / Risk の定期チェック、Kill Switch）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI関連（ニュースの NLP によるセンチメント評価、レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の一部：
- DB は DuckDB（分析） と SQLite（監視・発注ログ）を使用
- Paper Trading（検証）と Live（本番）は DB を分離
- LLM（OpenAI）をニュース評価やレジーム判定に利用（失敗時はフェイルセーフ）

---

## 主な機能一覧

- config
  - .env 自動ロード・パース（.env / .env.local）
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカクライアント抽象化（paper_trading 時は MockBroker を使用）
  - リスク管理（rate limit、position limits、drawdown 等）
- monitoring
  - System / Trade / Risk の監視（run_monitoring.py）
  - Monitoring DB（SQLite）への永続化（system_status、trade_logs、risk_logs、positions、dashboard）
  - Kill Switch ロジック（一定条件で data/kill.flag を書き込み、Execution を停止）
  - Alert 管理（LINE 等の通知は設定次第で有効化）
- portfolio
  - 候補選定（スコア順）、等重・スコア加重配分
  - セクターキャップ適用、レジーム乗数（bull/neutral/bear）
  - ポジションサイズ計算（単元丸め、risk-based 等）
- research
  - ファクター計算（momentum/value/volatility）
  - forward returns / IC / ファクター統計
- ai
  - ニュース NLP（OpenAI を使った銘柄別センチメント → ai_scores）
  - 市場レジーム推定（ETF とマクロニュースの組合せ）
- tools
  - paper_verification_report: ペーパートレードDBから検証レポート出力

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10+（型注釈に `X | None` 形式が使われているため）
- SQLite は標準ライブラリで利用可能
- 必要な外部ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証に使用）

例: 仮想環境を作って依存を入れる（requirements ファイルがない場合の例）
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

.env の作成
1. 対話式ウィザードで .env を作成/更新:
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabuAPI パスワードなど必須項目を案内します。

2. 作成後、設定を検証:
   ```
   python -m kabusys.validate_config
   ```
   必須環境変数が欠けているとエラーになります。`--strict` を付けると警告も失敗扱いになります。

主要環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 主要オプション:
  - KABUSYS_ENV = development | paper_trading | live
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/...)
  - OPENAI_API_KEY（AI 機能を使う場合）
  - PAPER_FILL_MODE = instant | partial | never | reject

ログ・データディレクトリ
- ログ: logs/<app_name>.log（setup_logging が自動作成を試みます）
- DB: data/ 以下に duckdb・sqlite 等を置くことを想定

注意点
- KABUSYS_ENV により動作が分岐します（paper_trading は発注をモック化し DB を分離）
- .env は絶対にソース管理にコミットしないでください（機密情報を含む）

---

## 使い方（起動・主要コマンド）

起動スクリプトはモジュールとして実行できます。

1. ExecutionEngine（実行エンジン）起動
```
python -m kabusys.run_execution
```
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に操作ログを書きます。
- 起動時に data/stop_requested.flag が存在すると起動せず終了します。
- 実行中、停止したい場合は監視側から kill.flag を書くか、stop flag を作成します（詳細は下記）。

2. Monitoring（監視ループ）起動
```
python -m kabusys.run_monitoring
```
- デフォルト 60秒間隔で各種チェックを行います。環境変数でポーリング間隔を上書き可能:
  - MONITOR_POLL_INTERVAL（秒、例: export MONITOR_POLL_INTERVAL=30）
- 監視は本番 sqlite_path を利用（KABUSYS_ENV に依存せず本番の monitoring DB を使用する設計）。
- 停止条件: プロジェクトルート/data/stop_requested.flag が存在すると監視ループは終了します。

3. Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```
- デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

4. 設定ウィザード / 検証
```
python -m kabusys.config_setup
python -m kabusys.validate_config [--strict]
```

停止・Kill Switch
- Kill Switch は監視コンポーネント（RiskMonitor 等）が条件を満たすと `data/kill.flag` を書き込みます（Settings.kill_flag_path）。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動クリアします（本番では 0 推奨）。
- 手動で Execution を停止したい場合はプロジェクトルートに `data/stop_requested.flag` を作成してください（run_execution/run_monitoring が検知して終了します）。

---

## よく使う設定の挙動（補足）

- KABUSYS_ENV の値:
  - development: ローカル開発（主に発注なし）
  - paper_trading: ペーパートレード（MockBrokerClient、専用 SQLite）
  - live: 本番（実際に発注）

- PAPER_FILL_MODE（ペーパートレードの約定挙動）:
  - instant / partial / never / reject（上記以外はエラー）

- ロギング:
  - 全スクリプトは共通の setup_logging を使用して stdout と logs/<app>.log に出力します。
  - ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。

- プロセス優先度:
  - 起動時に set_process_priority("high") が呼ばれます。psutil 権限により変更できない場合は警告を出して継続します。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 以下にライブラリ・スクリプトを持っています。主な構成:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の自動ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - research/
    - factor_research.py     — ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 + 永続化 API
    - system_monitor.py
    - trade_monitor.py       — （trade チェックのロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック）
  - execution/
    - execution_engine.py    — ExecutionEngine（セッション管理）
    - broker_factory.py      — BrokerClient 抽象化
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に使用する想定のパス)
    - monitoring.db (default)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb (default DuckDB)
    - kill.flag / execution.pid / stop_requested.flag etc.

注: 上記のうち一部ファイル（trade_monitor.py, alert_manager.py 等）は README 作成元の抜粋に含まれているものの、ここでは主要な役割のみを記載しています。

---

## 開発・デバッグのヒント

- テスト的に監視を 1 回だけ実行したい場合は MonitoringEngine をインスタンス化して `run_once()` を呼ぶと各モニタを一度だけ実行できます（ユニットテスト向け）。
- DuckDB 接続を渡して research / ai の関数を単体実行できます（ローカルの prices_daily / raw_news テーブルが前提）。
- OpenAI 関連は API キーが必要。テスト時は該当モジュールの API 呼び出しラッパーをモックしてください（コード内で patch 対応を想定した設計）。

---

## トラブルシューティング（よくある注意点）

- .env がプロジェクトルートに置かれていることを確認してください（config.py はプロジェクトルートを自動検出して .env を読み込みます）。
- DuckDB / SQLite のパスの親ディレクトリが存在しない場合、validate_config は警告を出しますが、実行時に自動作成されることが多いです。権限に注意してください。
- psutil の一部機能（nice/priority/cpu_affinity）は OS と権限に依存します。権限不足で失敗しても動作自体は継続するように設計されています。
- OpenAI 呼び出しはネットワークエラーや 429 レスポンスに対してリトライ実装がありますが、レート制限等で失敗する可能性はあります。API キー／クォータを確認してください。

---

必要であれば、この README をベースに以下の内容を追加できます：
- requirements.txt の具体的な推奨パッケージとバージョン
- systemd / Supervisor / Docker Compose の起動例
- 実行中ログの読み方と代表的なログメッセージの説明
- 各モジュール（ExecutionEngine / RiskManager / TradeMonitor 等）の詳細設計ドキュメント（API サンプル）

どの追加情報が必要か教えてください。