# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ用 README。

この README はコードベースから抽出した情報を元に、開発者／運用者向けにプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール化されたシステムです。主な役割は次のとおりです。

- シグナル生成／ポートフォリオ構築（research / portfolio モジュール）
- 注文発行・リスク管理・約定管理（execution モジュール）
- システム稼働状況・注文状況の監視とアラート（monitoring モジュール）
- ニュースを用いた AI ベースのセンチメント（ai モジュール）
- ペーパートレード検証用ツールや構成ウィザード等のユーティリティ群

設計上、研究ロジック（DuckDB を使ったファクター計算など）は発注ロジックや外部 API とは分離されています。

---

## 主な機能一覧

- ExecutionEngine: ブローカークライアント経由での実行（本番 / ペーパートレード切替対応）
- Monitoring: SystemMonitor / TradeMonitor / RiskMonitor を統合した監視ループ、Kill Switch による停止シグナル発行
- Portfolio Construction: 候補選択、重み算出、ポジションサイズ決定、セクター制約・レジーム調整
- Research: momentum/value/volatility 等のファクター計算、将来リターン・IC 計算、特徴量サマリ
- AI モジュール: news_nlp（OpenAI を使ったニュースセンチメント）、regime_detector（マクロ+MA を用いた市場レジーム判定）
- 設定管理: .env 対話ウィザード（config_setup.py）、起動前設定検証（validate_config.py）
- ツール: paper_verification_report（ペーパートレード検証レポート生成）
- 共通ユーティリティ: ログ設定（logging_setup）、プロセス優先度・CPU affinity（process_priority）

---

## 前提（依存、必要環境）

最低限の必須パッケージ（抜粋）：

- Python 3.8+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml のパース検証を行う場合）

インストール例（開発環境）:
```
pip install duckdb psutil openai PyYAML
# またはパッケージ化されている場合:
pip install -e .
```

---

## セットアップ手順

1. リポジトリを取得
2. 必要パッケージをインストール（上記参照）
3. .env の作成（対話ウィザード推奨）
   - 実行: `python -m kabusys.config_setup`
   - ウィザードは .env を生成／更新します。.env は決して Git にコミットしないでください。
4. 設定検証
   - 実行: `python -m kabusys.validate_config`  
   - 必須環境変数が未設定のままになっていないか確認してください。`--strict` を付けると警告も失敗として扱います。
5. データディレクトリの作成（自動で作成されることもありますが手動で用意する場合）:
   - `data/`（デフォルトの SQLite / PID / フラグファイル格納先）
   - `logs/`（ログ出力先）

---

## 環境変数（主なもの）

主要な設定は .env または環境変数で与えます。代表的なキー:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

運用関連:
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
  - paper_trading の場合、ExecutionEngine は MockBrokerClient を使用し、`data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）にデータを記録します。
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存先（デフォルト: logs/）
- PID_FILE_PATH — 実行 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag をクリアするか（0/1）

DB 関連:
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードでの約定挙動（instant | partial | never | reject）

AI 関連:
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで必要）

モニタリング:
- MONITOR_POLL_INTERVAL — SystemMonitor ポーリング間隔（秒、デフォルト 60）

その他: 詳細は `kabusys.config.Settings` のプロパティを参照してください。

---

## 使い方（主要コマンド）

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
  - 本番／ペーパートレードは KABUSYS_ENV に依存。
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に `data/stop_requested.flag` が存在する場合は起動せず終了します。
  - 実行中に stop フラグが作成されるとエンジンに停止シグナルを送りシャットダウンします。
  - 実行はスレッドで開始され、PID ファイル（デフォルト: data/execution.pid）を扱います。

- 監視ループ起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）。
  - `data/stop_requested.flag` を検知すると監視ループを終了します。
  - Monitoring は環境に関係なく本番の `SQLITE_PATH` を参照して監視データを記録します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する例
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラムから利用）
  - ニュースセンチメント: `kabusys.ai.score_news(conn, target_date, api_key=...)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)`
  - これらは DuckDB 接続オブジェクトを受け取り、結果をテーブルに書き込みます。API キーが必要です。

- ライブラリとしての利用（research, portfolio 等）
  - 例: DuckDB 接続を渡してファクター計算
    ```py
    from kabusys.research import calc_momentum
    res = calc_momentum(duckdb_conn, target_date)
    ```

---

## 運用メモ / 注意点

- データベース分離:
  - Monitoring（監視）は常に `SQLITE_PATH`（デフォルト: data/monitoring.db）を使用します。
  - Execution は KABUSYS_ENV=paper_trading の場合 `PAPER_TRADING_SQLITE_PATH` を使用して本番 DB と分離します。
- Kill Switch:
  - `KillSwitch` は条件が満たされると `KILL_FLAG_PATH`（デフォルト: data/kill.flag）を書き込み、ExecutionEngine に停止シグナルを送ります。運用時はこの挙動を理解しておいてください。
- 停止フラグ:
  - `data/stop_requested.flag` が存在すると `run_monitoring` / `run_execution` のループはシャットダウン手順を開始します。外部系のプロセス管理やシステム停止で利用できます。
- ログ:
  - ログは stdout とファイル（logs/<app_name>.log）に出力されます。ファイルは日次ローテーション（30 日保持）。
- プロセス優先度:
  - 起動時に `set_process_priority("high")` が呼ばれます。権限がない環境では警告が出ますが動作は継続します。
- AI モジュール:
  - OpenAI API 呼び出しはリトライやエラーハンドリングを備えていますが、API キーとコストに注意してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は必要なテーブル・カラムの作成や簡単なマイグレーションを実行します。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル／ディレクトリ構成（src/kabusys 以下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度ユーティリティ
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続層
    - system_monitor.py
    - trade_monitor.py       — （省略されたが存在想定）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信ロジック想定）
  - execution/               — Execution 関連（order_manager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（実際のリポジトリにはさらに細かいモジュール・テスト等が含まれる想定です）

---

## 主要ファイル説明（クイックリファレンス）

- src/kabusys/config.py
  - .env の自動読み込みロジック（プロジェクトルート検出）、Settings クラスで各設定を集約。
- src/kabusys/config_setup.py
  - 対話式で .env を生成／更新するウィザード。
- src/kabusys/validate_config.py
  - 起動前に環境変数・config/*.yaml の存在と整合性をチェックする CLI。
- src/kabusys/run_execution.py
  - ExecutionEngine を初期化して実行。paper_trading 環境では専用 DB と MockBroker を使用。
- src/kabusys/run_monitoring.py
  - SystemMonitor を定期実行して system_status / risk_logs / trade_logs 等に記録。MONITOR_POLL_INTERVAL で間隔を制御。
- src/kabusys/ai/news_nlp.py / regime_detector.py
  - OpenAI を使ったニューススコアリング・市場レジーム判定。API キー（OPENAI_API_KEY）が必要。

---

## トラブルシューティング（よくある問題）

- `.env` の必須値が足りない → `python -m kabusys.validate_config` を実行して確認、`python -m kabusys.config_setup` で補完
- ログファイルが作成されない → `LOG_DIR` のパーミッションを確認（logging_setup はディレクトリ作成に失敗すると stdout のみで継続）
- OpenAI 呼び出しで失敗する／キーがない → `OPENAI_API_KEY` を設定、または AI 機能を無効化して起動
- Execution が起動しない（すぐ終了する）→ `data/stop_requested.flag` の存在を確認。存在する場合は削除するか原因を確認
- パーミッションによりプロセス優先度設定に失敗 → 権限不足のため警告が出ますが動作自体は継続します

---

## 最後に

この README はコードベース（主要モジュール）から抽出した情報に基づいて作成しています。実運用前には `.env` の安全な管理、テスト環境での十分な検証、OpenAI キーや実ブローカへの接続情報の取り扱いにご注意ください。

不明点や追加で README に加えたい情報（例: 完全な依存ファイル、サンプル .env.example、起動用 systemd / supervisor サービス定義 等）があれば教えてください。README を拡張します。