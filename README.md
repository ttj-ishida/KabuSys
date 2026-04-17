# KabuSys

日本株自動売買システム（簡易版）のコードベース README。  
本ドキュメントはリポジトリ内の主要ファイルから機能・設定・起動手順をまとめたものです。

注意: 実行には Python 3.9+ を推奨します（実際の要件はプロジェクトの packaging/requirements を確認してください）。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視のためのモジュール群を提供します。主要機能は以下のカテゴリに分かれます。

- Execution: ブローカークライアントを用いた発注エンジン（本番 / ペーパートレード切替対応）
- Monitoring: システム状態・注文状態・リスクを定期監視してログ記録・アラート・Kill Switch を管理
- Portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター制約などの純粋関数群
- Research: DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- AI: OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- Tools: ペーパートレード検証レポート生成 等のユーティリティスクリプト
- Config: 環境変数の読み込み/ウィザード/検証ツール

設計方針の例:
- 本番 DB とペーパートレード DB は分離（ペーパートレードは data/paper_trading.db を使用）
- DuckDB は時系列データ・研究用途で使用
- 自動化された Kill Switch / リスクログ / アラート（LINE）を備える

---

## 機能一覧（抜粋）

- 環境設定ウィザード（interactive）: python -m kabusys.config_setup
- 設定検証ツール: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading で MockBroker を使用し DB を分離
- SystemMonitor 起動スクリプト（監視ループ）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.score_news: ニュースを OpenAI でスコアリングして ai_scores に格納
  - kabusys.ai.regime_detector.score_regime: マクロ＋MA200 を組み合わせたレジーム判定
- Portfolio モジュール:
  - 候補選定、等重・スコア重み、リスク調整、ポジションサイズ計算
- Monitoring:
  - system_status / trade_logs / risk_logs / positions / dashboard を SQLite に永続化
  - AlertManager による LINE 通知（トークンが設定されている場合）
  - KillSwitch による停止フラグ生成（data/kill.flag）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化し、必要ライブラリをインストールしてください。最低限必要なライブラリ（例）:

   - duckdb
   - psutil
   - openai
   - requests
   - PyYAML（config YAML の検証に任意で使用）

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate     # macOS/Linux
   .venv\Scripts\activate        # Windows

   pip install duckdb psutil openai requests PyYAML
   ```

   ※ 実際のプロジェクトでは requirements.txt か pyproject.toml を参照してください。

2. リポジトリルートに移動し、.env を作成します。対話式ウィザードを使うのが簡単です:

   ```
   python -m kabusys.config_setup
   ```

   ウィザードは `.env` を作成・更新します。手動で作る場合は下記のサンプルを参照してください。

3. 環境変数確認（推奨）:

   ```
   python -m kabusys.validate_config
   ```

   `--strict` を付けると警告も失敗扱いになります。

4. データディレクトリの準備（必要に応じて）:

   デフォルトでは `data/` 下に SQLite / DuckDB / PID / flag ファイルが作成されます。権限やディスク容量を確認してください。

---

## 主な環境変数（代表）

（.env で設定できます。未設定時は README 中のデフォルトが利用されます）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG / INFO / WARNING / ERROR、デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN（任意：アラート用）
- LINE_USER_ID（任意：アラート用）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト: 60）

サンプル .env:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（起動・運用）

1. 設定検証（必須ではないが推奨）
   ```
   python -m kabusys.validate_config
   ```

2. 実行エンジン（ExecutionEngine）の起動
   - 本番/ペーパーの切替は KABUSYS_ENV で制御します。
   - paper_trading の場合、MockBroker を使い `PAPER_TRADING_SQLITE_PATH` に記録されます。

   例（そのまま起動）:
   ```
   python -m kabusys.run_execution
   ```

   注意:
   - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
   - 実行中は `data/execution.pid` に PID が書き込まれます。SystemMonitor が stale PID を検出すると削除します。

3. 監視ループ（SystemMonitor）を起動
   ```
   python -m kabusys.run_monitoring
   ```
   - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可（秒）。
   - 監視は常に本番の `SQLITE_PATH` を使用する設計（環境にかかわらず monitoring DB は同じ）。
   - 終了させたいときは `data/stop_requested.flag` を作成してください。監視ループは検知して停止します。

4. ペーパートレード検証レポートを作成
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - `--db` で DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

5. AI 機能（ニューススコア・レジーム判定）
   - OpenAI API キーが必要: `OPENAI_API_KEY` を環境変数に設定するか、関数に直接渡します。
   - ライブラリ API としては `kabusys.ai.score_news(conn, date, api_key=None)` や `kabusys.ai.regime_detector.score_regime(conn, date, api_key=None)` が利用可能です（スクリプトの CLI は未提供）。DuckDB 接続を渡して利用します。

6. Kill Switch / 停止フラグ
   - KillSwitch は `data/kill.flag` を書き込み、ExecutionEngine 停止のトリガーになります（Monitoring が判定して書き込む）。
   - Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag をクリアする設定になります（本番では推奨しない）。

---

## 停止・フラグファイル

- stop_requested.flag
  - run_execution / run_monitoring がチェックするファイル。存在すると起動をスキップ（または実行中に停止）。
  - パス: project_root/data/stop_requested.flag

- kill.flag
  - KillSwitch が書き込み、ExecutionEngine に停止を促すフラグ（Monitoring がリスク検出時に書く）。
  - ExecutionEngine はこれを見て安全停止します（clear オプションあり）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイル・モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージエントリ（バージョン等）
  - config.py — 環境変数読み込み・Settings クラス（.env の自動読み込み含む）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金配分ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・読み書きラッパー
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成/管理
    - alert_manager.py — LINE 通知（push）
  - execution/ (一部参照のみ - 実装の詳細は別ファイル)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py
  - research/
    - factor_research.py — momentum/value/volatility ファクター計算（DuckDB 利用）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に保存
    - regime_detector.py — MA + LLM による市場レジーム判定
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ

---

## 開発・運用上の注意事項

- 本リポジトリは実運用を想定した設計要素（Kill Switch、監視ログ、冪等な DB 書き込みなど）を含みます。実運用時は以下に注意してください:
  - 本番環境（KABUSYS_ENV=live）では LINE トークンや各種キーの取り扱いに十分注意すること
  - KILL_FLAG_CLEAR_ON_START は本番で `1` に設定しないこと（危険）
  - DB のバックアップ、監視、ログローテーションを適切に行うこと
- OpenAI を利用するモジュールは API 呼び出しに失敗した場合のフォールバック処理を備えていますが、API 利用料金とレート制限に注意してください。
- psutil によるプロセス優先度設定は OS 権限に依存します。設定に失敗する場合は警告が出ますが処理は継続します。

---

この README はコード内の docstring と設計注釈を元に作成しています。詳細実装や追加のスクリプトについては各モジュールの docstring を参照してください。質問や README の補足を希望される場合は、どの部分を拡充したいか教えてください。