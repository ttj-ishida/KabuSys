# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした小型フレームワークです。  
ポートフォリオ構築、取引実行、監視・アラート、ファクター計算、LLM を使ったニュースセンチメント評価などのコンポーネントを含みます。

## 概要（Project overview）
- 自動売買エンジン（ExecutionEngine）とそれを補助する OrderManager / Reconciler。
- 動作監視（SystemMonitor / TradeMonitor / RiskMonitor）およびアラート送信（LINE）。
- DuckDB を用いた研究向けファクター計算、特徴量解析ユーティリティ。
- OpenAI を利用したニュース NLP（センチメント）および市場レジーム判定モジュール。
- Paper Trading モード（本番 DB と分離）、検証レポート生成ツール、Streamlit ダッシュボード。

## 主な機能（Feature list）
- Execution
  - ブローカー抽象化（実環境 / モックを切替可能）
  - 注文状態管理、発注/キャンセル、再起動時リコンシリエーション
  - リスク管理（ポジション上限、ドローダウン等）
- Monitoring
  - CPU / メモリ / ディスク / プロセス監視
  - 注文滞留・約定異常の検出
  - ダッシュボード用の永続化（SQLite）
  - Kill Switch（条件成立時に flag ファイルを書き ExecutionEngine を停止）
  - LINE へのプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（監視ビュー）
- Portfolio/Strategy Utilities
  - 候補選定、重み計算（等重・スコア重み）
  - セクター制約適用、レジーム乗数
  - 銘柄ごとの株数決定（単元取引対応、aggregate cap）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン・IC 計算・統計サマリ等
- AI
  - ニュース集約 → OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores へ保存
  - マクロニュース + ETF MA200 を使った市場レジーム判定

## 前提（Requirements）
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード使用時）
- SQLite は標準ライブラリで利用
- （オプション）LINE Messaging 用トークン、OpenAI API キー

※ 実行環境に応じて OS のプロセス優先度設定に制約（権限）がある点に注意。

## インストール（Setup）
1. ソースをクローン / 展開し、プロジェクトルートに移動します（pyproject.toml または .git が存在する想定）。
2. 仮想環境を作成・有効化：
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS)
   - .venv\Scripts\activate (Windows)
3. 必要なパッケージをインストール（pip）:
   - pip install duckdb psutil requests openai streamlit
   - 実行に必要な追加パッケージは環境に応じて調整してください。
4. データディレクトリを作成：
   - mkdir -p data

## 設定（Configuration）
- 環境変数（主なもの）
  - KABUSYS_ENV: 実行環境。'development' | 'paper_trading' | 'live'（デフォルト: development）
    - paper_trading の場合は MockBrokerClient を使用し、Paper 専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知に使用
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading 用の約定挙動（instant|partial|never|reject）
  - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト: 60）
  - PID_FILE_PATH, KILL_FLAG_PATH など（デフォルトは data 以下）
- .env / .env.local は自動読み込みされます（プロジェクトルート探索）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

## 初期 DB（監視用）作成
- Monitoring は起動時に必要なテーブルを自動作成します（init_monitoring_db）。特別な初期化手順は不要です。
- DuckDB の prices_daily / raw_financials 等のテーブルはユーザー側で準備してください（研究・AI モジュールはこれらを参照します）。

## 使い方（Usage）

基本的な起動コマンド（プロジェクトルート、仮想環境有効化済み）:

- 監視プロセス起動（SystemMonitor の単体ポーリング開始）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可（例: MONITOR_POLL_INTERVAL=30）

- 実行エンジン起動（取引エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると Paper Trading モード（モックブローカー + data/paper_trading.db）で起動します。

- 停止 / 強制停止
  - 停止フラグ: data/stop_requested.flag が存在すると run_monitoring/run_execution は停止します。
  - Kill Switch: 監視ロジックが DRAWDOWN 等の条件を満たすと data/kill.flag に理由を書き込み、Execution 側で検出して停止できます。
  - 実行開始時に KILL_FLAG_CLEAR_ON_START=1 を設定しておくと自動で kill.flag をクリアできます（Settings を参照）。

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- Streamlit ダッシュボード（監視ビュー）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を読み取り専用で開きます。MonitoringEngine を先に起動してください。

- AI / Regime スコアリング（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）。

## 動作のポイント / 注意事項
- Paper Trading は実運用 DB と明確に分離されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証を行う設計ですが、API レート制限や失敗時はフェイルセーフとしてスコア 0 やスキップを行います。
- Process priority の設定は psutil を使用します。権限や OS によっては設定に失敗することがあります（警告ログのみ）。
- DuckDB を使う機能は prices_daily / raw_financials / raw_news 等のテーブルが整備されている前提です。データ準備は利用者側で行ってください。

## ディレクトリ構成（Directory structure）
（src/kabusys 以下の主要ファイル / パッケージを抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数読み込み・Settings
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（ETF + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度 / PID チェック
    - trade_monitor.py — 注文滞留 / 約定価格異常
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor の実行ループ
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py — 注文作成 / 発注フロー
    - reconciler.py — 起動時リコンシリエーション
    - （その他ビジネスロジック、ブローカーファクトリ等）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数算出・スケールダウン・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - monitoring/
    - ... （上記）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

- data/
  - monitoring.db (デフォルト SQLITE_PATH)
  - kabusys.duckdb (デフォルト DUCKDB_PATH)
  - paper_trading.db (Paper Trading 用)
  - execution.pid, stop_requested.flag, kill.flag などの実行制御ファイル

## 開発メモ / 参考
- 環境変数読み込みは .git または pyproject.toml を基準にプロジェクトルートを探索します。CI / テストで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のクエリは大量データ処理を想定して最適化されていますが、テーブルスキーマやデータ量に応じてインデックスやクエリ範囲を調整してください。
- OpenAI 呼び出し部分はテスト容易性のため内部 API 呼び出し関数を patch して差し替え可能です（ユニットテストでのモック推奨）。

---

必要であれば、README にインストール用の requirements.txt の例、.env.example のテンプレート、よくあるトラブルシューティング（OpenAI API エラー、psutil の権限問題、Streamlit の接続エラー）等を追記します。どの情報を追加しますか？