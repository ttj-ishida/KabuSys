# KabuSys

KabuSys は日本株向けの自動売買・研究・監視を目的とした軽量なシステムです。  
このリポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動コマンド・環境変数）
- ディレクトリ構成（主要ファイル説明）
- 注意点・運用メモ

---

## プロジェクト概要

KabuSys は次のような目的で設計されています。

- 自動発注（ExecutionEngine）と発注状態管理
- 発注・約定・ポジションのリコンシリエーション（再起動後の同期）
- システム稼働状況・注文異常・リスク（ドローダウン・ポジション数）監視
- LINE によるアラート送信
- Paper Trading（検証）用に本番 DB と分離した動作モード
- DuckDB を使った時系列・ファクター計算（リサーチ）
- OpenAI を用いたニュースセンチメント評価（AI モジュール）
- Streamlit ベースの監視ダッシュボード、検証レポート出力ツール

設計上、ランタイムに依存する日時を直接参照しない（ルックアヘッドバイアス対策）等、金融システム運用を意識した実装方針が取られています。

---

## 主な機能一覧

- execution
  - ExecutionEngine（起動・セッション実行）
  - Broker クライアントファクトリ（実運用 / モックを切り替え）
  - OrderManager / OrderRepository による状態管理
  - Reconciler による再起動時の同期とポジション差分検出
- monitoring
  - SystemMonitor：プロセス監視・CPU/メモリ/Disk・データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格の異常検出
  - RiskMonitor：ドローダウン・ポジション上限の監視
  - KillSwitch：重大トリガで stop flag（data/kill.flag）を書き込み Execution 停止
  - AlertManager：LINE push による通知（クールダウン管理）
  - MonitoringEngine：複数モニタをまとめたポーリング実行
  - Streamlit ダッシュボード（read-only 接続）
- portfolio
  - 銘柄選抜、等重／スコア重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- research
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- ai
  - news_nlp: raw_news から銘柄ごとのセンチメントを OpenAI で評価し ai_scores に格納
  - regime_detector: ETF(ma200) とマクロニュースの LLM 評価を合成して market_regime を決定
- tools
  - paper_verification_report: Paper Trading DB から各種指標を集計し PASS/FAIL 判定を出力

---

## セットアップ手順

下記は最小限の手順例です。実行環境に応じて適宜調整してください。

1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境を作成して有効化する（例: venv / pyenv）

2. 依存ライブラリをインストール
   - 主要な依存（参考）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     ```bash
     pip install duckdb psutil requests openai streamlit
     ```
   - （requirements.txt がある場合はそれを利用）

3. プロジェクトルートに `.env` を配置（任意）
   - config モジュールは自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数より劣後）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. data ディレクトリ作成
   - デフォルトの DB / PID / フラグファイルは `data/` に置かれます。存在しない場合は自動作成されますが、権限に注意してください。
   - 例:
     ```bash
     mkdir -p data
     ```

5. 必要な環境変数（主なもの）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する機能を使う場合:
     - OPENAI_API_KEY
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (monitoring DB, default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper trading 用 DB, default: data/paper_trading.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, PAPER_FILL_MODE (instant|partial|never|reject)
     - LOG_LEVEL
     - MONITOR_POLL_INTERVAL（監視ポーリング秒、run_monitoring で利用）
   - 例 .env（抜粋）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     OPENAI_API_KEY=sk-...
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

---

## 使い方

### 実行スクリプト

- ExecutionEngine（取引エンジン）起動
  - ファイル: src/kabusys/run_execution.py
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と分離されます。
    - 起動直後に data/stop_requested.flag が存在すると起動をせず終了します（停止フラグ機構）。
    - プロセス優先度を high に設定します（psutil を利用）。
  - 実行例:
    ```bash
    python -m kabusys.run_execution
    ```
  - 停止:
    - 管理側（監視等）が data/kill.flag を書くことで ExecutionEngine 側が停止を検知するフローがあります（KillSwitch）。

- Monitoring（監視ループ）起動
  - ファイル: src/kabusys/run_monitoring.py
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor などをポーリングして監視データを SQLite に記録します。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒、デフォルト 60）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する実装になっています（注意）。
  - 実行例:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Streamlit ダッシュボード（監視画面）
  - ファイル: src/kabusys/monitoring/streamlit_dashboard.py
  - 起動例:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート
  - ファイル: src/kabusys/tools/paper_verification_report.py
  - 実行例:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # DB を指定する場合
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```
  - 出力: 稼働率・注文成功率・送信率・レイテンシ等の要約と PASS/FAIL 判定

### 環境ごとの挙動（重要）

- KABUSYS_ENV による分岐:
  - development (デフォルト)
  - paper_trading: ExecutionEngine は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
  - live: 本番運用向け
- Monitoring は KABUSYS_ENV にかかわらず監視用の sqlite_path を使用する点に注意してください（run_monitoring の実装）。

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数と .env ロードロジック、Settings クラス
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py

- src/kabusys/execution/
  - broker_api.py, broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py
  - 発注・ブローカー関連の実装（OrderRecord / OrderState 等）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・読み書きラッパー
  - system_monitor.py — CPU/メモリ/Disk・データ鮮度・PID ファイルチェック
  - trade_monitor.py — 滞留注文・約定価格異常チェック
  - risk_monitor.py — ドローダウン / ポジション上限チェック
  - kill_switch.py — kill.flag の書き込み / 管理
  - alert_manager.py — LINE Push 通知
  - monitoring_engine.py — 各 Monitor を束ねたポーリングエンジン
  - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定 / 重み算出
  - position_sizing.py — 発注株数計算（単元丸め、リスク制限）
  - risk_adjustment.py — セクター上限 / レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum / Value / Volatility の計算（DuckDB 参照）
  - feature_exploration.py — 将来リターン・IC・統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュース記事を OpenAI でセンチメント評価 → ai_scores 書き込み
  - regime_detector.py — ETF MA とマクロニュースの LLM 評価を合成して market_regime を書き込み

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 注意点・運用メモ

- .env のパースは多少の拡張（export プレフィックス、クォート、コメント）に対応しています。プロジェクトルートの .env(.local) が自動読み込みされます。
- MonitoringDB のスキーマは起動時に冪等に初期化・マイグレーションを行います（列追加など）。
- OpenAI API を使う機能（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）が必須です。API 呼び出しでの一時エラーはリトライやフェイルセーフ（スコア 0.0）で扱われます。
- LINE 通知は channel token / user id が未設定の場合は送信をスキップしてログ出力します。
- run_execution / run_monitoring はプロセス優先度を high に設定しようとします（権限がない場合は警告を出してスキップ）。
- 停止管理:
  - data/stop_requested.flag: run_* スクリプトが監視しており存在するとループを抜けます（外部から停止要求を出す用途）。
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine を停止させるトリガとなる（管理者による強制停止用途）。
- Paper Trading の検証では Paper 用 DB を使うことで本番 DB と完全に分離できます。

---

必要に応じて README を拡張します（実行例、.env.example、requirements.txt、運用チェックリスト、デプロイ手順など）。追加で欲しい情報があれば教えてください。