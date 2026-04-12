# KabuSys — README

日本株向け自動売買／リサーチ基盤の一部を抜粋したコードベースの README です。本リポジトリは取引エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、LLM ベースのニューススコアリング等のモジュールで構成されています。

注意: 本 README は提供されたソースコードに基づく説明です。実運用や本番接続を行う際は必ず設定・安全性・法令順守を確認してください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド・主要スクリプト）
- 環境変数 / 設定
- 実行時の挙動・注意点
- ディレクトリ構成（ファイル一覧と説明）

---

## プロジェクト概要

KabuSys は日本株自動売買・リサーチ用のモジュール群です。主に以下の役割を持ちます。

- 注文作成・送信・状態管理（Execution）
- リコンシリエーション（起動時自動復旧）
- リスク管理（ドローダウン・ポジション上限）
- 監視（システム状態、注文滞留、約定異常、監視 DB 保存）
- アラート送信（LINE Push）
- Paper Trading 用モック、検証レポート生成
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算）
- DuckDB を用いたファクター計算・研究用ユーティリティ
- OpenAI を用いたニュース NLP（銘柄センチメント）・レジーム判定

設計方針として、DB への永続化、DuckDB によるデータ処理、OpenAI API 呼び出しはフェイルセーフ（失敗時はスキップ・フォールバック）を重視しています。

---

## 主な機能一覧

- Execution
  - OrderManager: 注文の作成、送信、状態同期
  - BrokerClientFactory からブローカークライアントを切り替え可能（paper_trading は Mock）
  - Reconciler: 起動時に OrderSent を突合して自動復旧
  - RiskManager: 注文・ポジション投入上限などのチェック（設定あり）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID の監視、データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション数の監視、dashboard 更新
  - MonitoringEngine: 上記を束ねたポーリングエンジン
  - AlertManager: LINE Push によるアラート送信（クールダウン管理）
  - Streamlit ダッシュボードで監視情報を可視化
- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算
  - Portfolio construction（候補選定・重み付け・ポジションサイズ）
- AI
  - news_nlp: raw_news を OpenAI に送って銘柄ごとのセンチメントを ai_scores に書込
  - regime_detector: ETF の MA とマクロニュースの LLM センチメントを合成して market_regime を判定
- Tools
  - paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシなどの検証レポートを生成

---

## セットアップ手順

以下はローカルで動かすための基本手順例です。実際のプロジェクトでは requirements.txt/poetry などを用意して管理してください。

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ 本コードでは他のパッケージが使われる可能性があります。requirements を用意している場合はそちらを使用してください。

4. データディレクトリを作成
   - mkdir -p data

5. 環境変数または .env ファイルを用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込み（既存 OS 環境変数は上書きされません）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
     - その他必要に応じて LINE のトークンなど

例: .env の一部
```
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pass
JQUANTS_REFRESH_TOKEN=...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
PAPER_FILL_MODE=instant
```

---

## 使い方（主要スクリプト）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は Settings の sqlite_path（監視 DB）に接続します（環境に関わらず本番 sqlite_path を使用）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）を用います。本番 DB と分離されています。
  - 起動時にプロセス優先度を `high` に設定しようとします（psutil を使用）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` で DB パスを上書き可能（デフォルト: data/paper_trading.db）
  - レポートは稼働率・注文成功率・送信率・レイテンシ等を出力します

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## 環境変数 / 設定（主なもの）

- KABUSYS_ENV: 起動環境。valid: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker の挙動（instant | partial | never | reject）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag（停止指示）ファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各種外部 API 用トークン（必須設定にされているメソッドあり）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（設定がない場合は通知しない）

Settings モジュールはプロジェクトルートの `.env` / `.env.local` を自動読み込みします（OS 環境変数の保護あり）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 実行時の挙動・注意点

- run_monitoring および run_execution は起動時に set_process_priority("high") を呼び出します。権限がない等で設定できない場合は警告になります（スキップ）。
- Monitoring は監視ログを SQLite に永続化します。監視 DB は init_monitoring_db() により必要テーブルを作成・マイグレーションします（冪等）。
- Paper Trading は本番 DB と分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を用いるモジュール（news_nlp, regime_detector）は API 呼び出し中のエラー（429、タイムアウト、5xx 等）に対して指数バックオフ・リトライやフェイルセーフを実装していますが、API キーやコストには注意してください。
- KillSwitch は特定のリスク条件（ドローダウン・ポジション上限）で kill.flag を書き込むことで ExecutionEngine 停止を促します。既存 flag がある場合は冪等にスキップします。起動時に flag をクリアしたい場合は `data/kill.flag` を手動で削除するか、該当 API（内部クラスの clear）を使ってください。
- streamlit ダッシュボードは SQLite を read-only で開く設計になっています（起動時に読み取り専用 URI を使用）。監視エンジンが DB を更新している状態で読み取り可能なことを前提としています。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルの一覧と簡単な説明です。

- kabusys/
  - __init__.py — パッケージ情報（__version__ 等）
  - config.py — 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading は Mock）
  - tools/
    - paper_verification_report.py — Paper Trading DB の検証レポート生成スクリプト
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB のスキーマ作成・永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — LINE Push 通知（クールダウン付）
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 注文作成・送信・状態遷移の外向き API
    - reconciler.py — 起動時の自動復旧・突合作業
    - （その他 broker 関連、order_repository 等は該当ディレクトリ内に存在すると想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（等分・スコア重み）
    - position_sizing.py — 株数決定（risk-based / equal / score）、単元丸め、aggregate cap
    - risk_adjustment.py — セクター上限、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py — OpenAI を用いたニュースセンチメントスコアリング（ai_scores へ書込）
    - regime_detector.py — ETF MA とマクロニュースでレジーム判定し DB に書込
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 開発・拡張のヒント

- DuckDB を用いるモジュール（research, ai/regime_detector 等）はコネクションを引数で受け取る設計のため、テスト時にメモリ DB を用いた切替が容易です。
- OpenAI 呼び出し部はテスト時にパッチしてモック可能（内部で _call_openai_api を分離しているため）。
- MonitoringDB はスキーマ変更時に簡易マイグレーションロジックを含みます（例: カラム追加チェック）。

---

## ライセンス・免責

この README は与えられたソースコードの解析に基づく概要です。実運用やマネタイズを目的とする場合は、著作権・利用規約・API 利用規約（取引所・LINE・OpenAI 等）や金融法規制を確認し、必要に応じて専門家に相談してください。

---

必要であれば、README に以下の拡張を追加します：
- requirements.txt / poetry/pyproject.toml に記載する依存リストの提案
- より詳細な .env.example（テンプレート）
- 各コンポーネントのシーケンス図や起動フロー図
- テスト実行方法（ユニットテストの例）

どれを追加しましょうか？