# KabuSys

日本株自動売買システム（KabuSys）のコードベース用 README。

バージョン: 0.1.0

このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築・ポジションサイズ計算、リサーチ（ファクター計算）、およびニュース NLP / レジーム判定などの機能群を含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコアライブラリ群です。主な目的は以下です。

- 日次・リアルタイムでのシグナル生成から注文発行（ExecutionEngine）
- 実行状況／システム状態の監視（Monitoring）
- ポートフォリオ構築・リスク制御（Portfolio）
- ファクター計算や将来リターン解析などの研究用モジュール（Research）
- ニュースを LLM でスコアリングして投資判断に活用（AI）
- ペーパートレード用の分離された DB と検証レポート（Tools）

設計上、可能な限り本番 DB とペーパートレード DB を分離し、外部 API 呼び出しは明示的に管理されています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（実行エンジン）：ブローカークライアント経由で注文を管理
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、専用 SQLite（`data/paper_trading.db`）に記録
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス・データ鮮度を監視
  - TradeMonitor：滞留注文、約定異常（価格偏差）を検出
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch：しきい値に達した際に `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記をまとめてポーリング、アラート通知を統合
- Portfolio
  - 候補選定（score / rank）、等金額・スコア加重配分
  - セクター集中抑制、レジームに応じた投下資金乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントを算出して ai_scores に格納
  - レジーム判定（MA200 乖離 + マクロニュースセンチメントの合成）
- Tools
  - Paper Trading の検証レポート生成（成功率、レイテンシ、稼働率など）

---

## 必要条件（依存）

最低限必要なライブラリ（抜粋）:

- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定ファイル検証を行う場合、任意）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
（実際の requirements.txt はリポジトリに合わせて用意してください）

---

## セットアップ手順

1. レポジトリをチェックアウトし、仮想環境を用意して依存パッケージをインストールします。

2. 環境変数（.env）の作成
   - 対話式ウィザードで .env を作成できます:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは J-Quants トークンや kabu API パスワード等を対話的に入力して `.env` に保存します。
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - オプション:
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパー取引用、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能使用時）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知）

   - 自動ロードを無効にする（テスト等）:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も失敗扱いになります。

4. データディレクトリ作成
   - デフォルトの DB ファイルは `data/` 以下に作成されます。必要に応じ `data/` ディレクトリを作ってください（起動時に自動作成される箇所もあります）。

---

## 使い方（起動例）

- ExecutionEngine を起動（本番 or ペーパーは KABUSYS_ENV に依存）
  ```
  # 例: ペーパートレードとして起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - ペーパートレード時は `PAPER_TRADING_SQLITE_PATH` に記録され、本番 DB と完全に分離されます。
  - 実行中プロセスは `data/execution.pid` に保存されます。
  - 停止要求: プロジェクトルートの `data/stop_requested.flag` を作成すると run_execution は検知して終了します。
  - KillSwitch により `data/kill.flag` が書かれると ExecutionEngine は停止対象になります（設定次第で自動クリア可能）。

- Monitoring を起動
  ```
  # ポーリング間隔を環境変数で上書き可能（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。
  - `run_monitoring` は Monitoring 用に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依存しない本番監視 DB を対象）。
  - 停止要求: `data/stop_requested.flag` を配置すると監視ループは終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定したい場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI / リサーチ関連は主にライブラリ API として提供されています（プログラムから呼び出して使用）。
  - 例: ニュース NLP スコア付けを呼ぶ（プログラム例）
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,10), api_key="sk-...")
    ```

---

## 主要環境変数（概要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 主要（デフォルト値あり）
  - KABUSYS_ENV: development | paper_trading | live（default: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0 | 1
  - PAPER_FILL_MODE: instant | partial | never | reject (paper trading 挙動)
  - OPENAI_API_KEY: OpenAI を利用する場合に必要

- 実行監視用
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）。1未満の無効値や不正値は 60 にフォールバック。

---

## ファイル / ディレクトリ構成

主要モジュールを抜粋して示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みロジック
  - config_setup.py          — .env を対話式に作成するウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト（CLI）
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト（CLI）
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 実行関連コンポーネント（Engine / OrderManager 等）※一部省略
  - monitoring/
    - monitoring_db.py       — SQLite 永続層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信ロジック；ファイル内に未表示の可能性あり）
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

- data/                    — 既定の DB / PID / フラグを置く場所（実行時に使用）
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## 運用上の注意 / トラブルシュート

- .env は機密情報を含むため Git にコミットしないでください（config_setup でも警告あり）。
- 本番運用（KABUSYS_ENV=live）では LINE トークン等のアラート設定を必ず確認してください（validate_config で追加チェックを行います）。
- `KILL_FLAG_CLEAR_ON_START=1` を本番で有効にすると kill.flag を自動でクリアしてしまい危険です（デフォルトは 0）。
- run_execution / run_monitoring は stop フラグ（data/stop_requested.flag）で安全に停止できます。kill.flag は KillSwitch が発動した際に書き込まれ ExecutionEngine の停止を誘導します。
- OpenAI を使う機能は API のレート制限・コストに注意してください。失敗時はフォールバック（0.0 等）する設計になっていますが、API キーの保守は運営責任です。
- DuckDB / SQLite のファイルパスは Settings で簡単に上書きできます。複数環境（開発 / 本番 / ペーパー）で DB を分けてください。

---

## 開発者向けメモ

- Settings クラス（config.py）は起動時にプロジェクトルートの `.env` を自動ロードします。テスト等でこれを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- MonitoringDB.init_monitoring_db は冪等にテーブル・インデックスを作成し、既存 DB に必要カラムがない場合の簡易マイグレーション（ALTER TABLE）を行います。
- process_priority.set_process_priority はプラットフォーム差を吸収して優先度設定を行いますが、権限不足等で失敗する場合は警告を出してスキップします。
- AI 関連の OpenAI 呼び出し部はリトライとバリデーション（JSON mode + 生レスポンスの復元処理）を組み込んで堅牢化しています。

---

必要であれば、より詳しいセットアップ手順（systemd ユニット例、Docker イメージ、CI 設定、ユニットテスト追加方法 など）も作成できます。どの部分を拡張したいか教えてください。