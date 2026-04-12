# KabuSys

日本株向け自動売買システムの一部（モニタリング、実行エンジン、ポートフォリオ構築、リサーチ、AI補助など）の実装コードベースです。本 README はローカル開発／実行に必要な概要、セットアップ手順、使い方、ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は次の機能群を持つモジュール群から構成されます。

- 実行エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）
- モニタリング（System / Trade / Risk）とアラート送信（LINE）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- リサーチ（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 開発 / 運用ツール（paper trading 検証レポート、Streamlit ダッシュボード 等）

設計方針の要点：
- DuckDB / SQLite を用いたローカルデータストア
- 環境変数 / .env による設定
- Paper Trading は本番データと完全分離（専用 SQLite）
- OpenAI を用いる機能は API キー必須でフェイルセーフ処理あり

---

## 主な機能一覧

- 監視（monitoring）
  - システム状態（CPU / メモリ / ディスク、実行プロセス存在確認）
  - 注文滞留・約定異常検出
  - ドローダウン / ポジション上限監視とキルスイッチ（フラグファイルで Execution 停止指示）
  - LINE への通知（AlertManager）
  - Streamlit による監視ダッシュボード表示

- 実行（execution）
  - ブローカークライアントの抽象（本番 / モック切替）
  - OrderManager による注文状態管理とクラッシュ耐性（リコンシリエーション）
  - RiskManager によるレート制限、ドローダウン抑制など

- ポートフォリオ（portfolio）
  - 候補選定（スコア順）
  - 等金額 / スコア加重配分
  - リスク制御（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（リスクベース・重みベース）

- リサーチ（research）
  - Momentum / Value / Volatility 等のファクター計算（DuckDB 上で SQL + Python）
  - 将来リターン計算、IC（Information Coefficient）など統計解析ユーティリティ

- AI（ai）
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini）でセンチメント化し ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成して market_regime を決定

- ツール
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit ダッシュボード（監視用）

---

## 前提 / 必要環境

- Python 3.10 以上（型ヒント・注釈の使用に依存）
- 必須パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- 標準ライブラリ：sqlite3, logging, datetime, os, pathlib など

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil requests openai streamlit
```

（プロジェクトに requirements.txt / setup.py がある場合はそちらを使ってください。）

---

## 設定（環境変数と .env）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みはデフォルトで有効ですが、テストなどで無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。

主要な環境変数（抜粋）:
- KABUSYS_ENV: 起動モード。`development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading` の場合、Execution は別途指定の paper DB を使います
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の箇所あり）
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- SQLITE_PATH: monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: Execution PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill switch フラグファイル（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: paper_trading の mock fill 振る舞い（instant/partial/never/reject）

サンプル .env（最低限例）:
```
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_PASSWORD=your_kabu_password
JQUANTS_REFRESH_TOKEN=your_jquants_token
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン
2. 仮想環境の作成と依存パッケージのインストール（上記参照）
3. `.env` を作成（.env.example を参照できる場合はそれを基に）
4. データディレクトリ作成
```
mkdir -p data
```
5. DuckDB / SQLite の初期スキーマは各エントリポイントが自動で作成します（init_monitoring_db を実行）。

注意:
- Paper Trading を使う場合は `KABUSYS_ENV=paper_trading` を指定すると paper 用 SQLite を使います（`PAPER_TRADING_SQLITE_PATH` でパス変更可）。
- OpenAI を使う機能は `OPENAI_API_KEY` が必須です。

---

## 使い方（主要スクリプト）

パッケージとしてモジュールを直接実行する形で提供されています。プロジェクトルートから実行してください。

- 監視ループを起動（SystemMonitor のポーリング）
```
python -m kabusys.run_monitoring
```
オプション・環境変数:
- MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満または無効値は 60 秒にフォールバック。
- Monitoring は環境にかかわらず production 用の sqlite_path（SQLITE_PATH）を使用します。

- 実行エンジンを起動（ExecutionEngine）
```
python -m kabusys.run_execution
```
- Paper Trading モードで起動する例:
```
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
Paper Trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）にログが記録され、本番 DB と分離されます。

- Streamlit 監視ダッシュボード
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
`--db` オプションで読み取り専用で開く DB を指定可能（既定: data/monitoring.db）。MonitoringEngine を先に起動してデータを作成してください。

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または db を指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```
出力は標準出力に検証レポートを表示します。評価基準（稼働率、成功率、P95 レイテンシなど）はスクリプト冒頭の閾値で定義されています。

- AI 関連（news_nlp / regime_detector）
  - これらは関数 API（DuckDB 接続と target_date を渡す）として利用できます。実行時には OPENAI_API_KEY が必要です。
  - 例（簡易）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## 実行時のポイント / 注意点

- process priority 設定:
  - run_monitoring / run_execution の最初でプロセス優先度を "high" に設定します（psutil を利用）。権限やプラットフォームにより設定が失敗することがありますが、ログに警告が出てスキップされます。
- Kill Switch:
  - RiskMonitor が条件に合致すると `KILL_FLAG_PATH`（デフォルト data/kill.flag）に理由を書き込みます。ExecutionEngine は起動時にこのファイルを見て停止などの対応を行います（設定により起動時にフラグをクリア可能）。
- DB マイグレーション:
  - monitoring DB の init 関数は必要なカラムが無い場合に ALTER を行いマイグレーションを試みます（冪等実行可能）。
- Paper Trading:
  - Paper 環境では MockBrokerClient が利用される想定で、実際のブローカー呼び出しは行いません。`PAPER_FILL_MODE` により約定挙動を制御します。
- OpenAI API:
  - RateLimit / ネットワーク等の一時エラーはリトライ戦略がありますが、最終的に失敗した場合は処理をスキップして続行します（フェイルセーフ設計）。
- DuckDB / SQLite 接続:
  - DuckDB は分析用（prices_daily, raw_financials 等）、SQLite は監視ログ／注文履歴等に使われます。ファイルパスは Settings から取得します。

---

## ディレクトリ構成（主なファイル）

以下は主要モジュールとファイルの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env ロードと Settings
  - run_monitoring.py  — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py   — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - monitoring/
    - monitoring_db.py
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
    - (Broker / Engine / Repository 関連モジュール)
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
  - utils/
    - process_priority.py

（詳細はリポジトリの src/kabusys 配下を参照してください）

---

## 開発・デバッグのヒント

- 設定確認:
  - Settings クラスは `KABUSYS_ENV` やその他環境変数のバリデーションを行います。起動時のログに KABUSYS_ENV が出力されるので確認してください。
- ログ:
  - 各モジュールは logging を活用しています。`LOG_LEVEL=DEBUG` で詳細ログを確認できます。
- DB 読み取り専用起動（Streamlit）:
  - streamlit_dashboard は SQLite を URI + `?mode=ro` で開きます。MonitoringEngine が DB を作成している必要があります。
- テスト:
  - OpenAI 呼び出し等は内部関数を patch（モック）しやすい設計になっています（テスト時は API 呼び出しを差し替えてください）。

---

## ライセンス / 貢献

この README はプロジェクト内のソースコード（docstring や実装）に基づいて作成されています。実際の配布や外部 API キー取り扱い、商用利用は各自のポリシーに従ってください。貢献や問題報告はリポジトリの Issue / PR フローを利用してください。

---

必要があれば、以下を追加で作成できます：
- .env.example のサンプルファイル
- requirements.txt（実際の依存バージョン固定）
- 実行フロー図 / シーケンス図
- 各コンポーネントの詳細な API ドキュメント（関数シグネチャ・入出力例）

ご希望があれば作成します。