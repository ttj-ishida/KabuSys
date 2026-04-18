# KabuSys

日本株向け自動売買システムの軽量な実装（ライブラリ兼実行スクリプト群）です。  
このリポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、発注実行（本番／ペーパートレード）、監視・アラート、ニュースNLP を組み合わせた構成になっています。

> 注: 本 README はソースツリー（src/kabusys）に含まれる主要モジュールを元に作成しています。

## プロジェクト概要
- DuckDB / SQLite をデータ層に用い、分析・永続化を分離しています。
- 実行モードにより本番（live） / ペーパートレード（paper_trading） / 開発（development）を切り替え可能。
- OpenAI を用いたニュースセンチメント評価・レジーム判定機能を実装。
- 監視（System / Trade / Risk）と Kill Switch による自動停止機構を備え、安全性を重視しています。
- 純粋関数群で構成されたポートフォリオ構築・リスク調整・ポジションサイズ算出モジュールを提供。

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて実ブローカーか MockBroker を切り替え（paper_trading 時は paper DB を使用）
  - ExecutionEngine をデーモン風に起動・停止管理（PID / stop フラグ）
- 監視ポーリング（run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、SQLite にログを蓄積
  - Kill Switch 評価、アラート通知トリガー
  - MONITOR_POLL_INTERVAL でポーリング間隔を設定可能
- 環境設定ウィザード（config_setup）
  - 対話式に .env を作成・更新
- 設定検証 CLI（validate_config）
  - 必須環境変数や config/*.yaml の妥当性チェック
- 研究用モジュール（research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン・IC（Information Coefficient）計算など
- ポートフォリオ構築（portfolio）
  - 候補選定、重み付け（等分・スコア基準）、ポジションサイズ計算、セクターキャップ適用、レジーム乗数
- AI モジュール（ai）
  - news_nlp: ニュース記事を OpenAI でスコアリングして ai_scores テーブルに保存
  - regime_detector: ma200 とマクロセンチメントの合成による市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを出力

## 必要条件
- Python 3.10 以上（typing の | 演算子を使用）
- 推奨パッケージ（pip 等でインストールしてください）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を行う場合に必要。オプション）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

（requirements.txt は本 README に含まれていません。適宜仮想環境を作成して上記パッケージをインストールしてください。）

例:
pip install duckdb psutil openai PyYAML

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージのインストール
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式ウィザードを利用（推奨）
     - python -m kabusys.config_setup
   - または手動でルートに .env を配置（.env.example がある想定）
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番でより厳密にチェックする場合: python -m kabusys.validate_config --strict
6. DB ディレクトリ作成
   - デフォルトでは data/ に以下ファイルが作成されます:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (監視用 SQLite)
     - data/paper_trading.db (paper_trading 用 SQLite、KABUSYS_ENV=paper_trading の場合使用)
   - 必要なら .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定

## 主な環境変数（主要なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行・挙動制御
  - KABUSYS_ENV: development / paper_trading / live（既定: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレード時の約定モード（instant | partial | never | reject）
  - OPENAI_API_KEY: OpenAI を使うモジュールで必要（ai/news_nlp, ai/regime_detector）
  - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: 各 DB ファイルパス
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などの監視関連

## 使い方（実行例）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジンを起動
  - python -m kabusys.run_execution
  - note: 実行中は data/execution.pid に PID を書き、停止は data/stop_requested.flag を作成すると検知して停止します。
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、data/paper_trading.db に記録します（本番 DB と完全分離）。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（例: export MONITOR_POLL_INTERVAL=30）

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Kill Switch / 停止フラグ
  - 監視モジュールや外部操作で data/kill.flag を生成すると ExecutionEngine に停止アクションを促します（KillSwitch）。
  - run_execution/run_monitoring の停止は data/stop_requested.flag を作成しても行えます。

## 開発者向け（モジュールの利用例）
- ポートフォリオ関連（純粋関数でテスト容易）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- 研究関連
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - これらは DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算します。
- AI
  - from kabusys.ai import score_news
  - OpenAI API キーが必要。テスト時は _call_openai_api をモックして安定化できます。

## ログ
- ロギングは kabusys.utils.logging_setup.setup_logging を通じて統一して設定されます。
- デフォルト: logs/<app_name>.log（日次ローテーション、30日保持） と標準出力（stdout）。
- ログディレクトリは環境変数 LOG_DIR または引数で上書き可能。

## 注意事項 / 運用上のポイント
- KABUSYS_ENV=live の場合は本番として振る舞うため、設定（APIキー・LINE通知設定等）を慎重に確認してください。
- ペーパートレードと本番は DB を分離する設計になっています。ペーパートレード時でも本番 DB を誤って操作しないよう .env を確認してください。
- OpenAI の呼び出しはネットワーク障害やレート制限を考慮してリトライ／フォールバック設計が組み込まれていますが、API キーや利用制約には注意してください。
- ローカルでの cron / systemd 等での運用を想定しています。プロセス優先度設定（高優先度）を行うため、実行環境の権限に依存します（psutil を使用）。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env の自動ロード）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py             — ニュース記事を OpenAI でスコア化
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）

  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定・重み計算
    - risk_adjustment.py      — セクターキャップ／レジーム乗数
    - position_sizing.py      — 発注株数計算（単元丸め・上限対応）

  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value 計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ

  - monitoring/
    - monitoring_db.py        — SQLite テーブル定義・ラッパー
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （trade 監視、ソースに含まれる想定）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の作成・評価
    - monitoring_engine.py    — 各 Monitor を束ねる実行ループ
    - alert_manager.py        — （アラート送信の抽象化、ソースに含まれる想定）

  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py       — Broker クライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/ (DB helpers)
    - monitoring_db.py

  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパー検証レポート出力

  - utils/
    - logging_setup.py        — ロギング初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

（注）上記はソース中にある主要モジュールのスナップショットです。さらに細かい補助モジュールや未列挙のファイルが存在します。

---

必要であれば、本 README をベースに以下の追加ドキュメントも作成できます:
- 運用手順書（systemd / systemctl / docker での運用例）
- テスト手順（ユニットテスト・統合テストの例）
- configuration reference（.env.example と各設定の説明）
- API 仕様（ExecutionEngine / BrokerClient のインターフェース）

どのドキュメントを優先して作成するか教えてください。