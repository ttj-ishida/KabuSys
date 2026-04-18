# KabuSys — README

概要
- KabuSys は日本株向けの自動売買 / 研究 / 監視ツール群です。
- 主な機能は、ExecutionEngine による注文実行（実口座／ペーパートレード）、システム監視・リスク監視、ファクター計算・研究、ニュース NLP を用いたセンチメント解析、ペーパートレード検証レポート生成などです。
- 設定は環境変数（.env）で行い、SQLite / DuckDB をデータ永続化に使用します。

主な特徴（機能一覧）
- 実行制御
  - ExecutionEngine（本番／ペーパートレード切替）
  - BrokerClientFactory によるブローカークライアント生成（KABUSYS_ENV により Mock を使用）
- 監視・安全装置
  - SystemMonitor: CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor / RiskMonitor: 滞留注文・約定異常・ドローダウン・ポジション上限監視
  - Kill Switch: 条件で停止フラグを書き込み ExecutionEngine を停止
  - MonitoringEngine: 上記監視を束ねて定期実行・アラート送信
- ポートフォリオ構築（純粋関数）
  - 候補選定、重み付け（等金額・スコア）、ポジションサイズ計算、セクター制限、レジーム補正
- 研究用モジュール
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）
- ニュース NLP / レジーム判定（OpenAI）
  - raw_news を LLM で評価して ai_scores へ保存
  - ETF を用いた MA200 乖離 + マクロニュースで市場レジームを判定
- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

依存（主な Python パッケージ）
- python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証時に使用）
- （その他、実際のブローカー SDK 等が必要になる場合があります）

セットアップ手順（開発／ローカル利用向け）
1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ...
   - cd <project_root>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML

   （requirements.txt があれば `pip install -r requirements.txt` を利用）

4. .env の作成（対話式）
   - python -m kabusys.config_setup
   - ウィザードに従い J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV 等を設定します。
   - 生成された .env は絶対に VCS にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があればメッセージに従って修正します。
   - `--strict` を付けると警告も失敗扱いになります。

使い方（実行例）
- 実行スクリプト（パッケージ形式で実行）
  - 監視ループを起動:
    - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
    - python -m kabusys.run_monitoring
  - ExecutionEngine を起動:
    - KABUSYS_ENV によって実口座／ペーパートレードが切り替わります
    - python -m kabusys.run_execution

- Paper Trading（分離された DB を使用）
  - KABUSYS_ENV=paper_trading を設定すると、MockBrokerClient を使用し
    data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）へ記録します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- ログ
  - logs/<app_name>.log に日次ローテートでログが保存されます（ログディレクトリは LOG_DIR 環境変数で変更可）
  - setup_logging(app_name="execution") により統一されたログ設定が使われます

- 停止・Kill Switch
  - 実行停止用のフラグ:
    - run_monitoring / run_execution はそれぞれ data/stop_requested.flag による停止を監視します
  - Kill Switch トリガーが発生すると data/kill.flag に理由を書き込みます（ExecutionEngine はこれを見て停止）

主な環境変数（代表）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（default: logs）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector 等で使用）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、run_monitoring で利用）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（詳細は config_setup ウィザード参照）

注意と運用上のポイント
- KABUSYS_ENV=live の場合は本番設定です。LINE 通知設定や kill flag の扱いを十分に確認してください。
- Monitoring は設定にかかわらず本番 sqlite_path（default: data/monitoring.db）を使用します（監視ログは本番 DB に記録）。
- run_execution は paper_trading モードのときに DB を分離します（data/paper_trading.db）。
- OpenAI を利用する機能はネットワーク依存・API コストが発生します。API キーの管理に注意してください。
- ロギングディレクトリや data/ ディレクトリは実行時に自動作成されますが、権限設定等に注意してください。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START）は本番では 0 を推奨します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env の対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視ログ等）
    - system_monitor.py      — システム監視（CPU/メモリ/データ鮮度）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - trade_monitor.py       — （滞留注文等の監視）※実装ファイルを参照
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - kill_switch.py         — Kill Switch（flag ファイル）
    - alert_manager.py       — アラート送信（LINE 等）※実装ファイルを参照
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（注文処理ループ）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文履歴の永続化
    - broker_factory.py      — ブローカークライアント生成（Mock/実ブローカー）
    - reconciler.py          — 注文状態の差分整合処理
    - risk_manager.py        — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み付け
    - position_sizing.py     — 株数計算・資金配分
    - risk_adjustment.py     — セクター上限 / レジーム乗数
  - research/
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（MA200 + マクロ NLP）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/                    — 実行時生成される DB / flag / pid 等（default）
  - logs/                    — ログファイル出力先（default）

補足（開発者向け）
- モジュール設計は副作用を抑え、DB 接続やクライアントを呼び出し元で注入する形を基本としています（単体テストが容易）。
- ai モジュールの API 呼び出し部分はテスト時に差し替え可能な実装になっています（関数を patch する等）。
- DuckDB をデータ分析用に利用しており、prices_daily / raw_financials 等のテーブルを参照してファクター計算を行います。

問題報告・貢献
- バグ報告や改善提案は Issue を作成してください。Pull Request を歓迎します。

以上。README の内容はコードコメントと実装に基づいて要約しています。必要なら実際の開発環境・運用手順に合わせて調整してください。