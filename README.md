README
======

概要
----
KabuSys は日本株自動売買プラットフォームのコアライブラリ群です。本リポジトリは以下の主要機能を備えます。

- 実行エンジン（ExecutionEngine）: ブローカーとの発注・注文管理・リスク管理・再同期（リコンシリエーション）
- 監視機構（Monitoring）: システム状態・注文滞留・リスク（ドローダウン／ポジション上限）監視、LINE通知、監視 DB 永続化
- ポートフォリオ構築ロジック: 候補選定、配分（等配分・スコア重み）、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ / ファクター計算: モメンタム、ボラティリティ、バリューなどのファクター計算および特徴量探索ユーティリティ
- AI モジュール: ニュースを OpenAI で NLP スコアリングして ai_scores に書き込む、市場レジーム判定
- ツール: Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボード等

主な特徴
--------
- 簡潔でテストしやすい純関数群（ポートフォリオ構築・リスク調整・ポジションサイジング）
- DuckDB を用いたリサーチ（prices_daily / raw_financials 等のテーブル参照）
- SQLite（monitoring.db / paper_trading.db）による監視ログ・トレードログの永続化
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / マクロセンチメント評価（フェイルセーフなリトライ実装）
- LINE によるプッシュ通知（クールダウン制御付き）
- 実行停止はフラグファイルで制御（data/kill.flag / data/stop_requested.flag）
- プロセス優先度や CPU affinity をプラットフォーム差分を吸収して設定可能

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 演算子や型ヒントを使用）
- Git（推奨）

1. リポジトリをクローン、あるいはソースを配置
   - 例: git clone <repo_url>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

4. data ディレクトリ作成
   - mkdir -p data
   - （必要であれば書き込み権限を確認）

5. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（config.py の自動ロード機能）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な箇所あり）
     - KABU_API_PASSWORD: kabuステーション API 用（必須な箇所あり）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔秒（デフォルト 60）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

6. DB 初期化
   - 監視 DB は run_monitoring または run_execution 実行時に自動でテーブルが作られます（monitoring.monitoring_db.init_monitoring_db）。

使い方
------

実行エンジン（Execution Engine）
- 本番/開発/ペーパートレードで起動する際は Settings に従い DB / Broker が決まります。
- 起動コマンド例:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- ペーパートレード時は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に書き込みます。
- エンジンの停止は data/stop_requested.flag を作成すると処理が検知して停止します（KillSwitch は data/kill.flag を書き込むことで実行停止をトリガーします）。

監視ループ（Monitoring）
- 監視ループは SystemMonitor 等を初期化し、定期的にチェックして monitoring DB に記録します。
- 起動コマンド例:
  - python -m kabusys.run_monitoring
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で変更可能（デフォルト 60 秒）。
- run_monitoring は KABUSYS_ENV に関わらず production の sqlite_path を使う設計です（監視は常に本番 DB を参照）。

Streamlit ダッシュボード
- 監視データを可視化する簡易ダッシュボードを提供します。
- 起動コマンド例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- 過去の paper_trading DB を解析して運用検証レポートを出力します。
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合: --db path/to/paper_trading.db
- 主要指標: 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を出します。

AI モジュール（ニュース NLP / レジーム判定）
- OpenAI API を利用します。環境変数 OPENAI_API_KEY を設定してください。
- ニューススコアリング:
  - kabusys.ai.score_news を呼び出して ai_scores テーブルを更新します。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime を呼び出して market_regime テーブルへ書き込みます。
- 実装は API 失敗時のフォールバック・リトライを備えています（429/タイムアウト/5xx 等）。

停止・制御フラグ（運用上の注意）
- data/stop_requested.flag: run_monitoring/run_execution が存在を検知して優雅に停止します（手動で作成することで停止を要求）。
- KillSwitch: リスク閾値を超えると data/kill.flag を書き込み、ExecutionEngine の異常停止（強制停止）をトリガーできます。
- ExecutionEngine は起動時に設定に従い PID ファイル data/execution.pid を使います。stale PID ファイルは SystemMonitor が検出して削除します。

主な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- MONITOR_POLL_INTERVAL: 監視間隔（秒、デフォルト 60）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパー用 DB（default: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用（必須設定箇所あり）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / .env 自動ロードと Settings
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- order_manager.py               — 発注ワークフロー（OrderManager）
- reconciler.py                  — 起動時の自動リコンシリエーション
- (その他: broker_factory, order_repository, execution_engine 等が存在)

src/kabusys/monitoring/
- monitoring_db.py               — SQLite 永続化層（テーブル作成・CRUD）
- system_monitor.py              — システム状態・データ鮮度チェック
- trade_monitor.py               — 注文滞留・約定異常検出
- risk_monitor.py                — ドローダウン・ポジション制限監視
- kill_switch.py                 — kill.flag 書込ロジック
- alert_manager.py               — LINE 通知ラッパー
- monitoring_engine.py           — 各モニタの束ね（Polling loop）
- streamlit_dashboard.py         — Streamlit ダッシュボード

src/kabusys/portfolio/
- portfolio_builder.py           — 候補選定・等重/スコア重み算出
- position_sizing.py             — 発注株数計算（risk_based / equal / score）
- risk_adjustment.py             — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py             — momentum/value/volatility 等の計算
- feature_exploration.py         — 将来リターン / IC / 統計サマリー

src/kabusys/ai/
- news_nlp.py                    — ニュース NLP（OpenAI）スコアリング
- regime_detector.py             — マクロ + MA200 を合成したレジーム判定

src/kabusys/tools/
- paper_verification_report.py   — Paper Trading 検証レポート

src/kabusys/utils/
- process_priority.py            — プロセス優先度・CPU affinity 設定ユーティリティ

その他
-----
- 監視データの永続化は SQLite（monitoring_db.py）が担い、テーブル作成やマイグレーション（カラム追加チェック）も init_monitoring_db で行います。
- DuckDB はリサーチ系（prices_daily / raw_financials 等）の高速分析に利用します。
- 実運用での注意点:
  - OpenAI キーやプロダクションの API キーは適切に管理してください（.env.local を使う等）。
  - KillSwitch は自動で kill.flag を書き込みます。運用時は書き込み要因を確認してから再起動してください。
  - paper_trading は本番 DB と分離されます（デフォルトで data/paper_trading.db）。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献ガイドラインを追記してください）

問い合わせ
----------
不明点やバグは issue を立ててください。開発者向けには各モジュールに docstring と注意書きを多数記載していますので、実装を参照してください。