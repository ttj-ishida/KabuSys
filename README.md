# KabuSys

日本株自動売買システムのコアライブラリ群および起動スクリプト群です。  
このリポジトリには、実運用向けの ExecutionEngine / Monitoring / Research / AI 支援モジュールなどが含まれます。

---

## 概要

主な設計方針・特徴:

- モジュール分割（execution / monitoring / research / ai / portfolio / utils）
- 環境変数 / .env による設定管理（対話式ウィザード・検証ツールあり）
- 実運用（live）とペーパートレード（paper_trading）を明確に分離
- DuckDB（分析用） と SQLite（監視・発注履歴）を併用
- OpenAI を用いたニュース NLP / レジーム判定機能（オプション）

---

## 機能一覧

- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて実ブローカ or MockBroker を切替
  - Paper trading は専用 DB に記録（data/paper_trading.db）
  - PID ファイル管理 / stop フラグ監視
- Monitoring ポーリング（run_monitoring.py / monitoring package）
  - システム状態、注文ログ、リスク監視（ドローダウン・ポジション上限等）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み、Execution に停止信号を送る）
- 設定ウィザード（config_setup.py）
  - 対話式で .env を生成・更新
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml を起動前にチェック
- Research モジュール（research）
  - ファクター計算（momentum, volatility, value など）
  - 将来リターン / IC 計算など
- Portfolio モジュール（portfolio）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限
- AI モジュール（ai）
  - OpenAI を用いたニュースセンチメント（news_nlp）
  - マクロ + ETF 指標を合成したレジーム判定（regime_detector）
- ツール（tools）
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

---

## 前提条件 / 依存

- Python 3.10+
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config yaml の内容検証を行う場合)
- SQLite（標準ライブラリに同梱）
- （任意）ログは `logs/` に出力されます（ディレクトリは自動作成）

インストール例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成・有効化
3. 必要なパッケージをインストール（上記参照）
4. 環境変数を設定（.env を作成）
   - 対話式ウィザード推奨:
     ```
     python -m kabusys.config_setup
     ```
   - ウィザードで作成した .env を保存後、検証を推奨:
     ```
     python -m kabusys.validate_config
     ```
5. データディレクトリの作成（必要に応じて）
   - デフォルトの SQLite / DuckDB は `data/` 配下に置かれます
   - ログは `logs/` 配下に出力されます（存在しない場合は自動で作成を試みます）

---

## 設定 (.env) — 主な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

一般的な（任意 / デフォルトあり）:
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring)（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の約定挙動: `instant` | `partial` | `never` | `reject`（デフォルト: instant）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（開発用。1/0）

例（.env の一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（主要コマンド）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も失敗扱い
  ```

- Execution（エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録します。
  - 起動時に `data/stop_requested.flag` が存在する場合は起動を行いません。
  - 実行中は `data/execution.pid`（PIDファイル）を使用します。

- Monitoring 起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトポーリング間隔: 60 秒
  - `MONITOR_POLL_INTERVAL` 環境変数で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 停止: `data/stop_requested.flag` ファイルを作成するとループを抜けます
  - 監視は常に本番用 sqlite_path を使用（環境に依らず）

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で DB パスを指定できます。

---

## 停止 / Kill Switch / フラグファイル

- stop_requested.flag
  - `run_monitoring` / `run_execution` は `data/stop_requested.flag` の存在をチェックしてループを終了します。
  - 手動で停止させたい場合はこのフラグファイルを作成してください。

- kill.flag
  - KillSwitch（Monitoring 内の判定）により `data/kill.flag` が書き込まれると、ExecutionEngine は実取引を停止するためのシグナルとして利用します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされます（本番では 0 推奨）。

---

## ロギング

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` によってログを統一管理します。
- 出力先:
  - コンソール（stdout）
  - 日次ローテートされたファイル: `<LOG_DIR>/<app_name>.log`（デフォルト: logs/<app_name>.log）
- ログレベルは `.env` の `LOG_LEVEL`、または `setup_logging(level=...)` で指定可能。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要なファイル/ディレクトリ構成の概観:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（注）上記は主要ファイルの抜粋です。実際の全ファイルはパッケージ内をご確認ください。

---

## 注意事項 / 運用上のヒント

- 本番運用時 (KABUSYS_ENV=live) は設定を慎重に確認してください。validate_config は live 時に追加の警告を出します。
- .env は機密情報を含むため、決してリポジトリにコミットしないでください（config_setup でもその旨が出力されます）。
- OpenAI を利用する機能（ニューススコア・レジーム判定）は API コストとレイテンシを伴います。API キーとレート制限に注意してください。
- プロセス優先度・CPU affinity の設定は `psutil` を介して行われますが、権限不足で設定できない場合があります（警告ログが出ます）。
- DuckDB / SQLite のファイルパスは環境変数で上書き可能です。バックアップやアクセス権に注意してください。

---

## 参考コマンドまとめ

- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし特定のモジュール（例: ExecutionEngine の詳細、TradeMonitor の使い方、AI モジュールのテスト方法など）について README に追加したい情報があれば教えてください。必要に応じてコマンド例や設定例を追記します。