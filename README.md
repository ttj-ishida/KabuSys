README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。本リポジトリは戦略の研究・ファクター計算、ポートフォリオ構築、ポジションサイジング、監視（Monitoring）、および ExecutionEngine の起動補助を含むユーティリティ群を提供します。  
設計方針として、可能な限りフェイルセーフ・冪等性を重視し、Paper Trading と Live を明確に分離して運用できるようになっています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）に記録。
  - 起動時にプロセス優先度を high に設定し、停止フラグ / stop フラグに対応。
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システム稼働状況、データ鮮度、注文滞留・約定異常、ドローダウン監視。
  - kill.flag による ExecutionEngine 停止シグナル生成。
  - 監視結果は SQLite（デフォルト data/monitoring.db）に永続化。
- Portfolio 構築ユーティリティ（portfolio パッケージ）
  - 候補選定、等金額/スコア加重配分、セクターキャップ、レジーム乗数、株数決定（単元処理、aggregate cap）。
- Research（research パッケージ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC 計算、統計サマリー。
  - DuckDB を用いた高速な時系列集計。
- AI 支援モジュール（ai パッケージ）
  - ニュース NLP による銘柄センチメントスコア生成（OpenAI API 使用）
  - マクロニュースと MA200 を組み合わせた市場レジーム判定（LLM + データ合成）
- ツール
  - 対話式 .env 作成ウィザード（config_setup.py）
  - 環境設定の事前検証 CLI（validate_config.py）
  - Paper Trading の検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ、監視 DB の永続化レイヤ、等。

必要要件
--------
- Python 3.10+
- 必須ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 開発/補助（任意）:
  - PyYAML（validate_config で config/*.yaml の中身検証を行う場合）

セットアップ手順
----------------
1. リポジトリをクローン／展開

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - validate_config の YAML 検証を利用する場合: pip install PyYAML

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または .env を手動で作成: ルートに .env を配置（下記参照）
   - 自動読み込み: 起動時に .env（および .env.local）をプロジェクトルートから自動で読み込みます。
     - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict

初期 .env（例）
----------------
（.env は絶対に VCS にコミットしないでください）

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
# OpenAI を使う場合
OPENAI_API_KEY=sk-...

重要な環境変数（代表）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: one of development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注はモック。DB は data/paper_trading.db を使用
  - live: 実際の発注が行われるので注意
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード時の DB を上書き）
- PAPER_FILL_MODE（paper_trading 用の約定挙動: instant | partial | never | reject）
- OPENAI_API_KEY: AI 機能（news_nlp / regime_detector）利用時に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロード無効化

実行方法（主なコマンド）
-----------------------
- ExecutionEngine を起動（常用）
  - python -m kabusys.run_execution
  - 挙動:
    - 起動時にプロセス優先度を high に設定し、所定の pid ファイルに PID を書く。
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録。
    - 起動前に data/stop_requested.flag が存在すると起動を中止。
    - 停止は data/stop_requested.flag を作成するか、kill.flag により監視から停止指示を受ける。

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを保存します。
  - 停止: data/stop_requested.flag を作成するか、KeyboardInterrupt。

- 環境ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱いにできます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI モジュールのプログラム呼び出し例（Python REPL/スクリプト内）
  - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を利用。

停止フラグ・PID 周りのファイル
----------------------------
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine に停止指示を出す目的で使用。
  - 存在すると ExecutionEngine 側で停止処理が行われます。
- data/stop_requested.flag
  - run_monitoring/run_execution のループを外部から優雅に終了させるためのフラグ。
- data/execution.pid
  - ExecutionEngine 側で書き込まれる PID ファイル。system monitor が stale PID を検出すると削除し、アラート記録することがあります。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数と設定の読み込みロジック（.env 自動ロード）
- config_setup.py            — 対話式 .env 生成ウィザード
- validate_config.py         — 起動前の設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring ポーリングループ起動スクリプト

パッケージ（主要サブモジュール）
- ai/
  - news_nlp.py              — ニュース NLP（OpenAI）で ai_scores を生成
  - regime_detector.py       — マクロ + MA200 による市場レジーム判定
- monitoring/
  - monitoring_db.py         — SQLite 監視ログの永続化層
  - system_monitor.py        — システム稼働状況・データ鮮度監視
  - trade_monitor.py         — 注文滞留・約定異常監視
  - risk_monitor.py          — ドローダウン／ポジション上限監視
  - kill_switch.py           — kill.flag 書き込みロジック
  - monitoring_engine.py     — 各モニタを束ねるポーリングエンジン
  - alert_manager.py         — （未表示）アラート送信管理
- portfolio/
  - portfolio_builder.py     — 候補選定・重み計算
  - position_sizing.py       — 発注株数計算・キャップ調整
  - risk_adjustment.py       — セクターキャップ・レジーム乗数
- research/
  - factor_research.py       — モメンタム / ボラティリティ / バリュー計算（DuckDB）
  - feature_exploration.py   — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート生成
- utils/
  - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
- execution/                  — Engine / Broker 周り（主要コンポーネントはここに配置想定）
- data/                       — デフォルト DB 等の出力先（実行時に作成される）

運用上の注意
------------
- .env は決して Git 等にコミットしないでください。
- KABUSYS_ENV=live の場合は本番発注が行われます。LINE 通知や kill flag の設定を事前に確認してください。
- Monitoring は監視用の SQLite（SQLITE_PATH）に書き込みます。run_monitoring は環境にかかわらず本番 sqlite_path を使用する設計になっています。
- OpenAI 呼び出しはレート制限や API 障害を考慮してリトライとフォールバック（失敗時スコア 0.0 等）を行いますが、API キーや課金設定は事前に確認してください。
- プロセス優先度設定や CPU affinity の変更は権限により失敗することがあります（警告ログが出ます）。

トラブルシューティング（よくある原因）
-------------------------------------
- 起動時に「環境変数が未設定」と出る: 必須の環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を .env に設定してください。validate_config を実行すると足りない設定を確認できます。
- DuckDB / SQLite のパスの親ディレクトリがない: validate_config は親ディレクトリの存在を警告します。data/ ディレクトリを作成してください（多くのスクリプトが起動時に自動作成しますが、パーミッションに注意）。
- OpenAI API 呼び出しエラー: OPENAI_API_KEY がセットされているか、ネットワークとキーの有効性を確認してください。API エラーはリトライ後も失敗するとログに出ます。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理（現行: 0.1.0）。
- ライセンス情報や詳細な運用手順はプロジェクトの別ドキュメント（運用 Playbook 等）を参照してください。

最後に
------
この README はリポジトリ内のモジュールとスクリプトの主要な使い方と設定をまとめたものです。詳細な実装や追加のユーティリティは各モジュールの docstring、ソースコードのコメントを参照してください。問題や質問があれば、実装コメントやログ出力を元にデバッグを行うか、開発チームに問い合わせてください。