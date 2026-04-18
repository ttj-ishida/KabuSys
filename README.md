# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ内パッケージ README。  
ここではプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買および研究（ファクター計算 / 特徴量探索）を目的とした Python ベースのシステムです。  
主に以下の役割を持つコンポーネント群で構成されています。

- ExecutionEngine：発注・リスク管理・注文管理
- Monitoring：システム稼働・注文状況・リスク監視、Kill Switch（安全停止）
- Research：ファクター計算・統計・IC 計算
- Portfolio：銘柄選定・配分・ポジション決定
- AI（OpenAI）：ニュース NLP によるセンチメント解析・レジーム判定
- ユーティリティ：設定管理、ログ設定、プロセス優先度設定 など

設計方針として「本番 DB とペーパートレードの分離」「ルックアヘッドバイアス回避」「フェイルセーフ（APIエラー時のフォールバック）」等を重視しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の生成 / 更新）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml のチェック）: `kabusys.validate_config`
- 実行エンジン起動スクリプト（ExecutionEngine）: `run_execution.py`
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使って `data/paper_trading.db` に記録（本番 DB と分離）
- 監視ループ起動スクリプト（SystemMonitor）: `run_monitoring.py`
  - 環境にかかわらず監視用の本番 sqlite_path を使用
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- Monitoring サブシステム
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - RiskMonitor：ドローダウン・ポジション上限の検出とログ化
  - KillSwitch：条件発生時にフラグファイルを書き込み ExecutionEngine を停止
  - AlertManager（通知連携想定）
- Research（DuckDB）
  - ファクター（Momentum / Volatility / Value）計算
  - 将来リターン、IC、統計サマリー
- Portfolio（選定・重み・ポジションサイジング）
  - 候補選定、等金額／スコア重み、リスクベースの株数計算、セクターキャップ適用
- AI（OpenAI）
  - ニュース NLP による銘柄ごとのセンチメント（ai_scores テーブルへ書込）
  - マクロニュース + ETF MA200 乖離から市場レジーム判定（market_regime テーブルへ書込）
- ツール
  - Paper Trading の検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

---

## 必要条件

- Python 3.10 以上（型注釈や標準型エイリアス等を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML の検証を実行する場合）
- SQLite（標準ライブラリに含まれます）

例（仮想環境作成とパッケージインストール）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt があればそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動

```bash
git clone <repo-url>
cd <repo-root>
```

2. 仮想環境を作成して依存パッケージをインストール（上記参照）

3. 環境変数ファイルの作成（対話ウィザード推奨）

```bash
python -m kabusys.config_setup
# 対話式で .env を生成・更新します
```

4. 設定の検証

```bash
python -m kabusys.validate_config        # 警告は許容
python -m kabusys.validate_config --strict  # 警告も失敗扱い
```

5. （任意）ログディレクトリ、data ディレクトリの確認

- ログはデフォルトで `logs/` に日次ローテーションで出力されます
- 各種 PID / flag / DB ファイルはデフォルトで `data/` 配下に配置されます（.env で変更可）

---

## 使い方（起動 / 実行例）

基本的にパッケージ内のスクリプトはモジュール実行で起動します。

- 監視ループ起動（SystemMonitor）

```bash
# ポーリング間隔を環境変数で上書き（秒）
export MONITOR_POLL_INTERVAL=60
python -m kabusys.run_monitoring
```

特徴:
- プロセス優先度を "high" に設定します（可能な環境で）。
- 停止：プロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します。
- 監視は monitoring DB（Settings.sqlite_path）へ書き込みます（環境に依らず本番 sqlite_path を使用）。

- 実行エンジン起動（ExecutionEngine）

```bash
# 本番 / ペーパートレード切替：
export KABUSYS_ENV=development         # 実際の注文は行わない（開発）
export KABUSYS_ENV=paper_trading       # MockBroker を使用、data/paper_trading.db に記録
export KABUSYS_ENV=live                # 本番（実際に発注）

python -m kabusys.run_execution
```

特徴:
- paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用します。
- 起動時に `data/stop_requested.flag` があれば起動を中止します。
- Engine の PID は `data/execution.pid`（デフォルト）に保存されます。
- 停止は `data/stop_requested.flag` を作成するか、プロセスに SIGINT を送る等で行います。

- Paper Trading 検証レポート生成

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを明示する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

- AI 機能（ニュース NLP / レジーム判定）

これらを使うには OpenAI API キーを設定します:

```bash
export OPENAI_API_KEY="sk-..."
# ニューススコア付与を呼び出す（例: Python スクリプト内）
from datetime import date
from kabusys.ai.news_nlp import score_news
# duckdb_conn は duckdb.connect(...) で生成
# score_news(duckdb_conn, date(2026,4,1), api_key=None)
```

---

## 主要な環境変数（代表）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
  - OPENAI_API_KEY: OpenAI を使う場合に必要
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
  - PAPER_FILL_MODE: paper_trading 時の模擬約定挙動（instant|partial|never|reject）

Settings クラスで多くの値を読み取るので `.env` を作成しておくことを推奨します。

---

## 停止 / Kill Switch

- ExecutionEngine 側停止のトリガー:
  - KillSwitch（Monitoring の判定）により `data/kill.flag` が書き込まれると、運用者が確認のうえ Execution を停止できます。
  - `KillSwitch.clear()` によりフラグを削除できます。`KILL_FLAG_CLEAR_ON_START` を `1` にすると起動時に自動でクリアします（本番では `0` を推奨）。
- 強制停止フラグ:
  - `data/stop_requested.flag` を作成すると、`run_monitoring` / `run_execution` 起動ループが検知して終了します（運用上のメンテ用）。

---

## ログ

- ログはデフォルトで `logs/` に出力され、日次ローテーションで 30 日分が保持されます（`kabusys.utils.logging_setup.setup_logging`）。
- コンソール出力は STDOUT に出ます（cron 等での扱いを想定）。

---

## ディレクトリ構成（主なファイル）

リポジトリ内 `src/kabusys` を基準に代表的な構成を示します。

- run_monitoring.py — SystemMonitor ポーリングループ起動
- run_execution.py — ExecutionEngine 起動
- config.py — 環境変数 / 設定管理（Settings クラス）
- config_setup.py — .env 対話式作成ウィザード
- validate_config.py — 起動前設定検証 CLI
- __init__.py — パッケージメタ情報

サブパッケージ:

- ai/
  - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + マクロ NLP 合成）
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文ログ監視（ファイル中の該当処理あり）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書き込み
  - monitoring_engine.py — 各モニタ束ねてポーリング
  - alert_manager.py — アラート送信（実装箇所あり）
- execution/
  - execution_engine.py — 実行エンジン本体
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py 等
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py — momentum / volatility / value 等
  - feature_exploration.py — forward returns / IC / summary
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- data/ （ランタイムで使用）
  - monitoring.db（デフォルト）や paper_trading.db、flag / pid ファイル が格納されます
- logs/ （デフォルトログ出力先）

---

## 開発者向けメモ / ベストプラクティス

- .env は Git に絶対にコミットしない（config_setup も README に記載）。
- 本番では `KABUSYS_ENV=live` とし、`KILL_FLAG_CLEAR_ON_START=0` を推奨。
- AI 機能を使う際は OpenAI API のレート・コストを考慮して運用すること。
- DuckDB は分析処理（research / ai の一部）で使用。DB ファイルパスは `DUCKDB_PATH` で指定。
- 監視やリスクアラートは kill.flag を作成するため、アラートポリシーには慎重を期すこと。

---

必要があれば、README に含めるコマンド例、環境変数テンプレート（.env.example）、また各モジュールの API リファレンスや起動フロー図を追加します。どの情報を詳細化したいか教えてください。