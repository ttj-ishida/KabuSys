# KabuSys — 日本株自動売買システム

バージョン: 0.1.0

簡単な説明
- KabuSys は日本株を対象とした自動売買システムのコードベースです。  
  主に「ExecutionEngine（実行）」と「Monitoring（監視）」、研究・ポートフォリオ構築、AI を使ったニュース NLP、レポート生成ツールなどから構成されています。  
  本 README は開発者／運用者向けにプロジェクトの概要、機能、セットアップ手順、実行方法、ディレクトリ構成をまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 環境変数（主なもの）
- 使い方（起動・ツール）
- ディレクトリ構成
- 運用上の注意・トラブルシュート

---

## プロジェクト概要

このリポジトリは自動売買のコア機能を含みます:
- 発注エンジン（ExecutionEngine）：ブローカーへの発注／注文管理／リスク管理／約定整合
- 監視（Monitoring）：システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限等）の定期チェック、Kill Switch
- 研究モジュール（Research）：ファクター計算、特徴量探索、IC 計算など（DuckDB 上の時系列データを利用）
- ポートフォリオ構築（Portfolio）：候補選定、重み計算、ポジションサイズ算出、セクター制限やレジーム乗数
- AI（News NLP / Regime Detector）：OpenAI を用いたニュースセンチメント評価、市場レジーム判定（gpt-4o-mini 想定）
- ツール：ペーパートレード検証レポート生成など
- 設定ユーティリティ：.env の対話式生成（config_setup.py）と検証（validate_config.py）

設計方針の要点:
- 設定は環境変数 / .env で管理。プロジェクトルート検出に基づく自動 .env ロード（無効化可）。
- 本番 DB（monitoring）は監視コンポーネントが一貫して利用。ペーパートレード時は Execution は別 DB を使用して分離。
- DuckDB を分析用途（prices_daily / raw_financials 等）に使用。
- OpenAI 呼び出しはリトライ・レスポンス検証を備えた堅牢設計。

---

## 機能一覧

主な機能
- Execution
  - Broker クライアント抽象化（本番/モック切替）
  - 注文管理、OrderRepository
  - RiskManager（ポジション比率、利用率、ドローダウン等）
  - ExecutionEngine（PID ファイル、停止フラグ連携）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス存在チェック
  - TradeMonitor: 注文滞留や約定異常の検出
  - RiskMonitor: ドローダウン／ポジション上限チェック、dashboard 更新、risk_logs 記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み Execution 停止トリガ
  - AlertManager（通知送信責務、実装箇所あり）
- Research / Portfolio
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Spearman）計測、統計サマリ
  - 候補選定・重み付け・ポジションサイズ計算・セクター制限・レジーム乗数
- AI
  - ニュース NLP（raw_news を LLM へ投げて ai_scores に保存）
  - レジーム判定（ETF ma200 とマクロ記事の LLM 結果を合成）
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- 設定/ユーティリティ
  - 対話型 .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ロギングセットアップ、プロセス優先度設定ユーティリティ

---

## 前提・依存関係

必須（開発／運用環境により追加）
- Python 3.9+（型ヒント等を使用）
- pip でインストールする主要パッケージ:
  - duckdb
  - psutil
  - openai (OpenAI Python SDK)
  - （任意）PyYAML（config/*.yaml の構文チェックを行う場合）
- SQLite 標準ライブラリを使用
- ネットワークアクセス（kabuステーション API / J-Quants / OpenAI を利用する場合）

インストール例:
- (推奨) 仮想環境を作成してから:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt
  - もし requirements.txt がない場合:
    - pip install duckdb psutil openai pyyaml

注意:
- psutil によるプロセス優先度設定は OS に依存し、管理者権限が必要な場合があります。

---

## セットアップ手順

1. リポジトリをクローンし、ワークディレクトリに移動
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成し、必要な変数を設定
5. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いとなり終了コード 1 を返します
6. データディレクトリの準備（必要に応じて）
   - デフォルトでは data/ 以下に SQLite / PID / stop/kill フラグ等を保持します
7. DuckDB / SQLite の初期テーブルは起動スクリプトが自動作成します（init_monitoring_db）

---

## 主な環境変数（代表）

（.env に設定する主なキーとデフォルト）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN — 任意: LINE 通知トークン
- LINE_USER_ID — 任意: 通知先ユーザー
- KABUSYS_ENV — execution モード: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、ExecutionEngine は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH にデータを書きます
- LOG_LEVEL — ログレベル（例: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モデル（instant/partial/never/reject、デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト: 60）。run_monitoring は環境変数で上書き可能。

自動 .env ロード
- プロジェクトルートにある .env（および .env.local）は起動時に自動ロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 使い方（主要コマンド・例）

1. .env を対話式に作る
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い

3. ExecutionEngine を起動（本番 / ペーパーにより挙動が異なる）
   - KABUSYS_ENV を設定後に:
     - python -m kabusys.run_execution
   - ペーパートレード:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
     - → MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録されます
   - 実行はデーモン化や systemd / supervisor 等で運用する想定。data/execution.pid に PID ファイルを出力します。
   - 停止制御: data/stop_requested.flag を作成するとループが終了します（run_execution/run_monitoring の両方で使用）

4. Monitoring を起動（監視ループ）
   - MONITOR_POLL_INTERVAL を使って間隔を調整可能:
     - export MONITOR_POLL_INTERVAL=30
     - python -m kabusys.run_monitoring
   - 監視は Settings で決まる sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依存しない点に注意）

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - または DB を明示:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

6. AI 系の関数はライブラリ関数として利用（CLI は無し）
   - 例: ニュース NLP を実行して ai_scores を書き込む（Python から呼び出す）
     - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1), api_key='YOUR_KEY'))"
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, date(2026,4,1), api_key=...)

7. .env の注意
   - 本番環境で KILL_FLAG_CLEAR_ON_START=1 は危険（自動で Kill Flag をクリアしてしまうため）。validate_config でも警告が出ます。

---

## 停止・Kill Switch の仕組み

- data/stop_requested.flag:
  - run_execution/run_monitoring はこのファイルの存在を検知してループを終了します（外部からの優雅な停止指示用）。
- data/kill.flag:
  - KillSwitch が条件を満たす（ドローダウン超過等）とこのファイルを書き込み、ExecutionEngine に停止シグナルを与えます。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていれば自動的に削除されます（本番では 0 推奨）。

---

## ログ

- 共通のロギング設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout へ StreamHandler（標準出力）、ファイルは日次ローテーション（logs/<app_name>.log）で保持（デフォルト 30 日）。
  - 出力先・レベルは環境変数 LOG_DIR / LOG_LEVEL で制御。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity
  - execution/                   — 発注実行関連（BrokerFactory, Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI 連携）
    - regime_detector.py        — 市場レジーム判定（OpenAI 連携）
  - tools/
    - paper_verification_report.py
  - data/                         — 実行時に使用する DB / PID / flag ファイル（プロジェクトルートの data/）

---

## 運用上の注意 / トラブルシュート

- .env の自動読み込み:
  - プロジェクトルートが特定できない（.git や pyproject.toml が見つからない）場合は自動ロードしません。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI 関連:
  - OPENAI_API_KEY が未設定だと AI 機能は動作しません。score_news / score_regime は api_key を引数で渡すことも可能。
  - API 呼び出しはリトライと結果検証を行いますが、API の利用量・レート制限に注意してください。
- psutil による優先度設定:
  - set_process_priority は OS によって動作が異なり、権限が必要な場合があります（特に Windows の priority class、Linux の nice 値）。失敗時は警告を出して継続します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に新しいカラムがない場合に ALTER TABLE を試みる設計になっています。重大な DB 破壊は行いませんが、念のためバックアップを推奨します。
- ログディレクトリ作成失敗:
  - ログディレクトリの作成に失敗した場合、ファイルハンドラは無効化され stdout のみになります。パーミッションを確認してください。
- ペーパートレードと本番 DB の分離:
  - Execution は paper_trading モード時に PAPER_TRADING_SQLITE_PATH を使用しますが、Monitoring は常に sqlite_path（本番監視 DB）を使用します。設定ミスにより監視 DB とペーパートレード DB が混在しないよう注意してください。

---

必要に応じて README を拡張します（例: systemd Unit ファイル例、docker-compose 構成例、さらに詳しい API / DB スキーマ説明など）。どの情報を追加したいか教えてください。