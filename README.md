# KabuSys

日本株自動売買システムのコアライブラリ / 実行スクリプト群

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供する Python パッケージです。

- 株価データ・財務データを用いたファクター計算・リサーチ機能（DuckDB ベース）
- ポートフォリオ構築（候補選定・重み計算・リスク調整・ポジションサイジング）
- 注文管理／ExecutionEngine（本番・ペーパートレード分離）
- 監視（System / Trade / Risk）および Kill Switch（フラグファイルによる緊急停止）
- ニュースの LLM（OpenAI）による NLP スコアリング・レジーム判定
- 運用支援ツール（設定ウィザード、設定検証、Paper Trading 検証レポートなど）

設計方針の要点：
- DuckDB / SQLite をローカル DB として使用（分析用は DuckDB、監視／注文履歴は SQLite）
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により切替）
- 外部 API 呼び出し（OpenAI など）は必要に応じて安全に行い、フェイルセーフを考慮

---

## 主な機能一覧

- システム監視
  - CPU / メモリ / ディスク使用率の定期ログ記録
  - Execution プロセスの生存チェック、データ鮮度チェック
  - RiskMonitor によるドローダウン・ポジション上限監視
  - Kill Switch（条件に該当したら data/kill.flag を作成）
- Execution
  - Broker クライアント抽象化（本番 / Mock）
  - OrderRepository / OrderManager / Reconciler / RiskManager 組立て
  - ExecutionEngine による注文セッション実行（PID ファイル管理、停止フラグ対応）
- ポートフォリオ構築
  - 候補選定（スコア／ランク）と重み計算（等配分／スコア加重）
  - セクターキャップ適用、レジーム乗数（bull/neutral/bear）
  - ポジションサイズ計算（risk_based / equal / score）、単元株切り上げ・スケール調整
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析ユーティリティ
- AI（OpenAI）
  - ニュースのセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュース + ETF MA200 を使った市場レジーム判定
- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 必要条件（推奨）

- Python 3.10+
- 必要な Python パッケージ（少なくとも下記）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の内容検証を行う場合、オプション）
- SQLite（Python 標準の sqlite3 を使用）
- ネットワーク接続（OpenAI / 外部 API を使う場合）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（requirements.txt があればそれを利用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

2. 仮想環境作成・依存パッケージインストール（上記参照）

3. .env の作成（対話ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants / kabuステーション / DB パス等を対話式で作成します。
   もしくは .env を手動作成して以下の必須変数を設定してください：
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - OPENAI_API_KEY (AI 機能使用時)

   自動ロード:
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を検出して `.env` / `.env.local` を自動読み込みします。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   ```
   警告を厳密に扱いたい場合:
   ```
   python -m kabusys.validate_config --strict
   ```

5. デフォルト DB ファイル（必要時）は自動作成されます:
   - DuckDB: data/kabusys.duckdb
   - SQLite（監視）: data/monitoring.db
   - Paper Trading SQLite（ペーパー環境時）: data/paper_trading.db

---

## 使い方（実行例）

- 監視ループ起動（SystemMonitor のポーリング）:
  ```
  python -m kabusys.run_monitoring
  ```
  環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1未満や不正値は 60 秒へフォールバック。
  注意: run_monitoring は KABUSYS_ENV にかかわらず production 用の sqlite_path を使用します（監視データは本番 DB に書き込む想定）。

- ExecutionEngine（注文エンジン）起動:
  ```
  python -m kabusys.run_execution
  ```
  動作モード:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）へ記録します（本番 DB とは完全分離）。
  - PID ファイル: data/execution.pid（起動時に作成、終了時に削除）
  - 停止フラグ: data/stop_requested.flag（存在すると起動しない・ループ停止）

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB を明示する:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI（ニューススコア／レジーム判定）:
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY）
  - プログラム的に利用:
    ```py
    from kabusys.ai import score_news
    # score_news(conn, target_date, api_key=None) として呼ぶ（api_key 未指定なら OPENAI_API_KEY を参照）
    ```

- 設定ウィザード（.env 作成）:
  ```
  python -m kabusys.config_setup
  ```

---

## フラグ・制御ファイル

- 停止（Stop）フラグ: data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルの存在を検査してループを終了または起動を中止します（手動停止に使用可能）。
- Kill Switch フラグ: data/kill.flag
  - KillSwitch が危険条件を検出した場合に作成され、ExecutionEngine が停止されるトリガーになります。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されている場合は自動的にクリアされる（本番では 0 推奨）。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（paper_trading 時）
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）

---

## 開発者向けノート

- .env ファイルの読み込み順:
  - OS 環境変数 > .env.local > .env
  - OS 環境変数は保護され、.env.local による上書きを防止します（ただし override=True での読み込み処理は制御あり）。
- 設計上の注意:
  - AI 呼び出しはリトライ・バックオフやレスポンス検証が実装されており、失敗時は安全側にフォールバックします（例: macro_sentiment=0.0）。
  - DuckDB を使うリサーチ・AI 部分は本番注文ロジックとは分離しているため、分析用途での利用は安全です。
- ログ:
  - デフォルトで stdout（コンソール）および daily ログローテーション（logs/<app_name>.log）へ出力します。
  - ログディレクトリに作成できない場合はファイル出力をスキップして stdout のみで継続します。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要なファイル / モジュールを抜粋して示します。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数・設定管理
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI 経由スコアリング）
    - regime_detector.py    — 市場レジーム判定（AI + MA200）
  - monitoring/
    - monitoring_db.py      — 監視用 DB レイヤ
    - system_monitor.py     — システム状態監視
    - trade_monitor.py      — （存在）注文監視（コードベースに含まれる）
    - risk_monitor.py       — ドローダウン・ポジション監視
    - monitoring_engine.py  — 監視エンジン統括
    - kill_switch.py        — Kill Switch 実装
    - alert_manager.py      — （存在）アラート通知管理（コードベースに含まれる）
  - execution/
    - execution_engine.py   — 実行エンジン（EngineConfig / run_session 等）
    - broker_factory.py     — ブローカークライアント生成
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
  - monitoring/
    - monitoring_db.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は本リポジトリ内の主要モジュール構成を抜粋したものです。実際のファイル一覧はリポジトリを参照してください。）

---

## よくある運用フロー

1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / SQLite パスやログディレクトリの確認
4. 監視プロセス起動（python -m kabusys.run_monitoring）
5. ExecutionEngine 起動（python -m kabusys.run_execution）
6. 監視アラートや kill.flag により必要に応じて停止・対応
7. ペーパートレード検証 → レポート生成（python -m kabusys.tools.paper_verification_report）

---

## ライセンス / 貢献

この README はコードベースから作成した説明書です。実際のライセンスやコントリビューション方針はリポジトリにある LICENSE / CONTRIBUTING ファイルをご確認ください。

---

問題点の報告や補足したい情報があれば教えてください。README の内容を環境や運用ルールに合わせてカスタマイズして出力します。