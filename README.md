KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買システム向けユーティリティ群です。本リポジトリには
- 監視（Monitoring）、
- 注文実行エンジン起動ロジック（ExecutionEngine 起動スクリプト）、
- ポートフォリオ構築ユーティリティ（選定・重み・サイズ計算）、
- リサーチ用ファクター計算・特徴量解析、
- AI（ニュース NLP / レジーム判定）連携、
- 検証レポート生成ツール、
- Streamlit ベースの監視ダッシュボード
などのコンポーネントが含まれます。

主な機能
--------
- SystemMonitor / TradeMonitor / RiskMonitor による定期監視とログ永続化（SQLite）。
- MonitoringEngine によるポーリングループ、アラート送信（LINE API）、
  kill.flag による ExecutionEngine 停止信号出力。
- ExecutionEngine 起動スクリプト（本番 / Paper Trading 分離）。Paper Trading 時は専用 SQLite を使用。
- 起動時の再コンシリエーション（Reconciler）で注文状態・ポジションの自動復旧。
- ポートフォリオ構築モジュール（候補選定 / 重み算出 / リスク調整 / 発注株数計算）。
- DuckDB を用いたファクター計算・研究ユーティリティ（モメンタム / ボラティリティ / バリュー 等）。
- OpenAI（gpt-4o-mini）を利用したニュースセンチメントスコアリングと市場レジーム判定。
- Paper Trading 検証レポート生成ツール（期間指定可能）。
- Streamlit ダッシュボードによる監視データの可視化。

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - インストール例:
     - pip install duckdb psutil requests openai streamlit

   （リポジトリに requirements.txt がある場合はそれを使用してください:
    pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（既存の OS 環境変数は保護されます）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
     - KABU_API_PASSWORD — （必須）kabu API 用パスワード
     - OPENAI_API_KEY — OpenAI 呼び出しを利用する場合に必要
     - KABUSYS_ENV — 起動環境: development (default) | paper_trading | live
     - SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 DB（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading の約定モード (instant|partial|never|reject)（デフォルト: instant）
     - PID_FILE_PATH, KILL_FLAG_PATH など（監視 / プロセス管理用）
   - .env の書式は shell 形式（export 対応、コメントやクォート処理あり）です。

5. データディレクトリ
   - デフォルトで data/ 下に DB や PID/flag ファイルを作成します。必要に応じてディレクトリを作成してください:
     - mkdir -p data

使い方
------
主要な実行方法（パッケージルートで実行することを想定。PYTHONPATH=src または pip install -e . を利用してください）

- 監視ループを起動（SystemMonitor 単体起動）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - 監視は Settings.env にかかわらず本番の sqlite_path を使用します（監視ログは本番 DB に記録）。

- ExecutionEngine を起動（注文実行プロセス）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading をセットすると MockBrokerClient が使われ、data/paper_trading.db に記録して本番 DB と完全分離されます。
  - 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用モードで開きます（起動済みの MonitoringEngine が DB を更新していることが前提）。

- AI 関連
  - kabusys.ai.score_news(target_date) や kabusys.ai.regime_detector.score_regime(target_date) を用いてニューススコア / レジーム判定を実行できます。OpenAI キーが必要です（OPENAI_API_KEY 環境変数、または関数引数で指定）。
  - モデルは gpt-4o-mini を想定。API のエラーは再試行やフォールバック（0.0 など）でフェイルセーフに扱います。

設定と動作の注意点
-----------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。CWD に依存しないためパッケージ配布後も安定して動作します。
- Settings クラスで環境変数の妥当性チェックを行います（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- Monitoring の初期化（init_monitoring_db）は冪等で、既存 DB に対する簡単なマイグレーション（カラム追加）を行います。
- run_monitoring はプロセス優先度を set_process_priority("high") に試みます（psutil を利用）。権限不足時は警告でスキップされます。
- ExecutionEngine 起動時は Paper Trading の場合、paper_sqlite_path を使用して本番 DB と分離します。これにより実際のブローカー接続を使わない検証が可能です。
- AI モジュールは API 呼び出し回数の管理、チャンク処理、リトライ（429/ネットワーク/5xx）などを実装しています。結果のバリデーションを行い、不正応答は無視して継続します。

ディレクトリ構成（主要ファイル）
-------------------------------
- src/kabusys/
  - __init__.py               — パッケージメタ情報
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロード含む）
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト（paper_trading 切替対応）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py        — SQLite ベースの永続化レイヤ（テーブル定義・CRUD）
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度 / pid チェック
    - trade_monitor.py        — 滞留注文 / 約定異常検出
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag を書くロジック
    - alert_manager.py        — LINE Push API 経由の通知（クールダウン管理）
    - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - order_manager.py        — 発注フロー / Order 状態遷移
    - reconciler.py           — 起動時のリコンシリエーション（注文・ポジション照合）
    - ...                     — （ブローカー API, order_repository 等は同階層に存在）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py             — ニュース記事の LLM センチメントスコアリング
    - regime_detector.py      — ETF MA と マクロ NLP を合成したレジーム判定
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

開発・運用時のヒント
--------------------
- ロギングは標準 logging を使用。コンポーネント起動前に logging.basicConfig(level=logging.INFO) が呼ばれるケースが多いです。LOG_LEVEL 環境変数で制御できます。
- デバッグ時は KABUSYS_ENV=development に設定すると本番接続や paper_trading の切替を明確にできます。
- Paper Trading の約定挙動は PAPER_FILL_MODE で細かく制御できます（instant, partial, never, reject）。
- Streamlit ダッシュボードは DB を読み取り専用（URI に ?mode=ro を付与）で開くため、監視実行中でも安全に参照可能です。
- OpenAI 関連は API 利用料が発生するため、テスト時はモック化（関数のパッチ）を推奨します（コードにもテスト向け差し替えポイントが用意されています）。

以上。追加で README に盛り込みたい情報（例: 動作例ログ、API スキーマ、テーブル定義詳細、CI / デプロイ手順など）があれば教えてください。必要に応じて英語版 README も作成します。