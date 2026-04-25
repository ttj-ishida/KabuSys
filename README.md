KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株の自動売買を想定した研究・実行・監視プラットフォームです。  
主に以下を提供します。

- シグナル → 銘柄選定 → 配分 → 発注までの Execution エンジン
- システム稼働性・注文ログ・リスクの監視（kill switch を含む）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ）
- 研究用モジュール（ファクター計算・IC・将来リターン等）
- AI を用いたニュースセンチメント（OpenAI 経由）・市場レジーム判定
- ペーパートレード用の分離 DB、検証レポート生成ツール
- .env 対話ウィザードと設定検証ツール

特徴
----
- 本番／ペーパートレードを環境変数（KABUSYS_ENV）で切り替え
- DuckDB（分析用）と SQLite（監視 / ペーパートレード用）の併用
- OpenAI を用いたニュース NLP・レジーム検出（API キー必要）
- モジュール化されたポートフォリオ構築・リスク制御ロジック（純関数でテストしやすい）
- 監視エンジンは kill.flag による安全停止やアラート連携を想定
- ロギングは共通ユーティリティで設定（stdout + 日次ローテーション）

前提 / インストール
-------------------
必須（代表的なもの）
- Python 3.10+
- pip

推奨 Python パッケージ（requirements の例）
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml のパース検証を行う場合）
（SQLite は標準ライブラリで利用可）

セットアップ手順（簡易）
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env の作成（対話ウィザードを推奨）
   - python -m kabusys.config_setup
     → 対話形式で .env を生成できます（.env は Git にコミットしない）

5. 設定検証
   - python -m kabusys.validate_config
     → --strict を付けると警告も失敗扱いになります

6. データディレクトリ等（必要に応じて）
   - デフォルトで data/ と logs/ にファイルが作られます。権限や配置を確認してください。

主要環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

使い方
----

実行エンジン（Execution）
- 本番／ペーパートレードの発注エンジンを起動します。
- 実行例:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離します。
  - 起動時に data/stop_requested.flag や data/execution.pid 等のフラグ／PID を扱います。

監視（Monitoring）
- システム状態や注文の監視ループを起動します。
- 実行例:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- 備考:
  - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（監視用 DB）を使用します。

ペーパートレード検証レポート
- ペーパートレード DB を集計して PASS/FAIL レポートを出力します。
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも可）

AI（ニュース NLP / レジーム判定）
- OpenAI（gpt-4o-mini 等）を利用します。OPENAI_API_KEY を設定してください。
- 関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- API 呼び出しはレートリミットやサーバーエラーに対してリトライ・フォールバック処理があります。

ログ
- setup_logging により stdout とファイル（logs/<app_name>.log）へ出力
- ファイルは日次ローテーション（30日保持）

停止・Kill Switch
- モニタリング側でリスク基準（ドローダウン、ポジション上限など）を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る設計です。
- kill.flag の存在は ExecutionEngine 側で起動・継続判断に使用されます。

ディレクトリ構成（要約）
---------------------
以下は主要なソース配置（src/kabusys 以下）と簡単な説明です。実プロジェクトのツリーを抜粋しています。

- src/kabusys/
  - __init__.py                        — パッケージ初期化、バージョン定義
  - config.py                          — 環境変数 / 設定読み込み（.env 自動ロード含む）
  - config_setup.py                    — .env 対話ウィザード
  - validate_config.py                 — 起動前の設定検証 CLI
  - run_execution.py                   — ExecutionEngine 起動スクリプト（main）
  - run_monitoring.py                  — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py     — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py             — 候補選定・重み計算（等重・スコア重み）
    - position_sizing.py               — 株数決定・上限・単元丸め・aggregate cap
    - risk_adjustment.py               — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py               — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py           — 将来リターン・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py                      — raw_news を LLM でスコア化し ai_scores に書込
    - regime_detector.py               — ma200 と LLM を組合せて market_regime を判定
    - __init__.py
  - monitoring/
    - monitoring_db.py                 — SQLite による監視ログ永続化層（初期化・CRUD）
    - system_monitor.py                — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py                 — （省略されたが注文監視ロジック想定）
    - risk_monitor.py                  — ドローダウン・ポジション上限監視
    - kill_switch.py                   — kill.flag の書き込み・評価
    - monitoring_engine.py             — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py                 — （監視アラートの送信を担う想定モジュール）
  - execution/
    - execution_engine.py              — ExecutionEngine（発注セッション管理）
    - broker_factory.py                — ブローカークライアント生成（Mock/実装）
    - order_manager.py                 — 発注管理ロジック
    - order_repository.py              — 発注ログ永続化
    - reconciler.py                    — ブローカーとローカル状態の突合
    - risk_manager.py                  — 発注前リスクチェック（rate limit 等）
  - data/
    - pipeline.py                      — データパイプライン補助関数（get_last_price_date 等）
    - stats.py                         — 正規化等の統計ユーティリティ
  - utils/
    - logging_setup.py                 — ログ設定ユーティリティ
    - process_priority.py              — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

補足・運用メモ
----------------
- ペーパートレード: KABUSYS_ENV=paper_trading を指定すると実発注を行わず MockBroker を使用します。DB は PAPER_TRADING_SQLITE_PATH へ分離されます。
- 監視 DB（SQLITE_PATH）は監視・トレードログ・ダッシュボード等を格納します。monitoring モジュールは環境にかかわらずこの sqlite_path を使用します。
- ローカルでのテストでは KILL_FLAG_CLEAR_ON_START=1 を使うと起動時に既存の kill.flag を自動クリアできます（ただし本番では 0 を推奨）。
- OpenAI を利用する AI 機能は API キーが必要です。API 呼び出しはリトライやクリッピング等の安全処理がありますが、コストとレート制限に注意してください。

ライセンス・貢献
----------------
（ここにライセンスや貢献方法を記載してください）

お問い合わせ
------------
（プロジェクトの連絡先・Issue 提出先などを記載してください）

以上。必要に応じて README にインストール用 requirements.txt、具体的な systemd / docker の起動例、詳細な設定例を追加できます。どの情報を優先して追記しますか？