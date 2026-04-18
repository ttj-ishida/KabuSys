# KabuSys — 日本株自動売買システム (README)

このリポジトリは、日本株自動売買システム「KabuSys」のコアライブラリと起動スクリプト群を含みます。  
README は日本語で、プロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を整理しています。

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群です。

- 日次・リアルタイムのシグナル生成やポートフォリオ構築ロジック（純粋関数ベース）
- 発注エンジン（ExecutionEngine）とブローカークライアントの抽象化（ペーパートレード/本番切替対応）
- システム監視（SystemMonitor / MonitoringEngine）とリスク監視（ドローダウンやポジション上限）
- ニュースを用いた AI ベースのセンチメント評価（OpenAI API 経由）
- Research 用のファクター計算・特徴量解析ユーティリティ
- 運用補助ツール（設定ウィザード、設定検証、ペーパートレード検証レポート生成 など）

設計方針のポイント:
- 多くの演算は DuckDB / SQLite を入力として SQL + Python で完結
- 発注系は本番/ペーパートレードで DB を分離
- ログは統一的なロギング設定（stdout + 日次ファイルローテーション）
- 外部 API 呼び出し（OpenAI 等）はフェイルセーフ（失敗時はフォールバック）

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py : ExecutionEngine を起動（KABUSYS_ENV=paper_trading で MockBroker を使用）
- 監視（別プロセス）
  - run_monitoring.py : SystemMonitor を定期ポーリングして system_status / risk_logs 等へ永続化
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch
- 環境設定・検証
  - config_setup.py : 対話式に .env を生成 / 更新するウィザード
  - validate_config.py : .env と config/*.yaml の事前チェック CLI
- ポートフォリオ構築（純粋関数）
  - 選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research（DuckDB ベース）
  - ファクター（Momentum / Volatility / Value）計算
  - 前方リターン、IC（Spearman）計算、統計サマリー
- AI 関連
  - ニュースセンチメント評価（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- ツール
  - tools/paper_verification_report.py : ペーパートレード DB から検証レポートを生成

---

## 必要な依存ライブラリ

少なくとも以下をインストールしてください（バージョンは適宜指定してください）。

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config の内容検証を行う場合、任意）
- その他（標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など）

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 要件ファイルはリポジトリに含まれていない想定のため、必要なパッケージを手動で追加してください。

---

## 環境変数（主要）

自動読み込み: プロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（最低限）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う任意／上書き可能項目:
- KABUSYS_ENV (development | paper_trading | live) — 実行環境
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB, デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）
- OPENAI_API_KEY（AI 機能利用時）

運用関連:
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリア（本番では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH — デフォルトは data/ 以下

環境変数の完全な一覧・振る舞いは `kabusys.config.Settings` を参照してください。

例（.env の最小例）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存インストール
   - pip install duckdb psutil openai PyYAML
4. 初期設定ファイル作成（推奨）
   - python -m kabusys.config_setup
     - 対話式ウィザードで .env を生成できます
5. 設定検証
   - python -m kabusys.validate_config
   - (--strict をつけると警告もエラー扱い)
6. 必要なディレクトリを作成（logs, data などは自動作成されることが多いですが確認を推奨）
   - mkdir -p data logs

---

## 使い方（起動 / 実行例）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - 通常（KABUSYS_ENV の設定に従う）
  ```
  python -m kabusys.run_execution
  ```
  - ポイント:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い `data/paper_trading.db` に書き込む（本番 DB と分離）
    - 起動時に `data/stop_requested.flag` があると起動しません
    - `data/execution.pid` を生成してプロセス管理に利用します

- 監視プロセス起動（SystemMonitor のループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を変更可能:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は Settings の sqlite_path（本番 DB）を使用してログを保存します
  - 停止は `data/stop_requested.flag` を作成することで検知します

- Paper Trading 検証レポート（コマンドライン）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可

- AI 機能をプログラムから呼ぶ
  - ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` を使用

- ログ
  - ログは stdout とファイル（logs/<app_name>.log）に日次ローテーションで出力されます
  - `kabusys.utils.logging_setup.setup_logging(app_name="execution")` を各スクリプトが呼び出します

---

## 運用メモ・運用時の注意点

- 本番環境設定:
  - `KABUSYS_ENV=live` を使用する際は、LINE 通知設定や kill flag 設定等を慎重に確認してください。
  - `KILL_FLAG_CLEAR_ON_START=1` は本番では危険（起動時に kill flag を消してしまうため）なので 0 を推奨します。
- Kill Switch:
  - KillSwitch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります。監視は冪等に挙動します。
- DB
  - 監視用は SQLite（`SQLITE_PATH`）、分析用は DuckDB（`DUCKDB_PATH`）、ペーパートレードは別 SQLite（`PAPER_TRADING_SQLITE_PATH`）で分離されています。
- プロセス優先度:
  - 起動スクリプトは `set_process_priority("high")` を呼び OS レベルで優先度を上げようとします（失敗しても警告で継続）。
- AI API 呼び出し:
  - レート制限・タイムアウト・一時エラーはリトライ実装あり。API キーの管理に注意してください（.env に書かない運用も検討）。

---

## ディレクトリ構成（主要ファイルの説明）

以下は `src/kabusys` を起点とした主要ファイルと概要です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み / Settings クラスを提供
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - utils/
    - logging_setup.py : 統一的なログ設定
    - process_priority.py : プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py : SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py : CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py : （trade 関連の監視ロジック）
    - risk_monitor.py : ドローダウン / ポジション数監視
    - kill_switch.py : kill.flag 管理
    - alert_manager.py : LINE 等への通知（実装想定）
    - monitoring_engine.py : 各モニタを束ねる
  - execution/
    - ブローカーファクトリ、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等（発注周り）
  - portfolio/
    - portfolio_builder.py : 候補選定 / 重み計算
    - position_sizing.py : 株数算出・単元丸め・制限処理
    - risk_adjustment.py : セクターキャップ・レジーム乗数
  - research/
    - factor_research.py : Momentum / Volatility / Value ファクター
    - feature_exploration.py : 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py : ニュースを OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py : ETF MA + マクロセンチメントから市場レジーム判定
  - tools/
    - paper_verification_report.py : ペーパートレード検証レポート生成ツール

（上記は主要ファイルの抜粋。実装の詳細は各モジュール内の docstring / 関数コメントを参照してください）

---

## 開発時のヒント

- 単体関数（portfolio.*、research.* 等）は副作用を持たない純関数として設計されているためユニットテストが書きやすいです。
- DuckDB 接続を渡してテーブルをモック（小さな in-memory DB）でテストできます。
- OpenAI 呼び出しはモックしやすいように `_call_openai_api` 等を分離しています。ユニットテストでは patch を使って外部呼び出しを置き換えてください。

---

以上が README の要約です。必要であれば以下を追加で用意します：
- requirements.txt のテンプレート
- 具体的な systemd / supervisor 用の起動スクリプト例
- データベース初期化スクリプトやサンプル .env.example

どれを追加しますか？