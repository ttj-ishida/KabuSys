# KabuSys — 日本株自動売買システム (README)

このリポジトリは、日本株の自動売買を想定した実験的なシステムです。発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築／ポジションサイズ計算、リサーチ用のファクター計算、LLM を使ったニュース NLP / レジーム判定など、複数モジュールで構成されています。

以下は本コードベースの概要、使い方、セットアップ手順、ディレクトリ構成などのドキュメントです。

---

## プロジェクト概要

主要コンポーネント:

- ExecutionEngine（発注エンジン）
  - 実際のブローカークライアントまたはペーパートレード用の MockBroker を切り替え可能（`KABUSYS_ENV` による）。
  - 注文管理（OrderManager / OrderRepository）、リスク管理（RiskManager）、照合処理（Reconciler）などを含む。
- Monitoring（監視）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文ログの監視。
  - Kill Switch（閾値超過で `data/kill.flag` を書き込み ExecutionEngine を停止させる）やアラート送信のための統合ロジック。
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み算出（等金額 / スコア加重）、セクター制限、レジーム乗数、ポジションサイズ計算等の純粋関数群。
- Research（リサーチ）
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）、将来リターン・IC 計算、特徴量探索。
- AI（LLM を用いた処理）
  - ニュースのセンチメントスコア付与（OpenAI）や市場レジーム判定（MA とマクロ NLP の組み合わせ）。
- Tools
  - Paper Trading の検証レポート生成スクリプト等。

設計方針の例:
- 実運用とペーパートレードの DB は分離（`PAPER_TRADING_SQLITE_PATH`）。
- ルックアヘッドバイアスを避ける（日時参照の扱いに注意）。
- ミニマム依存外部 API（DuckDB / OpenAI のみ必要な箇所がある）。

---

## 機能一覧

- 設定管理 / ウィザード
  - `.env` の対話式生成: `python -m kabusys.config_setup`
  - 設定検証: `python -m kabusys.validate_config [--strict]`
- 実行
  - ExecutionEngine 起動: `python -m kabusys.run_execution`
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用して `data/paper_trading.db` に記録
  - Monitoring 起動: `python -m kabusys.run_monitoring`
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）
- 監視 / Kill Switch
  - `kill.flag` を書き込むことで ExecutionEngine 停止トリガーを発生させる
  - `data/stop_requested.flag` を置く／削除することで起動中スクリプトの外部停止を制御
- ポートフォリオ構築
  - 候補選定、等配分・スコア加重、セクター上限適用、リスクベースのポジションサイズ計算
- リサーチ（DuckDB 接続）
  - モメンタム・ボラティリティ・バリューなどのファクター計算
  - 将来リターン、IC、統計サマリー計算
- AI（OpenAI）
  - ニュースセンチメント集計 (`kabusys.ai.news_nlp.score_news`)
  - 市場レジーム判定 (`kabusys.ai.regime_detector.score_regime`)
- ツール
  - Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`

---

## 必要条件 / 推奨環境

- Python 3.10+
  - 型注釈や union 型 (|) を使用しています。
- 必要な Python パッケージ（主要）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定検証で YAML の中身を検証したい場合。なくても動作しますが警告が出ます）
- （開発）仮想環境の利用を推奨

例:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai PyYAML
```

注: requirements.txt がないため、上記を参考に必要なパッケージを追加してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・依存インストール（上記参照）

3. .env ファイルの作成（推奨: ウィザードを使用）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードを使わずに手動で作る場合は `.env.example` を参考にしてください。最低限必要な環境変数:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   その他（デフォルト値あり）:
   - KABUSYS_ENV（development / paper_trading / live） — デフォルト: development
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（デフォルト: INFO）
   - OPENAI_API_KEY（AI 機能を使う場合）

   サンプル（一部）:
   ```
   JQUANTS_REFRESH_TOKEN=your_token_here
   KABU_API_PASSWORD=your_password_here
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

5. 必要なディレクトリ / ファイル
   - `data/`（DB や PID / flag を置く）と `logs/`（ログ）ディレクトリは自動作成されることが多いですが、権限や配置に注意してください。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動
  - 本番 / 開発 / ペーパートレードは `KABUSYS_ENV` によって切り替え
  ```
  # 通常
  python -m kabusys.run_execution

  # 環境を指定して起動（例: ペーパートレード）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - ペーパートレードでは `MockBrokerClient` が使用され、データは `data/paper_trading.db` に保存されます。
  - ExecutionEngine の PID はデフォルトで `data/execution.pid` に書き込まれます。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を秒単位で変更する場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は本番 sqlite（`SQLITE_PATH`）を参照します（環境に関わらず本番監視 DB を使用する設計です）。

- 外部停止（外部からプロセスを終了させたい場合）
  - 監視 / 実行スクリプトはプロジェクトルートの `data/stop_requested.flag` の存在をチェックします。ファイルを作成するとループ内で検出して終了します。
  - Kill Switch は `data/kill.flag` を書くことで ExecutionEngine に停止シグナルを送ります（`KillSwitch` の条件に基づく）。

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（OpenAI）を使う場合
  - 環境変数 `OPENAI_API_KEY` を設定してください。
  - 例: ニューススコア付与（プログラム呼び出し）
    - Python から: `from kabusys.ai.news_nlp import score_news`
    - コマンドラインスクリプトは提供されていませんが、score_news を呼ぶユーティリティを作成して運用できます。

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用 / 推奨
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb（分析用）
  - SQLITE_PATH: data/monitoring.db（監視 DB）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
  - PAPER_FILL_MODE: ペーパートレード時の約定モード（instant | partial | never | reject）。デフォルト: instant
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

---

## 停止 / フラグ制御

- `data/stop_requested.flag`:
  - 実行中の run_monitoring / run_execution はループ中にこのファイルの有無をチェックします。存在すると正常終了（停止）します。
- `data/kill.flag`:
  - KillSwitch が条件を満たすとこのファイルを書き込み、ExecutionEngine に停止信号を与えます。
  - `Settings.kill_flag_clear_on_start` が 1 に設定されていると起動時に自動でクリアされます（本番環境では危険な設定のため注意）。

---

## ディレクトリ構成（主なファイル）

プロジェクトのソースは `src/kabusys` にあります。以下は主要ファイル / モジュールの概要（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（自動 .env ロード含む）
  - config_setup.py         — .env の対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリング起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ（Console + 日次ローテーション）
    - process_priority.py   — プロセス優先度 / CPU アフィニティ設定
  - monitoring/
    - monitoring_db.py      — SQLite ベースの監視 DB 永続化層
    - system_monitor.py     — システム・データ鮮度監視
    - trade_monitor.py      — （注文関連監視ロジック）
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — Kill Switch 実装（flag ファイル書き込み）
    - monitoring_engine.py  — 各 Monitor を束ねる実行エンジン
    - alert_manager.py      — （通知管理）
  - execution/
    - execution_engine.py   — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュース NLP / OpenAI 連携
    - regime_detector.py    — レジーム判定（MA + マクロ NLP）
  - tools/
    - paper_verification_report.py

（注）上記は本 README に含まれるソース一覧の抜粋です。実装の詳細は各ファイル内のドキュメンテーション文字列（docstring）を参照してください。

---

## 開発上の注意点 / 補足

- DB の初期化:
  - `init_monitoring_db()` が監視用 SQLite DB のテーブル作成と簡易マイグレーションを担います。起動スクリプトは自動的に呼び出します。
- ログ:
  - デフォルトで stdout と `logs/<app_name>.log`（日次ローテーション、30 日保持）へ出力します。`LOG_DIR` 環境変数で変更可能です。
- OpenAI 呼び出し:
  - API エラー時はリトライやフェイルセーフ（スコアを採らない、あるいはデフォルト値）で継続する実装になっていますが、API キーは必ず適切に管理してください。
- 本番環境注意点:
  - `KABUSYS_ENV=live` をセットする場合は `.env` の値・通知設定（LINE など）を十分確認してください。`validate_config.py` は live 時に追加チェックを行います。
- テスト:
  - 外部 API 呼び出し部分は関数をモックしやすい設計になっています（ユニットテストでの差し替えを想定）。

---

不明点や追加してほしい情報があれば知らせてください。README にサンプル .env のテンプレートや実行例を追加することもできます。