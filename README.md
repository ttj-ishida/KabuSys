# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を提供する Python ベースのシステムです。

- 戦略（ファクター計算、特徴量解析、ポートフォリオ構築）
- 発注実行（ExecutionEngine、注文管理、リスク管理）
- 監視（System / Trade / Risk の定期監視、Kill Switch）
- 研究用ツール（DuckDB ベースのファクター計算、検証レポート）
- AI 補助機能（ニュースのセンチメント評価、レジーム判定）

設計方針の概要:
- 本番・ペーパーを明確に分離（環境変数 `KABUSYS_ENV`）
- 設定は `.env` ファイル / 環境変数で管理（自動ロード機能あり）
- DuckDB と SQLite を用途に応じて使い分け
- ログは標準出力 + 日次ローテートファイル出力（`logs/<app>.log`）

---

## 主な機能一覧

- Settings 管理（`kabusys.config`）
  - .env の読み込み・パース（クォートやコメント対応）
  - 必須/任意の環境変数チェック
- 環境設定ウィザード（`kabusys.config_setup`）
  - 対話的に `.env` を生成・更新
- 設定検証 CLI（`kabusys.validate_config`）
  - 必須環境変数・YAML 設定・DB パス等の事前チェック
- ExecutionEngine 起動スクリプト（`run_execution.py`）
  - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し DB を分離
  - 停止フラグ（`data/stop_requested.flag`）検出で安全停止
  - プロセス優先度設定、PID ファイル出力
- Monitoring 起動スクリプト（`run_monitoring.py`）
  - SystemMonitor のポーリングループ（デフォルト 60 秒）
  - 監視ログは常に本番用 SQLite パスに書き込む
  - `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能
- Monitoring サブモジュール
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス検出
  - TradeMonitor: 注文の滞留や約定異常を検出（trade_logs 参照）
  - RiskMonitor: ドローダウン、ポジション上限監視（dashboard / positions 参照）
  - KillSwitch: リスク条件に応じて `data/kill.flag` を書き込み、Execution を停止
  - AlertManager（アラート送信の抽象）
- 研究・ポートフォリオ
  - factor_research: Momentum/Volatility/Value のファクター計算（DuckDB）
  - portfolio: 候補選定・重み付け・単元丸め・セクターキャップ等
  - research.feature_exploration: forward returns、IC、統計要約
- AI（OpenAI）連携
  - news_nlp: ニュース記事を LLM でセンチメント評価し `ai_scores` に保存
  - regime_detector: ETF MA とマクロセンチメントを合成し市場レジーム判定
  - OpenAI API 呼び出しは再試行（指数バックオフ）・レスポンス検証付き
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポート生成

---

## 要件 (推奨)

- Python 3.9+
- 必要ライブラリ（プロジェクトの requirements.txt がある場合はそちらを参照）
  - duckdb
  - psutil
  - openai
  - PyYAML（`validate_config` の YAML 検査に利用。無くても動作はする）
- SQLite は標準ライブラリで対応

---

## セットアップ手順

1. リポジトリを取得して Python 仮想環境を作成・有効化

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   ```

2. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを使う）

   ```bash
   pip install duckdb psutil openai PyYAML
   ```

3. 環境変数 `.env` を作成（ウィザード推奨）

   ```bash
   python -m kabusys.config_setup
   ```

   - 必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な設定:
     - KABUSYS_ENV: development | paper_trading | live
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db （ペーパートレード専用 DB）
     - OPENAI_API_KEY: OpenAI を使う場合に設定

4. 設定検証

   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（起動・操作）

- 実行エンジン（ExecutionEngine）を起動

  ```bash
  python -m kabusys.run_execution
  ```

  動作:
  - 起動直後にプロセス優先度を "high" に設定（可能な場合）
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、`PAPER_TRADING_SQLITE_PATH` に書き込む（本番 DB と完全分離）
  - 停止フラグ `data/stop_requested.flag` が存在すると起動を中止または実行中に停止する
  - 実行中は `data/execution.pid` を出力（PID 管理）

- 監視ループを起動

  ```bash
  python -m kabusys.run_monitoring
  ```

  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定（デフォルト 60 秒）
    例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`
  動作:
  - 監視は常に本番 sqlite_path（`SQLITE_PATH`）を使用してログを記録
  - System/Trade/Risk チェックを行い、KillSwitch により `data/kill.flag` を書くことがある
  - 監視ループの停止は `data/stop_requested.flag` を作成することで行える（外部からの制御）

- Paper Trading 検証レポート

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示したい場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

  レポートは PAPER_TRADING_SQLITE_PATH（または --db）を参照し、
  稼働率 / 注文成功率 / レイテンシ 等を集計して PASS/FAIL を出力します。
  閾値はスクリプト内で定義（変更可能）:
  - 稼働率 >= 99%
  - 注文成立率 >= 90%
  - 送信率 >= 95%
  - P95 レイテンシ <= 200 ms

- AI 機能を使う場合
  - 環境変数 `OPENAI_API_KEY` を設定してください
  - `kabusys.ai.score_news` や `kabusys.ai.regime_detector.score_regime` をプログラムから呼び出せます
  - LLM 呼び出しは再試行・検証ロジックが実装されていますが、API キーと利用料に注意してください

---

## 停止とフラグ管理

- 停止コントロール:
  - run 系スクリプトはプロジェクトルートの `data/stop_requested.flag` の存在を監視し、見つかれば安全に終了します。
  - KillSwitch は `data/kill.flag` を書き込み（既存なら再作成しない）、これにより ExecutionEngine を停止させる仕組みです（Monitoring 側で評価して書き込む）。
- 起動時のキルフラグ自動クリア:
  - 環境変数 `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に `kill.flag` を自動で削除します（本番では 0 推奨）。

---

## ロギング

- ログ設定ユーティリティ: `kabusys.utils.logging_setup.setup_logging`
- 出力:
  - コンソール (stdout)
  - 日次ローテートファイル: `logs/<app_name>.log`（30日保持）
- ログレベル:
  - 環境変数 `LOG_LEVEL`、または `setup_logging` の引数で指定

---

## 主要設定項目（環境変数）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能で必須
- LOG_LEVEL: DEBUG/INFO/...
- KILL_FLAG_CLEAR_ON_START: 0/1（起動時に kill.flag を自動クリアするか）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）

特に PAPER_FILL_MODE（ペーパートレードの約定挙動）やその他閾値は Settings 経由で取得できます:
- PAPER_FILL_MODE: instant | partial | never | reject

---

## 開発・デバッグのヒント

- 自動 .env ロードを無効にする:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると起動時の .env 自動ロードを無効化できます（テスト時に有用）。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（警告が表示されます）。
- psutil の優先度設定は OS 権限に依存します。AccessDenied が発生する場合は警告ログが出てスキップします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数 / .env 読み取り・Settings
- config_setup.py — .env 対話ウィザード（CLI）
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

src/kabusys/utils/
- logging_setup.py — 統一的なロギング設定
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

src/kabusys/monitoring/
- monitoring_db.py — SQLite ベースの監視 DB 永続化層（init / CRUD）
- system_monitor.py — システム状態・データ鮮度チェック
- trade_monitor.py — 注文ログ監視（referenced）
- risk_monitor.py — ドローダウン / ポジション上限監視
- kill_switch.py — kill.flag 管理
- monitoring_engine.py — 各 Monitor をまとめるエンジン
- alert_manager.py — アラート送信抽象（referenced）

src/kabusys/execution/
- 実行関連（Engine, OrderManager, BrokerFactory, RiskManager など） — 実装本体（referenced）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み付け
- position_sizing.py — 株数決定・資金配分
- risk_adjustment.py — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum / Volatility / Value 計算（DuckDB）
- feature_exploration.py — forward returns / IC / 統計サマリ

src/kabusys/ai/
- news_nlp.py — ニュースの LLM ベースセンチメント評価（ai_scores へ書込）
- regime_detector.py — ETF MA とマクロセンチメントを合成したレジーム判定

src/kabusys/tools/
- paper_verification_report.py — ペーパートレードの検証レポート生成（CLI）

その他:
- data/ — デフォルトのデータ格納ディレクトリ（DB ファイル、フラグファイル等）
- logs/ — ログファイル出力先（デフォルト）

---

## 注意事項 / 運用上の留意点

- 本番環境（KABUSYS_ENV=live）では `LINE_CHANNEL_ACCESS_TOKEN` 等の通知設定を必ず確認してください。`validate_config` の警告を無視しないこと。
- `.env` は絶対に Git にコミットしないでください（`config_setup.py` もその旨を注記）。
- OpenAI 等の API は利用料が発生します。API キーと呼び出し頻度に注意してください。
- データ鮮度や PID ファイルの扱いは環境依存のため、運用ポリシー（ファイル権限・自動起動スクリプト等）を整備してください。
- ペーパートレード用 DB は本番用 DB と完全分離するよう設計されています（`paper_sqlite_path` を利用）。

---

README はここまでです。必要であれば以下を追加できます:
- .env.example のサンプル
- systemd / supervisor の起動スクリプト例
- CI / テストの実行手順

必要な追加情報があれば教えてください。