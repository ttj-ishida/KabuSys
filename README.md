# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買システム「KabuSys」のコードベースです。
本ドキュメントはプロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめた README です。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール化された自動売買フレームワークです。

- シグナル → 注文発行 → リスク管理 → 約定・ポジション管理までの実行エンジン
- システム稼働監視・アラート送信（LINE）
- Paper Trading（モックブローカー）を用いた検証とレポート生成
- DuckDB / SQLite を用いたデータ/ログ管理
- ニュースを LLM（OpenAI）で解析し銘柄別スコアを生成する AI モジュール
- 研究用のファクター計算 / 特徴量解析ユーティリティ

設計方針として、DB 書き込みや IO 部分は明確に切り分けられており、主要なロジック（ポートフォリオ構築、サイズ配分、レジーム判定、ファクター計算など）は純粋関数または明示的なインターフェースを持つ実装になっています。

---

## 主な機能一覧

- ExecutionEngine（発注・リスク管理・オーダー状態管理）
  - Live / Paper Trading 切り替え（KABUSYS_ENV）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - リコンシリエーション（再起動時の自動同期）
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス生存確認
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・保有数上限監視、ダッシュボード更新
  - KillSwitch: しきい値トリガで Execution を停止するフラグ write
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（read-only 表示）
- Portfolio（銘柄選定・重み付け・ポジションサイズ算定）
  - 候補選定、等金額・スコア加重、リスクベースサイズ算定、セクターキャップ、レジーム乗数
- Research（ファクター計算 / 特徴量解析）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC（スピアマン）やファクター統計
- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント集約（ai_scores 生成）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（market_regime）
- ツール
  - paper_verification_report: Paper Trading DB を元に運用バリデーションレポート生成

---

## セットアップ

前提:
- Python 3.9+（コードは型注釈に Python 3.9+ の機能を想定）
- SQLite（標準で利用可）
- DuckDB（Python パッケージ）
- インターネット接続（OpenAI 等 API 利用時）

推奨パッケージ（概略）:
- duckdb
- psutil
- requests
- openai
- streamlit

例: 仮想環境作成・依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

環境変数:
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: (必須) J-Quants API 用トークン
- KABU_API_PASSWORD: (必須) kabuステーション API のパスワード
- OPENAI_API_KEY: OpenAI を使う場合必須（ai モジュール、regime 判定 等）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager で通知する場合
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード ("instant" | "partial" | "never" | "reject")
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で参照）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等も Settings を参照

.env の自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を起点）を探索し `.env` / `.env.local` を自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

データディレクトリ:
- data/ 以下に DB や PID/flag ファイルが作成されます（存在しない場合はプロセスが作成します）。

---

## 使い方（主なコマンド例）

注意: すべてのコマンドはプロジェクトルート（pyproject.toml 等がある場所）で実行してください。

1. 監視ループ起動（Monitoring）
- 監視プロセスを起動します。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
```bash
python -m kabusys.run_monitoring
# 例: 30秒間隔でポーリングしたい場合
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
※ run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path (Settings.sqlite_path) を使用します。

2. 実行エンジン起動（ExecutionEngine）
- 実際の発注を行うエンジンを起動します。KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に完全分離して記録します。
```bash
# Paper Trading
KABUSYS_ENV=paper_trading python -m kabusys.run_execution

# Live 実行
KABUSYS_ENV=live python -m kabusys.run_execution
```
- 実行は別スレッドで行われ、data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成するか、KillSwitch 経由で停止します。

3. Paper Trading 検証レポート
- Paper Trading DB から稼働率・注文成功率・レイテンシ等を集計するレポートを生成します。
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

4. Streamlit ダッシュボード（監視）
- 監視用ダッシュボード（read-only）を起動します。
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

5. AI / レジーム判定・ニューススコア
- ai モジュールはプログラムから直接呼び出します（OpenAI API キーが必要）。
  - 例: kabusys.ai.score_news(conn, target_date, api_key=...)
  - 例: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

6. ログ / フラグ操作
- 強制停止フラグ: data/kill.flag を書くことで ExecutionEngine に停止指示を送る仕組み（KillSwitch）。
- 起動時に kill.flag をクリアする設定（KILL_FLAG_CLEAR_ON_START）を有効にできます（Settings.kill_flag_clear_on_start）。

---

## 重要な設計・運用上の注意

- Paper Trading は本番 DB と完全分離する設計になっています（Settings.paper_sqlite_path を使用）。
- Monitoring（run_monitoring）は Settings.sqlite_path（本番 monitoring DB）を参照します。環境にかかわらず本番の監視 DB を使う点に注意してください。
- OpenAI など外部 API に依存する部分はフェイルセーフ設計（API エラー時にスコアを 0 にフォールバックする等）になっていますが、API キーの設定は必須です。
- プロセス優先度設定（高優先）や PID 管理を行います。権限によっては優先度変更が失敗する場合があります（警告ログのみ）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと目的の概観です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動ロード）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
- src/kabusys/execution/
  - execution_engine.py — 実行エンジン（起動/セッション管理）
  - order_manager.py — 発注・状態遷移管理（OrderManager）
  - order_repository.py — 注文 DB レイヤ（SQLite）
  - reconciler.py — 再起動時の照合・復旧
  - broker_factory.py / broker_api.py — ブローカー抽象化（Mock/実ブローカー切替）
  - order_record.py — 注文レコード / 状態列挙
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite 監視ログテーブル初期化 + DB ラッパ
  - system_monitor.py — システム状態 / データ鮮度チェック
  - trade_monitor.py — 注文滞留 / 約定異常チェック
  - risk_monitor.py — ドローダウン・保有数監視
  - kill_switch.py — 停止フラグ書き込みユーティリティ
  - alert_manager.py — LINE 送信ユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — 監視用 UI（Streamlit）
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・投下資金管理・単元丸め
  - risk_adjustment.py — セクター制約・レジーム乗数
- src/kabusys/research/
  - factor_research.py — ファクター計算（Momentum/Value/Volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- src/kabusys/ai/
  - news_nlp.py — ニューステキストを OpenAI でスコア化して ai_scores に書込
  - regime_detector.py — ETF MA + マクロニュースで市場レジームを判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/ (実行時に生成される想定)
  - monitoring.db (Settings.sqlite_path のデフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
  - kabusys.duckdb (DuckDB データ)
  - execution.pid, stop_requested.flag, kill.flag など

---

## サンプル .env（最小例）
.env に以下を設定しておくと便利です（実運用では秘匿管理を徹底してください）。
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
PAPER_FILL_MODE=instant
MONITOR_POLL_INTERVAL=60
```

---

## 開発・拡張のポイント（短評）

- DuckDB を使ったファクター計算 / リサーチロジックは SQL と Python を組み合わせる設計で高速に集計可能です。
- AI 周り（news_nlp, regime_detector）は OpenAI の応答フォーマット依存のため、外部 API の変更に注意してください（レスポンス検証ロジックあり）。
- Execution / Broker 抽象でモックと実ブローカーの切替が可能に設計されており、Paper Trading と Live の分離が強固です。
- 監視は冪等性やフェイルセーフ設計（例: API 失敗時はログを残して継続）を考慮してあります。

---

補足や具体的な使い方（例: Settings の追加設定、Broker 実装方法、テストの書き方など）について要望があれば、さらに詳しいガイドを作成します。