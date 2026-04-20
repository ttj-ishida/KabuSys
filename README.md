# KabuSys

日本株向け自動売買・リサーチ基盤ライブラリ / 実行スクリプト群

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買エンジン、監視（Monitoring）、リサーチ（ファクター計算・特徴量探索）、AI 支援（ニュースの NLP スコアリング・レジーム判定）などを含む統合的なコードベースです。  
モジュールは実運用を想定した堅牢な設計（DB 永続化、冪等性、バックオフ、フェイルセーフ）を特徴としています。

主な設計方針：
- 本番 / ペーパートレードを環境スイッチで分離（KABUSYS_ENV）
- DuckDB を用いた分析向けの時系列データ処理
- SQLite を監視・トレードログ保存に利用
- OpenAI API を用いたニュース NLP（オプション）
- モジュールは純粋関数で記述され、ユニットテストしやすい設計

---

## 機能一覧

- 実行系（ExecutionEngine）
  - ブローカークライアント（実口座 / モック切替）
  - 注文管理・オーダーリポジトリ・リスク管理
  - ExecutionEngine をデーモン的に実行
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態/データ鮮度チェック
  - TradeMonitor / RiskMonitor：注文滞留、約定異常、ドローダウン等の監視
  - KillSwitch：閾値超過時に停止フラグ（data/kill.flag）を発行
  - MonitoringEngine：上記をまとめてポーリング、通知連携可能
- 永続化
  - monitoring_db：監視ログ（system_status/trade_logs/positions/risk_logs/dashboard）を SQLite に保存
- リサーチ
  - factor_research：モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
  - feature_exploration：将来リターン計算、IC（情報係数）、統計サマリー
- ポートフォリオ構築
  - 候補選定、等重/スコア重み算出、セクター上限適用、ポジションサイズ計算（単元丸め・キャップ適用）
- AI（任意）
  - news_nlp：OpenAI を用いて銘柄別ニュースセンチメントを算出・ai_scores に保存
  - regime_detector：ETF とマクロ記事を組み合わせたレジーム判定を書き込み
- ツール
  - config_setup：.env の対話式ウィザードで初期設定を作成
  - validate_config：環境変数 / config/*.yaml の起動前チェック
  - paper_verification_report：ペーパートレード DB から性能レポートを生成

---

## セットアップ手順

※ 以下はローカル開発 / 実行向けの最小手順例です。

1. システム要件
   - Python 3.9+
   - SQLite（標準ライブラリ）
   - 必要な Python パッケージ（下記参照）

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml
   - PyPI パッケージ名: duckdb, psutil, openai, PyYAML
   - （AI 機能を使わない場合は openai は不要。YAML 検証を行わない場合は PyYAML は必須ではありません）

3. プロジェクトルートで .env を作成
   - 対話式で作る: python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に以下の必須変数を設定：
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 主要な環境変数（デフォルト値は右記）:
     - KABUSYS_ENV: development | paper_trading | live （default: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - OPENAI_API_KEY: OpenAI 利用時に必要
     - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒） — run_monitoring.py では環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定挙動）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict オプションで警告をエラー扱い可能

5. データディレクトリ作成
   - logs/ および data/ は自動作成されることが多いですが、権限などで失敗することがあるため事前に作成すると確実です。

---

## 使い方

基本的にはモジュールを直接 import して利用するか、付属のエントリスクリプトを実行します。

1. 実行エンジン（ExecutionEngine）の起動
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
     - PID ファイル: data/execution.pid（設定による変更可）
     - 停止: data/stop_requested.flag を作成すると安全停止処理が走ります（run_execution/run_monitoring の両方が参照）

2. 監視ループの起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（デフォルト 60）
   - 監視は本番 sqlite_path を環境にかかわらず使用（monitoring は本番 DB を参照する仕様）
   - 停止フラグ (data/stop_requested.flag) によりループ終了

3. 設定ウィザード / 検証
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config [--strict]

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

5. AI 周り
   - OpenAI を使う機能（news_nlp.score_news / regime_detector.score_regime）を利用する場合は OPENAI_API_KEY を設定してください。
   - AI の呼び出しはリトライ・バックオフ・レスポンス検証を行いますが、API キーがない場合は例外を投げます。

6. ログ
   - ロギングは kabusys.utils.logging_setup.setup_logging により統一されます。
   - デフォルトログディレクトリ: logs/
   - ログレベルは LOG_LEVEL 環境変数で指定可

7. 停止 / Kill Switch
   - KillSwitch（監視側）により致命的なリスク（ドローダウン超過等）が検出されると data/kill.flag が作成され、ExecutionEngine に停止を促します。
   - ExecutionEngine 側は起動時に kill.flag をクリアする設定（KILL_FLAG_CLEAR_ON_START=1）があるため、本番では 0 を推奨します。

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (default: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI を使う場合に必須
- LOG_LEVEL: INFO（または DEBUG 等）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視関連

---

## ディレクトリ構成（抜粋）

プロジェクト主なファイル・ディレクトリ構成（src/kabusys 以下を中心に記載）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite テーブル作成 / MonitoringDB クラス
    - monitoring_engine.py    — 複数監視を束ねるエンジン
    - system_monitor.py       — システム監視（CPU/メモリ/データ鮮度）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - (trade_monitor.py, alert_manager.py 等を想定)
  - execution/
    - execution_engine.py     — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + ETF 指標）
  - data/ (実行時に使われるファイル群、デフォルト)
    - monitoring.db (default: data/monitoring.db)
    - paper_trading.db (paper_trading 用)
    - kill.flag, stop_requested.flag, execution.pid などの制御ファイル
  - config/
    - system_config.yaml, data_config.yaml, ... （テンプレート / 参考）

---

## 開発者向けメモ / トラブルシューティング

- .env は絶対にリポジトリにコミットしない（config_setup のヘッダにも記載）
- YAML 検証に PyYAML が必要。インストールされていないと validate_config は YAML 検証をスキップします。
- OpenAI 呼び出しはネットワーク・API レート制限の考慮が入っていますが、API キーと料金設定を確認してください。
- DuckDB/SQLite のファイルパスは Settings で制御可能。監視は本番 sqlite_path を常に使用する点に注意（monitoring 側）。
- run_execution/run_monitoring は stop flag（data/stop_requested.flag）を監視して安全に終了します。手動停止時は flag を作成するか Ctrl+C で終了してください。
- process_priority の設定は権限によって失敗することがあります（警告ログが出るのみ）。

---

必要に応じて README に追記します。特に運用手順（systemd ユニット例、Dockerfile、CI/CD）や config/*.yaml の説明、ブローカー実装の詳細などを追加したい場合は要件を教えてください。