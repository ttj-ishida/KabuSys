# KabuSys

日本株自動売買システムのライブラリ / 実行スクリプト群のドキュメントです。  
この README はリポジトリ内の主要モジュール（実行エントリ、設定管理、監視、ポートフォリオ構築、リサーチ、AI ヘルパー等）に基づいて作成しています。

注意: 実行には Python 環境といくつかのネイティブモジュール（duckdb, psutil, openai など）が必要です。以下のセットアップ手順を参照してください。

## プロジェクト概要

KabuSys は日本株向けの自動売買システムで、主に以下の機能群を提供します。

- 注文実行エンジン（ExecutionEngine）およびブローカー抽象化（実際の取引 or ペーパートレード）
- システム監視（SystemMonitor）・トレード監視（TradeMonitor）・リスク監視（RiskMonitor）とそれらを束ねる MonitoringEngine
- ポートフォリオ構築（候補選定・重み付け・位置サイズ計算・セクター制限・レジーム乗数）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）および特徴量探索ユーティリティ
- ニュースを使った NLP 評価（OpenAI を使ったセンチメントスコア生成）と市場レジーム判定
- ペーパートレード検証レポート生成ツール
- .env 運用支援ウィザードと起動前設定検証ツール

設計上のポイント:
- 設定は .env ファイル / 環境変数から読み込み（プロジェクトルート自動検出）。.env の自動ロードは無効化可能。
- Paper trading（KABUSYS_ENV=paper_trading）は本番 DB と分離された専用 SQLite を使用。
- 監視機能はログ・監視 DB（SQLite）に書き込み、必要に応じて ExecutionEngine に停止シグナル（kill.flag）を出せる。

---

## 機能一覧（抜粋）

- 実行関連
  - run_execution: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時はモックブローカーと専用 DB を使用。
  - run_monitoring: SystemMonitor をポーリング実行し、監視ログを保持。

- 監視
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存・データ鮮度をチェックし monitoring DB に記録
  - TradeMonitor / RiskMonitor / MonitoringEngine: 注文滞留・約定異常・ドローダウン・ポジション上限などを監視
  - KillSwitch: 条件により data/kill.flag を書き込む（Execution 停止指示）

- ポートフォリオ構築
  - 候補選定、等金額/スコア重み・スコア加重、セクター上限の適用、位置サイズ（株数）計算（単元株丸め、aggregate cap）

- リサーチ
  - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily 等からファクターを計算
  - calc_forward_returns / calc_ic / factor_summary: 特徴量解析支援関数

- AI（ニュース関連）
  - news_nlp.score_news: raw_news を集約して OpenAI に投げ、銘柄ごとのスコアを ai_scores テーブルに保存
  - regime_detector.score_regime: ETF とニュースの組合せで市場レジーム（bull/neutral/bear）を判定して保存

- ツール
  - config_setup: .env を対話式で生成・更新するウィザード
  - validate_config: .env と config/*.yaml を起動前に検証
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを出力

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし Python 仮想環境を作成
   - 推奨: Python 3.10+
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須（代表的なもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証であると便利）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （実際の requirements.txt がある場合はそちらを使用してください）

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成し、必須変数を設定:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの準備
   - デフォルトで使用するパス:
     - DuckDB: data/kabusys.duckdb (DUCKDB_PATH)
     - 監視用 SQLite: data/monitoring.db (SQLITE_PATH)
     - ペーパートレード SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
   - 実行時に自動で作成される箇所もありますが、適切な権限を確認してください。

---

## 使い方（主要なコマンド）

- 実行エンジンを起動（通常 / 本番）
  - python -m kabusys.run_execution
  - 実行前に KABUSYS_ENV を設定:
    - development: 発注なし（ローカル開発）
    - paper_trading: モックブローカー + data/paper_trading.db を使用
    - live: 実際のブローカーで発注（十分な注意が必要）
  - ExecutionEngine は起動時に PID ファイル（data/execution.pid）を作成します。
  - 停止方法:
    - data/stop_requested.flag を作成すると run_execution と run_monitoring がそれを検知して終了処理します。
    - Kill スイッチで発動した場合は data/kill.flag が作成され、ExecutionEngine に停止指示を出します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用（KABUSYS_ENV に関係なく本番監視 DB を参照）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も失敗扱い

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーを引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

ログ:
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます。
- デフォルトログディレクトリ: logs/
- 各アプリ（execution, monitoring 等）は logs/<app_name>.log に日次ローテーションで出力（30日保持）。

---

## 主な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時必須)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート通知)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL (デフォルト: INFO)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB: デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード DB: デフォルト data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading の挙動)
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

---

## 停止・キルフロー

- run_execution と run_monitoring は data/stop_requested.flag の存在をチェックします。ファイルを作るとループ終了処理が開始されます。
- KillSwitch（監視側）は条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側はこれを検出して安全に停止します。
- run_execution は起動時に kill.flag が既に立っている場合は起動をスキップします（誤って起動しないよう保護）。

---

## ディレクトリ構成（主要ファイル）

想定ルート: src/kabusys 以下

- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py      — SystemMonitor ポーリング起動スクリプト

以下サブパッケージ（主要ファイルのみ抜粋）:

- ai/
  - news_nlp.py           — ニュース NLP（OpenAI）スコアリングロジック
  - regime_detector.py    — 市場レジーム判定
- monitoring/
  - monitoring_db.py      — SQLite 監視 DB スキーマ + ラッパー
  - system_monitor.py
  - trade_monitor.py      — （ファイル内に実装あり）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py      — アラート送信管理（LINE 等）（実装参照）
- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

補助ディレクトリ（実行時に使用／作成）
- data/                  — DB ファイル (.duckdb/.db)、flag、pid など
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/                  — ログファイル（logs/<app_name>.log）

---

## 開発者向けメモ / 実装の注意点

- Settings クラスはプロジェクトルート（.git / pyproject.toml）を起点に .env を自動ロードします。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution / run_monitoring は起動直後にプロセス優先度を高く設定しようとします（psutil を使用）。権限不足の場合はワーニングにフォールバックします。
- Monitoring は監視用 SQLite のスキーマを起動時に冪等で作成・マイグレーションします（monitoring_db.init_monitoring_db）。
- AI 呼び出しはリトライロジック・JSON バリデーション・スコアクリップ等を備え、失敗時はフェイルセーフで進行します（部分成功の保護や DB 書き込みを冪等にする実装）。
- DuckDB に対する実装は SQL を多用しており、prices_daily/raw_financials/raw_news 等のテーブル構造に依存します。データ投入の前にスキーマが揃っていることを確認してください。
- 設定検証（validate_config）は起動前チェックに有効です。本番 environment（KABUSYS_ENV=live）では特に LINE 通知設定や Kill Switch 設定を確認してください。

---

README はここまでです。追加で以下が必要であれば教えてください:
- 実行方法の具体的な例 (.env サンプル、systemd / supervisor 用のユニットファイル例)
- 開発用テスト・CI 設定のテンプレート
- 各モジュールの詳しい API ドキュメント（関数ごとの使用例）