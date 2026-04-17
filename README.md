# KabuSys

日本株自動売買システム（軽量版）  
このリポジトリは KabuSys のコアコンポーネント群を含みます。取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI ベースのニュース解析などのモジュールが実装されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・運用補助システムです。主な設計ポイント：

- ExecutionEngine による発注処理（本番 / ペーパートレード切替）
- Monitoring（System / Trade / Risk）によりシステム健全性・注文状態・リスクを監視
- Portfolio Construction（候補選定、重み算出、ポジションサイズ決定）
- Research（ファクター計算、将来リターン、IC 評価）
- AI モジュール（OpenAI を用いたニュースセンチメント評価、マーケットレジーム判定）
- DuckDB / SQLite を利用したデータ格納・分析基盤
- 環境設定ウィザード・設定検証 CLI を提供

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話式作成
- 設定検証 CLI（python -m kabusys.validate_config）で必須環境変数や設定ファイルをチェック
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
  - 停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - SystemMonitor をポーリングして system_status 等を記録
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- MonitoringEngine（System / Trade / Risk をまとめてポーリング）
  - Kill Switch（drawdown やポジション上限で Execution を停止）
  - AlertManager を使用した通知フロー（実装に依存）
- Portfolio モジュール
  - 候補選定（select_candidates）
  - 等重・スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
- Research モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Information Coefficient）算出
- AI モジュール
  - news_nlp: OpenAI を用いたニュースごとの銘柄センチメント算出（ai_scores テーブルへの書き込み）
  - regime_detector: ETF とマクロニュースを使った market_regime 判定と書き込み
- ツール
  - paper_verification_report: ペーパートレードDB から検証レポートを生成（稼働率・約定率・レイテンシ等）

---

## 必要な依存パッケージ

主に次を想定しています（環境により追加が必要）：

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config 検証時に YAML の検査を行う場合）
- sqlite3（標準ライブラリ）

インストール例（仮）:
- pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt があればそれを使用してください）

---

## セットアップ手順

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. 環境変数の準備（.env を作成）
   - 推奨: 対話式ウィザードを使用
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルートに配置）
     - 必須環境変数:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - よく使うオプション:
       - KABUSYS_ENV (development | paper_trading | live)
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
       - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
       - OPENAI_API_KEY（AI 機能を使う場合）
       - LOG_LEVEL（DEBUG|INFO|...）
       - KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag をクリア）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従い .env や config/*.yaml を修正

5. データディレクトリ
   - data/ 配下を作成（スクリプト実行時に自動作成されることもある）
   - stop_requested.flag, kill.flag, execution.pid などは data/ に置かれる（スクリプトが参照/作成）

---

## 使い方（主要スクリプト）

- 環境変数の自動ロードは既定では有効。テスト等で無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

1. 環境設定ウィザード
   - python -m kabusys.config_setup
   - .env を対話式に作成・更新します。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を指定すると警告も失敗（exit 1）扱いになります。

3. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL（秒）: ポーリング間隔を上書き（デフォルト 60）
     - 監視は Settings.sqlite_path を使い常に本番用の sqlite_path を参照（環境に依らず）
   - 停止: プロジェクトルート/data/stop_requested.flag が存在するとループ終了

4. 実行エンジン起動（Execution）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用
     - 起動時に data/stop_requested.flag が存在すると起動をスキップ
     - 実行中は data/execution.pid を PID ファイルとして管理（Settings.pid_file_path）
     - 停止は data/stop_requested.flag を作成することで行う（run_execution が検出して安全停止）
   - 環境変数:
     - PAPER_FILL_MODE（instant | partial | never | reject） — ペーパートレードでの約定動作を制御

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
   - 出力: 稼働率、注文成功率、送信率、レイテンシ指標、PASS/FAIL 判定

6. AI / リサーチ機能（プログラム的に利用）
   - news_nlp.score_news(duckdb_conn, target_date, api_key=None) — OpenAI API を使って ai_scores を更新
     - OPENAI_API_KEY が必要（引数または環境変数）
   - regime_detector.score_regime(duckdb_conn, target_date, api_key=None) — market_regime を算出・保存
   - research モジュールの関数は DuckDB 接続を渡して呼び出します（例: calc_momentum, calc_volatility, calc_value）

---

## 停止 / Kill Switch の仕組み

- 手動停止フラグ:
  - data/stop_requested.flag: run_monitoring や run_execution がチェック。存在すると起動中ループを停止
  - data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine に停止信号を送る用途。Settings.kill_flag_clear_on_start=1 の場合は起動時に自動クリア
- KillSwitch は RiskMonitor の検知（例: drawdown 超過、ポジション上限超過）により write される

---

## 設定項目（主要な環境変数）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用に影響する主な変数:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（data/paper_trading.db）
- OPENAI_API_KEY: AI 機能で必要
- LOG_LEVEL: ログ出力レベル（INFO 等）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 配下の主なファイル・モジュールです（抜粋）。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py        — SQLite ベースの永続化層
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信管理、省略箇所あり）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py     — プロセス優先度・CPU affinity ユーティリティ
  - (その他)
    - data/                   — 実行時に作成されることがある（monitoring DB 等）

---

## 開発 / デバッグのヒント

- 設定を素早く切り替える:
  - KABUSYS_ENV を development にすれば多くの機能が発注なしで動作（ただしモジュールの実装に依存）
- 自動環境変数読み込みを無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みをスキップ
- CPU 優先度設定:
  - 起動スクリプトは最初に set_process_priority("high") を呼ぶ（psutil の権限に依存）
- DuckDB のクエリや AI 呼び出しは副作用があるため、テスト時はモックやローカル DB を使う
- 設定検証 CLI は .env と config/*.yaml の存在・簡易パースをチェックします（PyYAML がない場合は YAML 検証をスキップ）

---

## ライセンス・注意事項

- .env には機密情報（API キー、パスワード）を含むため、絶対に Git 等にコミットしないでください。
- KABUSYS_ENV=live の設定は実際に発注を行います。設定・権限・資金管理を慎重に行ってください。

---

README は今後の機能追加やコード構成の変更に合わせて更新してください。必要であればコマンド例や環境変数の詳細、実行フロー図などを追記します。