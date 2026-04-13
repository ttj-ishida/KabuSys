# KabuSys

KabuSys は日本株の自動売買・研究・監視を目的とした軽量なコードベースです。本リポジトリは取引実行（Execution）、監視（Monitoring）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI を使ったニュース解析（AI）などのモジュールで構成されています。

以下はこのコードベースの簡易 README（日本語）です。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株自動売買システムのコアコンポーネント（発注エンジン、監視、ポートフォリオ構成、ファクター計算、AIベースのニュースセンチメント評価など）を提供する。
- 設計方針:
  - DB 層は SQLite（監視ログ等）および DuckDB（時系列データ・リサーチ）を利用
  - 環境による挙動分岐（development / paper_trading / live）
  - Paper Trading 環境はブローカー呼び出しをモックし本番 DB と完全分離
  - LLM（OpenAI）呼び出しはフェイルセーフ・リトライやレスポンス検証を実装
  - 可能な限りルックアヘッドバイアスを排除（date.today() 等を直接参照しない設計）

---

## 主な機能一覧

- Execution
  - 発注管理（OrderManager）
  - リコンシリエーション（再起動時の同期）: Reconciler
  - RiskManager / OrderRepository 等の実装（発注ロジックは別モジュール参照）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセスの監視、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウンやポジション上限の監視・アラート記録
  - MonitoringEngine: 各 Monitor を束ねてループ実行
  - AlertManager: LINE Push による通知（オプション）
  - Streamlit ダッシュボード（読み取り専用）
- Research
  - ファクター計算: Momentum / Volatility / Value 等
  - 特徴量探索: 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースセンチメント計算（OpenAI を利用）: news_nlp.score_news
  - 市場レジーム判定: ai.regime_detector.score_regime（MA200 とマクロニュースの LLM 評価の組合せ）
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成

---

## 事前準備 / セットアップ

要件（代表）:
- Python 3.10+（型アノテーションで | を使用しているため 3.10 以上を想定）
- pip, virtualenv 等
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - openai (AI 機能利用時)
  - そのほかプロジェクトで参照するパッケージ（requirements.txt がある場合はそちらを使用）

例: 仮想環境作成とパッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests streamlit openai
# 実プロジェクトでは requirements.txt があれば `pip install -r requirements.txt`
```

データディレクトリ作成:
```bash
mkdir -p data
```

環境変数設定:
- プロジェクトは .env / .env.local を自動的に読み込む（OS 環境変数が優先）
- 自動読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- プロジェクトルートの判定は `.git` または `pyproject.toml` を基準に行う

主要な環境変数（一例）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- PAPER_FILL_MODE: paper_trading の約定モード（"instant" / "partial" / "never" / "reject"）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（"DEBUG","INFO"...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager の通知用

注意事項:
- Paper Trading 環境（KABUSYS_ENV=paper_trading）では MockBroker を使用し、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離します。
- .env の読み込み順序: OS 環境変数 > .env.local > .env（既存の OS 環境変数は上書きされない）

---

## 使い方（主要コマンド）

モジュールとして実行できます（プロジェクトルートの src を PYTHONPATH に含めて実行するか、ローカルパッケージとしてインストールしてください）。

1) 監視ループの起動（SystemMonitor をポーリング）
```bash
# モジュール実行
python -m kabusys.run_monitoring

# またはスクリプト直接
python src/kabusys/run_monitoring.py
```
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト: 60 秒）
- 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限に依存）

2) 実行エンジン（ExecutionEngine）の起動
```bash
python -m kabusys.run_execution
# または
python src/kabusys/run_execution.py
```
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading.db に記録します（本番と完全分離）
- 起動時に Process 優先度を "high" に設定します
- ExecutionEngine は duckdb と sqlite（production または paper 用）に接続します

3) Streamlit ダッシュボード（監視結果表示）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 監視 DB を読み取り専用で開いて情報表示します

4) Paper Trading 検証レポート（ツール）
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db で DB パスを指定可能
```
- PAPER_TRADING_SQLITE_PATH 環境変数が優先され、指定がなければ data/paper_trading.db を使用

5) AI (ニューススコア / レジーム判定)
- OPENAI_API_KEY を設定して以下を利用
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- API 呼び出しはレート制限や 5xx に対してエクスポネンシャルバックオフでリトライし、失敗時は安全にフォールバック（多くのケースで 0.0 として継続）

---

## 重要な挙動・運用上の注意

- Settings（kabusys.config.Settings）は環境変数を参照して動作を決定します。未設定の必須変数は ValueError を投げます。
- .env 自動ロード:
  - 自動的にプロジェクトルート（.git または pyproject.toml）から .env → .env.local を読み込みます（OS 環境変数は保護される）
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DB マイグレーション:
  - init_monitoring_db() は既存 DB のスキーマに必要カラムがなければ ALTER TABLE による追加を試みます（例: trade_logs.latency_ms, dashboard.peak_value）
- kill.flag:
  - KillSwitch により条件を満たすとファイル (設定: KILL_FLAG_PATH) を書き込み、ExecutionEngine に停止を通知する設計
  - 手動クリアはファイルの削除（または KillSwitch.clear() を呼ぶ）で行います
- 実際の本番運用（live）ではブローカー API 資格情報や資金管理の厳格な取り扱いが必要です。コード中には安全弁（リスク制御、ドローダウン検知等）が組み込まれていますが、実稼働前に十分な監査とテストを行ってください。

---

## ディレクトリ構成（抜粋）

（src/kabusys 以下の主要ファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動読み込み等）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite ベースの監視ログ永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, order_repository, risk_manager 等 — 発注・実行ロジック)
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - (data モジュールは参照されるがここに含まれているかは実装次第)

---

## サンプル .env（最低限の例）

例としてプロジェクトルートに `.env` を作成しておくと便利です（セキュリティに注意してください）:

```
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# Broker / API
KABU_API_PASSWORD=your_kabu_password
JQUANTS_REFRESH_TOKEN=your_jquants_token

# OpenAI (AI 機能を使う場合)
OPENAI_API_KEY=sk-...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## トラブルシュート / よくある質問

- 「.env が読み込まれない」
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか、プロジェクトルートが .git / pyproject.toml で特定できているかを確認してください。
- 「監視が動作しない / データが見えない」
  - monitoring.db（デフォルト data/monitoring.db）が存在するか、run_monitoring を起動して init_monitoring_db が実行されているかを確認してください。
- 「OpenAI 呼び出しが失敗する」
  - OPENAI_API_KEY が正しいか、ネットワーク・レート制限の影響を確認してください。ライブラリの互換性（openai SDK のバージョン）にも注意してください。
- 「ExecutionEngine を停止したい」
  - kill.flag（デフォルト data/kill.flag）を作成することで停止シグナルを送る設計です。kill.flag を削除して再稼働します。

---

この README はコードベースの抜粋に基づく概要ガイドです。実際の運用や拡張に際しては各モジュール（execution / monitoring / ai / research）の詳細実装を参照し、テストと検証を十分に行ってください。必要であれば README を拡張し、インストール手順（依存パッケージのバージョン固定や systemd / Docker のユニットファイル例など）を追加できます。