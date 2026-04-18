# KabuSys

日本株向け自動売買システムの参照実装です。  
このリポジトリは発注エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算 / 研究用モジュール、ニュース NLP（OpenAI を利用したセンチメント評価）などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような責務を持つモジュール群で構成された自動売買フレームワークです。

- 発注ロジック（発注管理、リスク管理、約定リコンシリエーション）
- 監視システム（システム状態 / データ鮮度 / リスク監視 / Kill Switch）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ計算・セクター制約）
- リサーチ/ファクター計算（DuckDB を使ったファクター計算・IC評価）
- AI モジュール（ニュースを LLM でスコアリング、レジーム判定）
- ユーティリティ（ログ設定・プロセス優先度設定・環境設定ウィザード等）
- ペーパートレード用ツール（検証レポート生成）

設計方針の一部：
- DuckDB / SQLite を利用したローカル DB ベース
- .env による環境変数管理（config_setup による対話作成）
- paper_trading モードは本番 DB と完全分離（専用の paper_trading DB を使用）
- OpenAI を使う機能は API キーが必要で、失敗時はフェイルセーフ（継続）設計

---

## 主な機能一覧

- Execution（発注エンジン）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock）
  - OrderManager / OrderRepository / Reconciler / RiskManager を組み合わせた ExecutionEngine

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、プロセスの稼働、データ鮮度を監視し SQLite に記録
  - TradeMonitor: 注文の滞留や約定異常などを検出（trade_logs を参照）
  - RiskMonitor: ドローダウン / 保有上限の監視とアラート / risk_logs への記録
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み Execution を停止させる
  - MonitoringEngine: これらを束ねてポーリング

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重/スコア重み付け、セクター上限適用、ポジションサイズ計算（lot 単位考慮）

- Research（リサーチ / ファクター）
  - momentum / volatility / value などのファクター計算（DuckDB 経由）
  - forward returns / IC 計算 / 統計サマリ

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（ai_scores テーブルに書込）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（market_regime テーブル更新）

- ツール
  - 環境セットアップウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools/paper_verification_report）

---

## 前提 / 必要要件

- Python 3.10 以上（型ヒントに `X | Y` を使用）
- 必須パッケージ（pip 等でインストール）
  - duckdb
  - psutil
  - openai
- オプション
  - PyYAML（config/*.yaml の内容検証に使用。未インストールでも動作するが警告が出る）
- SQLite は標準ライブラリに含まれます

例（venv を使ったインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## 環境変数（主なもの）

.env に設定する主要なキーとデフォルト値（.env 作成は config_setup 参照）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV (choices: development, paper_trading, live) — デフォルト: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト: INFO
- KILL_FLAG_CLEAR_ON_START (0/1) — 本番での自動クリアは危険
- PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の約定挙動
- OPENAI_API_KEY — AI モジュール利用時に必要
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、default 60）

自動 .env ロード:
- プロジェクトルートに `.env` または `.env.local` がある場合、起動時に自動読み込みされます（OS 環境変数が優先）。
- 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順

1. リポジトリをクローン／展開する。

2. Python 仮想環境を作成して依存関係をインストールする
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```

3. 対話式で .env を作成する（推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - プロンプトに従って J-Quants トークンや kabu API パスワード等を入力します。
   - 保存後に `python -m kabusys.validate_config` で検証してください。

4. 必要に応じてデータディレクトリを作成（.env のパスに依存）
   ```bash
   mkdir -p data logs
   ```

5. DB スキーマ（監視 DB）は起動スクリプトが自動的に初期化します（init_monitoring_db）。

---

## 使い方（主なコマンド）

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
  ```

- ExecutionEngine（発注エンジン）の起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID ファイルが作られます。

- Monitoring（監視ループ）の起動
  ```bash
  # MONITOR_POLL_INTERVAL によってポーリング間隔を上書き可能（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。
  - 監視は本番 sqlite_path を使用（環境にかかわらず same path を使う設計）。
  - 停止フラグファイル data/stop_requested.flag の存在でループを終了します。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。`--db` で指定も可能。

- AI 関連（プログラム API 呼び出し）
  - OpenAI を使う機能（ニュース NLP / レジーム判定）は環境変数 `OPENAI_API_KEY` または引数で API キーを渡す必要があります。
  - 失敗時はフェイルセーフ動作（スコア=0.0 等）するよう設計されていますが、API キー未設定だと例外を送出する場合があります。

---

## 停止 / Kill スイッチ

- ExecutionEngine の停止
  - 監視側（KillSwitch）が条件を満たすと `data/kill.flag` を書き込みます。ExecutionEngine は起動中にこのフラグや stop フラグを参照して停止します。
  - 手動停止（安全に停止したい場合）：`data/stop_requested.flag` を作成すると run_execution/run_monitoring は検知して終了します。

- 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定していると Kill Flag を自動クリアします（本番では推奨されません）。

---

## ログ

- ログは `kabusys.utils.logging_setup.setup_logging` により統一設定されます。
- デフォルト:
  - コンソール: stdout（StreamHandler）
  - ファイル: 日次ローテート設定（logs/<app_name>.log、30日保持）
- ログディレクトリは `LOG_DIR` 環境変数、引数 `log_dir`、または `logs/` が使用されます。

---

## 主要なディレクトリ構成（抜粋）

リポジトリ内の重要ファイルと役割（src/kabusys 以下）

- __init__.py
- config.py — 環境変数 / Settings 管理、自動 .env ロードロジック
- config_setup.py — 対話式 .env 生成ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に書き込む
  - regime_detector.py — マクロニュース + ETF MA で market_regime を判定
- monitoring/
  - monitoring_db.py — SQLite の永続化層（schema 初期化・CRUD）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （trade_logs を監視）※詳細は実装参照
  - risk_monitor.py — ドローダウン/ポジション上限監視
  - kill_switch.py — kill.flag の書き込み
  - monitoring_engine.py — 各モニタを束ねる
  - alert_manager.py — LINE 等への通知管理（実装参照）
- execution/ — 発注エンジン関連（BrokerClientFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等）
- portfolio/ — portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/ — factor_research.py, feature_exploration.py
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

data/（ランタイムで作られる想定）
- data/monitoring.db （デフォルト SQLite）
- data/paper_trading.db （paper_trading 用）
- data/kabusys.duckdb（デフォルト duckdb）
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag

logs/
- logs/execution.log, logs/monitoring.log など

---

## その他・運用上の注意

- paper_trading モードは本番データベースと分離する設計になっています。必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- 本番運用時は KABUSYS_ENV=live の設定や KILL_FLAG_CLEAR_ON_START などに注意してください（validate_config は live 時のガードチェックを含みます）。
- OpenAI を利用する機能は API レート制限／エラーに対してリトライやフェイルセーフを実装していますが、API コストやレイテンシの運用影響を考慮してください。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソールのみの出力になります（警告が出ます）。

---

必要に応じて README をプロジェクトの実運用方針やデプロイ手順に合わせて拡張してください。README の他に各モジュールの docstring（ソース内コメント）に詳細な利用方法・設計意図が書かれていますので参照してください。