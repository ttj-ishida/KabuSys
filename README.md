# KabuSys

日本株向け自動売買システムのリファクタリング済みコアライブラリ群（ドメインロジック、監視、実行、リサーチ、AI連携など）。この README はリポジトリ内の主要スクリプト・モジュールに基づいて作成しています。

> バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株の自動売買エンジンのための共通ライブラリ群です。主な責務は以下の通りです。

- 実行部（ExecutionEngine）: ブローカークライアント経由での発注・注文管理・リスク制御
- 監視（Monitoring）: システム状態、注文状態、リスク指標のポーリングとアラート / Kill Switch
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制限
- リサーチ: ファクター計算、将来リターン、特徴量解析
- AI連携: ニュースのセンチメント解析、レジーム判定（OpenAI API 利用）
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定 等

設計思想として「テスト可能な純粋関数」「ルックアヘッドバイアス回避」「フェイルセーフ（部分的な失敗で影響を最小化）」が採用されています。

---

## 機能一覧（抜粋）

- 実行（run_execution.py）
  - KABUSYS_ENV に応じて実ブローカー / モックブローカーを選択（paper_tradingモードでは DB を分離）
  - ExecutionEngine をスレッドで実行、停止フラグに対応
- 監視（run_monitoring.py / monitoring/*）
  - CPU / メモリ / ディスク / プロセス稼働チェック
  - Trade / Risk モニタによる滞留注文・約定異常・ドローダウン検出
  - Kill Switch（data/kill.flag）によるエンジン停止
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御
- 環境設定・検証
  - 対話式ウィザードで .env を作成（config_setup.py）
  - 設定の事前検証（validate_config.py）
- リサーチ（research/*）
  - Momentum / Volatility / Value等のファクター計算（DuckDB 使用）
  - 将来リターン、IC（Information Coefficient）、統計サマリ
- AI連携（ai/*）
  - ニュースを OpenAI でスコアリングして ai_scores に保存（news_nlp）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
- 共通ユーティリティ
  - ログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
  - 設定読み込み（config.py）: .env 自動読み込み機能あり

---

## 前提 / 依存

最低限必要な Python ライブラリ（プロジェクトに requirements.txt がない場合の例）:

- duckdb
- psutil
- openai (AI 機能を使う場合)
- pyyaml (設定 YAML 検証を行う場合)
- （標準ライブラリに sqlite3/argparse 等を使用）

インストール例:
```
pip install duckdb psutil openai pyyaml
```

注意:
- SQLite は標準ライブラリに含まれます。
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）を必要とします。

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```
4. 対話式で .env を作成（推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env のデフォルト値を表示し、必要項目（J-Quants トークンや kabu API パスワード等）を入力できます。

5. 設定を検証
   ```
   python -m kabusys.validate_config
   # 必要に応じて --strict を付けると警告も失敗扱いになります
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの作成（必要に応じて）
   デフォルトでは以下のファイル/ディレクトリを使用します:
   - data/kabusys.duckdb
   - data/monitoring.db
   - data/paper_trading.db（paper_trading 用）
   - logs/（ログ出力先）
   これらの親ディレクトリは起動時に自動作成されることが多いですが、権限等に注意してください。

---

## 使い方（主要スクリプト）

基本的にモジュールを -m で実行します。

1. Execution（実行エンジン）
   - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切り替えます。
   - paper_trading モード時は MockBrokerClient を使用し、デフォルト DB は data/paper_trading.db です。

   実行例:
   ```
   KABUSYS_ENV=live python -m kabusys.run_execution
   # or
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```

   停止は data/stop_requested.flag を作成することで行えます（run_execution は起動時に存在すれば起動を停止します）。

2. Monitoring（監視ループ）
   - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）。
   - 監視は本番 sqlite_path を常に使用します（KABUSYS_ENV に依存しません）。

   実行例:
   ```
   MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   ```

3. 設定ウィザード
   ```
   python -m kabusys.config_setup
   ```

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```

5. Paper Trading 検証レポート
   - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
   - 期間指定:
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB 指定
   python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   ```

6. AI 機能（ニューススコア / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY 環境変数か引数で指定）
   - news_nlp.score_news / regime_detector.score_regime を呼び出して使用
   - 例（スクリプトは専用の CLI を提供していないため、Python から直接呼ぶ想定）:
     ```
     from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news

     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, target_date=date(2026,4,11), api_key="sk-...")
     ```

---

## 重要な環境変数（主なもの）

- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant / partial / never / reject; デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_PATH: Kill Switch のフラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、0=クリアしない。production では0推奨）

---

## Kill / Stop フラグ

- data/kill.flag: Kill Switch が発動した際に書き込まれるファイル。ExecutionEngine はこのフラグにより停止されます。
- data/stop_requested.flag: run_execution.py や run_monitoring.py が外部停止要求を検知するためのフラグ。
- data/execution.pid: 実行エンジンの PID を保存するためのファイルパス（設定により変更可）。

Kill フラグの書き込み・クリアは kabusys.monitoring.kill_switch.KillSwitch を通して行うと安全です。

---

## ログ

- ログは utils/logging_setup.setup_logging により統一的に管理されます。
- 出力先:
  - コンソール（stdout）
  - ファイル: <LOG_DIR>/<app_name>.log（デフォルト logs/<app_name>.log、日次ローテーション・30日保持）
- 起動スクリプト例: setup_logging(app_name="execution") が使用されます（run_execution/run_monitoring など）。

---

## ディレクトリ構成（主要ファイル/モジュールの説明）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン）
  - config.py — 環境変数 / .env 自動ロード、Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/プロセス/データ鮮度の監視
    - trade_monitor.py — （コードベースに存在する想定）注文関連の監視
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - kill_switch.py — Kill Switch 実装（flag ファイル生成）
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — アラート送信（LINE 等、実装は別ファイルに存在する想定）
  - execution/、strategy/、data/、research/、portfolio/ — 実行・戦略・データ処理・リサーチ・ポートフォリオ構築のロジック
    - 例:
      - portfolio/portfolio_builder.py, position_sizing.py, risk_adjustment.py
      - research/factor_research.py, feature_exploration.py
      - utils/logging_setup.py, process_priority.py
  - utils/
    - logging_setup.py — ログ初期化
    - process_priority.py — 優先度 / CPU affinity 制御

（上記はソース内の主要モジュールを抜粋した説明です。細かいクラスや補助モジュールは各ディレクトリを参照してください。）

---

## 運用上の注意 / ヒント

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨します。
- run_monitoring は常に本番 sqlite_path を使って監視データを書き込みます — 環境に依らず監視 DB は共通です。
- paper_trading モードは本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 経由の AI 機能は API エラーに対してリトライやフォールバック（スコア 0）を行うよう設計されていますが、API キーと利用コストに注意してください。
- process_priority の設定は OS に依存します（Windows と POSIX 系の差分を吸収するロジックあり）。権限不足（nice / プロセス優先度変更）で警告が出ることがあります。

---

## よくあるコマンドまとめ

- .env を作る（ウィザード）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動（paper_trading または live）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- 監視ループ起動（ポーリング間隔を30秒にしたい場合）
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README を拡張して、インストール手順、Docker / systemd ユニットのサンプル、各種設定ファイルのテンプレート（config/*.yaml）や実運用時のチェックリストを追加できます。追加したい項目があれば教えてください。