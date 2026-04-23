README.md

KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。  
主要コンポーネントは以下のとおりです。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行う（本番／ペーパートレード対応）。
- 監視（Monitoring）: システム稼働・注文状況・リスク（ドローダウン等）をポーリング監視し、Kill Switch（停止フラグ）やアラートを発行。
- ポートフォリオ構築（Portfolio）: 候補選定・重み算出・ポジションサイジング・セクター制限などの純粋関数群。
- 研究モジュール（Research）: ファクター計算、将来リターン・IC 計算、統計サマリーなど。
- AI ユーティリティ: ニュースを LLM（OpenAI）で評価し銘柄スコアを生成、レジーム判定など。
- ツール: Paper Trading 検証レポート生成や設定ウィザード、設定検証 CLI 等。

主な機能
--------
- ExecutionEngine の起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading.db に記録して本番 DB と分離。
  - 起動時にプロセス優先度を設定し、PID ファイル管理、停止フラグ検出による安全停止をサポート。

- Monitoring（run_monitoring.py / monitoring_engine）
  - システム稼働率、CPU/メモリ/ディスク使用率、データ鮮度の監視。
  - 注文滞留・約定異常・リスク（ドローダウン・ポジション上限）検出。
  - Kill Switch（data/kill.flag）書き込みで ExecutionEngine の停止をトリガー。
  - 監視ログは SQLite（デフォルト data/monitoring.db）に永続化。

- ポートフォリオ構築ライブラリ
  - 候補選定（スコア順）/ 等重・スコア重み / リスクベースのポジションサイズ計算。
  - セクターキャップ適用やレジーム乗数の計算。

- 研究用モジュール（DuckDB を利用）
  - モメンタム、ボラティリティ、バリュー系ファクターの計算（prices_daily / raw_financials を参照）。
  - 将来リターン・IC（Spearman）・ファクター統計量算出。

- AI（OpenAI）連携
  - ニュース記事をまとめて LLM に投げ、銘柄毎のセンチメント（ai_scores）を生成・DBへ書き込み。
  - マクロニュース＋ETF MA 乖離を使った市場レジーム判定（bull/neutral/bear）。

- 便利ツール
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提: Python 3.9+（ソースは型アノテーションで recent な構文を使用）を想定。

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール
   - duckdb, psutil, openai, pyyaml（YAML 検証用）などが必要です。
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそちらを使用してください）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成。主な環境変数（デフォルト値あり/必須）は以下。

主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL (デフォルト: INFO)
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE (paper_trading 時のモック約定モード): instant | partial | never | reject

.env の自動読み込み
- 起動時、OS 環境変数 > .env.local > .env の順で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化）。

4. データディレクトリの作成
   - デフォルトでは data/ 以下に DB・フラグファイル等を配置します。起動時に自動作成されない場合は手動で作成してください。
   - ログは logs/ 以下に出力（デフォルト）。ファイル出力が失敗するとコンソール出力のみで継続します。

使い方
------
起動スクリプト（実行例）:

- 監視ループを起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring

- 実行エンジンを起動
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB を使用（本番 DB と分離）。
  - python -m kabusys.run_execution

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

停止・Kill Switch
- ExecutionEngine を停止したい場合はプロジェクトルートの data/kill.flag に理由テキストを書き込む（KillSwitch が存在すれば ExecutionEngine を停止する設計）。
- run_monitoring / run_execution は data/stop_requested.flag を検出するとグレースフルに終了します。

ログ設定
- 共通ユーティリティである kabusys.utils.logging_setup.setup_logging により、console (stdout) と 日次ローテーションログ（logs/<app>.log）を設定します。ログレベルは LOG_LEVEL 環境変数で指定可能。

ライブラリ関数のサンプル利用（Python API）
- DuckDB 接続を渡してファクター計算:
  - from kabusys.research import calc_momentum
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - recs = calc_momentum(conn, datetime.date(2026, 4, 1))

- AI ニューススコア（ai.news_nlp）:
  - from kabusys.ai.news_nlp import score_news
  - # conn は duckdb 接続、target_date は datetime.date
  - score_news(conn, target_date, api_key="YOUR_OPENAI_KEY")

注意点 / 運用上のポイント
- .env は絶対に Git にコミットしないでください（config_setup.py 内のヘッダ参照）。
- KABUSYS_ENV=live の場合は特に注意（validate_config は本番向けの追加警告を出します）。
- Paper Trading は本番 DB と完全分離する設計ですが、データパスを誤ると混在する可能性があるため env の確認を行ってください。
- 起動時にプロセス優先度を high に設定します（psutil の権限がない場合は警告を出してスキップします）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数 / Settings 管理（.env 自動ロード含む）
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
- run_execution.py           — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py               — ニュースの LLM スコアリング
  - regime_detector.py       — 市場レジーム判定（LLM + ETF MA）
- monitoring/
  - monitoring_db.py         — SQLite の永続化レイヤ
  - system_monitor.py        — システム・データ鮮度監視
  - trade_monitor.py         — 注文滞留・約定監視（実装参照）
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — kill.flag の生成/管理
  - monitoring_engine.py     — 複数モニタ一括実行
  - alert_manager.py         — （アラート送信ロジック）
- execution/
  - execution_engine.py      — ExecutionEngine 本体（起動・セッション管理）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
- portfolio/
  - portfolio_builder.py     — 候補選定 / 重み計算
  - position_sizing.py       — 発注株数計算
  - risk_adjustment.py       — セクターキャップ・レジーム乗数
- research/
  - factor_research.py       — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py   — 将来リターン / IC / 統計サマリー
- monitoring/                — （上記）
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - logging_setup.py         — ルートロガー設定ユーティリティ
  - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

補足（開発者向け）
-----------------
- .env 自動読み込みはプロジェクトルート（.git や pyproject.toml を探索）から行われます。CI・テスト等で自動読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を使った研究機能は、prices_daily / raw_financials 等のテーブルスキーマに依存します。サンプルデータや ETL パイプラインを用意してから利用してください。
- OpenAI の呼び出し部分はリトライやレスポンス検証等の安全弁を備えています（429 / タイムアウト / 5xx を指数バックオフでリトライ）。

ライセンス・バージョン
---------------------
- 現在のパッケージバージョン: 0.1.0（kabusys.__version__）

問い合わせ / 貢献
-----------------
不具合や改善提案は Issue を立ててください。Pull Request は歓迎します。README に書かれていない実装上の詳細はソース内の docstring を参照してください。

以上。必要があれば各セクションの詳細な使い方（実行例・設定テンプレート・DB スキーマなど）を追記します。