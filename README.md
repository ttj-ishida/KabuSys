# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なプロジェクトです。  
このリポジトリは注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI ベースのニュース解析などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

- 注文実行（ExecutionEngine）：
  - 実際のブローカー（kabuステーション）またはペーパートレーディング用モックを使って発注を行う。
  - 実行は環境変数 `KABUSYS_ENV` に依存（`development` / `paper_trading` / `live`）。
- 監視（Monitoring）：
  - システム稼働状況、ポジションや注文の監視、Kill Switch（閾値超過で execution を停止するフラグ）などを実装。
  - SQLite に監視ログを永続化。
- ポートフォリオ構築：
  - 候補選定、配分（等金額 / スコア加重 / リスクベース）、セクター上限やレジーム補正などを含む純粋関数群。
- リサーチ：
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）と特徴量探索ユーティリティ。
- AI モジュール：
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集計（ai_scores 保存）や市場レジーム判定。
  - API 呼び出しは堅牢なリトライ／フォールバック設計。
- ツール類：
  - `.env` 対話式ウィザード、設定検証 CLI、ペーパートレード検証レポート生成など。

---

## 主な機能一覧

- 実行系
  - run_execution.py：ExecutionEngine 起動スクリプト（PID / stop フラグ処理、paper_trading 分離）
- 監視系
  - run_monitoring.py：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - MonitoringEngine：System / Trade / Risk モニタをまとめる
  - KillSwitch：kill.flag による停止指示の発行
  - MonitoringDB：監視用 SQLite テーブル定義と読み書き
- ポートフォリオ
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ
  - DuckDB 接続でのファクター計算（momentum, volatility, value）
  - forward returns / IC（スピアマン）計算、統計サマリ
- AI
  - news_nlp.score_news：ニュース記事から銘柄ごとのセンチメントを取得して ai_scores テーブルへ書き込み
  - regime_detector.score_regime：ETF の MA200 とマクロニュースを合成して市場レジーム判定と保存
- ユーティリティ
  - config_setup.py：対話式 .env 作成ウィザード
  - validate_config.py：環境変数 / config/*.yaml の事前検証
  - tools.paper_verification_report：ペーパートレード検証レポート生成

---

## セットアップ手順

推奨 Python バージョン: 3.10+

1. リポジトリをクローンして環境を用意
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   ```

2. 必要なパッケージをインストール（例）
   - 最低限:
     - duckdb
     - psutil
     - openai
   - validate_config の YAML 検証を有効化する場合:
     - PyYAML
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

3. .env の用意（対話式推奨）
   ```
   python -m kabusys.config_setup
   ```
   必須の環境変数（対話ウィザードや `.env.example` を参照）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   重要な環境変数（代表例）:
   - KABUSYS_ENV: development | paper_trading | live (default: development)
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時に使用)
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合）

   自動ロード:
   - プロジェクトルートに `.env` / `.env.local` があれば自動的に読み込まれます（OS 環境変数を上書きしません）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

---

## 使い方（起動例）

- 監視ループを起動（デフォルト間隔 60 秒）
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔を変更:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  注意:
  - run_monitoring は監視用 SQLite（Settings.sqlite_path）を使用します（環境に依らず本番用 sqlite_path を参照します）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成すると検知して終了します。

- 実行エンジンを起動
  ```
  python -m kabusys.run_execution
  ```
  Paper Trading モードで起動（MockBroker 使用、DB は PAPER_TRADING_SQLITE_PATH）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  実行中の停止:
  - data/stop_requested.flag を作成すると ExecutionEngine に停止シグナルが送られます。
  - Kill Switch が作動すると data/kill.flag が作成され、実行エンジンは起動時や実行中に検出して停止します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコアリング（ライブラリ API）
  - news_nlp をプログラムから呼ぶ例:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 11), api_key="YOUR_OPENAI_KEY")
    ```
  - regime_detector.score_regime も同様に利用可能。

- ログ
  - ログはデフォルトで logs/<app_name>.log（日次ローテート）と stdout に出力されます。
  - LOG_DIR 環境変数でログディレクトリを変更可能。LOG_LEVEL でレベルを調整。

---

## 主要ファイル・ディレクトリ構成

以下は src/kabusys 以下の主要モジュールの説明です。

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス：環境変数の取得・検証、自動 .env ロードロジック
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前の環境検証 CLI
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB を使用）
  - utils/
    - logging_setup.py：統一的なログ設定（stdout + 日次ローテートファイル）
    - process_priority.py：プロセス優先度 / CPU affinity 設定（psutil ベース）
  - monitoring/
    - monitoring_db.py：SQLite テーブル定義と CRUD ユーティリティ
    - system_monitor.py：CPU/メモリ/ディスク/データ鮮度/プロセス存在の監視
    - risk_monitor.py：ドローダウン/ポジション上限監視、ダッシュボード更新
    - trade_monitor.py：注文滞留・約定異常検出（ファイルに含まれる）
    - monitoring_engine.py：各モニタを束ねる定期実行エンジン
    - kill_switch.py：kill.flag の発行・管理
    - alert_manager.py：（アラート送信・管理、LINE 連携等）※実装箇所を参照
  - execution/
    - execution_engine.py, order_manager, risk_manager, reconciler など（Execution ロジック）
    - broker_factory.py（実ブローカー or MockBroker の生成）
  - portfolio/
    - portfolio_builder.py：候補選定・重み計算
    - position_sizing.py：株数計算、lot 単位丸め、aggregate cap
    - risk_adjustment.py：セクターキャップ、レジーム乗数
  - research/
    - factor_research.py：momentum/volatility/value の DuckDB 実装
    - feature_exploration.py：forward returns, IC, 統計サマリ
  - ai/
    - news_nlp.py：ニュースから銘柄別センチメントを生成して ai_scores に保存
    - regime_detector.py：ETF MA200 + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py：ペーパートレード検証レポート

（上記は主だったファイルの抜粋です。実際のソースコードは `src/kabusys` を参照してください。）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定ミスの影響が大きいため validate_config や .env の確認を必ず行ってください。
- Kill Switch（data/kill.flag）は本番保護に有用ですが、KILL_FLAG_CLEAR_ON_START を 1 に設定すると起動時に自動クリアされます。live 環境では 0 を推奨します。
- OpenAI API を使う際は API キー管理に注意してください（環境変数 OPENAI_API_KEY を利用）。
- モジュールはできるだけ副作用を抑える設計になっていますが、DB 書き込みや PID / flag ファイルの読み書きなどは実行環境のファイル権限に依存します。

---

## 開発・拡張のヒント

- DuckDB 接続を渡すことで research モジュールの関数を簡単にテスト可能です（IO を分離した純粋関数設計を意識）。
- AI 関連の API 呼び出しは内部でラップされており、テスト時は該当関数をモックすることで外部呼び出しを置き換えられます（例: unittest.mock.patch）。
- position_sizing や risk_adjustment は純粋関数群なのでユニットテストが書きやすいです。

---

README に記載していない小さな仕様・設定はソースコメント（各モジュール冒頭の docstring）に詳述しています。まずは `python -m kabusys.config_setup` → `python -m kabusys.validate_config` → `python -m kabusys.run_monitoring` / `python -m kabusys.run_execution` の順で環境を整えて動かしてみてください。