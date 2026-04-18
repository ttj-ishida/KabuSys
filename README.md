# KabuSys

日本株向け自動売買システムの Python パッケージ。  
このリポジトリはトレード実行、監視、リサーチ、ポートフォリオ構築、ニュース NLP（LLM を使ったセンチメント評価）等のコンポーネントを含みます。

以下はこのコードベースの README です — セットアップ、主要機能、実行方法、ディレクトリ構成などをまとめています。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュラーな自動売買フレームワークです。

- 日次の因子計算やリサーチ（DuckDB を用いた価格・財務データ処理）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング）
- ExecutionEngine による発注制御（実口座 / ペーパートレード切替）
- 監視（System / Trade / Risk モニタ）と Kill Switch（異常時の安全停止）
- ニュース NLP（OpenAI を用いた銘柄別センチメント）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）

設計方針：外部副作用（実口座 API など）は分離し、テストしやすい純粋関数と明確な I/O 層を志向しています。

---

## 主な機能一覧

- Execution
  - 実際のブローカークライアントと Mock クライアントの切替（`KABUSYS_ENV=paper_trading`）
  - 発注管理 / オーダーリポジトリ / リコンシリエーション / リスク管理
- Monitoring
  - システムリソース監視（CPU/メモリ/ディスク）、プロセス生存確認、データ鮮度チェック
  - トレードログ監視（滞留注文・異常約定の検出）
  - リスク監視（ドローダウン／ポジション上限）、kill.flag による安全停止
  - 監視結果の永続化（SQLite）
- Research
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- Portfolio
  - 候補選定、等配分・スコア加重、リスク制限（セクターキャップ、レジーム乗数）、ポジション数算出（単元丸め）
- AI（LLM）
  - ニュースを銘柄別に集約して OpenAI に送信しセンチメントを ai_scores に保存
  - マクロ記事 + ETF MA による市場レジーム判定（bull/neutral/bear）
- Tools
  - Paper Trading の検証レポート生成スクリプト

---

## 必要条件 / 依存パッケージ

- Python 3.9+
- パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証を行う場合）
- 開発環境では pip 等でインストールしてください（requirements.txt があればそちらを使用）。

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / コピーする

2. 仮想環境作成（推奨）
```
python -m venv .venv
source .venv/bin/activate   # POSIX
.venv\Scripts\activate      # Windows
pip install -U pip
```

3. 依存パッケージをインストール
```
pip install duckdb psutil openai PyYAML
```

4. 環境変数設定（.env）
- 対話式ウィザードで .env を生成できます:
```
python -m kabusys.config_setup
```
- もしくはプロジェクトルートに `.env` を作成してください。主要な環境変数の例:
```
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here

# 任意 / デフォルトあり
KABUSYS_ENV=development            # development | paper_trading | live
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxx            # ニュース NLP / レジーム判定を使う場合
LINE_CHANNEL_ACCESS_TOKEN=        # 本番アラートで使用する場合
LINE_USER_ID=
```

自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml により検出）から `.env` / `.env.local` を自動で読み込みます。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. ディレクトリ作成（初回）
```
mkdir -p data logs
```
SQLite / DuckDB ファイルは自動生成・初期化されます（必要に応じて parent ディレクトリを事前に作成してください）。

---

## 使い方 / 実行方法

※ モジュールはパッケージとして設計されています。以下は主なエントリポイント例です。

- 設定ウィザード（.env の対話生成）
```
python -m kabusys.config_setup
```

- 設定検証（.env と config/*.yaml のチェック）
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict   # 警告も失敗扱い
```

- 監視ループ起動（SystemMonitor ポーリング）
```
python -m kabusys.run_monitoring
```
- 説明:
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）。
  - 監視は常に本番の `SQLITE_PATH` を使用します（monitoring 用 DB）。
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します。

- ExecutionEngine 起動（発注エンジン）
```
python -m kabusys.run_execution
```
- 説明:
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用して `PAPER_TRADING_SQLITE_PATH` に記録します（本番 DB と分離）。
  - PID ファイル: `data/execution.pid`（Settings の `pid_file_path` で上書き可）。
  - 停止: `data/stop_requested.flag` を作成または監視プロセスで kill.flag を検出すると停止処理が行われます。

- Paper Trading 検証レポート
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パス指定:
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- OpenAI を使ったニューススコアリング（プログラムから呼ぶ例）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-xxx")
print("書き込み件数:", written)
```
- 注意:
  - `OPENAI_API_KEY` 環境変数を使う場合、`api_key` 引数は省略できます。
  - API 呼び出しはバックオフ / リトライ処理を含みますが、レート制限や API 料金に注意してください。

- 市場レジーム判定（プログラムから呼ぶ）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-xxx")
```

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / 設定:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 SQLite（paper_trading 時）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY: OpenAI を使う処理に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発用注意）

詳細は `src/kabusys/config.py` を参照してください。

---

## ログ / データ保存場所

- ログディレクトリ（デフォルト）: `logs/`（`LOG_DIR` 環境変数で変更可）
- 監視 DB（SQLite）: `data/monitoring.db`（`SQLITE_PATH` で変更可）
- DuckDB: `data/kabusys.duckdb`（`DUCKDB_PATH` で変更可）
- Paper trading DB: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH`）
- Kill/stop フラグ:
  - 停止フラグファイル: `data/stop_requested.flag`（run_* スクリプトが監視）
  - Kill Switch フラグ: `data/kill.flag`（KillSwitch が作成）

---

## トラブルシュート / 運用メモ

- ログディレクトリ作成失敗時はコンソール出力のみになります。`logs/` を作成して書き込み権限を確認してください。
- `set_process_priority("high")` は管理者権限を必要とする場合があります。失敗しても警告を出してスキップされます。
- OpenAI を利用する処理は API キー・課金・レート制限に注意してください。モデルとパラメータはコード内の定数で調整可能です。
- SQLite / DuckDB の初期化はコード側で行われます（テーブル作成、マイグレーション）。DB ファイルは適切にバックアップしてください。
- 本番運用時は `KABUSYS_ENV=live` に設定する前に `python -m kabusys.validate_config` で設定を確認してください。

---

## 主要ファイル / ディレクトリ構成

（`src/kabusys` 以下の主なファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパー取引検証レポート
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — monitoring 用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py      — （トレード監視、ファイルにあり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py      — （通知管理）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py    — Momentum / Value / Volatility 等
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA + LLM）
  - data/                   — データファイル（DB / flag / pid など）を置く場所（プロジェクトルートに `data/`）

---

## 開発 / テストのヒント

- 多くのモジュールは DB 接続（sqlite3 / duckdb）を受け取り純粋関数的に動作するため、ユニットテストが書きやすくなっています。mock / temporary DB を使ってテストを作成してください。
- OpenAI 呼び出しは `_call_openai_api` を patch することでテスト可能です（コード内でその旨がコメントされています）。
- 設定検証・ウィザードを活用して `.env` を整備してから起動してください。

---

必要に応じて README に追記します（例えば CI/CD、Docker、systemd ユニットファイルの例、より詳細な API ドキュメントなど）。追加したい項目があれば教えてください。