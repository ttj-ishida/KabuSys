# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・研究基盤「KabuSys」のコア実装です。  
主要コンポーネントとして、発注実行エンジン、監視（Monitoring）、ポートフォリオ構築・リスク制御、調査用ファクター計算、AI を使ったニュース NLP 等を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- ExecutionEngine：発注ロジック（本番 / ペーパートレード対応）
- Monitoring：システム稼働状況・注文状況・リスクの定期監視とアラート / Kill Switch
- Portfolio：銘柄選定、重み付け、株数決定（単元丸め・リスク制約）
- Research：DuckDB 上で動くファクター計算・解析ユーティリティ
- AI：ニュースのセンチメント評価・市場レジーム判定（OpenAI 使用）
- Tools：検証レポート等の補助スクリプト
- Utils：ロギング設定・プロセス優先度設定等のユーティリティ

設計上の特徴：
- .env による環境設定（自動ロード機能あり）
- 本番 DB（monitoring.db）とペーパートレード DB（paper_trading.db）を分離
- DuckDB を分析用途に使用
- OpenAI を用いた NLP 機能は API キーが必要（フォールバック / フェイルセーフ実装あり）
- ログは console（stdout）とファイル（日次ローテーション）へ出力

---

## 主な機能一覧

- ExecutionEngine（run_execution.py）
  - 実際の発注処理（kabuステーション API）または MockBroker によるペーパートレード
  - リスク管理（RiskManager）、オーダー管理、再整合処理などを組み合わせて動作
  - PID ファイル / 停止フラグ監視（data/execution.pid, data/stop_requested.flag）

- Monitoring（run_monitoring.py + monitoring/*）
  - CPU/メモリ/ディスク、プロセス稼働チェック、データ鮮度チェック
  - 注文滞留・約定異常・リスク（ドローダウン・ポジション上限）監視
  - Kill Switch（条件に応じて data/kill.flag を書いて ExecutionEngine 停止を促す）
  - 監視ログは SQLite（monitoring.db）へ永続化

- Portfolio（portfolio/*）
  - 候補銘柄選定、等金額・スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数（bull/neutral/bear）

- Research（research/*）
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー

- AI（ai/*）
  - news_nlp: ニュース記事を集約して LLM（gpt-4o-mini）で銘柄別センチメントを計算
  - regime_detector: ETF（1321）MA200乖離とマクロニュースを組み合わせて市場レジーム判定

- Tools
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを生成

---

## 依存関係（主なパッケージ）

以下はコード内で利用されている主要パッケージです。実際の requirements.txt はプロジェクト側で管理してください。

- Python 3.8+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイル検証を行う場合に任意で必要）

---

## セットアップ手順（ローカル）

以下は基本的なローカルセットアップ手順の例です。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   （実際のプロジェクトでは requirements.txt を用意している想定）

4. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または手動で .env を作成（リポジトリルートに配置）
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 推奨設定例（最小）
       - JQUANTS_REFRESH_TOKEN=your_token_here
       - KABU_API_PASSWORD=your_password_here
       - KABUSYS_ENV=development
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - LOG_LEVEL=INFO

   注意: 自動で .env が読み込まれます（env 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict を付ける

6. 必要ディレクトリ作成（通常は自動作成されるが手動で作る場合）
   - mkdir -p data logs

---

## 実行方法（使い方）

以下は主要な起動 / CLI の使い方例です。

- Execution Engine（発注処理）を起動
  - 通常（開発環境）
    - python -m kabusys.run_execution
  - ペーパートレードで起動（環境変数で切替）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレード時は MockBroker を使用し、デフォルトで data/paper_trading.db に記録されます。
  - 本番実行（注意: 実際に発注されます）
    - KABUSYS_ENV=live python -m kabusys.run_execution

  - 停止方法
    - run_execution スクリプトは data/stop_requested.flag の存在を監視して安全に停止します。停止させたい場合は touch data/stop_requested.flag（または同等の操作）を行ってください。
    - Kill Switch による停止は data/kill.flag を書き込みます（KillSwitch が自動的に生成）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルト: 60 秒
  - 監視プロセスも data/stop_requested.flag を見て終了します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 戻り値（exit code）: エラーがあれば 1 を返します。--strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先して DB を指定）

- AI 機能（ニュース NLP / レジーム判定）
  - 使用には OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
  - score_news / score_regime を呼ぶことで DuckDB のテーブルを参照して結果を保存します
  - API 呼び出しはリトライやフォールバックを備えていますが、API キー未設定時には ValueError が発生します

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — development | paper_trading | live （デフォルト: development）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — Execution pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch が書き込むフラグ（デフォルト: data/kill.flag）

- ロギング
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR — ログディレクトリ（デフォルト: logs/）

- AI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）

- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト: 60）

- その他
  - KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアする (0/1, 本番では 0 推奨)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env の自動ロードを無効化

---

## 停止 / 緊急停止（Kill Switch）

- run_execution や run_monitoring はプロセス内で data/stop_requested.flag を確認し、存在すれば安全に終了します（手動停止用）。
- Monitoring の KillSwitch はルール（ドローダウン超過・ポジション上限超過等）により data/kill.flag を書き込みます。ExecutionEngine は起動時の設定によりこの kill.flag を参照・クリアします。
- kill.flag はデフォルトで Settings.kill_flag_path（data/kill.flag）に配置されます。

---

## ディレクトリ構成（概観）

以下は主要なファイルとディレクトリの一覧（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - ...（上記）
  - tools/
    - paper_verification_report.py

- data/ (実行時に使用することが多いディレクトリ — DBやフラグファイルを格納)
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用)
  - kill.flag / stop_requested.flag / execution.pid

- logs/
  - execution.log
  - monitoring.log
  - ...（日次ローテーションで保持）

---

## 開発上の注意事項

- .env はセキュア情報（APIキー等）を含むため Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config の警告は重要です。
- AI 機能は API 呼び出しを行うため利用量とコストに注意してください。API の失敗はフェイルセーフでフォールバックする設計になっていますが、挙動は事前に把握しておいてください。
- DuckDB のテーブル構造（prices_daily, raw_financials, raw_news, ai_scores 等）は Research / AI モジュールが前提としています。データを投入する ETL が別に必要です。

---

## よく使うコマンドまとめ

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

必要に応じて README を拡張します。特に、実行用の requirements.txt、データベース初期化手順、ETL スクリプト、ExecutionEngine の設定（strategy / execution_config.yaml 等）を追加したい場合は、その旨を教えてください。