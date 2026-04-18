# KabuSys

日本株向けの自動売買／リサーチ基盤ライブラリ兼実行スクリプト群です。  
本リポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群で構成されています。

- 実際の（またはペーパートレーディングの）発注処理を行う ExecutionEngine
- システム稼働状態・データ鮮度・注文ログ等を定期ポーリングして記録・アラートを発する Monitoring
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイジング等）
- リサーチ用ファクター計算・統計ユーティリティ
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（ニュース NLP）と市場レジーム判定
- 開発補助スクリプト（.env ウィザード、設定検証、Paper Trading レポート生成 等）

設計方針の一部：
- 本番 DB とペーパートレード DB は分離（KABUSYS_ENV による切替）
- 重要なモジュールは副作用を抑え、テスト容易性を考慮
- LLM 呼び出しはリトライ・フォールバックを備え安全に動作するよう実装

---

## 主な機能一覧

- Execution
  - 実際のブローカークライアント / モックブローカー切替（KABUSYS_ENV=paper_trading）
  - 発注管理、リスク管理、注文の照合（reconciler）
- Monitoring
  - system_status / trade_logs / risk_logs / positions / dashboard を SQLite に永続化
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による外部停止（Kill Switch）
- Portfolio
  - 候補選定（スコア順）、等配分・スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value 等ファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュースを LLM で銘柄別にスコア化（ai_scores テーブルへ書込）
  - マクロニュース + ETF ma200 による市場レジーム判定（market_regime テーブル）
  - OpenAI API の扱いにリトライやバックオフを実装
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート作成スクリプト

---

## 必要条件（依存パッケージ）

主な依存ライブラリ（インストール方法は下記参照）:

- Python 3.9+
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML （設定ファイル検証を行う場合に任意）

pip での例:
```bash
pip install duckdb psutil openai pyyaml
```

（テストや開発用に追加パッケージがある場合があります）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを取得
2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb psutil openai pyyaml
   ```
3. 初期設定（.env）を用意
   - 対話式ウィザードで作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env をプロジェクトルートに作成（.env.example を参照）
4. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config      # 警告は許容
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```
5. DB ディレクトリの準備（通常は自動作成されますが念のため）
   - デフォルトファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite(監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な設定（デフォルト値は右記）:
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live") — default: development
  - paper_trading: MockBroker を使用し、paper_trading 専用 DB を使う
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- LOG_DIR: logs
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0/1（0 が本番推奨）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: "instant"）
- OPENAI_API_KEY: OpenAI を使う場合に必要

モニタリング用:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）

注意:
- Monitoring の DB は KABUSYS_ENV に関係なく設定された sqlite_path（本番用）を使用します（実装上の仕様）。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して本番と分離します。

---

## 実行方法

各モジュールはモジュール実行可能です（python -m ...）。以下は代表的な実行例。

- 監視ループを起動する（監視は MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能）
  ```bash
  # 既定では 60 秒間隔
  python -m kabusys.run_monitoring

  # 例: 30秒間隔に変更
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン（ExecutionEngine）を起動する
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込みます。

- .env 作成ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```bash
  # 全期間（DB にある範囲）
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パスを指定
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- ライブラリとして（開発・テスト向け）
  - ポートフォリオ関数:
    ```python
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
    ```
  - リサーチ関数:
    ```python
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns
    ```
  - AI:
    ```python
    from kabusys.ai import score_news
    ```

---

## 主要なファイル / スクリプトの説明

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングを行う起動スクリプト。MONITOR_POLL_INTERVAL で間隔上書き可。
  - 停止フラグ: data/stop_requested.flag を検出するとループを終了。

- src/kabusys/run_execution.py
  - ExecutionEngine を起動するスクリプト。paper_trading 環境では MockBroker を使用。
  - 停止フラグ: data/stop_requested.flag。PID を data/execution.pid に書き出す。

- src/kabusys/config_setup.py
  - .env を対話式に作成・更新するウィザード。

- src/kabusys/validate_config.py
  - .env / config/*.yaml の基本チェックを行う CLI。

- src/kabusys/monitoring/*
  - monitoring_db.py: SQLite のスキーマ初期化・読み書きラッパー
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py / kill_switch.py / alert_manager 等

- src/kabusys/portfolio/*
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py

- src/kabusys/research/*
  - factor_research.py, feature_exploration.py

- src/kabusys/ai/*
  - news_nlp.py, regime_detector.py

- src/kabusys/tools/paper_verification_report.py
  - Paper Trading 結果のサマリ / PASS/FAIL を判定するレポートツール

---

## ディレクトリ構成（抜粋）

プロジェクトルートの `src/kabusys` 以下の主要構成:

```
src/kabusys/
├─ __init__.py
├─ config.py
├─ config_setup.py
├─ validate_config.py
├─ run_monitoring.py
├─ run_execution.py
├─ utils/
│  ├─ __init__.py
│  ├─ logging_setup.py
│  └─ process_priority.py
├─ monitoring/
│  ├─ monitoring_db.py
│  ├─ system_monitor.py
│  ├─ trade_monitor.py
│  ├─ risk_monitor.py
│  ├─ monitoring_engine.py
│  ├─ kill_switch.py
│  └─ alert_manager.py
├─ execution/
│  ├─ execution_engine.py
│  ├─ order_manager.py
│  ├─ order_repository.py
│  └─ broker_factory.py
├─ portfolio/
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ ai/
│  ├─ news_nlp.py
│  └─ regime_detector.py
└─ tools/
   └─ paper_verification_report.py
```

（実際のファイルは上記以外にも多数あります。ツリーは抜粋です）

---

## 運用上の注意 / 補足

- 本番（KABUSYS_ENV=live）での実行前には必ず `python -m kabusys.validate_config` で設定を確認してください。
- .env は機密情報（API トークン等）を含むため絶対に Git にコミットしないでください。
- AI 機能を利用するには OPENAI_API_KEY を設定する必要があります。API 呼び出しはリトライやフォールバックを持ちますが、API 利用コストやレート制限に注意してください。
- run_monitoring の監視 DB は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。Monitoring は環境にかかわらずこの DB を使ってログを残す設計です。
- 停止フラグ（data/stop_requested.flag）や kill.flag（data/kill.flag）はファイルベースのシンプルなインターフェースです。自動クリア設定（KILL_FLAG_CLEAR_ON_START）に注意してください（本番では 0 推奨）。
- ログはデフォルトで logs/<app_name>.log（日次ローテーション）に書き出されます。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。

---

## 開発・拡張のヒント

- DuckDB は分析用テーブル（prices_daily / raw_financials / raw_news 等）を参照してファクター・AI モジュールが動作します。データインポートのパイプラインは `kabusys.data.pipeline` 等を参照してください。
- OpenAI 呼び出し箇所はユニットテストで差し替えやすいように `_call_openai_api` をラップしています。テストではモックによる差し替えを検討してください。
- position_sizing 等の純粋関数は外部依存がなくユニットテストが容易です。境界条件（価格欠損・lot_size 等）に対するテストを充実させてください。

---

必要であれば、README に含める具体的な環境変数テンプレート（.env.example）や起動例、実運用の手順（systemd サービス定義、コンテナ化手順）を追加で作成します。どの情報を優先的に補足しますか？