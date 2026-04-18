README
=====

プロジェクト概要
-------------
KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注・監視・AI 支援）です。  
主要処理は Python パッケージ化されており、以下の主要サブシステムを含みます。

- ExecutionEngine：ブローカーへの発注管理・リスク管理・約定整合
- Monitoring：システム・トレード状態のポーリング監視とアラート / Kill Switch
- Portfolio：銘柄選定・重み付け・ポジションサイズ算出
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI：ニュース NLP による銘柄センチメント評価・市場レジーム判定（OpenAI 利用）
- Tools：ペーパートレード検証レポート等のユーティリティ

主な特徴
--------
- 環境変数 (.env) による設定管理（対話式ウィザードあり）
- DuckDB（時系列/ファクタ分析）と SQLite（監視/取引ログ）を併用するデータ設計
- Paper Trading（ペーパートレード）モードは本番 DB と分離（data/paper_trading.db）
- OpenAI を利用したニュースセンチメント（ai module）とレジーム判定
- モニタリング 運用用 kill.flag / stop_requested.flag による安全な停止制御
- ログは stdout と日次ローテートファイルに出力（logs/ ディレクトリ）

前提条件
--------
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（validate_config の YAML 検証に使用）
- ネットワーク接続（kabuステーション API / OpenAI を使う場合）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - YAML 検証を使う場合: pip install PyYAML

   （パッケージ化されている場合は pip install -e . も可）

4. 環境変数の初期作成（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成後、.env を適宜編集して必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. 必要ディレクトリの作成（通常はスクリプトが自動作成しますが念の為）
   - mkdir -p data logs

主要な環境変数（抜粋）
-------------------
（.env で管理。主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、発注は MockBroker を使い data/paper_trading.db に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）

使い方（主なコマンド）
------------------

- 環境ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存。paper_trading のときは MockBroker を利用し paper_trading DB に記録。
  - 実行中に data/stop_requested.flag を作成すると起動ループは安全に終了します。
  - Kill Switch（監視から発動）による停止は data/kill.flag を作成して Engine に通知されます（Execution 側で処理）。

- Monitoring（監視プロセス）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。

- Paper Trading 検証レポート生成（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能（デフォルト: data/paper_trading.db）

停止・運用ルール
----------------
- Graceful stop:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して終了します。
- Kill Switch:
  - 監視（Monitoring）コンポーネントが条件を満たすと data/kill.flag を書き、ExecutionEngine に停止シグナルを与えます。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 をセットすると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ディレクトリ構成
----------------
（パッケージソース: src/kabusys 以下）

- kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / Settings 管理
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （取引監視ロジック、コード参照）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各モニタの統合実行
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — （アラート送信管理、コード参照）
  - execution/
    - execution_engine.py — 発注エンジン本体
    - broker_factory.py — ブローカークライアント生成（実ブローカー / モック）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注周りの実装
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・スケーリング
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — Momentum / Value / Volatility ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - data/ (runtime)
    - monitoring.db（デフォルト） / paper_trading.db（paper mode）
    - execution.pid（Execution エンジンの PID ファイル）
    - stop_requested.flag, kill.flag — 制御フラグファイル
  - logs/ (runtime)
    - execution.log, monitoring.log など（TimedRotatingFileHandler による日次ローテート）

開発メモ
--------
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます（stdout + 日次ファイル）。
- process_priority.set_process_priority で起動プロセスの優先度調整を行っています（High/Normal/Low）。
- DuckDB は分析向け（prices_daily / raw_financials / raw_news 等のテーブル想定）。データ投入は別途パイプラインが必要です。
- AI モジュールは OpenAI API を呼び出します。テスト時は API 呼び出し関数をモックする設計になっています。

よくある操作例
--------------
- .env を作成して検証まで行う
  1) python -m kabusys.config_setup
  2) python -m kabusys.validate_config

- 監視をデーモン的に起動（例）
  - nohup python -m kabusys.run_monitoring > logs/monitoring.out 2>&1 &

- 実行エンジン起動（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ・貢献
----------------
- バグ報告・機能要望は Issue を立ててください。
- コード変更は PR をお願いします。自動テスト・型チェックの導入を推奨します。

（以上）