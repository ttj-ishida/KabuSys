# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
この README はリポジトリ内の主要スクリプト・モジュールに基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買・研究用フレームワークです。  
主な機能は以下の通りです：

- 市場データ（DuckDB）・監視データ（SQLite）を用いたリサーチ／ファクター計算
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 実運用向けの ExecutionEngine（本番 / ペーパートレード分離）
- 監視（System / Trade / Risk）と Kill Switch（フラグファイルでエンジン停止）
- AI（LLM）を用いたニュースセンチメント評価・市場レジーム判定
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）
- ペーパートレード検証レポート生成ツール

設計方針として、データベース接続（DuckDB/SQLite）を外部から渡す関数設計、ルックアヘッドバイアスの回避、フェイルセーフ（API失敗時のフォールバック）などが取られています。

---

## 機能一覧（抜粋）

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式ウィザードで .env を生成（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 監視
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス生存をチェック
  - TradeMonitor / RiskMonitor：注文・ドローダウン・ポジション上限監視
  - MonitoringEngine：各 Monitor を束ねてポーリング/アラート連携
  - KillSwitch：ルールに応じて data/kill.flag を書き込みエンジン停止
- 実行（Execution）
  - ExecutionEngine（run_execution スクリプトで起動）
  - Paper trading 用の MockBrokerClient（KABUSYS_ENV=paper_trading 時に分離）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - news_nlp: OpenAI を用いたニュースセンチメント集計 → ai_scores テーブルへ書込み
  - regime_detector: ETF の MA とマクロニュースで市場レジーム判定
- ツール
  - papers_verification_report：ペーパートレード DB から検証レポートを生成

---

## セットアップ手順（開発者向け）

前提
- Python 3.10+ を推奨（型注釈や union 型記法を使用）
- 必要な外部ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で任意）
  - その他（実際の requirements.txt がある場合はそちらを使用）

例（venv を使う場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 依存関係をインストール（requirements.txt がある場合）
# pip install -r requirements.txt

# 主要な手動依存の例
pip install duckdb psutil openai PyYAML
```

.env の作成（対話式ウィザード）
```bash
python -m kabusys.config_setup
```
このウィザードは .env を作成／更新します。重要な環境変数の例:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development / paper_trading / live)
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用DB）
- OPENAI_API_KEY（AI モジュール利用時）

設定検証:
```bash
python -m kabusys.validate_config
# 警告をエラー扱いにする場合:
python -m kabusys.validate_config --strict
```

ログディレクトリ:
- デフォルトは `logs/`。設定に応じて `LOG_DIR` 環境変数で変更可能。

データディレクトリ:
- デフォルト DB 等は `data/` 配下に配置されます（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）。

---

## 使い方（主要スクリプト・例）

1. 監視ループ（SystemMonitor 単独起動）
```bash
python -m kabusys.run_monitoring
```
- 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
- 監視は実行環境に関係なく本番の sqlite_path（Settings.sqlite_path）を使用します。
- 停止はプロジェクトルートの `data/stop_requested.flag` を作成することで行います（フラグ検知でループ終了）。

2. 実行エンジン（ExecutionEngine）起動
```bash
python -m kabusys.run_execution
```
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用い、paper_trading 用の DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
- 起動時に `data/stop_requested.flag` が存在すると実行せず終了します。
- Execution の PID は `data/execution.pid` に書き出されます。

3. ペーパートレード検証レポート
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

4. AI 系機能（プログラム経由で利用）
- news_nlp.score_news(conn, target_date, api_key=...)
- regime_detector.score_regime(conn, target_date, api_key=...)
これらは DuckDB 接続（duckdb.connect()）を渡して呼び出します。OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` を使用します。

例（簡易）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026, 4, 10), api_key="sk-...")
```

注意点:
- AI 呼び出しは外部 API に依存するためキーやレート制限の考慮が必要です。失敗時はフォールバック動作が組み込まれている箇所が多い設計です。

5. プロセス優先度設定
- run_monitoring / run_execution は起動時にプロセス優先度を `high` に設定するユーティリティを呼び出します（psutil が必要）。許可がない環境では警告が出てスキップされます。

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL — ログレベル（DEBUG / INFO / ...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

---

## 注意事項 / 運用上のガイド

- 本番（KABUSYS_ENV=live）での起動時は .env の内容を慎重に確認してください（validate_config は本番向けの追加警告を出します）。
- Kill Switch（data/kill.flag）は危険停止用です。本番では自動クリア（KILL_FLAG_CLEAR_ON_START=1）は推奨されません。
- ペーパートレード（paper_trading）は本番 DB と分離されます。デフォルトで `data/paper_trading.db` を使用します。
- ログは `logs/<app_name>.log` に日次ローテーションで出力されます。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- DuckDB/SQLite のファイルはバックアップやロックに注意して運用してください。

---

## ディレクトリ構成（主要ファイル抜粋）

リポジトリの Python パッケージは `src/kabusys` 以下に格納されています。主要なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py      — 統一ログ設定
    - process_priority.py   — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite 監視テーブルの初期化 / ラッパー
    - system_monitor.py     — システム状態・データ鮮度監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - trade_monitor.py      — （注文監視ロジック、ファイル内で参照あり）
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - kill_switch.py        — kill.flag 書込みユーティリティ
    - alert_manager.py      — （アラート送信ロジック、例: LINE）
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory 等)
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

（上記はリポジトリ内のソースから抽出した主要モジュールです。補助的なファイル・モジュールも含まれます。）

---

## 開発・貢献

- コードはモジュール単位で分かれており、ユニットテストやモックを使ったテストがしやすい設計です（外部 API 呼び出し部は差し替え可能な関数にしている箇所があります）。
- 変更する際は .env.example を参照し、validate_config でチェックを行ってください。
- AI 関連は外部 API へ多くのリクエストを送る設計なので、レート制御や API キーの管理に注意してください。

---

README の内容はコードベースの主要機能と設定フローを説明するための要約です。より詳細な仕様（StrategyModel.md / PortfolioConstruction.md 等の設計文書）がリポジトリに含まれている場合はそちらも参照してください。