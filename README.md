# KabuSys

日本株向け自動売買システムの一部実装です。戦略・ポートフォリオ構築・実行エンジン・監視・研究・AI 補助モジュールを含みます。

以下はこのリポジトリの概観、セットアップ手順、主要な使い方、及びディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのフレームワークで、主に以下を目的とします：

- 市場データ（DuckDB）を用いたファクター計算・研究（research）
- ポートフォリオ構築（候補選定／重み計算／ポジションサイズ算出）
- 実行エンジン（ExecutionEngine）による注文発行（本番 / ペーパートレード切替）
- 実行系の監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ニュースの NLP によるセンチメントスコアリング（OpenAI）
- 運用・検証用ツール（設定ウィザード、設定検証、Paper Trading 検証レポート 等）

設計方針：
- モジュール化・純粋関数の採用（ポートフォリオ・リスク計算等）
- 本番 DB とペーパートレード DB の完全分離
- ルックアヘッドバイアスを避ける実装（日時参照は呼び出し側で制御）
- OpenAI 呼び出しはフォールバック・リトライ等のフェイルセーフを実装

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - 環境に関わらず監視用 sqlite（SQLITE_PATH）のパスを使用
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視コンポーネント
  - SystemMonitor：CPU/メモリ/Disk/プロセス・データ鮮度チェック
  - TradeMonitor / RiskMonitor：注文／ドローダウン等の監視、kill.flag 書き込み
  - MonitoringDB：SQLite に対する永続化レイヤ
- ポートフォリオ建設（選定・重み付け・ポジションサイズ算出・セクターキャップ）
- リサーチ（モメンタム／バリュー／ボラティリティ等のファクター計算）
- AI モジュール
  - news_nlp：ニュース記事を OpenAI でスコアリングして ai_scores に格納
  - regime_detector：MA とマクロセンチメントを合成して市場レジームを判定
- 運用支援ツール
  - tools/paper_verification_report.py：ペーパートレード DB の検証レポート生成

---

## 前提条件

- Python 3.10 以上（typing の union 型 | を使用）
- 必要な Python パッケージ（後述）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
  - その他（プロジェクトで利用するモジュールに依存）

推奨：
- 仮想環境（venv / virtualenv / conda）を使用すること

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動：
   - git clone ... && cd <repo>

2. 仮想環境作成（例）：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール：
   - pip install duckdb psutil openai
   - PyYAML を使いたい場合：pip install pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を利用）

4. 環境ファイルの作成：
   - python -m kabusys.config_setup
     → 対話形式で .env を生成／更新します（.env は絶対に Git にコミットしないでください）。

5. 設定検証（推奨）：
   - python -m kabusys.validate_config
   - エラー/警告を確認。--strict を付けると警告も失敗扱いになります。

6. DB・データディレクトリの準備（必要に応じて）：
   - デフォルトの DuckDB/SQLite は data/ 以下：
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

   スクリプト実行時に自動で親ディレクトリを作成する場合がありますが、権限等に注意してください。

---

## 必須 / 主な環境変数

必須：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション（デフォルト値あり）：
- KABUSYS_ENV: development | paper_trading | live  (default: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ保存先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- PAPER_FILL_MODE: instant | partial | never | reject  (paper_trading の約定挙動)
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）

---

## 使い方

基本的なコマンド例：

- 設定ウィザード（.env 作成）：
  - python -m kabusys.config_setup

- 設定検証：
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動：
  - python -m kabusys.run_execution
  - 動作：
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録
    - 実行中は data/execution.pid に PID を書き込む
    - data/stop_requested.flag が存在するとエンジンは停止します

- 監視ループ起動：
  - python -m kabusys.run_monitoring
  - 動作：
    - SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、監視ログを SQLITE_PATH に保存
    - MONITOR_POLL_INTERVAL でポーリング間隔を調整（秒）
    - data/stop_requested.flag があると監視ループを終了

- Paper Trading 検証レポート（ツール）：
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（プログラムから利用）：
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb 接続
    - api_key: 指定しない場合 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

終了 / 停止制御：
- ExecutionEngine を安全に停止させるには監視コンポーネント等が data/kill.flag を作成します（KillSwitch）。
- 手動で停止を要求する場合は data/stop_requested.flag を作成すると起動スクリプトが終了します。

ログ：
- デフォルトで stdout に出力しつつ logs/<app_name>.log に日次ローテートで保存されます（logs/ ディレクトリに出力）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
  - パッケージのメタ情報（__version__ 等）

- config.py
  - .env 自動ロード・Settings クラス（環境変数アクセスラッパ）

- config_setup.py
  - 対話式 .env 生成ウィザード

- validate_config.py
  - 設定検証 CLI（環境変数・config/*.yaml の基本チェック）

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / paper_trading 切替、pid/stop フラグ処理）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）

- monitoring/
  - monitoring_db.py
    - SQLite を使った監視ログの永続化（テーブル初期化・読み書き）
  - system_monitor.py
    - CPU/メモリ/Disk/データ鮮度/プロセス監視
  - trade_monitor.py (存在)
    - 注文滞留・約定異常検出（ソース参照）
  - risk_monitor.py
    - ドローダウン・ポジション上限監視（KillSwitch に連携）
  - kill_switch.py
    - kill.flag 書き込みロジック
  - monitoring_engine.py
    - 各 Monitor を束ねて運用するエンジン
  - alert_manager.py (存在)
    - アラート通知管理（LINE 等に送信する実装を想定）

- execution/
  - ExecutionEngine, OrderManager, Reconciler, RiskManager, BrokerFactory など実行に関する実装（実際の注文発行ロジックはここに）

- portfolio/
  - portfolio_builder.py
    - 候補選定・重み計算（等金額・スコア加重）
  - position_sizing.py
    - 株数決定・利用可能現金に基づくスケーリング・単元丸め等
  - risk_adjustment.py
    - セクター制限・レジーム乗数計算

- research/
  - factor_research.py
    - Momentum / Volatility / Value 等のファクター算出（DuckDB 経由）
  - feature_exploration.py
    - 将来リターン計算・IC（情報係数）・統計サマリ

- ai/
  - news_nlp.py
    - ニュース記事をまとめて OpenAI に送信し銘柄ごとにスコア化、ai_scores に書き込み
  - regime_detector.py
    - MA200 とマクロセンチメントの合成によるレジーム判定

- tools/
  - paper_verification_report.py
    - ペーパートレード DB を解析し検証レポートを生成

- utils/
  - logging_setup.py
    - アプリケーション共通のログ設定（コンソール + 日次ファイルローテーション）
  - process_priority.py
    - プロセス優先度 / CPU affinity 設定ユーティリティ

その他：
- config/*.yaml: 設定テンプレート（存在しない場合は生成ツールで作成）

---

## 運用上の注意

- .env に機密情報（API トークン / パスワード）を保存する場合、絶対に Git へコミットしないこと。
- KABUSYS_ENV=live の設定時は特に注意（本番発注が発生します）。validate_config は追加の警告を出します。
- OpenAI API を使用する機能は API キーとコストに留意してください。API のレート制限やエラーはリトライ・フェイルセーフで扱われますが、運用時には監視が必要です。
- データベース・ログディレクトリのパーミッションに注意。ログディレクトリ作成に失敗するとファイル出力は無効になります（コンソール出力は継続）。

---

必要であれば README にチュートリアル（データの投入、簡単なエンドツーエンドの起動手順）や、各モジュールのより詳細な API ドキュメントを追加します。どの部分を詳しくしたいか教えてください。