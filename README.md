# KabuSys

日本株向け自動売買システムのコンポーネント群。  
バックグラウンドの監視・アラート、Execution エンジン、ポートフォリオ構築、リサーチ（ファクター計算）および AI を用いたニュース NLP 等のユーティリティを含むモノリポジトリの一部。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- ExecutionEngine：ブローカーへの発注・状態管理・リコンシリエーション
- Monitoring：システム状態、注文・約定異常、リスク（ドローダウン／ポジション上限）を監視してログ・アラート、必要時に ExecutionEngine 停止フラグを出力
- Portfolio：候補選定・重み付け・ポジションサイズ計算等のポートフォリオ構築ロジック
- Research：DuckDB 上の時系列データからファクター計算や統計解析を行う
- AI：OpenAI を用いたニュースセンチメント評価（銘柄別スコア）や市場レジーム判定
- Tools：Paper Trading 検証レポート生成などのツール群

設計方針としては、外部 API に対する安全な呼び出し（リトライ、フォールバック）や本番と Paper Trading の分離、ルックアヘッドバイアス回避などが組み込まれています。

---

## 主な機能一覧

- SystemMonitor：CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度監視
- TradeMonitor：滞留注文（stale order）・約定価格異常検出
- RiskMonitor：ドローダウン監視、ポジション数上限監視、ダッシュボード更新
- KillSwitch：しきい値超過時に停止フラグを書き込み ExecutionEngine を安全停止
- AlertManager：LINE Messaging API による通知（クールダウン管理）
- MonitoringEngine：上記モニタをまとめてポーリング実行
- ExecutionEngine 起動スクリプト（run_execution）
  - `paper_trading` 環境では MockBroker を使用し DB を分離
- Monitoring 起動スクリプト（run_monitoring）
  - ポーリング間隔を環境変数で上書き可能
- AI モジュール（news_nlp, regime_detector）
  - OpenAI を用いたニュースセンチメントの集約・書き込み
- Research モジュール（factor_research, feature_exploration）
  - DuckDB を使ったファクター・将来リターン・IC 等の計算
- Tools（paper_verification_report）
  - Paper Trading DB を解析して通期の PASS/FAIL レポートを生成

---

## 前提 / 必要環境

- Python 3.9+
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（組み込みで不要）
- 任意で .env ファイル（環境変数管理）

requirements.txt はリポジトリにないため、上記パッケージをプロジェクトに合わせてインストールしてください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境作成・有効化
3. 必要なパッケージをインストール（上記参照）
4. 環境変数を設定
   - 簡易的にプロジェクトルートに `.env` を作成すると自動で読み込まれます（`.env.local` は上書き）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（主要）:
- JQUANTS_REFRESH_TOKEN：J-Quants API 用（研究機能など）
- KABU_API_PASSWORD：kabuステーション API パスワード
- OPENAI_API_KEY：AI 機能を使う場合に必要

その他（代表的なものとデフォルト）:
- KABUSYS_ENV：development | paper_trading | live（デフォルト: development）
- LOG_LEVEL：DEBUG/INFO/…
- SQLITE_PATH：監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH：paper_trading 用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH：DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH：ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH：KillSwitch の flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL：監視ループ間隔（秒、デフォルト: 60）

.env の例（参考）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
```

---

## データベース / ファイル

- 監視 SQLite（デフォルト）: data/monitoring.db
  - run_monitoring / run_execution 起動時に `init_monitoring_db` によりテーブルが作成されます（冪等）。
  - 主要テーブル: system_status, trade_logs, positions, risk_logs, dashboard, ai_scores, market_regime 等（AI/Research 用テーブルは DuckDB 側の場合あり）
- Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時、Execution はここへ書き込む）
- DuckDB: data/kabusys.duckdb（時系列データ・prices_daily 等）
- PID / フラグ:
  - data/execution.pid: ExecutionEngine が起動時に書き込む PID（存在チェックでプロセス生存判定）
  - data/stop_requested.flag: 外部から監視ループ／実行ループを終了させるためのファイル（run_monitoring, run_execution が参照）
  - data/kill.flag（デフォルト）: KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送る（ExecutionEngine 側は起動時にオプションで削除する設定有り）

---

## 使い方（コマンド例）

project のルートをカレントにして実行することを前提としています。

1. 監視ループ起動（SystemMonitor 等をポーリング）
```
python -m kabusys.run_monitoring
```
- ポーリング間隔を上書きするには環境変数を設定:
```
export MONITOR_POLL_INTERVAL=30
```
- 終了: Ctrl+C またはプロジェクトルートに `data/stop_requested.flag` を作成するとループを検知して終了します。

2. ExecutionEngine 起動
```
python -m kabusys.run_execution
```
- KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用し DB は data/paper_trading.db に分離されます。
- 起動前に `data/stop_requested.flag` が存在する場合は起動せず終了します。
- ExecutionEngine 側は `data/execution.pid` を書き込み、プロセス死や stale PID の検出を行います。

3. Streamlit ダッシュボード（監視用）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- デフォルトで読み込みは読み取り専用 URI を使います。
- MonitoringEngine がデータを書き込んでいればダッシュボードに表示されます。

4. Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を明示
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
- 出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等の指標と PASS/FAIL 判定

5. AI 関連（ニューススコア / レジーム判定）
- OpenAI API キーが必要です（環境変数 `OPENAI_API_KEY` または関数引数で渡す）。
- プログラム的に呼び出す例（Python API）:
```python
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime
# duckdb_conn は DuckDB 接続（kabusys.config.Settings.duckdb_path を使って接続）
count = score_news(duckdb_conn, target_date, api_key="...")
score_regime(duckdb_conn, target_date, api_key="...")
```
- API 呼び出しはリトライやフォールバックが組み込まれており、失敗時はスコアをデフォルト値で継続する設計です。

---

## 停止・強制停止の仕組み

- graceful stop:
  - `data/stop_requested.flag` を作成すると `run_monitoring` / `run_execution` が検知して安全に終了します。
- KillSwitch:
  - RiskMonitor 等が検出した重大事象（ドローダウンやポジション上限など）に対して KillSwitch が `data/kill.flag`（既定）を書き込み、ExecutionEngine 側がこれを検知して停止する運用を想定しています。
  - `Settings.kill_flag_clear_on_start` を使って起動時にフラグを自動削除できます（環境変数で制御）。

---

## 開発向け / 設計上のポイント

- 設定読み込み:
  - モジュール `kabusys.config` により `.env` / `.env.local` を自動読み込み（OS 環境変数優先）。テスト等で自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
  - KABUSYS_ENV の値は `development` / `paper_trading` / `live` のみ許容。
- DB 初期化:
  - `init_monitoring_db` は冪等でテーブルを作成し、既存 DB のマイグレーション（カラム追加等）も行います。
- プロセス優先度:
  - 起動スクリプトは最初に `set_process_priority("high")` を呼び出して可能な限りプロセス優先度を高めます（プラットフォーム依存で失敗した場合はログに記録してスキップ）。
- Paper Trading 分離:
  - Paper Trading 実行時は SQLite を別ファイルに切り替え、本番 DB と完全に分離します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - data/ (実行時に利用するファイル群: DB, pid, flags 等) — プロジェクトルート直下に想定
  - monitoring/
    - monitoring_db.py — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (DB 操作: OrdersDB)
    - execution_engine.py (起動・ランタイムロジック)
    - broker_factory.py / broker_api.py — ブローカー抽象
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

（上記は主なモジュールの抜粋です。細かなファイルはソースツリー参照）

---

## よく使う環境変数（まとめ）

- KABUSYS_ENV (development | paper_trading | live) — 動作モード
- OPENAI_API_KEY — OpenAI API キー（AI 機能）
- JQUANTS_REFRESH_TOKEN — J-Quants API
- KABU_API_PASSWORD — kabu API
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH, KILL_FLAG_PATH など（詳細は config.Settings）

---

## 注意事項 / 運用メモ

- OpenAI や外部 API を利用する機能は API キーと通信環境が必要です。呼び出し失敗時のフェイルセーフ（フォールバック値、リトライ）がありますが、本番運用ではレート制限・費用に注意してください。
- Paper Trading は本番 DB と分離されていますが、設定ミスで本番 DB に書き込まないよう `.env` の値を確認してください。
- PID ファイルやフラグファイルの取り扱いは OS のファイルパーミッションやコンテナの永続ボリュームに依存します。デプロイ時はその点に注意してください。
- DuckDB / prices_daily 等のデータ品質（時系列の抜け、NULL 値等）が研究・AI 結果に大きく影響します。ETL パイプラインとデータ確認を行ってください。

---

この README はソースコードの内容に基づいて作成しています。細かい動作や追加オプションはソース内ドキュメンテーション（Docstring）や各モジュール実装を参照してください。質問や追記したい項目があれば教えてください。