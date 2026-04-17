# KabuSys

日本株向けの自動売買・リサーチ基盤（ライブラリ）。  
本リポジトリは、データ処理（DuckDB）、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視機能、AI（OpenAI）を組み合わせた実装を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコアロジック群を提供します。主な目的は以下です。

- 市場データの集計・ファクター計算（DuckDB を使用）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- 実際の発注ロジック（本番/ペーパートレード対応）
- 実行中プロセス・注文・リスクの監視とアラート
- OpenAI を用いたニュース NLP（センチメント）およびレジーム判定
- 各種ユーティリティ・CLI（設定ウィザード、設定検証、検証レポート）

設計方針として、ルックアヘッドバイアスの排除、フェイルセーフ（API失敗時のフォールバック）、およびモジュールの独立性を重視しています。

---

## 主な機能一覧

- 環境設定読み込み／ウィザード
  - .env 自動読み込み（`.env` / `.env.local`、OS 環境変数優先）
  - 対話式ウィザード: `kabusys.config_setup`
  - 起動前の設定検証: `kabusys.validate_config`
- Execution
  - ExecutionEngine を起動して発注処理を回す（本番 / ペーパートレード切替）
  - BrokerClientFactory 経由で本番ブローカー or MockBroker（paper_trading）を選択
  - 発注履歴は SQLite（paper_trading は専用 DB）
- Monitoring
  - SystemMonitor: CPU/MEM/DISK、プロセス生存、データ鮮度
  - TradeMonitor: 滞留注文・約定価格異常の検知
  - RiskMonitor: ドローダウン、ポジション上限の監視とログ
  - KillSwitch: 条件に応じて停止フラグを書き込み（ExecutionEngine 停止）
  - AlertManager: LINE Messaging API へのプッシュ（クールダウン管理）
- Research / Factors
  - Momentum / Volatility / Value 等のファクター算出（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）等の分析ツール
- AI
  - news_nlp: ニュースを集約して OpenAI に問い合わせ、銘柄別センチメントを ai_scores テーブルへ
  - regime_detector: ETF（1321）MA200 とマクロニュースを使った市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 必須 / 推奨依存パッケージ

（requirements.txt は含まれていないため手動でインストールしてください）

- python >= 3.9
- duckdb
- psutil
- openai
- requests
- PyYAML（config YAML の内容検証を行う場合に必要）
- （開発 / テスト用に追加ライブラリが必要な場合があります）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. .env の準備
   - 対話式ウィザードで作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（`.env.example` を参照してください）。

4. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. 必要ならデータディレクトリを作成
   ```bash
   mkdir -p data
   ```

注意:
- 環境変数 `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれかを指定します（デフォルト: development）。
- `.env` の自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

主な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development|paper_trading|live）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — Monitoring 用 DB（run_monitoring は常にこれを使用）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用）
- LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など

重要な設定:
- PAPER_FILL_MODE（paper_trading 時の約定挙動: instant/partial/never/reject）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔 秒、デフォルト 60）

---

## 使い方（主要コマンド）

- 監視ループ起動（SystemMonitor をポーリング）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を設定: `MONITOR_POLL_INTERVAL=30`
  - 監視実行中にプロジェクトの `data/stop_requested.flag` が作成されるとループを終了します。

- 実行エンジン（ExecutionEngine）起動
  ```bash
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、データは `data/paper_trading.db` に分離記録されます。
  - ExecutionEngine は `data/execution.pid` に PID を書きます。監視は `data/stop_requested.flag` や `data/kill.flag` を使って停止します。

- 設定ウィザード（.env 生成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI（ニュース NLP / レジーム判定）
  - これらはライブラリ関数として呼び出すことが想定されています。環境変数 `OPENAI_API_KEY` を設定してください。
  - 例（Python から呼び出し）:
    ```py
    from kabusys.ai.news_nlp import score_news
    score_count = score_news(duckdb_conn, target_date, api_key="...")

    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```

---

## 停止 / Kill Switch の挙動

- ExecutionEngine は外部からの停止指示をフラグファイルで受け取ります:
  - stop_requested.flag — 起動スクリプト（run_monitoring/run_execution）が監視している停止トリガー（プロジェクトの `data/stop_requested.flag`）。
  - kill.flag — KillSwitch（監視コンポーネント）が書き込む停止指示。`Settings.kill_flag_path`（デフォルト `data/kill.flag`）で指定。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると、起動時に kill.flag を自動でクリアします（本番環境では推奨されません）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下を中心に抜粋した構成です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py                — .env 対話式ウィザード CLI
  - validate_config.py             — 起動前設定検証 CLI
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py             — SQLite 監視ログ永続化層
    - system_monitor.py            — システム監視
    - trade_monitor.py             — 注文監視（滞留、約定異常）
    - risk_monitor.py              — ドローダウン / ポジション上限監視
    - kill_switch.py               — Kill Switch（フラグファイル書き込み）
    - alert_manager.py             — LINE 通知ユーティリティ
    - monitoring_engine.py         — 監視コンポーネントの束ね
  - execution/                      — 発注エンジン（実装のエントリ、ファクトリ等はここに格納される想定）
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 発注株数計算
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py           — 各種ファクター計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — レジーム判定（MA200 + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

- config/
  - *.yaml （system_config.yaml 等。validate_config でチェック対象）

- data/
  - monitoring.db (デフォルト) / paper_trading.db / kabusys.duckdb など（環境変数で上書き可）
  - stop_requested.flag, kill.flag, execution.pid などのフラグ / PID ファイルが置かれる場所

---

## 開発・運用上の注意点 / トラブルシューティング

- DB 分離
  - run_execution は `KABUSYS_ENV=paper_trading` の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番の monitoring DB と分離します。
  - しかし run_monitoring（監視）は KABUSYS_ENV にかかわらず Settings.sqlite_path（監視用 DB、デフォルト data/monitoring.db）を使用します。監視ログは本番 DB を前提とする点に注意してください。
- OpenAI
  - AI 機能を使うには `OPENAI_API_KEY` が必要です。API のエラーはリトライやフォールバック（例: macro_sentiment=0.0）実装がありますが、キー未設定の場合はエラーとなります。
- process priority / CPU affinity
  - プロセス優先度設定は psutil を利用。権限不足や未サポートプラットフォームでは警告を出してスキップします。
- YAML 検証
  - validate_config は PyYAML が未インストールの場合、YAML の中身チェックをスキップします（警告）。
- ログレベル・ログ出力
  - Settings.log_level によってログレベルチェックがあります。起動スクリプトは基本的に logging.basicConfig(level=logging.INFO) で開始します。

---

## 参考コマンドまとめ

- 監視開始:
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン開始（ペーパートレード）:
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- .env ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要があれば、この README にシステム図、より詳細な設定例（.env のテンプレート）やデバッグガイド（ログの見方、db の中身確認クエリ例）を追加します。どの情報を優先して追記しましょうか？