# KabuSys

日本株向けの自動売買システムのコアライブラリ。バックテスト／リサーチ、ポートフォリオ構築、注文実行（実売買 / ペーパートレード）、監視、AI 支援（ニュース NLP / レジーム判定）などをモジュール化しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買を想定したモジュール群です。主な責務は以下です：

- 市場データ（DuckDB）を使ったファクター計算・リサーチ
- ポートフォリオ候補選定・重み付け・株数決定（単元丸め・リスク制約）
- ExecutionEngine による注文発行（実口座 / ペーパートレード）
- Monitoring（System / Trade / Risk）による稼働監視と Kill Switch
- AI モジュール（ニュースのセンチメント評価・市場レジーム判定）による補助指標生成
- 運用用ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証、レポート生成）

本リポジトリはライブラリと CLI 相当の起動スクリプト群を含み、運用時は環境変数 / .env の設定により動作を切り替えます。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config (--strict オプションあり)
- ロギング
  - 統一的なログ設定（コンソール stdout + 日次ローテートファイル）
- Execution（注文）
  - 実口座 or ペーパートレード切替（KABUSYS_ENV）
  - RiskManager、OrderManager、Reconciler を組み合わせた ExecutionEngine
  - Paper trading は専用 SQLite（data/paper_trading.db）に記録（本番 DB と分離）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - TradeMonitor: 注文の滞留や約定異常の検知（trade_logs テーブル参照）
  - RiskMonitor: ドローダウン／ポジション上限の検出とリスクログ化
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor を束ねて定期実行（ポーリング）
- Portfolio construction
  - 候補選定、等重・スコア重み、リスク制約（セクターキャップ、レジーム乗数）
  - 株数決定（単元株丸め、aggregate cap、コストバッファ）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、統計サマリ
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメントの生成（ai_scores）
  - レジーム判定（ETF ma200 とマクロニュースの LLM 評価を合成）
- ユーティリティ
  - process_priority（プロセス優先度 & CPU Affinity）
  - logging_setup（統一ログ）
  - tools: Paper Trading 検証レポート生成スクリプト（paper_verification_report）

---

## 前提 / 必要環境

- Python 3.9+
- 推奨パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config の YAML 検証に必要）
- SQLite は標準ライブラリで利用
- 実際に OpenAI API を使う場合は OPENAI_API_KEY（環境変数）を設定

※ requirements.txt は本リポジトリに含まれていない場合があるため、上記パッケージを適宜 pip でインストールしてください。

例:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてルートへ移動
   - プロジェクトルート（.git または pyproject.toml がある場所）を想定しています。

2. Python パッケージをインストール
   - 例: pip install -r requirements.txt（ファイルがある場合）
   - 最低限: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（設定検証）

3. ディレクトリ作成
   - 必要に応じて data/ と logs/ を作成。ログや DB ファイルはデフォルトで data/ / logs/ 配下に生成されます。
   ```bash
   mkdir -p data logs
   ```

4. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要オプション:
     - KABUSYS_ENV: development | paper_trading | live
       - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
     - OPENAI_API_KEY: AI 機能を使う場合に必要
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_LEVEL など
   - 自動読み込み:
     - 起動時に .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

5. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. 初期 DB 作成は起動スクリプト側で行われます（Monitoring は起動時に監視テーブルを初期化します）。

---

## 使い方（起動・実行例）

- ExecutionEngine（注文エンジン）を起動:
  - 本番・開発は KABUSYS_ENV に依存（ペーパートレードは分離 DB を使用）
  ```bash
  python -m kabusys.run_execution
  ```
  - 起動時にプロセス優先度を High に設定。data/execution.pid に PID を書きます。
  - 停止は data/stop_requested.flag や data/kill.flag の存在で検出します（KillSwitch は監視側で評価して書き込む）。

- Monitoring（監視ループ）を起動:
  ```bash
  # デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は system_status / trade_logs / risk_logs / dashboard テーブルを管理します。
  - monitoring は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する点に注意。

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能。

- AI 関連（スクリプト内関数呼び出し例）
  - ニュース NLP（銘柄別スコア作成）
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定
  - レジーム判定
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 設定の自動クリア / Kill Switch
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

ログ:
- logs/<app_name>.log に日次ローテートで出力されます（app_name は run_execution/run_monitoring 等で指定されます）。

プロセス優先度:
- 起動スクリプトは set_process_priority("high") を呼びます。プラットフォームにより動作が異なり、権限不足で設定できない場合は警告が出ます。

停止フラグ:
- data/stop_requested.flag（run_execution/run_monitoring で監視）
- data/kill.flag（KillSwitch により書き込まれる）

---

## 主要ファイル・ディレクトリ構成

（src/kabusys の主要な構成を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数 / .env の管理）
  - config_setup.py
    - .env 対話ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory, Reconciler, RiskManager 等の実装)
  - monitoring/
    - monitoring_db.py — SQLite スキーマ・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度監視
    - trade_monitor.py — 注文滞留/約定異常監視（ファイルはプロジェクト内に実装あり）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねる
    - kill_switch.py — kill.flag の操作
    - alert_manager.py — （LINE 等への通知を担う想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ／レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB を利用）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で銘柄別スコア生成
    - regime_detector.py — 市場レジーム判定（ETF ma200 + マクロニュース）
  - data/ (実行時に生成される想定)
    - monitoring.db（SQLITE_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - kill.flag / stop_requested.flag / execution.pid
  - logs/ (ログ出力先、デフォルト)

---

## 実運用上の注意

- KABUSYS_ENV の値によって注文発行の実挙動が変わります。特に `live` は本番発注となるため環境変数や通知設定（LINE）が適切か必ず確認してください。
- Monitoring は監視用の sqlite_path（デフォルト data/monitoring.db）を使用します。run_monitoring は環境にかかわらず本番 sqlite_path を参照します。
- Paper trading は本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使用します。誤って本番 DB を上書きしないよう注意してください。
- OpenAI API を利用する機能は API 呼び出しエラーに対してフェイルセーフ（フォールバック値）を持つ設計ですが、API キーの管理・コストには注意してください。
- ローカルでのテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を使って .env の自動ロードを無効化できます（テスト用に環境を完全に制御したい場合）。

---

## サポート / 参考

- .env.example を参照して環境変数を準備してください（プロジェクトにある場合）
- 設定作成後は必ず:
  ```bash
  python -m kabusys.validate_config
  ```
  で設定検証を行ってください。

---

README の内容は随時更新される想定です。実装や運用ポリシー変更時は README を合わせて更新してください。