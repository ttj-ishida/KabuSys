# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なシステムです。本リポジトリは以下の主要コンポーネントを含みます:

- 注文実行エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository 等）
- モニタリング（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI（ニュースセンチメント / レジーム判定 - OpenAI を利用）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）
- ユーティリティ（プロセス優先度設定、設定読み込み等）

この README ではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は、取引ロジックやリスク管理を組み合わせた日本株向けの自動売買システムの骨格実装です。DuckDB / SQLite を用いたデータ管理、OpenAI を用いたニュースの NLP スコアリング、監視（稼働率・注文滞留・ドローダウン監視）や、Paper Trading 用の分離された DB を用いた検証機能を備えています。

設計方針の一部：

- DB / 外部 API へのアクセスはモジュールごとに責務を分離
- ルックアヘッドバイアス回避（date.now / today の不適切使用回避を意識）
- フェイルセーフ設計（API 失敗時は安全側にフォールバック）
- 冪等性とマイグレーションを考慮した DB 初期化

---

## 主な機能一覧

- Execution（注文生成 → ブローカー送信 → 同期 / リコンシリエーション）
  - OrderManager、Reconciler、OrderRepository など
  - paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 DB に記録
- Monitoring（常時ポーリングによる監視）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス生存/データ鮮度
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション数上限の監視とリスクログ記録
  - MonitoringEngine：各モニタの束ねとアラート送信 / kill.flag 制御
  - AlertManager：LINE Push を用いたアラート通知（オプション）
  - Streamlit ベースの監視ダッシュボード
- AI（OpenAI）
  - news_nlp.score_news：ニュースを銘柄別に集約してセンチメントスコアを ai_scores テーブルに書き込み
  - regime_detector.score_regime：ETF の MA とマクロニュースを組合せて市場レジーム判定、market_regime テーブル書込
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（スピアマン）など
- Portfolio（銘柄選定・重み付け・ポジションサイズ計算）
  - 等金額 / スコア加重 / risk-based な株数計算
  - セクターキャップ、レジーム乗数調整
- ツール
  - paper_verification_report：Paper Trading の検証レポートを生成
  - Streamlit ダッシュボード（監視用）
- ユーティリティ
  - 環境変数読み込み（.env / .env.local 自動ロード）、Settings クラス
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順

以下は開発・運用の一般的な手順例です。プロジェクトに `requirements.txt` がない場合は下記の依存パッケージをインストールしてください。

必要な Python バージョンの目安：Python 3.10 以上（型アノテーションで | 演算子を使用）

推奨パッケージ（主要依存）：
- duckdb
- psutil
- requests
- streamlit
- openai

例（仮の requirements をインストール）:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil requests streamlit openai
```

（必要に応じてテスト用モックや追加ユーティリティをインストールしてください）

.env の用意
- プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必要な主要環境変数（例）:

```
# API / 認証
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

# DB / ファイルパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag

# 動作モード / ログレベル
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO

# Paper trading 動作モード
PAPER_FILL_MODE=instant  # instant | partial | never | reject
```

注: Settings モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` を自動ロードします。環境変数が OS の環境に既にある場合は `.env` の値を上書きしません（`.env.local` は上書き可能）。

---

## 使い方（主要スクリプト）

各スクリプトは package のモジュールとして実行できます（プロジェクトルートで実行）。

1. ExecutionEngine を起動（本番 / Paper Trading）
   - 本番（live / development）:
     ```bash
     python -m kabusys.run_execution
     ```
   - Paper Trading（環境切替）:
     ```bash
     export KABUSYS_ENV=paper_trading
     python -m kabusys.run_execution
     ```
   - 実行時の挙動:
     - 起動直後にプロセス優先度を "high" に設定しようとします（権限により失敗する場合あり）。
     - Paper Trading モードでは `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に書き込まれ、本番 SQLite DB とは分離されます。
     - duckdb は `DUCKDB_PATH` に接続します。

2. Monitoring を起動（ポーリングループ）
   ```bash
   python -m kabusys.run_monitoring
   ```
   - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を変更できます（デフォルト 60 秒）。
   - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用して監視ログを記録します（`SQLITE_PATH`）。

3. Streamlit ダッシュボード（監視画面）
   ```bash
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - read-only 接続で監視 DB を参照します。MonitoringEngine が書き込んでいる SQLite を参照してください。

4. Paper Trading 検証レポート（コマンドライン）
   ```bash
   # 指定期間を与える例
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

   # DB パス指定例
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```
   - 出力は標準出力にレポートを表示します。P95 レイテンシ、稼働率、注文成功率などの指標に基づいて PASS/FAIL を判定します。

5. AI 関連（プログラムから呼び出し）
   - ニュース NLP のスコア化は関数 `kabusys.ai.score_news` を通して呼ぶことができます（DuckDB 接続を渡す）。
   - レジーム判定は `kabusys.ai.regime_detector.score_regime` を使用します。
   - これらは OpenAI API キー（`OPENAI_API_KEY`）が必要です。API 呼び出しはリトライやフォールバック処理が組み込まれています。

---

## 実運用上のポイント（注意事項）

- Monitoring は監視用の SQLite（`SQLITE_PATH`）へ書き込みます。Monitoring は常に本番の `sqlite_path` を参照する点に注意してください（Execution の paper_trading は分離されますが、Monitoring は環境にかかわらず同一 DB を使います）。
- Execution は起動時に PID ファイルを書き込み、SystemMonitor は PID ファイルを監視してプロセス生存を判定します。監視スクリプトからの stale PID 検出時はファイル削除などの処理を行います。
- KillSwitch: RiskMonitor が一定条件を満たすと `data/kill.flag` を書き込み、Execution に停止を促す仕組みがあります（冪等で書き込み）。`KILL_FLAG_CLEAR_ON_START` を使用して起動時にクリアする設定があります。
- OpenAI を利用する機能はレイテンシ・API 制限・エラーを考慮して実装されていますが、API キーの管理・コストは運用者が注意してください。

---

## ディレクトリ構成（主なファイル／モジュール）

以下は主要なファイルとディレクトリです（抜粋）。ソースは `src/kabusys` 以下に配置されています。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス：環境変数 / .env 読み込みと検証
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading をサポート）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメントの取得（OpenAI）
    - regime_detector.py   — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - __init__.py
    - monitoring_db.py     — SQLite テーブル初期化 / MonitoringDB ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py     — LINE 通知（push）
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（ブローカーインターフェース等）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py   — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (実行時に使用する DB / PID / フラグ等を配置するディレクトリ)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper_trading 用 DB)

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabu ステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視ログ用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- KABUSYS_ENV — 動作環境（development | paper_trading | live）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH, KILL_FLAG_PATH — PID / kill flag ファイルパス
- PAPER_FILL_MODE — paper_trading 時のモック約定挙動（instant / partial / never / reject）

---

## 開発・拡張のヒント

- DuckDB 接続を受け取る研究・AI モジュールは、データベーススキーマ（prices_daily / raw_financials / raw_news 等）に依存します。データの用意（ETL）とスキーマ整備が前提です。
- OpenAI を使う部分は外部依存があり、テスト時は `_call_openai_api` をモックすることで API 呼び出しを置き換えられるように実装されています（テスト容易性を考慮）。
- DB スキーマの移行は `monitoring_db.init_monitoring_db` にて簡易的に実施しています。多段階のマイグレーションが必要な場合は専用のマイグレーション管理を追加することを検討してください。
- process priority / cpu affinity の設定は psutil を利用しており、権限不足・未対応 OS に対しては警告を出してスキップする安全設計です。

---

## サポート / 貢献

- バグ報告や改善提案は Pull Request / Issue を通して受け付けてください。
- 大規模な機能追加（例: ブローカープラグインの追加、個別銘柄ごとの lot_size サポート、テストスイート整備など）は別ブランチでの実装を推奨します。

---

README に書かれている内容はコードベースの一部に基づく集約です。実行前に必須環境変数や DB の整備、OpenAI キーや外部 API の接続設定を必ず確認してください。必要であれば、プロジェクトに合わせた `requirements.txt` や `.env.example` を作成して本 README に追加することを推奨します。