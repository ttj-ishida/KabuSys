# KabuSys

日本株向けの自動売買／リサーチ／監視フレームワーク（プロトタイプ）。  
このリポジトリは取引実行ロジック、監視・アラート、ポートフォリオ構築、ファクター計算、LLM ベースのニュース解析などを含みます。

## 概要
KabuSys は以下を目的としたモジュール群です。

- 注文の作成・送信・再同期（Execution）
- 実行状況・システム状態・リスク指標の継続監視（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数算出・リスク制御）
- DuckDB を用いた時系列データに基づくファクター計算・リサーチ
- OpenAI を用いたニュースセンチメント（AI モジュール）
- Paper Trading（模擬取引）と検証レポートの生成
- Streamlit を用いた監視ダッシュボード

設計上、実働系（live）と検証系（paper_trading）は DB を分離して運用できるようになっています。設定は環境変数（.env）で管理し、自動的にルートの .env/.env.local を読み込みます（無効化可能）。

---

## 主な機能一覧
- Execution
  - Broker クライアントの抽象化とファクトリ（本番 / モック）
  - OrderManager: 注文作成・送信・状態同期のワークフロー
  - Reconciler: 再起動時の注文・ポジション整合処理
  - リスク管理、約定管理等（OrderRepository 等と連携）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 滞留注文・異常約定検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: フラグファイルで Execution 停止シグナル
  - AlertManager: LINE へプッシュ通知（クールダウン実装）
  - MonitoringEngine: 各種 Monitor を束ねたポーリングループ
  - monitoring.db（SQLite）への永続化レイヤ
  - Streamlit ダッシュボード（read-only で monitoring.db を参照）
- Portfolio
  - 候補選定、等重・スコア重み配分
  - セクター集中制限、レジーム乗数
  - 単元丸め・リスクベースの株数決定（lot_size サポート）
- Research
  - DuckDB を用いたファクター計算（Momentum / Value / Volatility 等）
  - 特徴量探索（将来リターン、IC、統計サマリー）
- AI
  - news_nlp: raw_news をまとめて OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジーム判定
  - リトライ・レスポンス検証やスコアクリッピングなど堅牢性考慮
- Tools
  - paper_verification_report: Paper Trading DB に対する検証レポート生成

---

## セットアップ手順

前提
- Python 3.9+（タイプヒントで union 型等を利用しているため推奨）
- SQLite（標準ライブラリ）
- 必要パッケージ（以下参照）

推奨: 仮想環境を作成してインストールしてください。

例（venv + pip）:
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

（プロジェクトによっては追加の依存があるかもしれません。setup.py/pyproject.toml があればそちらを参照してください。）

環境変数（最低限の例）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション接続パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV: 起動環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- PAPER_TRADING_SQLITE_PATH: paper_trading DB（paper_trading 時）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

プロジェクトルートに `.env` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

例 `.env`（最小例）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
LINE_CHANNEL_ACCESS_TOKEN=xxxx...
LINE_USER_ID=Uxxxxxxxxxxxxx
```

---

## 使い方（主要なコマンド）

- 監視ループの起動（SystemMonitor 単体を永続化）
```bash
python -m kabusys.run_monitoring
# MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）
```
- 実行エンジン（ExecutionEngine）の起動
```bash
python -m kabusys.run_execution
# KABUSYS_ENV=paper_trading の場合はモックブローカーを使い、data/paper_trading.db を使用します
```

- Streamlit ダッシュボード（監視 DB を読み取り専用で表示）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート出力
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db オプションで DB パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数も使用）
```

- AI モジュール（プログラムから）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意点:
- 実行開始直後にプロセス優先度を high に設定しようとします（set_process_priority）。権限がない場合は警告が出てスキップされます。
- Monitoring は常に「本番用の monitoring.sqlite_path」を使用する設計になっています（環境にかかわらず監視用 DB はデフォルト path を使用）。

---

## 重要な環境変数・設定一覧（抜粋）

- KABUSYS_ENV: "development" | "paper_trading" | "live"
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、デフォルト 60）
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（data/paper_trading.db）
- DUCKDB_PATH: DuckDB のファイル（data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- PAPER_FILL_MODE: paper_trading の約定動作（instant | partial | never | reject）
- PID_FILE_PATH: 実行プロセスの PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag（デフォルト data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

設定読み込み:
- .env / .env.local がプロジェクトルートにあれば自動読み込み（OS 環境変数が優先）
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定管理（Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングスクリプト（エントリポイント）
  - run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — monitoring DB スキーマ + MonitoringDB ラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — kill.flag の読み書き（Execution 停止指示）
    - alert_manager.py — LINE push 通知ラッパー
    - monitoring_engine.py — 各モニタをまとめるエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 注文ワークフローの表層 API
    - reconciler.py — 再起動時の注文／ポジション照合
    - (その他: broker_factory, order_repository などが想定)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金割当
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング
    - regime_detector.py — レジーム判定（ETF + マクロニュース）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

---

## データベース（既定のパス）
- 監視 SQLite: data/monitoring.db（Settings.sqlite_path）
- Paper Trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading の場合）
- DuckDB: data/kabusys.duckdb

monitoring_db.init_monitoring_db() は冪等的にテーブルとインデックスを作成します。既存 DB に対する軽微なスキーママイグレーション処理（列追加）も含まれます。

---

## 運用上の注意
- Production（live）で稼働させる場合は KABUSYS_ENV を適切に設定し、DB のバックアップ・権限・監視を整えてください。
- OpenAI API 呼び出しを行うモジュールは API 失敗に強い実装（リトライ／フェイルセーフ）ですが、API 利用料・レート制限に留意してください。
- kill.flag による停止は冪等実装ですが、実稼働では運用ルールを明確にしてください（誰がいつ書くか等）。
- process priority / cpu affinity の適用は環境によっては権限不足で失敗します（ログに WARNING）。

---

## 開発者向け補足
- Settings クラスは .env の自動ロードを行います。テスト時に自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続はリサーチ／AI モジュールで直接 SQL を実行します。prices_daily / raw_financials / raw_news 等のテーブル構造に依存します。
- テストやモック化:
  - news_nlp と regime_detector は内部で OpenAI 呼び出しを行う関数を分離しているため、ユニットテストではパッチしやすく設計されています（例: unittest.mock.patch）。
- ロギングは標準 logging を利用。起動スクリプトは基本的に INFO レベルで起動します（Settings.log_level を参照）。

---

README では主要な点をまとめました。その他の細かい実装や API の挙動は各モジュールの docstring を参照してください。必要であれば、セットアップ（依存の固定化 / requirements.txt 作成）やデプロイ手順（systemd / supervisor 用ユニット例）などのドキュメントを追加できます。どの情報を優先的に追加しましょうか？