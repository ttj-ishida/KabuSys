# KabuSys — 日本株自動売買システム（簡易 README）

このリポジトリは日本株向けの自動売買システムの主要コンポーネント群（戦略・ポートフォリオ構築・実行エンジン・監視・研究・AI 補助機能）を含みます。以下はコードベースの概要、主要機能、セットアップ方法、使い方、ディレクトリ構成の説明です。

注意: 本 README はソースコード（src/kabusys 以下）を元に記述しています。

---

## プロジェクト概要

KabuSys は以下の機能を備えた日本株自動売買向けフレームワークです。

- ファクター計算・研究（DuckDB ベースの prices_daily/raw_financials 参照）
- ポートフォリオ構築（候補選定、重み算出、単元株丸め、ポジションサイズ計算）
- 実行エンジン（ブローカークライアント抽象化、注文管理、再同期）
- 監視（システム状態、注文滞留、リスク監視、アラート送信、kill-switch）
- AI 支援（ニュースからのセンチメント算出、レジーム判定。OpenAI API を使用）
- 開発用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計方針の一部：
- DuckDB を用いたローカル分析（外部 API に依存しない部分を可能な限り保持）
- .env ファイルを自動でロードする仕組み（必要に応じて無効化可）
- Paper Trading（テスト）用 DB を本番 DB と分離
- LLM 呼び出しは失敗時にフェイルセーフ（スコア 0 やスキップ）となる設計

---

## 主な機能一覧（抜粋）

- 設定/環境管理: `kabusys.config.Settings`
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可）
  - 環境: `development` / `paper_trading` / `live`
- Execution:
  - 起動スクリプト: `kabusys.run_execution`
  - BrokerClientFactory を経由して本番/モックブローカーを切替
  - OrderManager / Reconciler による注文発行・再同期
- Monitoring:
  - DB スキーマ初期化: `monitoring.monitoring_db.init_monitoring_db`
  - System/Trade/Risk モニタと MonitoringEngine によるポーリング監視
  - AlertManager (LINE push) による通知
  - KillSwitch による flag ファイルで ExecutionEngine 停止指示
  - Streamlit ダッシュボード（`monitoring.streamlit_dashboard.py`）
- Research:
  - ファクター計算: モメンタム / ボラティリティ / バリュー（`research.factor_research`）
  - 特徴量探索・IC 計算等（`research.feature_exploration`）
- AI:
  - ニュース NLP（OpenAI を用いた銘柄単位センチメント）`ai.news_nlp.score_news`
  - レジーム判定（ma200 + マクロセンチメント合成）`ai.regime_detector.score_regime`
- Tools:
  - Paper Trading 検証レポート: `kabusys.tools.paper_verification_report`

---

## 必要条件 / 依存パッケージ

推奨 Python バージョン: 3.10+

主な依存ライブラリ（例）:
- duckdb
- psutil
- openai
- requests
- streamlit (ダッシュボード用)
- （sqlite3 は標準ライブラリ）

例: requirements.txt を用意する場合は次のような行が必要です（実プロジェクトに合わせて調整してください）。
- duckdb
- psutil
- openai
- requests
- streamlit

インストール例:
```
python -m pip install duckdb psutil openai requests streamlit
```

---

## 環境変数（主要）

Settings クラスで参照される主な環境変数（.env に設定）:

必須（使用箇所に応じて）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/...)
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — デフォルト: data/kill.flag
- PAPER_FILL_MODE — instant | partial | never | reject（paper_trading の挙動）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager 用
- OPENAI_API_KEY — AI 機能で必要

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を検出）を基準に `.env` と `.env.local` を読み込みます。
- 自動読み込みを無効にするには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、Python 仮想環境を作成：
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存ライブラリをインストール：
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb psutil openai requests streamlit
   ```

3. .env を作成（例）:
   ファイル: `.env`（プロジェクトルート）
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_token
   KABU_API_PASSWORD=your_password
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```
   - .env.example があればそれを参考にしてください（本コードは .env.example を想定しているが実体はリポジトリに依存します）。

4. 必要ディレクトリ作成:
   ```
   mkdir -p data
   ```

5. DuckDB / SQLite の初期テーブルは起動時に自動作成されます（monitoring 用テーブルは `init_monitoring_db` で作成）。

---

## 使い方（主なコマンド）

- 監視ループを起動（SystemMonitor のポーリング）:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を変更可能（デフォルト 60）。
  - 監視は KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用します（コメント参照）。

- 実行エンジン起動（ExecutionEngine）:
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合はモックブローカーを使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に書き込まれます（本番 DB と分離）。
  - 起動時にプロセス優先度を "high" に設定する処理が実行されます（OS の権限による失敗はログに出力されるのみ）。

- Streamlit ダッシュボード（監視）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - DB を読み取り専用で開きます。MonitoringEngine を先に起動してデータを生成しておく必要があります。

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`（`--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で変更可能）
  - 出力は標準出力のテキストレポート（稼働率、注文成功率、レイテンシなど）

- AI（ニューススコア・レジーム判定）:
  - モジュール関数をプログラム上から利用:
    - `kabusys.ai.score_news` → 内部で OpenAI API を使い ai_scores テーブルへ書き込み
    - `kabusys.ai.regime_detector.score_regime` → market_regime テーブルへ書き込み
  - これらを実行するには `OPENAI_API_KEY` を設定してください。API 呼び出しは失敗時にフェイルセーフ（0 値またはスキップ）で進みます。

---

## 注意事項 / 運用メモ

- Monitoring は Settings.sqlite_path（本番 DB）を使用します（監視は環境に依存しない設計）。run_execution は `KABUSYS_ENV=paper_trading` の場合に paper_sqlite を使用して分離します。
- デフォルトで起動スクリプトはプロセス優先度を "high" に設定します。権限がない場合は警告ログになります。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI を使う機能は API レート制限やネットワークエラーに対してリトライ処理を持ちますが、キー未設定時は ValueError を送出します。
- kill.flag（デフォルト: data/kill.flag）を作成するとExecution エンジン側で停止シグナルとして扱う仕組みがあります（KillSwitch）。
- SQLite / DuckDB ファイルは `data/` 下に配置する想定です。バックアップ・レプリケーションは別途構築してください。

---

## ディレクトリ構成（主要ファイル）

※ 実際は `src/kabusys` 配下がパッケージです。以下は主要モジュールと用途の一覧です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数 / 設定管理（.env 読み込みロジック含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・制限・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — モメンタム / ボラ / バリュー等
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し・バッチ・バリデーション）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 / MonitoringDB ラッパ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
    - __init__.py
  - execution/
    - reconciler.py — 起動時リコンシリエーション（注文・ポジション突合）
    - order_manager.py — 注文状態遷移 / ブローカー連携
    - order_repository.py, order_record.py, broker_*.py ... （発注周りの実装)
  - data/（実データファイルは通常ここに配置）
    - (例) kabusys.duckdb, monitoring.db, paper_trading.db
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定

---

## 開発・テストに関する補足

- モジュールは可能な限り純粋関数や DB 抽象層で分離されています。ユニットテストでは DB 接続や OpenAI コールをモックすることでテスト可能です（例: news_nlp._call_openai_api を patch）。
- .env パーサは quote エスケープやコメントの扱いに注意した実装があります（config._parse_env_line を参照）。

---

## 最後に

この README はコードベースの要点をまとめたものです。各モジュールの詳細な挙動やパラメータは該当ファイル内の docstring / コメントをご確認ください。実運用を行う場合は DB バックアップ・権限・OpenAI 使用料・ブローカー API のレート制限等の運用面も十分に検討してください。必要であれば、README を拡張してデプロイ手順や運用 runbook を作成できます。