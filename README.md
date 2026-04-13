# KabuSys

日本株自動売買システムのユーティリティ群とコアロジック群をまとめたリポジトリ。  
本リポジトリには取引実行周りのエンジン・監視機能・ポートフォリオ構築ロジック・リサーチ用関数・AI を使ったニュース/レジーム判定などが含まれます。

---

## 概要

- 証券ブローカー API 経由での発注ロジック（ExecutionEngine 等）と、その復旧/同期（Reconciler）機能
- 監視コンポーネント（System / Trade / Risk モニタ）とアラート送信（LINE）
- Paper Trading 用の分離された DB と Mock ブローカーのサポート
- DuckDB を用いたファクター計算 / リサーチ機能（prices_daily / raw_financials 想定）
- OpenAI（gpt-4o-mini）を活用したニュースセンチメント（ai/news_nlp）・マクロ判定（ai/regime_detector）
- Streamlit による監視ダッシュボード、検証レポート生成ツール等

---

## 主な機能一覧

- Execution
  - 発注フロー管理（OrderManager、OrderRepository、ExecutionEngine）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - Paper Trading と Live の切り替え（KABUSYS_ENV）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度の監視
  - TradeMonitor: 滞留注文・約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ記録
  - KillSwitch: kill.flag による ExecutionEngine 停止シグナル
  - AlertManager: LINE Push による通知（クールダウン付き）
  - Streamlit ダッシュボード（読み取り専用で monitoring DB を表示）
- Portfolio（純粋関数群）
  - 候補選定、重み計算、リスク調整（セクターキャップ、レジーム乗数）、株数決定（単元丸め、aggregate capping）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で実行）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - ニュースを LLM でスコアリングして ai_scores に格納
  - ETF + マクロニュースを合成して市場レジーム判定を実施
- ユーティリティ
  - process priority / cpu affinity 設定ユーティリティ
  - 簡易レポート生成ツール（paper_verification_report）

---

## 必要条件（依存ライブラリの例）

- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- （その他、ExecutionEngine の Broker 実装に依存するパッケージがある場合があります）

インストール例（pip）:
```
pip install duckdb psutil requests openai streamlit
```

requirements.txt がある場合はそれを利用してください（本コードベースには同梱されていません）。

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定（.env またはシステム環境変数）
   - 自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. データディレクトリを作成
```
mkdir -p data
```
6. 初回実行時に必要な DB やテーブルはスクリプト内で自動作成・マイグレーションされます（monitoring の init_monitoring_db 等）。

---

## 主要な環境変数

（.env に記述する例を示します）

必須（使用する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...

運用切替/DBパス:
- KABUSYS_ENV=development|paper_trading|live
  - paper_trading の場合、Execution は MockBroker を使用し、paper 用 SQLite に記録されます
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- DUCKDB_PATH=data/kabusys.duckdb

OpenAI:
- OPENAI_API_KEY=...

通知 / 監視:
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

その他:
- PAPER_FILL_MODE=instant|partial|never|reject  (paper_trading の約定挙動)
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=1  (Execution 起動時に kill.flag を自動削除)
- MONITOR_POLL_INTERVAL=60  (monitoring ポーリング間隔 秒、run_monitoring で使用)
- LOG_LEVEL=INFO|DEBUG|...

注意: Settings モジュールは OS 環境変数→.env.local→.env の順で読み込みます（自動ロードを利用する場合）。

---

## 起動 / 使い方

以下は代表的な起動方法です。

1. 監視ポーリングを起動（常駐プロセス）
```
python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- monitoring は KABUSYS_ENV にかかわらず、settings.sqlite_path（デフォルト: data/monitoring.db）を使用します
- プロセス優先度を "high" に設定しようとします（権限によりスキップされる場合あり）

2. Execution を起動（発注エンジン）
```
python -m kabusys.run_execution
```
- KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込み、MockBrokerClient を使用します。live の場合は本番ブローカーを使用します。
- 起動時に優先度を "high" に設定します
- 終了時に SQLite / DuckDB をクローズします

3. Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB パスを明示
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

4. Streamlit ダッシュボード（監視 DB の読み取り専用ビュー）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- ダッシュボードは読み取り専用で、監視 DB が存在しない場合はエラーを表示します

5. AI系（ニューススコア / レジーム判定）
- ai.news_nlp.score_news(), ai.regime_detector.score_regime() は OpenAI API キー（OPENAI_API_KEY）を必要とします。呼び出しは Python API 経由で行います（スクリプト化はされていませんが、関数呼び出しで利用可能）。

---

## 注意点 / 運用メモ

- run_monitoring は監視用 DB（settings.sqlite_path）を使います。monitoring は本番監視 DB を参照する想定で、KABUSYS_ENV に依存しません。
- run_execution は KABUSYS_ENV が `paper_trading` のときに paper 用 DB に切り替えます（本番 DB と完全分離）。
- kill.flag による停止機構:
  - KillSwitch が条件を満たすと data/kill.flag を書き込み、ExecutionEngine 停止を促します。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を削除できます（クリアのオンスタート挙動）。
- OpenAI 呼び出しはネットワークエラー/429/5xx を考慮してリトライやフェイルセーフ設計になっていますが、API キーが未設定だと例外を投げます（呼び出す側でハンドリングを）。
- DuckDB のバージョンや executemany の空リスト挙動に対する対応が実装に散見されます。DuckDB の互換性に注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - run_monitoring.py                — SystemMonitor ポーリング起動
  - run_execution.py                 — ExecutionEngine 起動
  - utils/
    - process_priority.py            — プロセス優先度 / CPU affinity
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite 永続層（system_status / trade_logs / positions / risk_logs / dashboard）
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
    - (その他ブローカー / engine / repository 等)
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

（上記は主要ファイルのみの抜粋です。実際のリポジトリには更に細分化されたモジュールが含まれます）

---

## 例: .env（簡易サンプル）

```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=xxxxxxxx
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
PAPER_FILL_MODE=instant
MONITOR_POLL_INTERVAL=60
KILL_FLAG_CLEAR_ON_START=1
```

---

## さらに詳しく

- 各モジュールの docstring に設計方針・前提・返却値の仕様が細かく記載されています。実装を拡張・運用する際は該当モジュールの docstring を参照してください。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）は Research / AI 機能で参照されます。必要に応じて ETL パイプラインで事前にデータ投入してください。

---

以上が README の概要です。必要であれば「セットアップ向けの Dockerfile / systemd ユニット例」や「運用チェックリスト」「よくあるトラブルシュート」を追記します。どれを追加しますか？