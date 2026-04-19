README
======

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした軽量な Python コードベースです。  
主な機能はシグナル生成 → ポートフォリオ構成 → 発注（本番/ペーパー） → モニタリング／アラート、さらに研究用のファクター計算・特徴量解析や OpenAI を使ったニュース NLP によるセンチメント評価を含みます。

本リポジトリはライブラリ的なモジュール群（portfolio / research / ai / monitoring / utils 等）と、起動用スクリプト（run_execution / run_monitoring）・運用支援スクリプト（config_setup / validate_config / tools）で構成されています。

機能一覧
--------
- ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、paper_trading 用 DB (data/paper_trading.db) に記録して本番 DB と分離
- Monitoring ポーリング
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行して監視ログを SQLite に永続化し、必要に応じて Kill Switch（data/kill.flag）を書き込む
  - ポーリング間隔は環境変数で調整可能（MONITOR_POLL_INTERVAL）
- 環境設定ウィザード（.env 作成支援）
  - python -m kabusys.config_setup で対話的に .env を生成
- 設定検証 CLI
  - python -m kabusys.validate_config で必須環境変数や config/*.yaml の存在・基本チェック
- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report によりペーパートレード DB を解析して PASS/FAIL レポートを出力
- 研究用モジュール
  - ファクター計算 (momentum, volatility, value)
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI モジュール（OpenAI）
  - ニュース記事を LLM でセンチメント評価して ai_scores に書き込む（news_nlp）
  - ETF とマクロニュースを組み合わせて市場レジーム判定（regime_detector）
- ユーティリティ
  - ロギング設定（ログのコンソール + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

動作要件 / 依存
--------------
主に以下を想定しています（実運用では仮想環境を推奨）。

- Python 3.10+
- 必要なパッケージ（抜粋）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で YAML 検証を行う場合、任意）
- SQLite（標準ライブラリで利用可能）
- OS: Linux / macOS / Windows（process_priority は OS による差分を吸収しますが、一部機能はプラットフォーム依存）

セットアップ手順
----------------
1. リポジトリをチェックアウトし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（プロジェクトに requirements.txt があればそれを使用してください）。
   - pip install duckdb psutil openai PyYAML

3. 環境変数設定 (.env) を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   - あるいはプロジェクトルートに .env を手動作成

4. 設定を検証します。
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従って .env や config/*.yaml を修正してください

5. 必要に応じてデータディレクトリを作成（デフォルトでは data/ に DB や PID /フラグファイルを置きます）。
   - mkdir -p data logs

主要な環境変数（主なもの）
--------------------------
以下は主要な環境変数とデフォルトです（.env で設定）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を利用する場合に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番では 0 推奨）

簡易 .env サンプル
------------------
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=（必要なら設定）

使い方
------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も終了コード 1 扱いになります

- 実行エンジンの起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB に書き込み（本番 DB とは分離）
    - PID ファイルや data/stop_requested.flag を監視して安全に停止します

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor を中心に監視を行い、SQLite（settings.sqlite_path）へ書き込み
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト: 60）
    - 停止は data/stop_requested.flag の存在や KeyboardInterrupt（Ctrl-C）

- Paper Trading 検証レポート（分析ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で別パス指定可。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数か明示的引数）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用
  - 実行中にネットワークや API エラーが発生してもフェイルセーフで継続する設計（部分的にログ警告を出す）

運用上の注意
------------
- Monitoring は（コード内の設計で）KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。監視 DB を別途運用したい場合は適切に SQLITE_PATH を設定してください。
- Execution は paper_trading 時に PAPER_TRADING_SQLITE_PATH を使用して本番 DB とデータ分離します。
- Kill Switch:
  - RiskMonitor 等がトリガー条件に達した場合、data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 にすると自動クリアしますが、本番では 0 を推奨します（誤クリア防止）。
- ログ:
  - デフォルトは logs/<app_name>.log に日次ローテートで出力（logs ディレクトリを作成してください）
  - logging 設定は kabusys.utils.logging_setup.setup_logging で統一

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要なモジュール・ファイル一覧（src/kabusys 以下を抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定読み込みロジック（.env 自動ロード等）
  - config_setup.py          -- .env 対話式ウィザード
  - validate_config.py       -- 設定検証 CLI
  - run_execution.py         -- ExecutionEngine 起動スクリプト
  - run_monitoring.py        -- Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  -- ペーパー検証レポート生成
  - portfolio/
    - portfolio_builder.py    -- 候補選定・重み計算
    - position_sizing.py      -- 株数決定・投下量調整
    - risk_adjustment.py      -- セクター制限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py      -- momentum / volatility / value の計算
    - feature_exploration.py  -- 将来リターン・IC・統計
    - __init__.py
  - ai/
    - news_nlp.py             -- ニュースを OpenAI でスコアリング
    - regime_detector.py      -- 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py        -- SQLite テーブル作成・読み書き層
    - monitoring_engine.py    -- 各 Monitor を束ねる
    - system_monitor.py       -- システム状態・データ鮮度監視
    - risk_monitor.py         -- ドローダウン / ポジション上限監視
    - trade_monitor.py        -- （注文滞留・約定異常監視など）
    - kill_switch.py          -- data/kill.flag の書き込みロジック
  - utils/
    - logging_setup.py        -- ログ初期化ユーティリティ
    - process_priority.py     -- プロセス優先度設定ユーティリティ
    - __init__.py
  - monitoring/monitoring_db.py  -- 監視用 DB スキーマ（テーブル定義）

（上位に data/, logs/, config/ 等のディレクトリを想定）

開発者向けメモ
--------------
- モジュールはできるだけ副作用を避ける設計になっています（DB 書き込みは明示的、時間の取得は呼び出し側で与える等）。
- AI 関連はネットワーク不確実性に対してリトライやフォールバック（0.0 等）を実装しています。
- DuckDB 接続を渡してオフラインでファクター計算や研究を実行できます（prices_daily / raw_financials テーブルに依存）。

ライセンス / バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンス情報はプロジェクトルートの LICENSE（存在する場合）を参照してください。

お問い合わせ
------------
運用上の疑問や機能追加の要望はリポジトリの issue または担当者に連絡してください。

以上。必要なら README に含める具体的な .env のテンプレートや systemd / supervisor 用の起動スクリプト例、docker-compose 例などを追加します。必要でしたら教えてください。