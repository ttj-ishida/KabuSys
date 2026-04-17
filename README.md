# KabuSys

日本株自動売買システムの一部を切り出したモジュール群です。本リポジトリは監視・実行・ポートフォリオ構築・リサーチ・AI支援（ニュースセンチメント・レジーム判定）などを含む設計になっています。

以下はコードベースの概要、機能、セットアップ・実行方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な目的は以下：

- ExecutionEngine（発注エンジン）による注文作成・ブローカー連携・リスク管理
- Monitoring（監視）によるシステム稼働監視、注文滞留／約定異常検出、ドローダウン監視
- Portfolio Construction（候補選定・重み付け・ポジションサイジング）
- Research（ファクター計算、特徴量探索、IC評価）
- AI モジュール（ニュースの LLM センチメント評価、市場レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針として外部副作用を過度に行わない純粋関数群、DDL の冪等性、Paper Trading（検証）と本番 DB の分離などが考慮されています。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動、ブローカークライアントの切替（`KABUSYS_ENV=paper_trading` で MockBroker）
  - Paper trading 時は専用 SQLite（デフォルト `data/paper_trading.db`）を使用
  - PID 管理（`data/execution.pid`）・停止フラグ（`data/stop_requested.flag`）対応

- run_monitoring.py
  - SystemMonitor ポーリングループ。ポーリング間隔は `MONITOR_POLL_INTERVAL` で上書き可（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番の sqlite_path を使用してログ永続化

- 監視（monitoring）
  - SystemMonitor：CPU / メモリ / ディスク / プロセス存在チェック、データ鮮度チェック
  - TradeMonitor：滞留注文（stale orders）・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視とダッシュボード更新
  - KillSwitch：閾値超過で `data/kill.flag` を書いて ExecutionEngine に停止指示
  - AlertManager：LINE Push API を使ったプッシュ通知（cooldown 管理）

- データ永続化
  - monitoring_db (SQLite)：system_status / trade_logs / positions / risk_logs / dashboard テーブル・マイグレーション対応
  - DuckDB：時系列株価やファイナンスデータを格納してリサーチ処理で利用

- Portfolio（portfolio）
  - 銘柄候補選定、等ウェイト・スコア加重重み計算、セクター制約適用、ポジションサイズ計算（lot 丸め・リスクベース配分、aggregate cap）

- Research（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
  - DuckDB を使った SQL + Python 実装

- AI（ai）
  - news_nlp: raw_news を LLM（OpenAI）でセンチメント評価して `ai_scores` に書込む
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）判定

- ツール
  - tools/paper_verification_report.py：Paper Trading DB から検証レポートを生成（稼働率・成功率・レイテンシ等）
  - monitoring/streamlit_dashboard.py：Streamlit を使った監視ダッシュボード

---

## 必要条件 / 依存ライブラリ

推奨 Python バージョン: 3.10 以上（型アノテーションの union 演算子などを使用）

主な外部依存（抜粋）:
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）

例（pip）:
```bash
pip install duckdb psutil requests openai streamlit
```

requirements.txt があればそれを使ってください。

---

## 環境変数（主なもの）

Settings クラスで利用される主な環境変数：

必須（実運用時）:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

API / 動作設定:
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで必要）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

データベース / ファイル:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — Monitoring SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PID_FILE_PATH — Execution PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするか（"1" で有効）

Paper Trading 固有:
- PAPER_FILL_MODE — MockBroker の約定モード（instant|partial|never|reject、デフォルト "instant"）

監視閾値（任意）:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

その他:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" にすると .env 自動読み込みを無効化

.env / .env.local の自動読み込み:
- プロジェクトルート（.git または pyproject.toml が存在する場所）にある `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先され、.env.local は上書き）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 .env（テンプレート）:
```
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## セットアップ手順（簡易）

1. Python（3.10 以上）を用意
2. 依存パッケージをインストール
   - 例: pip install -r requirements.txt または個別インストール
3. 環境変数または .env を準備
   - 必要な値 (上記参照) をセット
4. data ディレクトリの作成（必要に応じて）
   - 例: mkdir -p data
5. DuckDB / SQLite の初期化は各起動スクリプトが自動で行います（init_monitoring_db を実行）

---

## 使い方（実行例）

- 監視プロセス起動（デフォルトポーリング 60 秒）:
```bash
# 環境変数 MONITOR_POLL_INTERVAL で秒数を変更可
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- ExecutionEngine 起動:
```bash
# 本番/開発/ペーパートレードを切り替える
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- 停止方法:
  - 監視/実行プロセスは `data/stop_requested.flag` 存在でループを抜けて停止します（上書きせず存在チェック）。
  - KillSwitch がトリガーすると `data/kill.flag` を書き、その存在を Engine が検出して安全停止します。
  - 実行中に CTRL+C（KeyboardInterrupt）でも正常終了パスが実装されています。

- Paper Trading 検証レポート生成:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB パスを明示
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- Streamlit ダッシュボード起動:
```bash
# 例（ソースファイルを直接指定する方法）
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- AI モジュール（プログラム内呼び出し例）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
# ニューススコア（OPENAI_API_KEY を環境変数で設定）
score_news(conn, target_date=date(2026,4,10))
# レジーム判定
score_regime(conn, target_date=date(2026,4,10))
```

---

## 停止/制御ファイルについて

- data/stop_requested.flag — run_monitoring.py / run_execution.py が存在をチェックして安全に起動ループを終了します（管理者が停止したいときにファイルを作成）。
- data/kill.flag — KillSwitch によって書き込まれる。ExecutionEngine は kill.flag の存在を検知して停止します。
- data/execution.pid — ExecutionEngine の PID 管理に使用されます。

---

## ディレクトリ構成（抜粋）

以下は `src/kabusys` 以下の主要ファイル / サブパッケージと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数・設定管理（.env 自動読み込み・Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — ニュース記事を LLM でセンチメント評価して ai_scores に書き込む
    - regime_detector.py — MA200 とマクロニュースで市場レジームを判定

  - monitoring/
    - monitoring_db.py — SQLite テーブル定義 / 永続化 API
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/data freshness チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE 通知（クールダウン管理）
    - monitoring_engine.py — 各 Monitor の実行制御
    - streamlit_dashboard.py — Streamlit ダッシュボード

  - execution/
    - reconciler.py — 再起動時の注文・ポジション照合（リコンシリエーション）
    - order_manager.py — 注文の外向け管理（作成・キャンセル・同期）
    - （その他: broker_factory, order_repository, order_record, execution_engine 等が想定）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（等分配・スコア重み）
    - position_sizing.py — 株数算出・lot 丸め・aggregate cap
    - risk_adjustment.py — セクター上限・レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value などのファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ等

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール

  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（実際のファイル/モジュールはソースを参照してください）

---

## 注意事項 / 運用メモ

- Paper Trading（`KABUSYS_ENV=paper_trading`）時はブローカーはモックになり、paper_trading 用の SQLite DB にログを書きます。本番 DB とは分離されます。
- monitoring の初期化（テーブル作成・マイグレーション）は run* スクリプト内で `init_monitoring_db` を呼びます。既存 DB に対するマイグレーション（列追加等）も一部自動で行います。
- AI API 呼び出しはネットワーク／API エラーを考慮したリトライとフェイルセーフ（失敗時は 0.0 フォールバック等）を実装していますが、APIキーの管理には注意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI 等で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視ループのポーリング間隔は `MONITOR_POLL_INTERVAL` で簡単に調整可能（0 以下は受け付けずデフォルトにフォールバックします）。

---

この README はコードベースの主要機能と利用方法を簡潔にまとめたものです。詳細な API、ExecutionEngine の内部、broker 実装、OrderRepository のスキーマ等はソースを参照してください。必要であれば各モジュールごとの詳細ドキュメント（使用例・設計メモ）も作成できます。