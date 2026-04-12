# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・注文実行・監視・研究・AIによるニュースセンチメント評価などを含む日本株向け自動売買基盤の一部実装です。本 README はプロジェクトの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含みます。

- シグナル→ポートフォリオ構築→発注までの実行エンジン（ExecutionEngine 関連）
- 注文の管理・再同期（OrderManager / Reconciler）
- 監視基盤（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- 監視情報の永続化（SQLite を利用する monitoring_db）
- Paper Trading 向けの分離された DB と検証レポート生成ツール
- 研究用ファクター計算（DuckDB を想定）
- ニュース記事の LLM（OpenAI）によるセンチメント評価・レジーム判定
- Streamlit を用いた監視ダッシュボード

設計方針として、DB の読み書き・純粋関数（ポートフォリオ計算等）・外部 API 呼び出し（OpenAI / ブローカー）を明確に分離しており、フェイルセーフや冪等性、クラッシュ後の再同期を重視しています。

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードあり）
- 監視ループ起動スクリプト
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 監視基盤
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - kill_switch（フラグファイルで実行停止シグナル）
  - AlertManager（LINE Push による通知）
  - monitoring_db（SQLite スキーマ作成・アクセス層）
  - Streamlit ダッシュボード（リアルタイム監視表示）
- 実行関連
  - OrderManager / Reconciler / OrderRepository（SQLite）
  - BrokerFactory（本番/モックブローカー切替）
- ポートフォリオ構築
  - 候補選定、重み算出（等分配・スコア加重）、ポジションサイズ計算、セクター上限適用、レジーム乗数
- 研究（Research）
  - ファクター計算（momentum/value/volatility）
  - 特徴量探索（forward returns, IC, summary）
- AI（OpenAI）
  - news_nlp.score_news — raw_news を LLM で評価して ai_scores に保存
  - regime_detector.score_regime — ETF MA とマクロ記事を組み合わせてレジーム判定
- ツール
  - tools.paper_verification_report — Paper Trading DB から検証レポートを生成

---

## セットアップ手順

必須（最低限の手順）:

1. Python 3.9+ をインストール。
2. 仮想環境を作成・有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール。代表的な依存は以下（プロジェクトに requirements.txt があればそれを利用してください）:

   pip install duckdb psutil requests streamlit openai

   - duckdb: 価格データ等の分析に使用
   - psutil: プロセス優先度・システム情報取得
   - requests: LINE API 通信
   - streamlit: ダッシュボード
   - openai: LLM 呼び出し（news_nlp / regime_detector）

4. データディレクトリを作成（任意の場所に変更可）:

   mkdir -p data

5. 環境変数を設定（.env または .env.local をプロジェクトルートに置くと自動ロードされます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）  

   主要な環境変数（代表）:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: 必須
   - KABU_API_PASSWORD: 必須（kabuステーション API 用）
   - OPENAI_API_KEY: OpenAI を使用する場合に必須
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE通知）を使う場合
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading 用の約定モード（instant|partial|never|reject）
   - PID_FILE_PATH: 実行プロセス PID 保存パス（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

   例 (.env):
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（代表的なコマンド）

- ExecutionEngine を起動（本番/ペーパートレード判定は KABUSYS_ENV）:

  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。

- SystemMonitor のポーリングループを起動（監視プロセス）:

  python -m kabusys.run_monitoring

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - 監視は常に Settings.sqlite_path（本番用監視 DB）を使用します（paper_trading にも依存しない）。

- Paper Trading 検証レポート生成:

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

  - 出力は標準出力。期間フィルタは YYYY-MM-DD。

- Streamlit ダッシュボード（監視 UI）:

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  - 監視 DB を読み取り専用で開きます（監視プロセスが先に DB を初期化している必要があります）。

- AI モジュール（プログラム内利用）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を利用します。

注意点:
- run_monitoring は監視 DB のスキーマ（monitoring_db.init_monitoring_db）を起動時に確保します。
- run_execution は実際のブローカー／モックブローカーを BrokerClientFactory 経由で生成します。paper_trading モードでは DB を分離します。
- kill.flag (Settings.kill_flag_path) を作成すると ExecutionEngine 停止シグナルとして扱われます（KillSwitch ロジック）。

---

## 主要コンポーネント・設計メモ

- Config 自動読み込み:
  - config モジュールはプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動読み込みします。OS 環境変数は保護され、.env.local は上書きして読み込まれます。自動読み込みを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB の役割:
  - DuckDB: 時系列・ファクターデータ（prices_daily / raw_financials など）を分析・研究用途に使用
  - monitoring SQLite: system_status / trade_logs / positions / risk_logs / dashboard を保持
  - paper_trading SQLite: paper_trading モード専用の取引ログ

- フェイルセーフ/冪等設計:
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存カラムの追加マイグレーション処理を持ちます。
  - Reconciler は起動時の注文/ポジション不整合を検出・同期して安全に復旧します。
  - AI 呼び出しはリトライ/バックオフ・部分失敗時の保護を備えます。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主なファイルと役割:

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env 読み込み・Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

- src/kabusys/execution/
  - order_manager.py — 注文作成 / 送信の外向き API
  - reconciler.py — 再起動時の自動復旧（注文・ポジションの突合）
  - order_repository.py, order_record.py, broker_factory.py, execution_engine.py ...（実行関連コンポーネント）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ・読み書き層
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常の検出
  - risk_monitor.py — ドローダウン／ポジション上限監視
  - kill_switch.py — kill.flag 管理
  - alert_manager.py — LINE 通知クライアント
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit 監視ダッシュボード

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出・投資上限・丸め処理
  - risk_adjustment.py — セクター上限・レジーム乗数

- src/kabusys/research/
  - factor_research.py — ファクター計算 (momentum/value/volatility)
  - feature_exploration.py — 将来リターン・IC・統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュース記事を OpenAI でスコア化して ai_scores に書き込む
  - regime_detector.py — マクロセンチメント＋ETF MA によるレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

---

## 開発時の注意点・ヒント

- Paper Trading と Production の DB は分離されますが、監視 DB（SQLITE_PATH）は監視側で明示的に使われます。run_monitoring は常に sqlite_path を参照します。
- OpenAI 呼び出しを含む処理は API キーが必須です。テスト時は該当関数（_call_openai_api 等）をモックすることを推奨します。
- psutil によるプロセス優先度設定や CPU affinity は権限や環境に依存します。アクセス拒否は警告ログに留まり動作継続します。
- DuckDB のクエリは SQL と Python 混在で実装されています。大規模データを扱う際はリソースに注意してください。

---

## 参考コマンド例まとめ

- 仮想環境作成・依存インストール
  - python -m venv .venv && source .venv/bin/activate
  - pip install duckdb psutil requests streamlit openai

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（ペーパートレード例）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

この README はコードの主要な使い方と構成を素早く把握するための概要です。詳細な設計仕様（StrategyModel.md、PortfolioConstruction.md 等）や実装の細部はソースコードとプロジェクト内ドキュメントを参照してください。必要であれば、README に追加したい具体的な手順（デプロイ手順、systemd ユニット例、CI 設定など）を指示してください。