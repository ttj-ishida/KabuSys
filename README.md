# KabuSys

日本株自動売買システムの軽量モジュール群。ポートフォリオ構築、発注・リスク制御、監視、研究（ファクター計算）、
およびニュース NLP / レジーム判定（OpenAI）などの機能を含みます。

この README はコードベース（src/kabusys 以下）を前提に、概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要な責務を持つモジュール群で構成されています。

- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- 注文管理・Execution Engine（ブローカー API を介した発注、再起動時のリコンシリエーション）
- リスク管理（ドローダウン・ポジション上限などの検出・ログ）
- 監視（システム状態、注文滞留、約定異常の検出、kill flag 発行）
- 研究用モジュール（DuckDB を使ったファクター計算・特徴量解析）
- ニュース NLP / レジーム判定（OpenAI を用いたセンチメント集約）
- ツール（Paper Trading の検証レポート生成、Streamlit ダッシュボード）

設計方針の一部：
- DuckDB / SQLite を分析・監視用 DB として利用（発注はブローカー API）
- 本番（live）と Paper Trading（paper_trading）で DB を分離し、Paper 環境は本番 DB に影響しない
- 外部 API 呼び出し（OpenAI 等）は明示的な API キーが必要でフェイルセーフ処理あり
- 自動ロード可能な .env 機構（Settings モジュール）を備える

---

## 主な機能一覧

- portfolio/
  - 銘柄候補選定（select_candidates）
  - 等金額／スコア加重配分（calc_equal_weights, calc_score_weights）
  - リスク調整（セクター上限 apply_sector_cap, レジーム乗数 calc_regime_multiplier）
  - 株数決定（calc_position_sizes） — 単元株単位・aggregate cap・スケールダウン対応
- execution/
  - OrderManager（注文状態遷移・重複防止）
  - Reconciler（起動時の注文・ポジション突合）
  - Broker クライアントファクトリ（paper_trading 時は MockBrokerClient を使用）
- monitoring/
  - SystemMonitor（CPU/メモリ/ディスク・実行プロセス・データ鮮度監視）
  - TradeMonitor（滞留注文、約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - AlertManager（LINE Push 通知、クールダウン管理）
  - KillSwitch（kill.flag により ExecutionEngine 停止シグナル）
  - MonitoringDB（SQLite に監視ログを永続化、スキーマ自動作成／マイグレーション）
  - Streamlit ダッシュボード（監視 DB を read-only で可視化）
- research/
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン、IC、統計サマリー）
- ai/
  - news_nlp.score_news（raw_news を集約して OpenAI で銘柄ごとのセンチメントを ai_scores に書き込み）
  - regime_detector.score_regime（ETF MA とマクロ記事の LLM センチメントを合成してレジーム判定）
- tools/
  - paper_verification_report（Paper Trading DB を集計して検証レポートを標準出力へ）
- ユーティリティ
  - process_priority（クロスプラットフォームでプロセス優先度・CPU affinity 設定）
  - config.Settings（.env 自動読み込み、環境変数ラッパー）

---

## セットアップ手順（ローカル開発向け）

以下は一般的な手順です。プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を優先してください。

1. Python 環境
   - 推奨: Python 3.9+（実装で typing の記法等を使用）
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate   （Windows: .venv\Scripts\activate）

2. 依存パッケージ（代表例）
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて）pip install typing_extensions など

3. プロジェクトルートに .env を用意（任意）
   - .env.example がある場合は参考にしてください（このリポジトリのルートに .env 自動ロード機能あり）
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 必須環境変数（代表）
   - JQUANTS_REFRESH_TOKEN — (必須) J-Quants API 用トークン
   - KABU_API_PASSWORD — (必須) kabuステーション API パスワード
   - OPENAI_API_KEY — OpenAI を使用する場合（news_nlp / regime_detector）
   - PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject）。デフォルト "instant"
   - KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL — ログレベル（DEBUG|INFO|...）, デフォルト INFO
   - SQLITE_PATH / DUCKDB_PATH — DB ファイルパス（デフォルト data/monitoring.db、data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を有効にする場合

5. データディレクトリ
   - data/ 配下に SQLite/duckdb の DB ファイルや pid/flag が作られます。必要なら作成してください。
   - 監視起動時にスキーマは自動作成されます（init_monitoring_db 呼び出し）。

---

## 使い方（主要スクリプト）

以下はよく使うエントリポイントと実行方法の例です。

- ExecutionEngine 起動（発注処理）
  - python -m kabusys.run_execution
  - 挙動:
    - Settings.env によって paper_trading では PAPER_TRADING_SQLITE_PATH を使い、MockBroker を使用して本番 DB と分離
    - プロセス優先度を high に設定（set_process_priority）
    - duckdb 接続も使用
    - 終了時に DB 接続をクローズ

- SystemMonitor ポーリング起動（監視プロセス）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書き（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視は常に本番 DB を見る設計）
    - プロセス優先度を high に設定
    - SystemMonitor.check_once() を定期実行して system_status 等へ記録

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH を上書き）
  - 出力: 標準出力に集計レポート（稼働率、注文成功率、P95 レイテンシ等）

- Streamlit ダッシュボード（監視 DB を可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用モードで DB を開き、Overview / Positions / Orders / System タブを表示

- AI 関連（ニューススコア・レジーム判定）
  - kabusys.ai.score_news（プログラムから呼ぶ API）
    - OpenAI API キーを渡すか OPENAI_API_KEY を環境変数で設定
    - raw_news / news_symbols / ai_scores テーブルを利用
  - kabusys.ai.regime_detector.score_regime
    - 同様に API キー必須（環境変数経由でも可）
  - 注意: OpenAI 呼び出しは費用が発生します。API レスポンスや失敗時のフェイルセーフ（0.0 フォールバック）実装あり

---

## 重要な設定 / 環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注は MockBrokerClient、DB は PAPER_TRADING_SQLITE_PATH に分離
- SQLITE_PATH: data/monitoring.db（監視用 / デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb（分析用 / デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定シミュレーション）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行 PID / kill flag のパス（デフォルト data/execution.pid, data/kill.flag）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 用の必須トークン
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env の自動ロードを無効化（テスト等で使用）

Settings の実装は .env の自動読み込み（.env → .env.local）を行い、OS 環境変数を保護します。プロジェクトルートの判定は .git または pyproject.toml を探して行われます。

---

## 注意点 / 運用上の留意点

- Paper Trading は本番 DB から分離される設計ですが、設定ミスで DB パスを誤ると影響が出るので .env を慎重に扱ってください。
- OpenAI を使うモジュールは API コストが発生します。API キーは安全に管理してください。
- Monitoring は常に本番 sqlite_path を参照してログするため、監視プロセスの実行環境は本番 DB にアクセスできることを確認してください。
- kill.flag を使った停止は冪等（既に存在する場合は再書き込みしない）です。必要に応じて ExecutionEngine 側で起動時にフラグを消去する挙動があります（設定による）。
- process priority / cpu affinity の設定は OS によって振る舞いが異なります。権限がない場合は警告を出してスキップします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env 読み込み・Settings
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

src/kabusys/portfolio/
- portfolio_builder.py     — 候補選定・重み計算
- position_sizing.py       — 株数決定（risk_based / equal / score）
- risk_adjustment.py       — セクター制限・レジーム乗数
- __init__.py

src/kabusys/execution/
- order_manager.py
- reconciler.py
- (その他ブローカー関連・order_repository などは同ディレクトリに存在する想定)

src/kabusys/monitoring/
- monitoring_db.py         — SQLite スキーマ定義 / CRUD ヘルパー
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- monitoring_engine.py     — 各 Monitor を束ねるエンジン
- alert_manager.py         — LINE Push
- kill_switch.py
- streamlit_dashboard.py   — Streamlit ベースのダッシュボード
- __init__.py

src/kabusys/research/
- factor_research.py       — momentum / volatility / value 等の DuckDB ベース計算
- feature_exploration.py   — 将来リターン・IC・統計サマリー
- __init__.py

src/kabusys/ai/
- news_nlp.py              — raw_news を LLM でスコア化して ai_scores へ書き込み
- regime_detector.py       — ETF MA + マクロセンチメントでレジーム判定
- __init__.py

src/kabusys/tools/
- paper_verification_report.py  — Paper Trading 検証レポート
- __init__.py

src/kabusys/utils/
- process_priority.py      — クロスプラットフォーム優先度 / CPU affinity 設定
- __init__.py

データベース・ログ等は標準で data/ 配下に配置されます（Settings のデフォルト参照）。

---

## 開発 / テストのヒント

- Settings はプロジェクトルートを .git または pyproject.toml から検出して .env を自動読み込みします。テストで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続を受け取る研究・AI モジュールは副作用を避ける設計になっており、ユニットテスト時は DuckDB のインメモリ DB やモックを渡すとよいです。
- OpenAI 呼び出しは _call_openai_api を wrapper 化しているため、ユニットテストでは patch / monkeypatch で差し替えることが推奨されます（コード内にその旨コメントあり）。
- MonitoringDB の init_monitoring_db は冪等でスキーマを作成・マイグレーションを行います。初回起動時に自動で必要なテーブルが作られます。

---

README でカバーしているのは高レベルな利用方法と設計上のポイントです。実際の運用前には .env の確認・DB バックアップ・OpenAI キー管理・LINE トークンの設定などを行ってください。追加でドキュメント化したい箇所（API 使用例、Engine の細かいパラメータ、OrderRepository のスキーマ等）があれば教えてください。