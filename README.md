# KabuSys — README

概要
----
KabuSys は日本株の自動売買および研究用コンポーネント群のサンプル実装です。本リポジトリは以下の機能を持つモジュール群を含みます。

- 注文管理・実行エンジン（ExecutionEngine）
- 監視（Monitoring）とアラート（LINE）
- ポートフォリオ構成 / ポジションサイジング / リスク調整
- ファクター計算・リサーチユーティリティ（DuckDB ベース）
- ニュース NLP を用いた銘柄センチメント（OpenAI API 統合）
- Paper Trading 用検証レポート生成ツール
- Streamlit による監視ダッシュボード

主な特徴
-------
- 環境分離: KABUSYS_ENV に応じて paper_trading（テスト用 DB）と live を分離
- フェイルセーフ設計: リトライ・バックオフや部分失敗時の保護（DB 書き込みや AI 呼び出しでの保護）
- モジュール分割: 監視 / 実行 / ポートフォリオ / リサーチ / AI が独立しており、単体で実行・テスト可能
- DuckDB を使った時系列ファクター計算（prices_daily / raw_financials テーブル参照）
- LINE によるアラートと kill.flag による ExecutionEngine 停止シグナル機能

要件
----
- Python 3.10+
- ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード起動時）
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI や LINE API を使用する場合）

インストール例（仮）
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合:
pip install duckdb psutil requests openai streamlit
```

セットアップ
----------
1. プロジェクトルートに .env ファイルを配置（任意）
   - config.py はプロジェクトルート（.git または pyproject.toml を起点）から .env/.env.local を自動で読み込みます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
2. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - SQLITE_PATH: 監視用 SQLite DB のパス（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
   - PID_FILE_PATH, KILL_FLAG_PATH など（デフォルトは data 以下）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。run_monitoring で使用、デフォルト 60）
   - LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

例 .env（簡易）
```
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
OPENAI_API_KEY=sk-xxx
KABU_API_PASSWORD=your_kabu_password
JQUANTS_REFRESH_TOKEN=your_jquants_token
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

使い方（コマンド）
-----------------

1. ExecutionEngine を起動（本番/ペーパー共通エントリポイント）
- 通常起動（環境に応じて paper_trading 用 DB を自動選択）
```bash
python -m kabusys.run_execution
```
- point:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、デフォルトで `data/paper_trading.db` に記録され本番 DB と分離されます。
  - 実行開始時にプロセス優先度を High に設定します（psutil による処理。権限がない場合は警告）。

2. Monitoring を起動（ポーリング監視ループ）
```bash
python -m kabusys.run_monitoring
```
- 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
- 監視は常に本番用の sqlite_path を使用する設計になっています（KABUSYS_ENV にかかわらず）。

3. Paper Trading 検証レポート生成
- 単発で Paper Trading DB の解析レポートを生成します。
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- 出力には稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を含み、いくつかの閾値で PASS/FAIL を判定します。

4. Streamlit 監視ダッシュボード
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを提供します。

5. AI 関連（ニュース NLP / レジーム判定）
- ニュースセンチメント付与（ai モジュール）:
  - プログラムから直接呼び出す:
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key=...)
  - またはモジュール関数をインポートして使用してください。
- レジーム判定（market regime）:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - OpenAI API の呼び出しに失敗した場合はフェイルセーフとして macro_sentiment=0.0 で続行します。

注意点・運用上のポイント
-----------------------
- Paper Trading は本番 DB とは分離されます。KABUSYS_ENV=paper_trading を使用することで mock ブローカーと専用 DB に切り替わります。
- kill.flag（デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送る設計です（KillSwitch）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）から行われます。必要に応じて .env.local を使って優先上書きが可能です。
- OpenAI や LINE の API キーが未設定のときは、それら機能はスキップまたはフェイルセーフで継続します（ログ警告が出ます）。
- process priority（優先度）設定や CPU affinity は psutil の権限制約により適用できないことがあります。失敗時は警告ログでスキップされます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                   — 環境変数 / .env ロード処理および Settings
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py                — ニュースセンチメント (OpenAI 統合)
  - regime_detector.py         — 市場レジーム判定 (MA + マクロセンチメント)
  - __init__.py

- monitoring/
  - monitoring_db.py           — SQLite テーブル定義 + DB 層ラッパー
  - system_monitor.py          — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py           — 注文滞留・約定異常監視
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - kill_switch.py             — kill.flag 書き込み管理
  - alert_manager.py           — LINE Push 通知
  - monitoring_engine.py       — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py     — Streamlit ダッシュボード

- execution/
  - reconciler.py              — 起動時リコンシリエーション
  - order_manager.py           — 注文ステートマシン（外向け API）
  - (その他 order_repository / broker_factory 等は実装ファイルが想定される)

- portfolio/
  - portfolio_builder.py       — 候補選定 / 重み計算
  - position_sizing.py         — 株数決定・スケールダウン・単元丸め
  - risk_adjustment.py         — セクター制限・レジーム乗数
  - __init__.py

- research/
  - factor_research.py         — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - __init__.py

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
  - __init__.py

- utils/
  - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ

（注意）上記はこのリポジトリの主要ファイルの抜粋です。実運用では broker 実装や order_repository、data pipeline 等の追加モジュールが必要です。

貢献・開発
----------
- 新しい機能を追加する場合はモジュールごとに単体テストを用意してください（特にポートフォリオ計算やファクター計算は純粋関数でのテストが容易です）。
- OpenAI 等外部 API を呼ぶ箇所はモック可能な設計（ラッパー関数や依存注入）になっています。CI では環境変数を差し替え or モックしてテストしてください。

ライセンス
---------
リポジトリにライセンスファイルを追加してください（本 README にはライセンス情報を含みません）。

補足
----
- 詳細な設計指針や理論的背景（PortfolioConstruction.md / StrategyModel.md 等）はコメントや関数ドキュメンテーションに記載された参照に従って実装されています。プロダクション運用前に十分な検証を行ってください。