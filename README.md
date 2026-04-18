# KabuSys

日本株向け自動売買システムのコアライブラリ群。  
戦略構築、ポートフォリオ設計、注文実行、監視、Research / AI（ニュース NLU / レジーム検出）などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株のアルゴリズム取引パイプラインの主要機能を提供するモジュール群です。  
主な目的は次のとおりです。

- 日次/オンデマンドでのファクター計算や特徴量分析（DuckDB を利用）
- 銘柄選定・配分・株数算出（Portfolio Construction）
- 取引注文の管理・実行（実際のブローカー or モック：paper_trading）
- システム稼働・注文状態・リスクの監視とアラート
- ニュースを用いた LLM ベースのセンチメント評価・市場レジーム判定
- 開発時の設定ウィザード / 設定検証 / 検証レポート出力ツール

このリポジトリはライブラリとしても、`python -m <モジュール>` で実行可能なスクリプト群も含みます。

---

## 機能一覧

- 設定管理
  - .env の対話式生成（config_setup）
  - 起動前設定検証（validate_config）
  - Settings クラスで環境変数アクセスの一元化
- 実行エンジン（Execution）
  - 本番 / ペーパートレードに応じたブローカークライアント切替
  - OrderRepository / OrderManager / RiskManager / ExecutionEngine 等
- 監視（Monitoring）
  - SystemMonitor：プロセス生存、CPU/メモリ/Disk、データ鮮度チェック
  - TradeMonitor：注文滞留や約定異常検出（コード内にあり）
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボード管理
  - KillSwitch：条件により `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringEngine：複数モニタの巡回とアラート連携
  - monitoring.db（SQLite）への永続化
- ポートフォリオ（Portfolio）
  - 候補選定、等重/スコア重み付け
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元丸め・最大利用率・リスクベース等）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ
  - DuckDB を用いた SQL+Python 実装
- AI（OpenAI）
  - ニュース記事の銘柄別センチメント（news_nlp）
  - マクロニュース＋ETF MA200 の合成によるレジーム判定（regime_detector）
  - OpenAI（gpt-4o-mini など）を想定、リトライ・レスポンス検証処理あり
- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

---

## 必須 / 推奨依存パッケージ

（プロジェクトには requirements.txt が同梱されていない想定です。以下をインストールしてください）

- Python 3.10+（`|` 型注釈があるため）
- duckdb
- psutil
- openai
- pyyaml（設定検証で YAML 検証を行う場合に必要）
- そのほか標準ライブラリ（sqlite3 等）

例:
```bash
python -m pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 展開する
2. Python 3.10+ 環境を用意する（venv 推奨）
3. 依存パッケージをインストール
4. 初回は対話式ウィザードで .env を作成する（推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須
   - KABUSYS_ENV の値: `development` / `paper_trading` / `live`
5. 設定を検証する
   ```bash
   python -m kabusys.validate_config
   # 警告も許容しない場合:
   python -m kabusys.validate_config --strict
   ```
6. DB ファイル確認
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）
   - 必要に応じて .env の `DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` を上書き

注意: デフォルトで .env はプロジェクトルート（.git か pyproject.toml によるルート検出）から自動ロードされます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 起動 / 使い方

いくつかの主要な実行スクリプトと利用方法を示します。

- ExecutionEngine（取引実行）
  - 開始:
    ```bash
    python -m kabusys.run_execution
    ```
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録します。実際の発注は行いません。
    - 起動時に `data/stop_requested.flag` が存在する場合、起動せず終了します。
    - 実行中に同フラグが作成されるとエンジンを停止します。
    - プロセス PID を `data/execution.pid` に書きます（Settings.pid_file_path で変更可能）。

- Monitoring（監視ループ）
  - 開始:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - オプション:
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で変更可能（デフォルト 60）。
    - 監視は production の sqlite_path を環境にかかわらず使用する設計です（monitoring 用 DB を共通で参照）。
  - 停止:
    - `data/stop_requested.flag` を作成するとループが終了します。

- Paper Trading 検証レポート
  - 実行:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB 指定:
    - デフォルト: `data/paper_trading.db`
    - `--db PATH` で別パス指定、または環境変数 `PAPER_TRADING_SQLITE_PATH` を使用

- AI / Research 呼び出し
  - ニューススコア:
    - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - 実行には OpenAI API キーが必要（引数 or 環境変数 `OPENAI_API_KEY`）
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1）

簡易の .env 例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             — monitoring.db 操作
    - system_monitor.py            — システム状態監視
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - trade_monitor.py             — 注文関連監視（コードベースに含む）
    - kill_switch.py               — kill.flag 制御
    - monitoring_engine.py         — 監視の統合ループ
    - alert_manager.py             — （アラート送信管理、実装に依存）
  - execution/
    - execution_engine.py          — ExecutionEngine（実行ループ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                  — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py           — レジーム判定（MA + マクロ NLP）
  - data/ (runtime)
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - kill.flag / stop_requested.flag / execution.pid
  - logs/ (デフォルトのログ出力先)

---

## 運用メモ / トラブルシューティング

- ログ
  - ログは `logs/<app_name>.log` に日次ローテーションで保存（デフォルト 30 日保持）。`LOG_DIR` 環境変数で変更可。
- Kill Switch / Stop フラグ
  - 監視が Kill 条件を満たすと `data/kill.flag` を作成し ExecutionEngine を停止できます。
  - 手動停止用に `data/stop_requested.flag` を作成すると run_* スクリプトが終了します（run_execution は起動中に検知して engine.stop() を呼ぶ）。
- 権限
  - `psutil` による優先度変更や CPU affinity の設定は権限が必要な場合があります。失敗すると警告ログが出ますが処理は継続します。
- DB マイグレーション（軽微な自動処理）
  - monitoring_db.init_monitoring_db はテーブル作成と簡単なカラム追加マイグレーションを行います。
- OpenAI / API エラー
  - news_nlp / regime_detector は API エラー時にリトライやフォールバック（0.0）を行うため、完全停止にはなりませんが、API キーは必須です。

---

## 開発上の注意

- DuckDB を使った Research 関数群は外部 API にアクセスせず、prices_daily / raw_financials テーブルのみ参照する設計です（安全にオフライン検証可能）。
- AI 関連処理は外部 OpenAI を使うため、テスト時は `_call_openai_api` の差し替えやモックを推奨します（コード内でその想定あり）。
- 設定ファイル（.env）は機密情報を含むため絶対に Git にコミットしないでください（config_setup のメッセージでも注意喚起があります）。

---

この README は提供されたコードベースをもとに作成しています。追加の実行スクリプト、broker 実装、アラート送信先（LINE など）は環境や実装によって補完してください。必要であれば、インストール用の requirements.txt / Dockerfile / systemd ユニットファイルのテンプレート等も作成できます。希望があれば教えてください。