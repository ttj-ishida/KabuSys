# KabuSys

日本株向け自動売買システムのモジュール群です。ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ（DuckDB を使ったファクター計算）、およびニュース NLP を使ったセンチメント評価などの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のコンポーネントで構成される、実運用を想定した自動売買基盤のプロトタイプ実装です。

- ExecutionEngine（発注エンジン）: ブローカークライアントを通じて注文を管理・送信し、リスク制御を行います。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、発注ログを paper_trading 用 DB に分離します。
- Monitoring（監視）: システム稼働状況、データ鮮度、注文の滞留・約定異常、ドローダウンなどを定期チェックし、Kill Switch（フラグファイル）でエンジンを停止できます。
- Portfolio（ポートフォリオ構築）: 候補選定、重み付け、ポジションサイズ計算（等金額・スコア加重・リスクベース）、セクター上限・レジーム調整。
- Research（リサーチ）: DuckDB 上の時系列データからファクター（モメンタム、ボラティリティ、バリュー等）や将来リターン、IC 等を計算。
- AI（ニュース NLP / レジーム判定）: OpenAI（gpt-4o-mini 等）によるニュースのセンチメント評価、マクロセンチメントと ETF MA を使った市場レジーム判定。
- Utilities: ロギング設定、プロセス優先度 / CPU affinity 設定、設定ウィザード / バリデータなど。

---

## 主な機能一覧

- 設定管理（.env）の対話式ウィザード（kabusys.config_setup）
- 起動前の設定検証ツール（kabusys.validate_config）
- ExecutionEngine（本番 / ペーパー取引モード対応）
- MonitoringEngine（system/trade/risk の監視とアラート / Kill Switch）
- ポートフォリオ構築ライブラリ（候補選定、重み計算、ポジション決定）
- リサーチツール（DuckDB を使ったファクター計算・IC 等）
- AI ベースのニュースセンチメント評価（OpenAI API 経由）
- ペーパートレード検証レポート生成ツール
- 統一的ログ設定（コンソール + 日次ローテートファイル）
- OS 間でのプロセス優先度 / CPU affinity 操作（psutil 利用）

---

## 必要要件（概略）

- Python 3.9+
- 推奨パッケージ（機能に応じて）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証のため任意）
- （実運用）kabuステーション等の API、J-Quants API トークン 等

requirements.txt はプロジェクトに同梱されている想定です。まずは仮想環境を作成して依存関係をインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

※ 実際の requirements.txt が無い場合は上記の主要ライブラリを個別にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリを移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成と依存インストール（上記を参照）

3. .env の作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードが .env を作成します。機密値（トークン等）はマスク表示されます。
   - 重要: .env は決して Git にコミットしないでください。

4. 設定検証（起動前に必ず確認）
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。

5. DB ディレクトリの確認
   - デフォルトの DB パス:
     - DuckDB: `data/kabusys.duckdb`
     - SQLite(監視): `data/monitoring.db`
     - Paper trading SQLite: `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時）
   - 必要に応じて `.env` の `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` を調整

6. OpenAI を使う場合
   - 環境変数 `OPENAI_API_KEY` を設定するか、該当関数に api_key を渡してください。

---

## 使い方（起動例）

- ExecutionEngine（発注エンジン）起動:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、紙の DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - 実行中に `data/stop_requested.flag` を作成するとエンジンを停止します。
  - 実行時は `data/execution.pid` に PID を出力します。

- Monitoring（監視）起動:
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使います（環境にかかわらず）。
  - 停止は `data/stop_requested.flag` を作成して行います。

- 設定検証ツール:
  ```
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は `PAPER_TRADING_SQLITE_PATH` 環境変数、または `--db` オプションで指定できます。

- AI スコアリング（プログラムから呼び出す）
  - OpenAI API キーを設定し、DuckDB 接続を渡して `kabusys.ai.score_news(...)` や `kabusys.ai.regime_detector.score_regime(...)` を呼び出します。

---

## 主要な環境変数

必須（起動前に設定が必要）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション / 推奨
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI を使うときに必要
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring で参照）
- PAPER_FILL_MODE: ペーパートレード時の約定振る舞い（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

詳細は `kabusys.config.Settings` を参照してください。

---

## ログと永続化

- ログ:
  - デフォルトで stdout と `logs/<app_name>.log`（日次ローテーション・30日保持）に出力されます。
  - ログレベルは `LOG_LEVEL` または `setup_logging` の引数で指定します。

- DB:
  - DuckDB は分析用の大容量データ保存に使用（prices_daily / raw_financials など）。
  - SQLite（monitoring.db / paper_trading.db）は監視ログ・発注ログなどの永続化に使用。
  - `monitoring_db.init_monitoring_db()` はテーブル作成／簡易マイグレーション（列追加）を行います。

---

## Kill Switch / 停止フラグ

- `KillSwitch` は監視結果から条件が満たされると `data/kill.flag` を書き込み、ExecutionEngine 停止を促します。
- 監視／実行停止のための簡易フラグ:
  - 起動スクリプトは `data/stop_requested.flag` の存在を検出して起動・ループを終了します。
  - ExecutionEngine は `data/execution.pid` を PID 保持に使用します。
- 本番運用では `KILL_FLAG_CLEAR_ON_START` の設定に注意してください（本番では 0 を推奨）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要モジュールは `src/kabusys` 下に配置されています。代表的な構成:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時生成（DB・フラグ類）

（実際のファイル一覧はリポジトリの内容に従ってください。）

---

## 重要な注意事項 / 運用上のポイント

- KABUSYS_ENV に応じて発注先や DB の扱いが変わります。特に `live` は実際に発注するため、設定の取り扱い・API パスワードの管理を厳重に行ってください。
- .env は秘匿情報を含むため決してリポジトリにコミットしないでください。
- OpenAI API 呼び出しはレート制限や費用が発生します。API キーの管理、リトライポリシーの挙動を理解した上で運用してください。
- `monitoring` は本番 sqlite_path を使うため、モニタープロセスが別環境の DB を上書きしないよう注意してください。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソール出力のみになります。

---

## 開発・拡張のヒント

- DuckDB によるファクター計算は SQL を多用して高速に動作します。新しいファクターを追加する場合は `kabusys.research` 配下に実装してください。
- AI モジュールは外部 API を扱うため、テスト時は `_call_openai_api` をモックすることを想定しています（既存実装でもコメントが記載されています）。
- position sizing や risk adjustment は純粋関数で実装されておりユニットテストが書きやすくなっています。

---

この README はコードベース（src/kabusys/*）の主要機能と利用方法をまとめたものです。詳細な API 仕様や実装方針は各モジュールの docstring を参照してください。必要であれば README を拡張してデプロイ手順や CI/CD、テスト手順を追加できます。