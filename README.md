# KabuSys

日本株自動売買システムのコアライブラリ（リサーチ / ポートフォリオ構築 / 実行エンジン / 監視 / AI補助）。  
このリポジトリはシステムの各機能をモジュール化しており、ローカル SQLite / DuckDB を用いたデータ保持、LINE での通知、OpenAI を用いたニュースセンチメントやレジーム判定などをサポートします。

---

## プロジェクト概要

- 目的: 日本株の自動売買アルゴリズムを安全に実行するための基盤機能群を提供する。
- 構成: リサーチ（ファクター計算・特徴量解析）、ポートフォリオ構築（候補選定・重み付け・株数算出）、実行（Order 管理・リコンシリエーション）、監視（プロセス・注文・リスク監視）、AI（ニュース NLP / レジーム判定）など。
- 挙動の方針:
  - 本番/ペーパートレードを環境変数 `KABUSYS_ENV` で切り替え（`development` / `paper_trading` / `live`）。
  - Paper Trading は本番 DB と分離して `data/paper_trading.db`（デフォルト）を使用。
  - 環境変数は `.env` / `.env.local` を自動で読み込む（無効化可能）。

---

## 主な機能一覧

- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン計算・IC 計算・統計サマリー
- ポートフォリオ構築
  - 候補選定（スコア順）、等配分・スコア加重配分
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ算出（単元丸め、リスクベース配分、キャッシュ制約）
- 実行エンジン（Execution）
  - ブローカーインターフェース抽象化（本番 / モック切替）
  - OrderManager / OrderRepository による状態遷移管理
  - Reconciler による起動時の自動復旧（OrderSent 照合、ポジション差分検知）
- 監視
  - SystemMonitor: CPU/メモリ/ディスク、プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 注文滞留 / 約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限検出、dashboard の永続化
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: 指定条件で `data/kill.flag` を書き込み ExecutionEngine 停止シグナル
  - Streamlit ダッシュボード（監視可視化）
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメントスコア化と ai_scores への書き込み
  - レジーム判定（ETF ma200 とマクロニュースの LLM スコア合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（注文成功率・レイテンシ等の指標）

---

## 必要条件

- Python 3.10+
- DuckDB
- sqlite3（標準ライブラリ）
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- その他（開発環境に合わせて pip で個別インストール）

例（pip）:
```
pip install duckdb psutil requests openai streamlit
```

実際のプロジェクトでは requirements.txt / poetry 等で依存管理してください。

---

## セットアップ手順

1. リポジトリをクローンしてソースを配置（本説明はソースが `src/` 以下にある前提）。
2. Python 仮想環境を作成・有効化:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール:
   ```
   pip install -r requirements.txt
   ```
   requirements.txt が無い場合は上記の主要パッケージを個別インストールしてください:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
4. 環境変数設定:
   - プロジェクトルートに `.env` を置けば自動読み込みされます（デフォルトでは OS 環境 > .env.local > .env の優先順）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
5. データディレクトリ作成:
   ```
   mkdir -p data
   ```
   デフォルト DB ファイルは `data/monitoring.db`, `data/kabusys.duckdb`, `data/paper_trading.db`（paper_trading 時）などです。

---

## 主要な環境変数

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の設定箇所あり）
- KABU_API_PASSWORD: kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE: paper trading の約定挙動（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite DB パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

設定の自動読み込み:
- プロジェクトルートに `.env` / `.env.local` がある場合、自動で読み込みます。
- 自動読み込みを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## 使い方（起動・主要コマンド）

基本的にソースが `src/` にある場合は PYTHONPATH を通してモジュール実行します。

- 監視ループ起動（SystemMonitor の周期的実行）:
  ```
  PYTHONPATH=src python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（デフォルト 60）。
  - 監視は常に Settings による sqlite_path（本番 DB）を参照します。

- 実行エンジン起動（ExecutionEngine）:
  ```
  PYTHONPATH=src python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と完全分離）。
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします（停止フラグ機構）。

- Streamlit 監視ダッシュボード:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - デフォルトは `data/monitoring.db`（読み取り専用で接続）。

- Paper Trading 検証レポート生成:
  ```
  PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - オプション `--db` で DB パスを上書き可能。
  - 指標: 稼働率 / 注文成功率 / 送信率 / P95 レイテンシ など。

- AI 機能（ニュース NLP / レジーム判定）:
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）。
  - 外部呼び出しはライブラリ API (`kabusys.ai.score_news`, `kabusys.ai.regime_detector.score_regime`) を使ってスクリプトやスケジューラから呼べます。

- 停止・キルフラグ
  - `KillSwitch` は `data/kill.flag` を書くことで ExecutionEngine に停止シグナルを出します（ExecutionEngine 側は定期チェックして停止）。
  - 監視停止要求（手動）として `data/stop_requested.flag` を作成すると run_monitoring/run_execution のループが終了・起動を中止します。

---

## 開発・デバッグのヒント

- Settings は自動で .env を読み込みます。テスト時に自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- DuckDB / SQLite のファイルは `data/` 以下に置くことを想定しているため、ファイルパス権限に注意してください。
- プロセス優先度の設定は psutil によるため権限不足（Linux の負の nice 値など）で失敗する可能性があります。ログで警告が出ますが処理は継続します。
- OpenAI 呼び出し箇所はリトライロジック（429 / タイムアウト / 5xx 対応）を備えていますが、API 負荷やコストに注意してください。
- 複数プロセスで DB を扱う場合は sqlite/duckdb の同時書き込みに関する挙動に注意が必要です（設計上、monitoring 用 sqlite は軽量なトランザクションしか行わない想定です）。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py            — ニュースを OpenAI でスコア化するロジック
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化ラッパ
    - system_monitor.py      — CPU/メモリ/ディスク / データ鮮度 / PID チェック
    - trade_monitor.py       — 注文滞留・約定異常検出
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の生成 / 管理
    - alert_manager.py       — LINE Push 通知
    - monitoring_engine.py   — 複数 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py       — 発注フローの上位 API
    - reconciler.py          — 起動時リコンシリエーション
    - （その他 execution 関連実装ファイルが存在）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - position_sizing.py     — 株数計算・スケーリング
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / ボラ / バリュー等
    - feature_exploration.py — 将来リターン / IC / 統計処理
  - data/                    — （実行時に使用する DB等を置く想定）
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## 追加メモ

- Paper Trading モードは本番 DB と完全分離する設計です。ペーパートレード検証を行う場合は `KABUSYS_ENV=paper_trading` を設定してください。
- ログ出力は各モジュールで logging を使用しています。必要に応じて logging.basicConfig の設定やハンドラを追加してください。
- DB スキーマのマイグレーション処理（軽微なカラム追加）は monitoring_db.init_monitoring_db に実装されています。

---

もし README に含めたい追加情報（インストール方法の詳細、CI やテスト手順、実際に必要な requirements.txt の内容など）があれば教えてください。必要に応じて README を拡張します。