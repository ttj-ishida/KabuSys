# KabuSys

日本株向け自動売買システムのコアライブラリ群（プロトタイプ / 研究開発用）。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・AI を組み合わせたパイプラインの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成されています。

- データ処理・リサーチ（DuckDB を利用したファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター上限適用）
- 発注実行（ExecutionEngine：ブローカークライアント経由で発注管理、ペーパートレード対応）
- 監視（System / Trade / Risk モニタ、Kill Switch による安全停止）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 運用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針としては「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避（日時の直接参照抑制）」「外部 API 呼び出しは明示的にキーを要求する」など安全性と再現性に配慮しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話的生成）: kabusys.config_setup.run_wizard
- 設定検証 CLI（.env / config/*.yaml チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading / live の切替
  - paper_trading 時は MockBrokerClient を使用し paper DB を使用
  - 停止は data/stop_requested.flag / data/kill.flag を用いる
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリング（MONITOR_POLL_INTERVAL で間隔指定）
  - 監視ログは SQLite（monitoring.db）へ永続化
- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク監視、データ鮮度、Execution PID の生存チェック
  - TradeMonitor: 注文滞留や約定異常検出（trade_logs テーブル参照）
  - RiskMonitor: ドローダウン、ポジション数上限検出・ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringEngine: 各 Monitor を束ねてアラート発行・KillSwitch 評価
- ポートフォリオ関連（純関数）
  - 候補選定、等重/スコア重み計算、リスクに基づく株数算出、セクターキャップ、レジーム乗数
- Research（DuckDB ベース）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI モジュール
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、銘柄毎にスコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF MA による指標＋マクロニュースの LLM センチメントでレジーム判定
  - どちらも OPENAI_API_KEY が必要（引数でキー渡し可）、エラー時はフェイルセーフ動作
- 運用ツール
  - tools.paper_verification_report: ペーパートレード結果の検証レポート生成

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. 必要な Python パッケージをインストール（例）
   - Python >= 3.9 以上を想定
   - 例: pip install -r requirements.txt（requirements.txt がある場合）
   - 主なランタイム依存: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（設定検証時に任意）
3. プロジェクトルートで .env を作成
   - 対話的ウィザード:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
4. 重要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development | paper_trading | live）デフォルト: development
   - OPENAI_API_KEY（AI 機能を利用する場合）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（任意、デフォルト: INFO）
   - KILL_FLAG_CLEAR_ON_START（本番で 1 にすると起動時に kill.flag を自動クリアする; 本番は 0 推奨）
5. データディレクトリ作成（必要に応じて）
   - data/, logs/ は起動処理で自動作成されることが多いですが、権限問題を避けるため事前に作成しておくと安心です。

注: .env の自動読み込みはデフォルトで有効。テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（主要コマンド例）

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証（.env / config/*.yaml の事前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告を失敗扱いにする

- ExecutionEngine を起動（バックグラウンド監視される発注エンジン）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db を使用します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 停止の通知は data/stop_requested.flag または data/kill.flag を書き込むことで行います。

- Monitoring を起動（ポーリング監視ループ）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に production の sqlite_path を使用（環境にかかわらず監視用 DB は本番 DB を指す設計）。
  - 監視ループを停止したい場合は data/stop_requested.flag を作成するとループが終わります。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite ファイルを指定可能（省略時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）。

- AI モジュールの実行例（プログラムから呼ぶ）
  - news_nlp.score_news(duckdb_conn, target_date, api_key=None)  # OPENAI_API_KEY を使用
  - ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

---

## 重要なファイル / フラグ（運用時）

- data/stop_requested.flag
  - run_execution / run_monitoring が存在を検知すると安全に停止動作を開始します（プロセス内でポーリングチェック）。
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine 停止の「最終手段」として使用。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で消す設定になるため、本番では 0 を推奨。
- data/execution.pid
  - ExecutionEngine が PID を書き込むためのファイルパス（Settings.pid_file_path で設定可）。
- logs/<app_name>.log
  - 日次ローテーションでログが保存されます（ログディレクトリは LOG_DIR またはデフォルト 'logs'）。

---

## 設定・環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（よく使う）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: AI 機能で使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- LOG_DIR: ログ保存先ディレクトリ
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1"=クリア、デフォルト "0"）

設定は .env に記述してください。対話ウィザード（config_setup）を推奨します。

---

## 開発者向けメモ

- ロギングは共通ユーティリティで統一的に設定されています（kabusys.utils.logging_setup.setup_logging）。
- プロセス優先度や CPU affinity は kabusys.utils.process_priority でプラットフォーム互換的に設定します。run_* スクリプトは起動直後に優先度を "high" に設定します。
- Monitoring は SQLite（監視ログ）を用い、init_monitoring_db() でスキーマを冪等的に初期化します。既存 DB に対するマイグレーション（列追加）ロジックも含まれます。
- AI 呼び出しは外部 API（OpenAI）へ行うため、テストでは _call_openai_api をモックすることを想定しています。
- DuckDB を使用する関数群は接続オブジェクトを受け取り、SQL と Python の組合せで処理を行います（再利用しやすい関数設計）。

---

## ディレクトリ構成（src/kabusys の主要ファイル）

- __init__.py
  - パッケージ定義・バージョン
- config.py
  - Settings クラス（環境変数の読み込み・検証・デフォルト）
- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - Monitoring 起動スクリプト
- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・DB ラッパー（MonitoringDB）
  - system_monitor.py: CPU/メモリ/ディスク・データ鮮度・PID チェック
  - trade_monitor.py: 注文ログチェック（滞留・約定異常）※（ファイル内に実装あり）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 管理
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - alert_manager.py: 通知管理（LINE などとの連携を想定）
- execution/
  - broker_factory.py: ブローカークライアント生成（環境別）
  - execution_engine.py: 発注実行エンジン（EngineConfig 等）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py: 発注管理・リスク管理
- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数算出・投資配分ロジック
  - risk_adjustment.py: セクター上限・レジーム乗数
- research/
  - factor_research.py: ファクター計算（momentum/volatility/value）
  - feature_exploration.py: 将来リターン・IC・統計サマリー
- ai/
  - news_nlp.py: ニュースセンチメント（OpenAI）→ ai_scores 書込
  - regime_detector.py: 市場レジーム判定（MA + マクロニュース）
- tools/
  - paper_verification_report.py: ペーパートレードのパフォーマンス検証出力
- utils/
  - logging_setup.py: ロギング設定ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定
  - その他ユーティリティ群

（上記は主要ファイルの概要。細かな実装はソースを参照してください）

---

## よくある運用フロー（例）

1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB にデータを投入（外部スクリプト / ETL）
4. 開発モードでエンジンを起動して挙動確認（KABUSYS_ENV=development）
5. ペーパートレードでロジック検証（KABUSYS_ENV=paper_trading）
6. モニタリング（python -m kabusys.run_monitoring）を常時稼働
7. リスクトリガーで kill.flag が書かれたら、本番エンジンを安全停止

---

## ライセンス・貢献

この README はコードベースの要約です。実運用前に必ずソース全体をレビューし、必要なテスト・監査を行ってください。  
機能追加・バグ修正は Pull Request を歓迎します。

---

必要であれば、README に含めるサンプル .env テンプレートやよくあるトラブルシュート（ログが出ない、DB パス権限エラー等）を追記します。どの程度の詳細を追加したいか教えてください。