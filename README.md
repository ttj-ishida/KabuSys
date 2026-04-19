# KabuSys

日本株自動売買システムのリポジトリ（ドキュメント版）。  
このREADMEはリポジトリ内の主要スクリプト／モジュール（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI連携など）をまとめた使い方ガイドです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な目的は以下：

- シグナル → ポートフォリオ構築 → 注文管理 → 約定監視 のワークフローを実装
- 監視（System / Trade / Risk）により安全停止（Kill Switch）を実現
- Paper Trading（模擬発注）を本番 DB と分離して検証可能
- DuckDB を使ったファクター計算・リサーチ機能
- OpenAI を用いたニュースの NLP スコアリングや市場レジーム判定（任意）

設計方針の一部：
- 多くのロジックは純粋関数（副作用なし）で記述され、テスト容易性を確保
- .env ベースの設定管理（`config_setup` / `validate_config` CLI を用意）
- ロギングは統一された `setup_logging` で管理（stdout + 日次ファイルローテーション）

---

## 機能一覧

- Execution（発注エンジン）
  - 実際のブローカークライアントまたは MockBroker（KABUSYS_ENV=paper_trading）を切替
  - OrderRepository / OrderManager / RiskManager / Reconciler を統合してセッション実行
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク・データ鮮度・プロセス生存の監視
  - TradeMonitor：発注／約定ログの異常検出（滞留注文、価格異常など）
  - RiskMonitor：ドローダウン・ポジション上限監視、Kill Switch との連携
  - MonitoringEngine：各モニタのポーリングと Alert 発行
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額／スコア加重、リスクベースの株数算出、セクター上限、レジーム乗数
- Research（リサーチ）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI（オプション）
  - news_nlp：OpenAI を利用したニュースセンチメント評価 → ai_scores 書き込み
  - regime_detector：ETF（1321）MA200 とマクロニュースで市場レジーム判定
- ユーティリティ
  - config_setup：対話式 .env 作成ウィザード
  - validate_config：起動前チェック（必須環境変数・ファイルの存在等）
  - tools.paper_verification_report：Paper Trading の検証レポートを生成

---

## セットアップ手順（ローカル）

1. リポジトリをチェックアウトしワークディレクトリへ移動

2. 仮想環境作成（例）
   - python 3.10+ を推奨
   - venv を使う例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合、主要依存をインストールしてください：
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML （validate_config で YAML 検証をする場合、なくても動作するが警告が出ます）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. 環境変数の準備
   - 対話式ウィザードで .env を作成：
     - python -m kabusys.config_setup
   - あるいは `.env` を手動で作る（下記に主要な変数を記載）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も FAIL としたい場合は `--strict` を付ける

6. データディレクトリ
   - デフォルトで `data/` 下に DB・PID・フラグファイル等を置きます。必要があれば `.env` でパスを書き換えてください。
   - ログは `logs/` に出力されます（`LOG_DIR` で変更可能）。

注意:
- 自動で `.env` をロードする仕組みが組み込まれています（プロジェクトルートに `.env` / `.env.local` がある場合）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要環境変数（抜粋）

以下はコードの `config_setup` / `Settings` に基づく主要変数です。デフォルト値や用途も併記します。

- JQUANTS_REFRESH_TOKEN（必須）
  - J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD（必須）
  - kabuステーション API 用パスワード
- KABUSYS_ENV（default: development）
  - 実行環境: `development` / `paper_trading` / `live`
  - `paper_trading` 時は MockBroker を使用し DB を分離
- KABU_API_BASE_URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH（default: data/kabusys.duckdb）
  - DuckDB ファイルパス（リサーチ・AI 用）
- SQLITE_PATH（default: data/monitoring.db）
  - 監視ログ用 SQLite（Monitoring）
- PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）
  - Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading 時に使用）
- LOG_LEVEL（default: INFO）
- LOG_DIR（default: logs/）
- OPENAI_API_KEY
  - OpenAI を使う機能（news_nlp / regime_detector）で必須
- KILL_FLAG_CLEAR_ON_START（default: 0）
  - Execution 起動時に kill.flag を自動でクリアするか（0 推奨）
- MONITOR_POLL_INTERVAL（default: 60）
  - run_monitoring のポーリング間隔（秒）
  - 1 未満や不正値を与えるとデフォルトにフォールバック

その他の設定は `config_setup` を実行すると対話的に作成できます。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: 起動時に `data/stop_requested.flag` が存在すると起動しません（停止フラグによる制御）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を用い paper_trading DB に記録します
  - 起動中は `data/execution.pid` に PID が書き込まれます

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）
  - 監視は本番 sqlite_path を常に使用（環境によらず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 日付範囲指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能（例）
  - news_nlp.score_news / regime_detector.score_regime を呼び出して DuckDB に書き込みを行います。これらを CLI からラップして使うことを想定しています。
  - 必要: OPENAI_API_KEY 環境変数（または関数引数で渡す）

ログ:
- 全スクリプト共通の `kabusys.utils.logging_setup.setup_logging` を使います。`LOG_DIR`/`LOG_LEVEL` を環境変数で調整できます。

停止制御:
- Monitoring の KillSwitch は `data/kill.flag` を書きます（存在すると Execution に停止要求を行う仕組み）。
- 管理者が手動で停止したい場合は flag を作成するか、`data/stop_requested.flag` を置くことで run_* スクリプトを速やかに終了できます。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` をルートとする主要モジュールのツリー（抜粋）：

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 自動 .env ロード / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py       — SQLite 永続層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 発注／約定監視（※ファイル内で実装あり）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor 統合ループ
    - alert_manager.py       — アラート送信（LINE 等、実装箇所に依存）
  - execution/
    - execution_engine.py    — 発注エンジン本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 数量決定ロジック
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等の計算（DuckDB）
    - feature_exploration.py — forward returns, IC, summary
  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI 統合
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成ツール
  - utils/
    - logging_setup.py       — ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity（psutil 利用）
    - __init__.py

プロジェクトルート直下:
- .env, .env.local (自動ロード対象)
- data/（デフォルトの DB, PID, flag を置く場所）
- logs/（デフォルトログ出力先）

---

## 注意点 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では Kill Switch 設定や LINE 通知設定等を必ず確認してください。`validate_config` の警告に特に注意。
- `psutil` によるプロセス優先度設定は OS に依存します。権限不足で警告が出る場合がありますが処理は継続します。
- DuckDB のクエリは大きなデータセットを読み込むため、ディスク容量と I/O を事前に確認してください。
- OpenAI 関連の API コールはレート制限・コストの観点から注意して運用してください（リトライ・バックオフ実装あり）。
- `.env` は機密情報（APIトークン）を含むため、絶対に Git 等にコミットしないでください。

---

## よく使うコマンドまとめ

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README にサンプル .env テンプレート、デプロイ手順（systemd / Supervisor / Dockerfile など）、各モジュールの API 仕様書（関数の引数と戻り値詳細）を追加で作成します。どのドキュメントを優先してほしいか教えてください。