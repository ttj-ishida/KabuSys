# KabuSys

日本株向けの自動売買システム（ライブラリ／実行コンポーネント群）。  
このリポジトリは取引実行、監視、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）などのモジュールを含みます。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群で構成される自動売買基盤です。

- ブローカーとの発注・状態管理（ExecutionEngine / OrderManager / Reconciler）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- モニタリング DB（SQLite）による永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ構築ロジック（候補抽出・重み付け・株数算出・リスク調整）
- リサーチ用ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
- ニュースセンチメント評価（OpenAI API を用いたニュースNLP）
- 市場レジーム判定（ETF + マクロニュースを組み合わせた判定）
- ユーティリティ（プロセス優先度 / CPU アフィニティ設定、Streamlit ダッシュボード、検証ツールなど）

設計上のポイント：
- DB スキーマ初期化は `init_monitoring_db` による冪等操作で安全に行われる
- Paper Trading（検証）モードを用意：本番 DB と完全分離して動かせる
- 外部 API（OpenAI 等）は明示的に API キーを渡すか環境変数で設定
- 重要箇所はフェイルセーフ設計（API失敗時のフォールバック、部分書き込み回避など）

---

## 主な機能一覧

- 実行関連
  - Order 作成 / 送信 / 同期（OrderManager / Reconciler）
  - ExecutionEngine（エンジン起動・停止制御、PID 管理）
- 監視関連
  - SystemMonitor：CPU/メモリ/ディスク、プロセス存在、データ鮮度を監視
  - TradeMonitor：滞留注文（stale）や約定異常価格を検出
  - RiskMonitor：ドローダウンやポジション上限を監視し、risk_logs に記録
  - KillSwitch：条件に応じて `data/kill.flag` を書いて Execution を停止
  - AlertManager：LINE Push によるアラート送信（トークン未設定時はログのみ）
  - Streamlit ダッシュボード（監視情報閲覧）
- ポートフォリオ関連
  - 候補選定（スコア降順）、等比配分・スコア加重、ポジションサイズ計算、セクター上限適用、レジーム乗数
- リサーチ
  - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB 上で完結）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュースを集約して OpenAI に投げ、ai_scores テーブルへ保存（score_news）
  - マクロニュース + ETF MA を組み合わせて market_regime を算出（score_regime）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - 各種ユーティリティ（.env 自動読み込み、プロセス優先度設定 等）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子等を利用）
- Git リポジトリのクローン済み

1. 仮想環境作成＆有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   必要な主なライブラリ（抜粋）:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit

   例（pip）:
   ```
   pip install duckdb psutil openai requests streamlit
   ```

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨。）

3. 環境変数 / .env の設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（既存 OS 環境変数は保護）。
   自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   例: `.env`（最小）
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   ```

   主要な環境変数（デフォルト値や意味）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用トークン
   - LOG_LEVEL: ログレベル（INFO 等）
   - PAPER_FILL_MODE: paper_trading 時の Fill 挙動（instant|partial|never|reject）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定 60）

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

   DB やフラグファイル（例: data/execution.pid、data/kill.flag、data/stop_requested.flag）を配置／確認します。
   `init_monitoring_db` は起動時に自動でスキーマを作成／マイグレーションを行います。

---

## 使い方（実行例）

以下は主要な起動方法の例です。各スクリプトはパッケージモジュールとして実行可能です。

- ExecutionEngine（取引実行）を起動する
  - Paper Trading（検証）モード:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    Paper Trading のときは `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）を使用し、MockBrokerClient が使われます（本番口座と分離）。

  - 本番想定:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
    （本番利用時は十分なテストと安全策を講じてください）

  - 停止: エンジン起動中にプロセスを終了するか、監視側／管理者が `data/kill.flag` を書くことで停止シグナルを送れます。`data/stop_requested.flag` を作成すると起動スクリプトは終了します（実装により利用箇所が異なります）。

- MonitoringEngine（監視ループ）を起動する
  ```
  python -m kabusys.run_monitoring
  ```
  ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。例:
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  または `--db` を指定せずデフォルトパスを使用。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB を明示:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ニューススコア・レジーム判定）
  - `kabusys.ai.score_news(conn, target_date, api_key=...)`
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)`
  いずれも OpenAI API キーが必要（引数で渡すか環境変数 `OPENAI_API_KEY` を設定）。

---

## 停止・フラグファイルについて

- 停止リクエスト（起動スクリプトの監視）:
  - `data/stop_requested.flag` が存在すると `run_monitoring` と `run_execution` は起動・ループを終了します（スクリプト内でチェック）。
- Kill Switch（監視→実行停止）:
  - `KillSwitch` によりシステム上の重大なリスク（ドローダウン超過やポジション上限超過）を検出すると `data/kill.flag` を作成します。Execution 側はこのフラグを見て停止する仕組みを採る運用ができます。
- PID ファイル:
  - ExecutionEngine は `data/execution.pid`（デフォルト）を使います。SystemMonitor は PID ファイルの stale（存在するが該当 PID がない）を検出して削除する処理を持っています。

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン
- KABU_API_PASSWORD: kabu API のパスワード
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH 等は Settings でさらに細かく指定可能

詳しい取得方法は `src/kabusys/config.py` を参照してください。`.env` の自動ロードはプロジェクトルートを `.git` または `pyproject.toml` で検出して行います。

---

## ディレクトリ構成

主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定の読み取りと Settings クラス
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (実行エンジン本体)
    - broker_factory.py
    - ...
  - monitoring/
    - monitoring_db.py — SQLite スキーマ & ラッパー（MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
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
  - data/  (運用時に利用するディレクトリ、DB やフラグファイルを置く)
  - utils/
    - process_priority.py

簡易ツリー（プロジェクトルート直下）:
```
src/
  kabusys/
    ai/
    execution/
    monitoring/
    portfolio/
    research/
    tools/
    utils/
    config.py
    run_execution.py
    run_monitoring.py
```

---

## 開発上の注意点 / 運用メモ

- Paper Trading を使えば本番 DB・実口座に影響を与えず検証できます（`KABUSYS_ENV=paper_trading`）。
- 監視は監視 DB（監視用 SQLite）へ常時書き込みます。`init_monitoring_db()` によりスキーマは自動作成されます。
- AI 呼び出しにはネットワークと API クォータが必要です。OpenAI の失敗・エラーは再試行・フォールバック実装が組み込まれていますが、運用では API 制限に注意してください。
- `set_process_priority("high")` の呼び出しは起動直後に行われますが、OS/権限により失敗する場合があります（ログに警告が出ます）。
- `.env` のパース処理は Bash 風の export/コメント/クォートをある程度サポートします（詳細は config.py を参照）。

---

必要であれば README に以下を追加できます：
- 具体的な .env.example（テンプレート）
- systemd / supervisor 用のサンプルユニットファイル
- CI/テスト実行方法（ユニットテストがあれば）
- よくあるトラブルシュート（DB 関連、OpenAI エラー、PID 関連）

必要なら追記します。