KabuSys — 日本株自動売買システム
================================

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買／バックテスト／リサーチを想定した小規模なシステム群です。本リポジトリには以下の主要機能が含まれます。

- 注文発行・状態管理・リコンシリエーション（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk モニタ）とアラート送信（LINE）
- Paper Trading 用の分離された DB と検証レポート出力
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- DuckDB を用いた因子計算・研究用モジュール（ファクター計算、将来リターン、IC 等）
- ニュース NLP を使った銘柄センチメント評価と市場レジーム判定（OpenAI API 経由）
- Streamlit による監視ダッシュボード

主要機能一覧
-------------
- Execution
  - 注文作成・送信・同期（OrderManager / OrderRepository / Reconciler）
  - Paper Trading 時は MockBroker を用いて data/paper_trading.db に記録（本番 DB と分離）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ
  - KillSwitch: 閾値超過時に data/kill.flag を書き込み ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Push API による通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用）
- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計サマリー
  - 候補選定、等重・スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算
- AI (OpenAI)
  - ニュース記事から銘柄ごとにセンチメントを算出し ai_scores に格納（kabusys.ai.score_news）
  - マクロニュース × ETF（1321）の MA200 乖離を組み合わせた市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- ツール
  - paper_verification_report: Paper Trading DB から運用指標（稼働率、約定率、レイテンシ等）の検証レポートを生成

要件（概略）
-------------
- Python 3.9+
- SQLite（OS 標準）
- パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- ネットワークアクセス（OpenAI / LINE API を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン／チェックアウトする。

2. 仮想環境を作成して有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）。
   - pip install duckdb psutil requests openai streamlit

   ※ 実プロジェクトでは requirements.txt / poetry 等で依存管理してください。

4. データディレクトリの準備（必要に応じて）。
   - デフォルトの DB 等は data/ 以下に作られます。存在しない場合はアプリ側で作成されます。

5. 環境変数の設定（.env ファイルを推奨）
   - .env または .env.local をプロジェクトルートに置くと自動読み込み（OS 環境変数優先）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（抜粋）
---------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に必要
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant | partial | never | reject） デフォルト: instant
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（主なコマンド）
---------------------
- 監視ループの起動（常時ポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（1秒以上）

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録
  - 実行中に data/stop_requested.flag を作成すると起動を阻止／停止する仕組み
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine 停止を促します

- Streamlit 監視ダッシュボード（読み取り専用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH を上書き）

- AI / 研究用 API の呼び出し（Python から直接）
  - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - Research:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

停止・フラグ関連
----------------
- data/stop_requested.flag: run_monitoring / run_execution が監視する外部停止フラグ（存在するとループ終了）
- data/kill.flag: KillSwitch が書き込む停止指示ファイル（Execution 側で検出して停止させる）
- 実行前に kill.flag をクリアしたい場合は削除してください。KillSwitch クラスは clear() を提供します。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                       — パッケージ定義（バージョン）
- config.py                         — 環境変数 / 設定ローダ
- run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                  — ExecutionEngine 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py                  — SQLite による監視ログ永続化層（init / MonitoringDB）
- system_monitor.py                 — システム・データ鮮度監視
- trade_monitor.py                  — 注文滞留・約定異常監視
- risk_monitor.py                   — ドローダウン・ポジション監視
- kill_switch.py                    — kill.flag 書き込みユーティリティ
- alert_manager.py                  — LINE 通知（クールダウン付き）
- monitoring_engine.py              — 各モニタを束ねるエンジン
- streamlit_dashboard.py            — Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py                  — 発注管理（OrderStateMachine 外向 API）
- reconciler.py                     — 起動時リコンシリエーション
- ...（ブローカー・リポジトリ等の実装ファイル）

src/kabusys/portfolio/
- portfolio_builder.py              — 候補選定・重み計算
- position_sizing.py                — 株数計算・リスク制限・単元丸め
- risk_adjustment.py                — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py                — ファクター計算（momentum/value/volatility）
- feature_exploration.py            — 将来リターン / IC / summary utilities

src/kabusys/ai/
- news_nlp.py                       — ニュース記事→銘柄センチメント（OpenAI）
- regime_detector.py                — マクロニュース×MA200 でレジーム判定

src/kabusys/tools/
- paper_verification_report.py      — Paper Trading 検証レポート生成 CLI

src/kabusys/utils/
- process_priority.py               — プロセス優先度 / CPU affinity ユーティリティ

設定・設計上の注意点
-------------------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml 基準）が検出される場合、自動で .env / .env.local を読み込みます。
  - OS 環境変数が優先されます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB 分離:
  - paper_trading モードでは paper_trading 用の SQLite が使われ、本番用 monitoring DB と完全分離します。
- OpenAI 利用:
  - API 呼び出し部分はエラーに対してフェイルセーフ（リトライ・0.0 フォールバック等）が組み込まれていますが、APIキーは必須です（ない場合は例外になります）。
- 権限:
  - set_process_priority や cpu_affinity はプラットフォームや権限によって動作しない場合があり、その場合は警告ログを出してスキップします。
- ログ:
  - run_* スクリプトは logging.basicConfig(level=logging.INFO) を使っています。詳細ログを出したい場合は LOG_LEVEL 環境変数やコードの調整で変更してください。

トラブルシューティング（よくある質問）
---------------------------------------
- DB が見つからない・読み込み失敗:
  - data/*.db のパスを確認し、ファイルの存在とパーミッションをチェックしてください。Streamlit は読み取り専用 URI を使います。
- Execution が起動しない:
  - data/stop_requested.flag または data/kill.flag の存在を確認。存在する場合は削除または理由を確認してください。
- OpenAI / LINE への接続失敗:
  - ネットワーク、API キー、トークン、アクセス権限やレート制限を確認してください。

拡張・開発メモ
---------------
- DuckDB を用いたデータ解析 / ファクター計算は SQL と Python の組み合わせで実装されています。大量データでのパフォーマンス改善には DuckDB の最適化やインデックス設計を検討してください。
- ポートフォリオ構築やポジションサイズのロジックは将来的に銘柄別 lot サイズ・手数料モデルを受け取るよう拡張可能です。
- テスト環境では .env.local を使って実 DB を汚さないように設定してください。

ライセンス / 著作権
------------------
（ここにライセンス情報を入れてください。README に明記が必要な場合は追記してください。）

以上

--- 
必要なら README の英語版、より詳細な環境変数一覧、またはデプロイ/サービス化（systemd / Docker / containerization）用の手順も作成します。どれを優先しますか？