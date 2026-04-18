# KabuSys

KabuSys は日本株の自動売買・リサーチ・運用監視を目的とした小規模なフレームワークです。本リポジトリには実行エンジン、監視・アラート、ポートフォリオ構築・ポジションサイズ計算、ファクター計算、News NLP（OpenAI 連携）などのコンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下の通りです。

- 日次マーケットデータを用いたファクター計算・シグナル生成（research）
- ポートフォリオ構築、ポジションサイズ計算（portfolio）
- 発注系エンジン（ExecutionEngine） — 実口座 / ペーパートレード切替対応
- 監視コンポーネント（System / Trade / Risk Monitoring）と Kill Switch（危険時に発注エンジン停止）
- ニュースの NLP スコアリング（OpenAI を利用したセンチメント評価）
- 各種ユーティリティ（ログ設定、プロセス優先度、設定管理等）
- 検証ツール（Paper Trading 検証レポート生成 等）

設計方針として、外部 API 呼び出し（OpenAI やブローカ API）は明示的に管理され、ペーパートレード時は本番 DB と分離されるようになっています。

---

## 機能一覧

- ExecutionEngine の起動・発注フロー（実際の BrokerClient / MockBrokerClient を切替可能）
- Monitoring（system / trade / risk）による定期チェックとログ保管（SQLite）
- Kill Switch：ドローダウンやポジション上限により発注エンジンを停止させる仕組み
- Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- ニュース NLP（OpenAI）による銘柄別センチメント計算と ai_scores への書き込み
- 市場レジーム判定（ETF とマクロニュースの合成により bull/neutral/bear を判定）
- ポートフォリオ構築: 候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- 環境設定ウィザード（.env 作成補助）と設定検証 CLI
- 統一的なログ設定（stdout + 日次ローテートファイル）

---

## 前提条件

- Python 3.10 以上（PEP 604 の型注釈やモダンな構文を使用）
- SQLite（Python 標準ライブラリ）
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（YAML 検証を行う場合）
- ネットワークアクセス（OpenAI / ブローカ API 等を使う場合）

必要パッケージはプロジェクトの requirements.txt がある場合はそれを使ってください。無い場合は少なくとも上記を pip で入れてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動します。

2. 仮想環境を作成・有効化して依存関係をインストールします（上記参照）。

3. .env (環境変数) を作成します。
   - 対話式ウィザードを利用する:
     ```
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートに `.env` を生成 / 更新できます。
   - もしくは `.env.example` を参照して手動で作成してください（リポジトリに例ファイルがある場合）。

4. 設定検証を実行して問題を洗い出します:
   ```
   python -m kabusys.validate_config
   # 警告を FAIL としたい場合:
   python -m kabusys.validate_config --strict
   ```

5. DB ディレクトリ（デフォルトは `data/`）やログディレクトリ（デフォルトは `logs/`）が自動的に作成されますが、パーミッション等を確認してください。

6. OpenAI を使う場合は環境変数 `OPENAI_API_KEY` を設定します（`news_nlp` / `regime_detector` が利用）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: 実行モード（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、MockBrokerClient を使用し DB は `data/paper_trading.db` に分離されます
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（ニュース NLP / レジーム判定で必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか。0/1）

注意: 自動 .env 読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト目的など）。

---

## 使い方

### 1) 監視ループを起動（Monitoring）
run_monitoring は SystemMonitor（および MonitoringDB）を定期ポーリングします。

```
# デフォルトのポーリング間隔 60 秒
python -m kabusys.run_monitoring

# 環境変数でポーリング間隔を変更
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します（環境に依存しません）。
- 停止: プロジェクトルートの `data/stop_requested.flag` ファイルが存在するとループを終了します。

### 2) 実行エンジンを起動（Execution）
ExecutionEngine を起動します。`KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、本番 DB と分離されます。

```
python -m kabusys.run_execution

# paper_trading モードで起動
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

- 起動時に `data/execution.pid` が作られます（設定によりパス変更可能）。
- 停止は `data/stop_requested.flag` を作成することで実行中のエンジンに停止信号が送られます。
- Kill Switch の `data/kill.flag` が存在すると起動時に自動停止するロジックや挙動に注意してください（設定次第でクリアを禁止／許容）。

### 3) Paper Trading 検証レポート
tools に含まれるスクリプトでペーパートレード DB から簡単なレポートを出力できます。

```
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB を明示的に指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

### 4) News NLP / レジーム判定（プログラムから呼び出す）
OpenAI キーを設定して DuckDB 接続を渡すことで実行できます（ライブラリ関数）。

例（概念）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
r = score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
```

- API 呼び出しはリトライ・サニティチェックが組み込まれています。
- 結果は DuckDB 内の `ai_scores` / `market_regime` テーブルへ書き込まれます。

---

## 停止・Kill フラグについて

- `data/stop_requested.flag`：run_monitoring / run_execution の外部停止トリガ。存在するとループ・スレッド停止フローへ移行します。
- `data/kill.flag`：Kill Switch によって作成されるファイル。ExecutionEngine に停止を指示するために使用されます。
- `KILL_FLAG_CLEAR_ON_START` を `1` に設定すると起動時に kill.flag が自動クリアされます（本番では `0` 推奨）。

---

## ログ

- ロギングは stdout（コンソール）と日次ローテートのファイル出力（デフォルト: logs/<app_name>.log）を行います。
- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name=..., log_dir=..., level=...)` を通じて統一的に行われます。
- デフォルトログレベルは `LOG_LEVEL` 環境変数で制御します。

---

## ディレクトリ構成（主要ファイル・概観）

以下はコードベースに含まれる主要なファイル / モジュールの例です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続層（テーブル初期化 + CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — (省略されたが取引ログ監視)
    - risk_monitor.py        — ドローダウン／ポジション数監視
    - kill_switch.py         — kill.flag 制御
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       — (アラート送信ロジック想定)
  - execution/
    - execution_engine.py    — ExecutionEngine（本体）
    - broker_factory.py      — BrokerClient のファクトリ（実/Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py     — Momentum/Value/Volatility ファクター計算（DuckDB）
    - feature_exploration.py — IC/統計サマリ等
  - portfolio/
    - portfolio_builder.py   — 候補選定、等重/スコア重み
    - position_sizing.py     — 発注株数計算、aggregate cap スケールダウン等
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロ NLP）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

（リポジトリ全体のファイル・詳細は実際の tree を参照してください）

---

## 開発メモ / 注意点

- DuckDB 接続を渡して分析系関数（research / ai）は動作します。テーブル名やスキーマは実行前に用意してください（例: prices_daily, raw_financials, raw_news 等）。
- `Settings` クラスは .env と環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テスト時に自動ロードを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI を使う機能は外部 API 呼び出し／APIキーを必要とします。API 呼び出し失敗時はフェイルセーフで継続する実装が多く取り入れられていますが、結果の妥当性は運用者が監視してください。
- 本番モード（KABUSYS_ENV=live）では十分に設定を検証し、LINE 等の通知設定を行ってください（validate_config は Live 向けのガードを含む）。

---

## よく使うコマンド一覧

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```

- 実行エンジン起動
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの主要な使い方・構成をまとめたものです。実運用に当たっては `.env` の内容、DB のバックアップ、ログローテーションの監視、OpenAI など外部 API の利用制限（レート／課金）に注意してください。さらに細かい実装や API 仕様は各モジュール（特に execution、monitoring、ai、research）の docstring を参照してください。