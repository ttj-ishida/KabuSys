# KabuSys

日本株向け自動売買フレームワーク（ライブラリ/実行スクリプト群）。

このリポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、注文実行（本番／ペーパートレード）、監視・アラート、及びニュース系の NLP 処理を含むコンポーネント群で構成されています。

---

## プロジェクト概要

- 戦略（research）やポートフォリオ構築（portfolio）用の純粋関数群を提供。
- ExecutionEngine による注文実行ロジック（kabuステーション / MockBroker を利用）。
- Monitoring サブシステムはシステム状態や注文状態を定期的にチェックし、Kill Switch（フラグファイル）やアラートを発動。
- AI モジュールは OpenAI を用いたニュースセンチメント評価や市場レジーム判定をサポート（任意）。
- DB: DuckDB（分析用）と SQLite（監視・発注ログ等）を使用。Paper Trading 用に分離された SQLite DB を利用可能。

---

## 主な機能一覧

- 設定管理:
  - .env の自動ロード（環境変数優先）。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 対話式ウィザードで .env を生成/更新（`kabusys.config_setup`）。
  - 起動前検証 CLI（`kabusys.validate_config`）。

- 実行スクリプト:
  - `run_execution.py`：ExecutionEngine 起動スクリプト。`KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、paper_trading DB に書き込む。
  - `run_monitoring.py`：SystemMonitor のポーリングループ。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。

- 監視:
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度をチェック。
  - TradeMonitor / RiskMonitor: 注文の滞留・約定異常、ドローダウン・ポジション上限を監視。
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み、ExecutionEngine 停止を指示。
  - MonitoringDB: SQLite を用いた永続化（system_status, trade_logs, positions, risk_logs, dashboard 等）。

- ポートフォリオ構築:
  - 候補選定、重み付け（等金額/スコア加重）、セクター集中制限、ポジションサイズ計算（単元丸め・リスクベース等）。

- リサーチ:
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）。
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ。

- AI（任意）:
  - ニュース NLP（OpenAI）による銘柄別センチメントスコア算出。
  - 市場レジーム判定（MA200 とマクロニュースの合成）。

- ツール:
  - ペーパートレード検証レポート生成（`kabusys.tools.paper_verification_report`）。

---

## 前提 / 必要環境

- Python 3.10 以上（Union 型 `|` を利用しているため）。
- 推奨インストールパッケージ（機能に応じて必要）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - pyyaml（`validate_config` の YAML 検証を有効にする場合）
- SQLite は標準ライブラリで利用可能。

例（最小）:
```bash
python -m pip install duckdb psutil
```

AI 機能を使う場合:
```bash
python -m pip install openai
```

開発時に YAML 検証を有効にするなら:
```bash
python -m pip install pyyaml
```

（requirements.txt は本リポジトリに含まれていない想定のため、用途に応じて必要パッケージをインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール（上記参照）
4. .env の作成:
   - 対話式ウィザードを推奨:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは `./.env` を手動作成（例は下記）。

5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も厳密に扱いたい場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの作成（必要に応じて）:
   - デフォルト DB / ログ保存先:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
     - ログ: logs/
   多くはコード側で自動作成を試みますが、権限等で失敗する場合は手動作成してください。

.env の最小例（テンプレート）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

注意: `.env` をリポジトリにコミットしないでください（機密情報を含みます）。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV で切替）
  ```bash
  # ペーパートレード
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution

  # 本番 / ローカル開発
  export KABUSYS_ENV=live
  python -m kabusys.run_execution
  ```

  補足:
  - paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録される（本番 DB と分離）。
  - 実行中に `data/stop_requested.flag` を作成すると起動中のプロセスがループを抜けて終了します。
  - 実行時にプロセス優先度を "high" に設定しようとします（権限によっては失敗することがあります）。

- Monitoring を起動
  ```bash
  # ポーリング開始（デフォルト 60 秒）
  python -m kabusys.run_monitoring

  # ポーリング間隔を変更する場合（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  補足:
  - Monitoring は環境にかかわらず本番用の `Settings.sqlite_path` を使用して監視テーブルを初期化します。
  - 停止フラグ（data/stop_requested.flag）を検出するとループを終了します。

- .env ウィザード（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（SQLite DB を指定可能）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI（OpenAI）機能の利用例（ライブラリ呼び出し）
  - `kabusys.ai.score_news(conn, target_date, api_key=None)` を呼び出すことで ai_scores テーブルへ書き込みます。
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` でレジーム判定を書き込みます。
  - これらは OpenAI の API キー（環境変数 `OPENAI_API_KEY`）が必要です。

---

## .flag / PID ファイルの意味

- data/stop_requested.flag
  - 外部からの「プロセスを停止してほしい」合図として利用。起動ループ内で検出すると安全に終了します。

- data/kill.flag
  - KillSwitch によって作成されるファイル。ExecutionEngine に対して「完全停止（本番停止）」を指示するために利用される設計です。
  - `Settings.kill_flag_clear_on_start` が `1` の場合、ExecutionEngine 起動時に自動クリアする挙動になります（本番では `0` 推奨）。

- data/execution.pid
  - ExecutionEngine の PID を書くためのファイル。Monitoring はこの PID を監視に使います（設定で変更可能）。

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理
  - config_setup.py         — .env ウィザード（CLI）
  - validate_config.py      — 起動前検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py           — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py    — 市場レジーム判定（AI 結合）
    - __init__.py

  - monitoring/
    - monitoring_db.py      — SQLite のスキーマ初期化 / 永続化 API
    - system_monitor.py     — システム/データ鮮度監視
    - trade_monitor.py      — （注）TradeMonitor 実装（ファイルにあり）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — Kill Switch（フラグ書込み）
    - monitoring_engine.py  — 各モニタを束ねるエンジン
    - alert_manager.py      — （ファイルにあり）
    - __init__.py

  - execution/
    - execution_engine.py   — 実際の注文セッション制御（Engine）
    - broker_factory.py     — Broker クライアント選択（Mock / 実ブローカ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - __init__.py

  - portfolio/
    - portfolio_builder.py  — 候補選定 / 重み付け
    - position_sizing.py    — 発注株数計算・上限制御
    - risk_adjustment.py    — セクターキャップ、レジーム乗数
    - __init__.py

  - research/
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン、IC、統計サマリ
    - __init__.py

  - monitoring/ (上記参照)
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
    - __init__.py

  - utils/
    - logging_setup.py      — ログ設定ユーティリティ（console + 日次回転）
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
    - __init__.py

- data/
  - (デフォルトで DB / フラグ / PID を置く場所)
- logs/
  - (ログファイルが daily ローテーションで保存される)

---

## ログ / ローテーション

- ログは `kabusys.utils.logging_setup.setup_logging` 経由で統一的に設定されます。
- デフォルトは `logs/<app_name>.log` に日次ローテーションで保存（最大 30 日保持）。
- 標準出力は stdout に出力されます（cron 等でリダイレクトしやすい設計）。

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を `0` に設定することを強く推奨します（誤って Kill Switch を自動クリアすると危険）。
- Monitoring は監視用の SQLite DB を初期化しますが、本番 DB と Execution の DB が分離されていることを確認してください（paper_trading の場合は paper_sqlite_path を使用）。
- OpenAI を利用するモジュールは API 利用料が発生します。API キーは環境変数 `OPENAI_API_KEY` に設定してください。
- `validate_config` を CI／デプロイ前チェックに組み込むと安全です。

---

この README はリポジトリに含まれる主要なスクリプト・モジュールの概要と起動手順をまとめたものです。詳細な API 使用方法や内部仕様は各モジュールの docstring を参照してください。ご不明点があれば実行したいユースケース（例: ペーパートレードでの動作確認手順）を教えてください。追加で具体的な手順やサンプルを提示します。