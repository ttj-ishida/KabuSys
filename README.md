# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買基盤（バックテスト・ペーパートレード・本番運用を想定）です。  
README は主要な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します：

- 株価データの集計・分析（DuckDB を利用）
- ファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定・配分・リスク調整・ポジションサイジング）
- 実際の発注（kabuステーション連携）およびペーパートレードの分離運用
- 監視（System / Trade / Risk）と Kill Switch（閾値超過時の停止信号）
- ニュース NLP / レジーム判定（OpenAI を使用するモジュール）
- 運用補助ツール（設定ウィザード、設定検証、検証レポート生成など）

設計方針として、DB（DuckDB/SQLite）接続を渡して処理する関数群や、純粋関数（副作用なし）で記述されたポートフォリオロジックが中心です。監視・実行エンジンはプロセス優先度設定やログ、PID/フラグファイルを用いた制御を備えています。

---

## 主な機能一覧

- 環境管理
  - .env の自動読み込み（プロジェクトルートに `.env` / `.env.local` がある場合）
  - 対話式設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行エンジン
  - ExecutionEngine: ブローカー接続、注文管理、リスク管理、発注実行
  - Paper Trading モード: 実口座と完全分離して `data/paper_trading.db` を使用（MockBrokerClient）
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログ永続化（SQLite: monitoring.db）
  - Kill Switch（閾値超過時に `data/kill.flag` を作成して ExecutionEngine を停止）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等金額/スコア加重、セクター制限、レジーム補正、ポジション算出（単元株丸めなど）
- リサーチ・ファクター計算
  - Momentum/Volatility/Value などを DuckDB 上で計算
  - IC（Information Coefficient）や統計サマリー
- AI/ニュース系（OpenAI 必須）
  - ニュースを LLM でセンチメント評価して ai_scores へ書き込み
  - マクロニュース + ETF MA200 を使った市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## 必要な依存パッケージ

最低限（一例）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定検証で config/*.yaml を検証する場合）
- sqlite3（標準ライブラリ）
- その他、requirements.txt があればそちらを参照してください。

インストール例（pip）:

```
pip install duckdb psutil openai pyyaml
```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

任意/デフォルト:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使うモジュールで必要
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）

注意:
- 自動で .env をロード（プロジェクトルートに .env/.env.local）します。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env を生成するには設定ウィザード（下記）を利用してください。

---

## セットアップ手順（開発 / ローカル実行向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
2. 必要パッケージをインストール（上記参照）
3. .env を作成
   - 対話式ウィザード:

     ```
     python -m kabusys.config_setup
     ```

   - 生成後は `.env` に機密情報が含まれるため Git 管理しないでください。

4. 設定検証（起動前に推奨）:

```
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

5. DB 初期化
   - DuckDB / SQLite のファイルは多くの処理で自動的に初期化・テーブル作成されます（例: monitoring は init_monitoring_db を使って必要テーブルを作成）。

---

## 実行方法（代表的なコマンド）

- 監視プロセス起動（Monitoring）

```
python -m kabusys.run_monitoring
```

環境変数でポーリング間隔を上書き:

```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 実行エンジン起動（ExecutionEngine）

```
python -m kabusys.run_execution
```

KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。

- 設定ウィザード

```
python -m kabusys.config_setup
```

- 設定検証

```
python -m kabusys.validate_config
```

- Paper Trading 検証レポート（ツール）:

```
python -m kabusys.tools.paper_verification_report
# 期間指定:
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

---

## 停止・制御方法

- Global 停止フラグ（run_monitoring / run_execution が監視）
  - data/stop_requested.flag を作成すると、監視ループや実行スレッドが検知して優雅に終了します。
- Kill Switch（リスク超過時）
  - RiskMonitor + KillSwitch により `data/kill.flag` が作成されると ExecutionEngine に停止シグナルが渡ります。
  - 設定により起動時に kill.flag を自動クリアするオプション（KILL_FLAG_CLEAR_ON_START）がありますが、本番では `0` 推奨。
- PID ファイル
  - 実行開始時に PID が `data/execution.pid` 等に書き出されます（Settings.pid_file_path を参照）。

---

## ログ

- ログはルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定します。
- デフォルトログディレクトリ: logs/
- アプリごとのログファイル: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- LOG_LEVEL / LOG_DIR 環境変数で制御可能

---

## AI（OpenAI）機能について

- ニュース NLP（kabusys.ai.news_nlp）とレジーム判定（kabusys.ai.regime_detector）は OpenAI API を利用します。
- 必要: OPENAI_API_KEY 環境変数（または関数へ明示的に渡す）
- API 呼び出しはリトライやバックオフを実装しています。API 失敗時はフェイルセーフ（0 相当 or スキップ）で継続します。

---

## よく使う設定・環境変数まとめ（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能用)
- LOG_LEVEL (DEBUG/INFO/...)
- MONITOR_POLL_INTERVAL (監視ポーリング sec, default 60)
- PAPER_FILL_MODE (instant/partial/never/reject)

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を基準）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（OpenAI + ETF）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py       — （監視ロジック、ファイルには一部のみ提示）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック、ファイルに依存）
  - execution/               — ExecutionEngine / OrderManager / RiskManager 等
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/ (実行時生成)
    - monitoring.db (デフォルト SQLite)
    - paper_trading.db
    - kabusys.duckdb
    - kill.flag / stop_requested.flag / execution.pid など制御用ファイル
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルの抜粋です。リポジトリ全体の詳細はツリーを参照してください。）

---

## 開発・運用上の注意点

- .env には機密情報を含めるため必ず Git 管理から除外してください。
- KABUSYS_ENV を `live` に設定する際は validate_config の出力を確認し、LINE 通知設定など監視手段が整っていることを確認してください。
- DuckDB / SQLite ファイルのバックアップや永続保存方針を決めておいてください（分析と本番 DB を分離）。
- AI 機能は API コスト・レイテンシが発生します。運用頻度やバッチサイズ（定数で制御）を調整してください。
- Process 優先度や CPU affinity の設定は管理者権限が必要な場合があります。権限不足時は警告ログが出てスキップされます。

---

もし README に追記してほしい実行例、環境変数一覧のテンプレート（.env.example 形式）、あるいは systemd / docker-compose 用の起動例が必要であれば、目的（開発/本番/コンテナ化）を教えてください。サンプルを作成します。