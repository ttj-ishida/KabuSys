KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・調査・監視を目的とした Python コードベースです。  
主な機能群は次のとおりです：

- 実行エンジン（Execution Engine）：シグナル受信 → 注文管理 → ブローカー連携、リコンシリエーション
- 監視（Monitoring）：プロセス/リソース/注文/ドローダウンの定期チェック、アラート発行、kill スイッチ
- ポートフォリオ構築（Portfolio）：候補選定・重み付け・ポジションサイズ計算・セクター制約
- リサーチ（Research）：ファクター計算、将来リターン・IC 計算、特徴量探索
- AI 補助（AI）：ニュースの NLP スコアリング（OpenAI 使用）・市場レジーム判定
- 運用ツール：Paper Trading 検証レポート生成、Streamlit ダッシュボード

主な特徴
--------
- 本番／ペーパートレードの明確な分離（paper_trading 用の専用 SQLite DB）
- DuckDB を使った時系列データ処理（prices_daily / raw_financials 等）
- LINE へのプッシュ通知機能（アラート）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（冪等性・リトライ・バリデーション実装）
- 監視用 DB（SQLite）と Streamlit ダッシュボードによる運用可視化
- stop/kill フラグによる外部からの実行停止制御

セットアップ
----------
前提
- Python 3.9+
- SQLite（標準ライブラリで利用可）
- 必要な Python パッケージ（例: duckdb, psutil, requests, openai, streamlit）

開発環境の簡単な手順例
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロダクション用の requirements.txt がある場合は pip install -r requirements.txt を使用）

3. プロジェクトルートに .env を作成（任意）
   - .env 自動読み込みが有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 必須環境変数（少なくとも実行に応じて設定）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 便利な環境変数（抜粋）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading 用の約定挙動
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）

例: .env の最小例
    JQUANTS_REFRESH_TOKEN=your_jquants_token
    KABU_API_PASSWORD=your_kabu_password
    OPENAI_API_KEY=sk-...
    KABUSYS_ENV=development

使い方
------

実行エンジン（Execution）
- 本番／ペーパー問わず engine を起動するエントリポイント:
  - python -m kabusys.run_execution
  - または python src/kabusys/run_execution.py

- 挙動補足:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、データは data/paper_trading.db に記録されます（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に同フラグを作成すると安全に停止します（例: touch data/stop_requested.flag）。
  - 実行時のプロセス優先度は set_process_priority("high") で上げようとします（権限が必要な場合あり）。

監視ループ（Monitoring）
- 監視ポーリングループ起動:
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
- 監視は Settings の sqlite_path（監視 DB）を使用します（環境にかかわらず本番 SQLite パスを参照する実装上の注意あり）。
- 停止: data/stop_requested.flag を作成すると監視ループは終了します。

Streamlit ダッシュボード
- 監視 DB を読み取り専用で可視化:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- Paper Trading の検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI（ニューススコア / レジーム）
- ニューススコア（ai_scores）生成:
  - kabusys.ai.score_news をプログラムから呼ぶ（DuckDB 接続 + target_date + OPENAI_API_KEY が必要）
- レジームスコア（market_regime）生成:
  - kabusys.ai.regime_detector.score_regime を呼ぶ（同様に DuckDB 接続 + target_date + OPENAI_API_KEY）

停止・kill フラグ
- run_execution/run_monitoring いずれも data/stop_requested.flag の存在をチェックして安全に停止します。
- KillSwitch（内部）は特定のリスク条件で data/kill.flag を書き込み、Execution を停止するトリガーとして機能します。
- 管理操作としては単にフラグファイルを作成/削除することで外部から停止・解除できます。
  - 停止要求: touch data/stop_requested.flag
  - kill フラグ作成: echo "reason" > data/kill.flag
  - kill.flag 削除（実行前クリア）: rm -f data/kill.flag

設定（Settings）と自動 .env ロード
- プロジェクトルート（.git または pyproject.toml がある場所）を基準に .env および .env.local を自動読み込みします。
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- Settings クラスは多くの設定を環境変数から取得し、値チェックを行います（例: KABUSYS_ENV, PAPER_FILL_MODE）。

注意点・運用メモ
- High 優先度設定や CPU affinity 設定は psutil を使用します。権限不足で失敗するとログに警告を出してスキップします。
- AI API 呼び出しはリトライとバリデーションを備えていますが、API キーが未設定だと例外になります。AI 機能はオプションです。
- Paper Trading は実際の注文を発注しないためロジック検証に適していますが、本番とは挙動が異なる点に注意してください。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor 起動スクリプト

パッケージ群:
- ai/
  - news_nlp.py                   — ニュース NLP（OpenAI 連携）
  - regime_detector.py            — 市場レジーム判定
- monitoring/
  - monitoring_db.py              — 監視用 SQLite 抽象化（テーブル初期化・CRUD）
  - system_monitor.py             — CPU/memory/data 鮮度監視
  - trade_monitor.py              — 注文滞留・価格異常チェック
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — kill.flag 書き込みユーティリティ
  - alert_manager.py              — LINE 通知
  - monitoring_engine.py          — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py        — Streamlit ダッシュボード
- execution/
  - order_manager.py              — 注文作成 / 状態遷移管理
  - reconciler.py                 — 再起動リコンシリエーション
  - (その他ブローカー関連・エンジン実装)
- portfolio/
  - portfolio_builder.py          — 候補選定・重み計算
  - position_sizing.py            — 株数計算・丸め・集約キャップ
  - risk_adjustment.py            — セクター上限・レジーム乗数
- research/
  - factor_research.py            — ファクター計算（momentum/value/volatility）
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート
- utils/
  - process_priority.py           — プロセス優先度 / CPU affinity 設定
- data/（運用時に生成・利用される）
  - monitoring.db                  — 監視用 SQLite（デフォルト）
  - paper_trading.db               — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading）
  - kabusys.duckdb                 — DuckDB ファイル（時系列データ）
  - stop_requested.flag            — 外部停止フラグ
  - kill.flag                      — KillSwitch 用フラグ
  - execution.pid                  — PID ファイル（ExecutionEngine）

開発・拡張ポイント
-------------------
- DuckDB スキーマ（prices_daily / raw_financials / raw_news 等）に準拠したデータ投入が必要です。
- Broker クライアントの実装次第で Execution の挙動が変わるため、本番接続は慎重に。
- AI 部分は OpenAI SDK に依存しており、API バージョンの変更に注意してください。
- ストリーミングや高頻度運用を目指す場合はプロセス優先度 / affinity / リソース監視のチューニングが重要です。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンス情報が別途ある場合はプロジェクトルートの LICENSE を参照してください。

問い合わせ・貢献
----------------
不具合報告・機能追加や改善提案はリポジトリの issue にてお願いします。Pull Request は歓迎します。

以上がこのコードベースの主要な使い方と構成の概要です。必要があれば、環境変数の全リストや具体的な実行例（systemdユニット定義、docker-compose など）を追記できます。どの部分をさらに詳しく記載しましょうか？