# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株向けの自動売買／検証ツール群を収めた Python パッケージです。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）や AI を使ったニュース評価まで含むモジュール群を提供します。

重要：.env（機密情報）をリポジトリにコミットしないでください。

---

## プロジェクト概要

- 自動売買のコア機能（発注、オーダー管理、リスク管理、約定追跡）
- ポートフォリオ構築（候補選定、重み付け、数量計算、セクター制限）
- ファクター計算・リサーチ（モメンタム、バリュー、ボラティリティ、IC 計算等）
- AI を用いたニュースセンチメント評価（OpenAI API 経由）
- 監視（System / Trade / Risk の監視、Kill Switch、アラート管理）
- ペーパートレード用の分離された DB サポートと検証レポート生成ツール

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は環境に関係なく本番（SQLITE_PATH）を参照する設計
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- AI モジュール
  - ニュースセンチメント: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime
- ポートフォリオ関連ユーティリティ（選定、重み付け、サイズ決定、セクター制限）
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
  - monitoring DB の永続化（SQLite）

---

## 依存関係（主なもの）

少なくとも次をインストールしてください（環境により追加が必要）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能使用時)
- PyYAML（設定検証で YAML の内容検証を行う場合に必要）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（requirements.txt がない場合は上記を参考に必要なパッケージを追加してください）

---

## セットアップ手順

1. リポジトリをクローンし Python 仮想環境を用意：
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

2. 対話式で .env を作成（推奨）：
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは J-Quants / kabuAPI トークンや DB パス等を対話式に生成します。
   - 生成された .env を絶対に Git に含めないでください。

3. 設定を検証：
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告も失敗扱いになります。

4. データディレクトリを作成：
   デフォルトの DB パスは `data/` 配下です。存在しない場合は作成してください。
   ```
   mkdir -p data
   ```

5. （AI 機能を使う場合）OpenAI API キーを環境変数に設定：
   ```
   export OPENAI_API_KEY="sk-...."
   ```

---

## 使い方（主要コマンド）

- 実行エンジン（発注部）を起動：
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV により挙動が変わります:
    - development: 発注無し（開発用）
    - paper_trading: MockBroker を使用し paper_trading_db に記録
    - live: 実際のブローカーへ発注（kabuステーション API を使用）

- 監視ループを起動：
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は常に Settings.sqlite_path（通常 data/monitoring.db）を使用します。

- 設定ウィザード（.env 作成）：
  ```
  python -m kabusys.config_setup
  ```

- 設定検証：
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート作成：
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスはオプション `--db PATH` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 関連（プログラムから呼び出す関数）
  - ニュース評価:
    ```python
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, datetime.date(2026, 4, 1), api_key='your_key')
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    # duckdb 接続と target_date を渡す
    ```

- 注意: 多くのモジュールは DB 接続（duckdb / sqlite）や環境変数に依存します。使用前に .env を正しく設定してください。

---

## 環境変数（主なもの）

必須（最低限設定が必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な任意/デフォルト:
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- OPENAI_API_KEY (AI 機能利用時)
- LOG_LEVEL (DEBUG / INFO / ...)

自動 .env ロード:
- プロジェクトルートにある `.env` / `.env.local` は自動で読み込まれます（OS 環境変数を上書きしないよう配慮）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

その他（監視関連）:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH / PID_FILE_PATH / KILL_FLAG_CLEAR_ON_START など（Settings クラス参照）

---

## 停止・Kill Switch の仕組み

- 監視（Monitoring）と実行（Execution）はファイルフラグで制御します:
  - data/stop_requested.flag（run_monitoring / run_execution の停止検知に使用）
  - data/kill.flag（KillSwitch が作成し、ExecutionEngine に停止シグナルを送る）
  - data/execution.pid（ExecutionEngine が PID を書き込む）
- KillSwitch はリスク（ドローダウン超過、ポジション上限超過等）を検出すると `kill.flag` を生成します。ExecutionEngine はこれを参照して安全停止します。
- 設定 `KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは危険です（自動で Kill Flag をクリアしてしまいます）。本番は 0 推奨。

---

## トラブルシューティング（よくある問題）

- OpenAI API キー未設定:
  - AI 機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。キー未設定で呼ぶと ValueError を送出します。
- PyYAML 未インストール:
  - validate_config は YAML のパース検証をスキップし、警告を出します。検証を行うには PyYAML をインストールしてください。
- DB パスの親ディレクトリがない:
  - validate_config は親ディレクトリが存在しない場合に警告を出します。`data/` を作成してください。
- プロセス優先度の設定失敗:
  - `psutil` による優先度変更は権限が必要な場合があります。失敗すると警告を出してスキップします。
- DuckDB / SQLite のバージョン依存:
  - 一部の executemany 空リスト制約など、DuckDB のバージョンに依存する挙動があります。問題が出たら DuckDB のバージョンを確認してください。

---

## ディレクトリ構成（一部抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI）
    - regime_detector.py    — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py      — （アラート送信ロジック：未表示）
  - execution/               — 発注 / オーダー管理系（別ファイル群）
  - tools/
    - paper_verification_report.py

（実際のファイル構成はリポジトリ内を参照してください）

---

## 開発メモ / 設計上の注意

- Paper Trading は本番 DB と物理的に分離されるように設計されています（PAPER_TRADING_SQLITE_PATH）。
- 監視（monitoring）は環境に関係なく Settings.sqlite_path（通常の監視 DB）を使用します。監視側と実行側で DB を分離したい場合は設定を調整してください。
- AI 呼び出しはリトライとフォールバックを備え、失敗時は安全に続行するように設計されています（部分書き込みや 0.0 フォールバック等）。
- ルックアヘッドバイアス防止のため、モジュールは date.today() に依存しない設計を心掛けています（ターゲット日付を引数で与える方式）。

---

必要であれば、各モジュール（ExecutionEngine、OrderRepository、AlertManager 等）の使い方や API サンプル、単体テストの書き方等も追記できます。どの情報を優先して追加しますか？