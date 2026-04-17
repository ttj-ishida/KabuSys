# KabuSys

日本株自動売買システムのコードベース（抜粋）。この README はローカル実行や開発時に役立つ概要・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアコンポーネント群を実装したリポジトリです。本コードベースは以下の主要機能を含みます：

- Execution（発注エンジン、ブローカークライアント、オーダー管理、再同期）
- Monitoring（システム監視、取引監視、リスク監視、アラート送信、監視 DB）
- Portfolio（候補選定、重み計算、ポジションサイズ決定、セクター制限）
- Research（ファクター計算、特徴量探索、将来リターン）
- AI ユーティリティ（ニュースセンチメント解析・市場レジーム判定、OpenAI 利用）
- ツール類（Paper Trading 検証レポート、Streamlit ダッシュボード）
- 設定管理、プロセス優先度ユーティリティ等ユーティリティ群

設計上の特徴として、DuckDB を使ったリサーチ処理、SQLite による監視ログ永続化、OpenAI（gpt-4o-mini 等）を用いたニュース NLP などが含まれます。

---

## 主な機能一覧

- SystemMonitor
  - CPU / メモリ / ディスク使用率の記録
  - Execution プロセス生存チェック（PID ファイル）
  - データ鮮度チェック（prices_daily の最終日付）
  - system_status テーブルへのログ化
- TradeMonitor
  - 注文滞留（stale order）検出
  - 約定異常（価格乖離）検出
  - risk_logs への記録
- RiskMonitor
  - ドローダウン監視（ハイウォーターマーク管理）
  - ポジション数上限チェック
  - dashboard テーブル更新 / risk_logs への記録
- KillSwitch / AlertManager
  - 条件に応じたデータ/ファイルベースの停止シグナル（data/kill.flag）
  - LINE API を用いたアラート通知（クールダウン管理）
- MonitoringEngine / run_monitoring.py
  - 上記モニタ群のポーリング実行、監視 DB（SQLite）への永続化
- ExecutionEngine / run_execution.py
  - ブローカーへの発注実行、リスク管理、Reconciler による起動時リコンシリエーション
  - paper_trading 環境では MockBrokerClient を使用して本番 DB と分離
- Portfolio モジュール
  - 候補選定（スコア順）、等金額・スコア加重、リスクベースの株数計算、セクター制約
- Research
  - モメンタム / ボラティリティ / バリュー等ファクター計算
  - 将来リターン・IC・統計サマリ
- AI
  - ニュースを集約して OpenAI でセンチメント評価 → ai_scores に書き込み
  - 市場レジーム判定（ETF ma200 乖離 + マクロセンチメント）
- Tools
  - paper_verification_report: Paper Trading DB を解析して PASS/FAIL レポートを出力
  - streamlit_dashboard: 監視 DB を可視化するダッシュボード

---

## セットアップ手順

前提：
- Python 3.10+ を推奨（コード上 typing | None の注記等）
- 必要なパッケージをインストールしてください。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt が無い場合は最低限:
pip install duckdb psutil requests streamlit openai
```

（補足）
- Windows / macOS / Linux で挙動差分を扱うユーティリティ（process_priority 等）があります。
- OpenAI を利用する機能を動かす場合は `openai` パッケージが必要です。

初期ディレクトリ準備（data ディレクトリ等）:
```bash
mkdir -p data
# 必要に応じて権限や初期 DB を配置
```

環境変数:
- 自動ロード: プロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主な必須／重要な環境変数:
  - JQUANTS_REFRESH_TOKEN （必須）
  - KABU_API_PASSWORD （必須）
  - OPENAI_API_KEY （AI 機能を使うなら必須）
- 構成や挙動に影響する主要な環境変数（デフォルト値）:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - SQLITE_PATH: data/monitoring.db（監視 DB）
  - DUCKDB_PATH: data/kabusys.duckdb
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - MONITOR_POLL_INTERVAL: 監視ポーリング秒（デフォルト: 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL 等（Settings を参照）

注意:
- 自動ロードは __file__ を起点にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して行われます。

---

## 使い方

### 実行（監視ループ）
監視（SystemMonitor の単独起動ではなく run_monitoring を使う）:
```bash
python -m kabusys.run_monitoring
# 環境変数でポーリング間隔を上書き:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
特徴:
- MONITOR_POLL_INTERVAL（秒）で監視の間隔を変えられます（1 以上）。
- 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV の影響を受けない）。
- 停止ファイル data/stop_requested.flag を作成するとループは終了します。

### 実行（エンジン）
ExecutionEngine を起動:
```bash
python -m kabusys.run_execution
```
挙動:
- KABUSYS_ENV=paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）と MockBrokerClient を使用し、本番 DB とは分離されます。
- 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
- 実行中、停止は data/stop_requested.flag を作成するか、KillSwitch により data/kill.flag が書き込まれると engine.stop() が呼ばれて停止します。
- 実行中は PID が data/execution.pid（デフォルト）に書かれる（Settings.pid_file_path）。

### Paper Trading 検証レポート
Paper Trading DB を解析して検証レポートを標準出力に出します。
```bash
# デフォルト DB パスを使う場合
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パスを明示
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

主な判定基準（コード内の定数）:
- 稼働率 >= 99.0%
- 注文成功率（Filled/Created） >= 90.0%
- 送信率（Sent/Created） >= 95.0%
- P95 レイテンシ <= 200 ms

### Streamlit 監視ダッシュボード
監視 DB を可視化するダッシュボード（読み取り専用）:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- DB は読み取り専用で開かれます。DB が見つからない場合はメッセージが表示されます。

### AI 関連（ニューススコア・レジーム判定）
プログラムから呼び出して利用できます（OpenAI API キーが必要）。
例（ニューススコアリング）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 4, 1), api_key="sk-...")
print("書き込み銘柄数:", count)
```

レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
# duckdb_conn を用意
score_regime(duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
```

注意:
- OpenAI API 呼び出しはリトライ/バックオフ実装がありますが、API キーの設定が必須です。
- LLM のレスポンスは JSON モード想定でパース・検証されます。

---

## ファイル・フラグ／PID の振る舞い

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が監視している停止フラグ。存在するとループを終了します（手動停止用）。
- data/kill.flag
  - KillSwitch が書き込むことで ExecutionEngine 停止を要求するために使用されます（Reason がファイルに書かれる）。
- PID ファイル
  - ExecutionEngine は起動時に pid をファイルに書き（Settings.pid_file_path）、SystemMonitor はその PID ファイルを確認してプロセスの生存確認を行います。
- DB マイグレーション
  - init_monitoring_db() は冪等的に監視用テーブルを作成し、既存テーブルにカラムがない場合は ALTER TABLE による追加（簡易マイグレーション）を行います。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys/ 以下の主要な構造（抜粋）です:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - run_monitoring.py        # SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py    # プロセス優先度・CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py       # SQLite 永続化層
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
      - order_repository.py    # （参照されるが今回の抜粋では一部のみ）
      - execution_engine.py   # （参照されるが抜粋外）
      - broker_factory.py     # BrokerClientFactory の生成（paper/live 切替）
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/                     # 実行時に使う DB / フラグファイル等（リポジトリ外に置くことが多い）
    - tools/
      - __init__.py
      - paper_verification_report.py

（注）上記は抜粋に基づく主要ファイルの一覧です。実際のリポジトリではさらに細かなモジュールが存在します。

---

## 追加メモ・開発上の注意

- 設定の自動読み込み:
  - config.py はプロジェクトルート（.git / pyproject.toml）を探索して `.env` / `.env.local` を読み込みます。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- paper_trading 環境:
  - `KABUSYS_ENV=paper_trading` の際は paper_trading 用の sqlite（PAPER_TRADING_SQLITE_PATH）を使い、本番 DB と完全分離されます。演習や検証に便利です。
- ロギング:
  - run_* スクリプトは basic logging を INFO レベルで使います。詳細なデバッグを行う場合は環境変数 `LOG_LEVEL=DEBUG` 等を設定してください。
- テスト:
  - OpenAI やブローカークライアント呼び出し部分はテスト容易性のために API 呼び出し関数を差し替え可能に設計されています（例: unittest.mock.patch）。

---

必要があれば、README に以下の追記が可能です：
- requirements.txt の具体的な例（バージョン固定）
- 実行用 systemd ユニットファイルや Dockerfile サンプル
- よくあるトラブルシューティング項目（権限、ファイルロック、DB のロック回避方法）
- 詳細な API/DB スキーマ ドキュメント

追記希望があれば用途（運用手順、デプロイ、テスト）を教えてください。