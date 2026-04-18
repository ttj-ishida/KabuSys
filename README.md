# KabuSys

日本株自動売買システムのモジュール群（ライブラリ＋起動スクリプト群）

このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースNLP / レジーム判定）などの主要コンポーネントを含むモジュール集合です。各コンポーネントはテストしやすい純粋関数／副作用を明示した設計になっており、SQLite / DuckDB をデータ永続化と分析に利用します。

--- 

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数と設定 (.env)
- 使い方（起動コマンド例）
- ツール
- 注意事項・運用メモ
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤を構成するための Python モジュール群です。  
主な責務は以下の通りです。

- ExecutionEngine（発注ロジック／オーダー管理／リスク管理）
- Monitoring（システム状態・注文状態・リスクの定期監視と Kill Switch）
- Portfolio Construction（銘柄選定、配分、ポジションサイズ算定）
- Research（ファクター計算・特徴量解析）
- AI（ニュースに基づくセンチメント評価、レジーム判定）
- ユーティリティ（設定管理、ログ設定、プロセス優先度設定など）

設計上、paper_trading（ペーパートレード）モードは本番 DB と分離され、MockBrokerClient による仮想注文記録を行えます。

---

## 主な機能（機能一覧）

- 環境設定ウィザード（kabusys.config_setup）
- 起動前設定検証 CLI（kabusys.validate_config）
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV に応じた paper/live モード分離
  - PID ファイル管理、停止フラグ監視
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - システム状態、データ鮮度、注文状態、リスクの定期チェック
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔変更可能
  - 監視から Kill Switch を発動して ExecutionEngine を停止可能
- 監視永続化層（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard 等
- ポートフォリオ構築ユーティリティ
  - 候補選定、等配分／スコア配分の重み計算
  - セクター制約、レジーム乗数
  - ポジションサイズ決定（単元丸め・集約キャップ）
- リサーチ機能（DuckDB ベース）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI 機能（OpenAI を利用）
  - ニュースを LLM でスコアリングして ai_scores に保存（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA によるレジーム判定（kabusys.ai.regime_detector）
- 運用用ツール
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

---

## 前提条件（依存関係の一例）

最低限インストールが必要なパッケージ（この一覧は実行する機能により増えます）:

- Python 3.9+（型注釈から推測）
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（config 検証で YAML をチェックしたい場合）
- （SQLite は標準ライブラリで利用）

実行環境に合わせて必要なパッケージをインストールしてください。requirements.txt はこの抜粋に基づいて用意してください（本リポジトリには含まれていません）。

例:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンします。

2. 仮想環境を作成して依存をインストールします（任意）:
   - python -m venv .venv
   - source .venv/bin/activate (Windows の場合は .venv\Scripts\activate)
   - pip install -r requirements.txt （requirements.txt を用意している場合）

3. .env の初期作成:
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト）を生成または更新します。

   - 手動で作成する場合は .env.example を参考に、必須変数を設定してください。

4. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. DB ディレクトリ（data）やログディレクトリ（logs）は、必要に応じて作成されます。起動時に自動作成される箇所もありますが、アクセス権等を事前に確認してください。

---

## 環境変数 (.env) — 主な一覧

必須（最低限設定するもの）
- JQUANTS_REFRESH_TOKEN  — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabuステーション API パスワード（必須）

運用に関する主要変数（省略時は括弧内のデフォルト）
- KABUSYS_ENV (development | paper_trading | live) — 実行環境（デフォルト: development）
- DUCKDB_PATH ("data/kabusys.duckdb")
- SQLITE_PATH ("data/monitoring.db")
- PAPER_TRADING_SQLITE_PATH ("data/paper_trading.db")
- LOG_LEVEL ("INFO")
- LOG_DIR ("logs")
- OPENAI_API_KEY — AI 機能を使う場合に必須
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラートに必要（任意）
- PID_FILE_PATH ("data/execution.pid")
- KILL_FLAG_PATH ("data/kill.flag")
- KILL_FLAG_CLEAR_ON_START ("0" / "1") — 起動時に kill.flag を自動クリアするか（本番は 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング秒数（run_monitoring で利用。デフォルト 60）

注意:
- run_monitoring は KABUSYS_ENV にかかわらず sqlite_path（デフォルトの監視 DB）を使用します。
- run_execution は paper_trading モード（KABUSYS_ENV=paper_trading）の場合、PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離します。

---

## 使い方（起動コマンド例）

- 環境作成・検証
  - .env 作成:
    ```
    python -m kabusys.config_setup
    ```
  - 検証:
    ```
    python -m kabusys.validate_config
    ```

- ExecutionEngine 起動
  - 通常起動（バックグラウンド管理は任意）:
    ```
    python -m kabusys.run_execution
    ```
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録されます。
    - 起動時に data/execution.pid に PID を書き込みます。
    - data/stop_requested.flag が存在すると起動をスキップ、または実行中に検知されると停止します。

- Monitoring 起動
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を変更する例（30秒ごと）:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor を使い定期チェックを実行し、SQLite にログを書きます。
    - Kill Switch の判定や LINE 通知等のトリガー処理を実行します。

- Paper Trading 検証レポート（ツール）
  - 期間指定でレポートを表示:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB 指定:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI 機能（Python API 呼び出し）
  - news_nlp スコア付与を直接呼ぶ例（DuckDB 接続を構築して利用）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - regime_detector の呼び出し:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

---

## ロギング・ファイル配置

- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日分保持）。
- ログの設定は kabusys.utils.logging_setup.setup_logging により統一的に設定され、LOG_LEVEL / LOG_DIR / 引数で上書きできます。

---

## KILL / STOP フラグ（運用）

- 実行中のエンジンを外部から停止したい場合は flag ファイルを使います:
  - 停止要求ファイル: data/stop_requested.flag（run_* スクリプトがチェック）
  - Kill Switch（自動停止）: Settings.kill_flag_path（デフォルト data/kill.flag）を監視・書き込み
- 起動時に KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動で削除します（本番では推奨しません）。

---

## 注意事項・運用メモ

- 本番環境（KABUSYS_ENV=live）の設定は慎重に行ってください。validate_config で live 時の追加ガード（LINE 設定等）をチェックします。
- OpenAI（AI 機能）を使う場合は API 呼び出しに課金が発生します。API キー（OPENAI_API_KEY）は安全に管理してください。
- DuckDB / SQLite への互換性や executemany の空リスト制約など、コード側で互換性対策が入っています。運用時は DB バージョンを合わせてください。
- プロセス優先度設定（psutil を利用）は OS に依存します。必要に応じて権限を確認してください。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なファイル一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                         — 環境変数/設定読み込みユーティリティ（Settings）
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py    — Paper Trading 検証レポート生成
  - utils/
    - __init__.py
    - logging_setup.py                — ログセットアップユーティリティ
    - process_priority.py             — プロセス優先度 / CPU affinity 設定
  - portfolio/
    - __init__.py
    - portfolio_builder.py            — 候補選定・重み計算
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
    - position_sizing.py              — 発注株数計算（単元丸め・集約 cap）
  - research/
    - __init__.py
    - factor_research.py              — モメンタム・バリュー・ボラ計算
    - feature_exploration.py          — 将来リターン・IC 等
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py              — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py                — 監視用 SQLite 永続化層
    - system_monitor.py               — システム状態監視（データ鮮度等）
    - risk_monitor.py                 — ドローダウン・ポジション上限監視
    - trade_monitor.py                — （注文監視 — 省略されているが存在想定）
    - monitoring_engine.py            — 各 Monitor を束ねるエンジン
    - kill_switch.py                  — kill.flag の書き込みロジック

（実際のリポジトリには上記以外に execution/*.py、data/*.py などが含まれる想定です）

---

必要に応じて README を拡張して、運用手順（systemd ユニット例、Dockerfile、CI 用スクリプト等）やテスト手順、詳細な設定項目の説明を追加できます。必要ならその内容に合わせた追記を作成します。