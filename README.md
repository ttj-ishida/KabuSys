README
=====

概要
----
KabuSys は日本株向けの自動売買フレームワークです。本リポジトリは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）: ブローカーと連携して発注・状態管理を行う
- 監視（Monitoring）: プロセス・システムリソース・データ鮮度・注文挙動をポーリングしてログ／アラートを生成
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制約等の純粋関数群
- リサーチ／ファクター: モメンタム／バリュー／ボラティリティ等のファクター計算・統計ユーティリティ
- AI モジュール: ニュースの LLM によるセンチメント評価（OpenAI）や市場レジーム判定
- ツール類: Paper Trading の検証レポート生成、Streamlit ダッシュボードなど
- ユーティリティ: 設定読み込み、プロセス優先度設定など

特徴
----
- 開発 / Paper Trading / Live を環境で切り替え可能（KABUSYS_ENV）
- Paper Trading と実運用データベースは分離（paper_trading 用 DB を利用）
- 監視ログは SQLite に永続化し、DuckDB を用いた分析との併用を想定
- OpenAI を用いたニューススコアリングはバッチ・リトライ・検証を備えた堅牢実装
- Streamlit による監視ダッシュボードとコマンドラインレポートが利用可能

セットアップ
-----------

前提
- Python 3.10 以上（typing の union 演算子 (A | B) を使用）
- SQLite（標準で付属）
- DuckDB（Python パッケージ）
- ネットワークアクセス（ブローカー API / OpenAI / LINE 等を利用する場合）

推奨手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests streamlit openai
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 環境変数設定
   - プロジェクトルートに .env または .env.local を作成すると自動ロードされます（CWD に依存せず .git / pyproject.toml を基準に検出）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（一部）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 sqlite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL / LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID など

初回起動（DB テーブル作成）
- monitoring の起動スクリプトや run_execution は内部で init_monitoring_db() を呼び、必要なテーブル／マイグレーションを行います。手動での初期化は不要です。

使い方
------

実行エンジン（本番・Paper）
- 実行: python -m kabusys.run_execution
  - KABUSYS_ENV により Paper Trading（mock ブローカー + data/paper_trading.db）と Live を切替えます。
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority を使用）。
  - 依存コンポーネント（BrokerClient, OrderRepository, RiskManager, Reconciler 等）を初期化して ExecutionEngine を実行します。

監視プロセス
- 実行: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 監視は環境にかかわらず本番 sqlite_path を使用します（monitoring DB は常に共有される想定）。

監視ダッシュボード（Streamlit）
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは read-only モードで DB を開き、Overview / Positions / Orders / System を表示します。

Paper Trading 検証レポート
- コマンドライン:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または: python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - レポートは稼働率、注文成功率、送信率、レイテンシなどをまとめ、 PASS/FAIL 判定を行います。

AI 関連（ニューススコアリング / レジーム判定）
- プログラムから呼び出す例:
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
  - どちらも DuckDB 接続（duckdb.connect(...)）と target_date を渡します。OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定します。
- 注意点:
  - LLM 呼び出しはリトライやレスポンス検証を行い、失敗時は安全なフォールバック（0.0 等）で継続します。

ユーティリティ
- 環境設定: kabusys.config.Settings を通じてアプリ全体で一貫した設定検証を行います。.env の自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われます。
- プロセス優先度/CPU affinity: kabusys.utils.process_priority.set_process_priority / set_cpu_affinity

注意点 / 運用メモ
- Paper Trading は本番 DB と分離されています（settings.is_paper を使って paper_sqlite_path を使用）。
- monitoring の init は冪等であり、マイグレーション（カラム追加）も含みます。
- kill.flag による ExecutionEngine のシャットダウン制御があります（KillSwitch）。Execution 側は kill.flag を検出して安全に停止する設計です。
- Settings クラスは多くの環境変数にバリデーションを持ち、不正値は例外になります。デプロイ前に .env を確認してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ 等）

- config.py
  - 環境変数/.env 読み込み、Settings クラス（バリデーション含む）

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading を分離）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- execution/
  - order_manager.py — 発注フローと状態遷移の外向き API
  - reconciler.py — 起動時の注文/ポジション照合と自動復旧
  - order_repository.py, order_record.py, broker_api.py, broker_factory.py など（ブローカー抽象化）

- monitoring/
  - monitoring_db.py — SQLite ベースの永続化層（テーブル定義・読み書き）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常の検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイルで Execution を止める仕組み
  - alert_manager.py — LINE Push API 送信とクールダウン管理
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算（等重/スコア重み）
  - position_sizing.py — 株数算出・ロット丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — momentum / value / volatility 計算（DuckDB ベース）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ

- ai/
  - news_nlp.py — raw_news を LLM で集計・スコアリングし ai_scores に書き込み
  - regime_detector.py — ETF MA とマクロニュースを使った市場レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - __init__.py

- utils/
  - process_priority.py — OS 間差分を吸収したプロセス優先度/affinity 設定

補足／開発者向け情報
--------------------
- ログレベルは Settings.log_level で検証されます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- .env パースはシェル形式に近い実装で、シングル／ダブルクォートや export プレフィックスに対応しています。
- DuckDB を使うモジュール群（research, ai）は大量データを高速に処理する設計です。DuckDB ファイルの配置やアクセス権に注意してください。

問い合わせ / 貢献
-----------------
- バグ報告や改善提案は Issue にお願いします。プルリクエスト歓迎です。

以上が本コードベースの概要と基本的な利用方法です。必要であれば .env.example のテンプレートやデプロイ手順（systemd / Docker / k8s）についても追記します。どの項目を優先して詳述しますか？