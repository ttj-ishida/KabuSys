# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量な Python 製フレームワークです。DuckDB / SQLite をデータ層に、OpenAI を用いたニュース NLP やレジーム判定、監視・アラート・キルスイッチ、発注エンジンのリコンシリエーション等の機能を含みます。

本 README はリポジトリ内の主要モジュールに基づき、導入・起動・簡単な使い方・ディレクトリ構成を日本語でまとめたものです。

---

## 主な特徴

- ポートフォリオ構築用の純粋関数群（銘柄選定、重み付け、ポジションサイズ算出）
- DuckDB を使ったファクター計算・リサーチモジュール（モメンタム・ボラティリティ・バリュー等）
- OpenAI を用いたニュースセンチメント（銘柄別）スコアリングと市場レジーム判定
- ExecutionEngine（発注エンジン）と OrderManager / Reconciler による発注管理と再同期処理
- 監視（MonitoringEngine）：システム状態・注文滞留・ドローダウン監視、LINE 通知、キルスイッチ
- Streamlit ベースの監視ダッシュボード（read-only）
- Paper Trading モード（本番 DB と分離された data/paper_trading.db を使用）

---

## 必要な依存パッケージ（例）

以下をインストールしてください（プロジェクトに requirements.txt がない場合）:

pip (例)
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（必要に応じて他の依存を追加してください。プロダクションでは適切なバージョン固定を推奨します）

---

## 環境変数 / .env の自動読み込み

- プロジェクトルートに `.env` および `.env.local` を置くことで自動的に読み込まれます（OS 環境変数が優先）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- 必須・よく使う環境変数（例）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 SQLite、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（実行エンジンの PID ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（kill.flag、デフォルト: data/kill.flag）
  - PAPER_FILL_MODE（paper_trading の約定モード: instant | partial | never | reject、デフォルト: instant）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）。run_monitoring で使用、デフォルト 60）

環境変数は `src/kabusys/config.py` で定義・検証されています。`.env.example` を参照して `.env` を作成してください（リポジトリに含める場合）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成・有効化。
2. 依存パッケージをインストール（上記参照）。
3. 必要な環境変数を `.env` に設定（OpenAI やブローカーの認証情報など）。
4. データディレクトリを作成（例: data/）。
5. DuckDB / SQLite DB を用意（初回起動時に必要テーブルは自動作成される箇所が多い）。

例:
```
mkdir -p data
# .env をプロジェクトルートに配置（例で示した値を設定）
```

監視 DB（SQLite）は起動スクリプト内で `init_monitoring_db` によりテーブル作成・軽微なマイグレーションが行われます。

---

## 実行方法（主要スクリプト）

- 監視ポーリングループ（SystemMonitor 単体呼び出しを含む最小起動）
```
python -m kabusys.run_monitoring
```
挙動:
- `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- Monitoring は KABUSYS_ENV にかかわらず本番設定の `sqlite_path` を使用します
- 起動時にプロセス優先度を "high" に設定（権限不足時は警告）

- 実行エンジン（ExecutionEngine）起動
```
python -m kabusys.run_execution
```
挙動:
- KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録するため本番 DB とは完全に分離されます
- 起動時にプロセス優先度を "high" に設定
- 内部で Reconciler による再同期や ExecutionEngine のセッション実行が行われます

- Streamlit 監視ダッシュボード
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
（`--db` 引数で監視 DB パスを指定、デフォルトは data/monitoring.db）
ダッシュボードは監視データを read-only で表示します。

- Paper Trading 検証レポート生成ツール
```
python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
```
例:
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```
`--db` を指定しない場合、`PAPER_TRADING_SQLITE_PATH` 環境変数、さらに無ければ `data/paper_trading.db` を参照します。レポートは稼働率／注文成功率／送信率／P95 レイテンシ等を算出して PASS/FAIL 判定を行います。

---

## ライブラリ API の使用例（AI 関連）

- ニュース NLP（銘柄別センチメント）をプログラムから呼ぶ例:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026,4,10), api_key="sk-xxxxx")
print(f"wrote {written} scores")
```
- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,4,10), api_key="sk-xxxxx")
```
いずれも `OPENAI_API_KEY` を環境変数に入れておけば api_key 引数は不要です。API 呼び出しはリトライ・フォールバックを実装しており、失敗時は安全側の値（例: macro_sentiment=0.0）で継続する設計です。

---

## 監視・アラート・キルスイッチの概念

- Monitoring 系は MonitoringDB（SQLite）へログを永続化し、各種 Monitor（System / Trade / Risk）を集約して周期実行します。
- AlertManager は LINE PUSH API を用いて通知を行います（トークン未設定時は送信せずログのみ）。
- KillSwitch は条件（ドローダウンやポジション上限超過）に該当した場合、`KILL_FLAG_PATH`（デフォルト data/kill.flag）へ理由を出力し、ExecutionEngine 側で停止トリガーとして利用できます。
- PID 管理: ExecutionEngine は起動時に PID を `PID_FILE_PATH` に書き込み、SystemMonitor はその PID を監視して stale PID を検出・削除します。

---

## 設定の要点（Settings）

主要プロパティ（default）の例:
- duckdb_path: data/kabusys.duckdb
- sqlite_path: data/monitoring.db
- paper_sqlite_path: data/paper_trading.db
- pid_file_path: data/execution.pid
- kill_flag_path: data/kill.flag
- PAPER_FILL_MODE: instant / partial / never / reject

KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか。`paper_trading` 時は発注先がモックに切り替わり、DB は paper_trading 用ファイルを使います。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ宣言
  - config.py — 環境変数 / 設定読み込み・検証
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- src/kabusys/ai/
  - news_nlp.py — ニュースセンチメントの収集・OpenAI 呼び出し・ai_scores への書込
  - regime_detector.py — マクロ + ETF ma200 によるレジーム判定
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite の監視テーブル定義と CRUD
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 各モニタを束ねる実行ループ
  - streamlit_dashboard.py — streamlit ダッシュボード
- src/kabusys/execution/
  - reconciler.py — 起動時の注文 / ポジション再同期処理
  - order_manager.py — 発注の高レベル API（状態遷移）
  - (その他: broker_factory, execution_engine, order_repository, order_record 等)
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - position_sizing.py — 株数決定・単元切捨て・aggregate cap
- src/kabusys/research/
  - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成ツール
- src/kabusys/utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

（上記は主要ファイルのみ抜粋。実際のファイル構成はリポジトリを参照してください）

---

## 運用上の注意点 / ベストプラクティス

- 本番運用時は KABUSYS_ENV を `live` に設定し、適切なバックアップ・監視を行ってください。
- OpenAI API キーは秘匿して管理し、必要最小限の権限で運用してください。API 呼び出し箇所はレート制御とリトライの実装がありますが、コスト管理に注意してください。
- Paper Trading を使うことで本番 DB と操作を分離できます。テスト・検証は paper_trading モードで実施してください。
- process priority の設定は環境（OS, 権限）によって失敗することがあります（警告ログのみ）。

---

## よく使うコマンドまとめ

- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- Streamlit ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースのコメント・設計注釈に基づき作成しています。より詳細な設計文書（PortfolioConstruction.md, StrategyModel.md 等）が存在する場合はそちらを参照してください。追加の説明やサンプルが必要であれば教えてください。