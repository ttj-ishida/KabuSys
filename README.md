# KabuSys

日本株向け自動売買システムのコアライブラリ群。信号生成・ポートフォリオ構築・発注エンジン・監視・AI を使ったニュース評価などを含むモジュール群です。

以下はこのリポジトリに含まれる主な機能と使い方の概要です。

## プロジェクト概要
KabuSys は以下のような責務を持つコンポーネントで構成されます。

- strategy/research: DuckDB を用いたファクター計算・特徴量解析（momentum, volatility, value 等）
- portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム補正などの純粋関数群
- execution: ブローカークライアントに対する注文管理・リスク管理・照合処理を行う ExecutionEngine（本番／ペーパートレード切替対応）
- monitoring: system / trade / risk の各種監視、Kill Switch（フラグファイル）による停止、ログ永続化（SQLite）
- ai: OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- tools: ペーパートレード検証レポート生成などのユーティリティスクリプト
- utils: ロギング設定・プロセス優先度設定等のユーティリティ

設計上のポイント:
- DuckDB は分析用 DB、SQLite は監視・注文履歴（ペーパートレードは分離された SQLite）に使用
- 環境変数 / .env による設定管理（自動読み込み機能あり）
- AI 呼び出しは冪等性・リトライ・バリデーションを考慮して実装

---

## 機能一覧（抜粋）
- 設定ウィザード（.env）: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- Execution エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- Monitoring ポーリングスクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL によるポーリング間隔制御（デフォルト 60 秒）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- ニュース NLP（OpenAI）による銘柄別センチメント評価: kabusys.ai.news_nlp.score_news
- 市場レジーム判定（AI + MA200 合成）: kabusys.ai.regime_detector.score_regime
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイズ算出等）
- 監視 DB 永続化 (SQLite) と Risk Monitor / Kill Switch の実装

---

## 前提 / 必要な環境
- 推奨 Python バージョン: 3.8 以上（注: ソースは typing の新構文や __future__ annotations を使用）
- SQLite: Python に組み込み
- 主要 Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML の妥当性を確認する場合）

インストール例:
- 仮想環境を作成してから:
  - pip install duckdb psutil openai PyYAML

もし requirements.txt をプロジェクトに追加するなら:
- pip install -r requirements.txt

---

## 環境変数 / 設定 (.env)
- 自動ロード:
  - プロジェクトルートにある `.env`、`.env.local` は起動時に自動で読み込まれます（OS 環境変数が優先）。
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要な必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
- 主要なオプション / デフォルト:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - OPENAI_API_KEY: OpenAI を使う機能で必要
- .env の作成はウィザードを推奨:
  - python -m kabusys.config_setup

---

## セットアップ手順（ローカルで試す最小手順）
1. リポジトリをクローン / ワークツリーに移動
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - python -m kabusys.config_setup
   - 作成後、設定が整っているか検証:
     - python -m kabusys.validate_config
5. データディレクトリを作成（必要に応じて）
   - mkdir -p data logs

---

## 使い方（主要スクリプト）
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用
  - 起動前に data/stop_requested.flag が存在すると起動はスキップされます
  - 実行中に停止要求を出すには data/stop_requested.flag を作成（運用上の手順に従ってください）

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または環境変数 PAPER_TRADING_SQLITE_PATH を指定して DB パスを解決

- AI 関連（ニューススコア・レジーム判定）
  - ニューススコアリング: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - api_key 引数を渡すか OPENAI_API_KEY 環境変数を設定
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- 実際に本番発注を行う場合は KABUSYS_ENV=live とし、設定・テストを厳重に行ってください。
- Kill Switch:
  - kabusys.monitoring.kill_switch は一定条件で data/kill.flag を書き込み、ExecutionEngine の停止トリガーとなります（実運用時は取り扱いに注意）。

---

## ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging を使って統一管理
- デフォルト: logs/<app_name>.log に日次ローテーションで出力（30 日保持）
- 環境変数 LOG_DIR でログディレクトリを上書き可能

---

## ディレクトリ構成（主要ファイルの説明）
（src/kabusys 以下を想定）

- __init__.py
  - パッケージのエントリポイント。バージョン等を定義

- config.py
  - Settings クラス: 環境変数と .env の取り扱い、各種パスやフラグの取得ロジック

- config_setup.py
  - .env を対話式に作成・更新するウィザード

- validate_config.py
  - .env と config/*.yaml の妥当性を検証する CLI

- run_execution.py
  - ExecutionEngine を起動するスクリプト（本番 / ペーパートレード分離対応）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL に対応）

- utils/
  - logging_setup.py: ルートロガーに StreamHandler と TimedRotatingFileHandler を設定
  - process_priority.py: プロセス優先度・CPU affinity のユーティリティ

- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/ディスク、データ鮮度、実行プロセス存在チェック等
  - trade_monitor.py: （注文滞留・約定異常等の監視ロジック）
  - risk_monitor.py: ドローダウン・ポジション数制限の監視
  - kill_switch.py: kill.flag 管理
  - monitoring_engine.py: 各モニタを束ねる実行エンジン
  - alert_manager.py: （LINE 等への通知を扱う想定）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注・注文管理・リスク管理・ブローカー抽象など（run_execution が利用）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算・ロット丸め・集約キャップ
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: momentum/value/volatility 等のファクター計算（DuckDB ベース）
  - feature_exploration.py: 将来リターン計算、IC 計算、統計サマリー

- ai/
  - news_nlp.py: ニュース記事の銘柄ごとのセンチメント評価（OpenAI 呼び出し、バリデーション、DuckDB への書き込み）
  - regime_detector.py: MA200 とマクロセンチメントを合成して市場レジーム判定・書き込み

- tools/
  - paper_verification_report.py: ペーパートレードの検証レポート生成

---

## 運用上の注意
- 本番稼働時は KABUSYS_ENV=live を設定し、LINE 通知・Kill Switch の設定などを必ず確認してください
- .env は絶対に Git 等へコミットしないでください
- OpenAI を利用する機能は API キーの管理やコスト・レイテンシ考慮が必要です
- データベース（DuckDB / SQLite）のバックアップと権限管理を行ってください
- run_execution/run_monitoring は stop flag（data/stop_requested.flag）を監視しており、外部からの停止要求に対応します

---

## 開発・貢献
- コードはモジュール単位で純粋関数と副作用を分離する方針で実装されています。単体テストを書きやすい構造になっています。
- 外部 API や I/O を含む箇所はモック可能なように設計されています（テスト時はモックを注入して実行）。

---

必要であれば、この README をベースに「展開例（docker-compose / systemd のサービス定義）」「運用チェックリスト」「環境変数の詳細一覧（.env.example 相当）」などの追加ドキュメントも作成します。どの項目を追加したいか教えてください。