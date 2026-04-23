# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動用スクリプト群を含むリポジトリの README（日本語）。

この README はソースコード（`src/kabusys`）を参照して作成しています。各種モジュールの概要、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群を提供します。主な機能は次のとおりです。

- ExecutionEngine を中心とした発注実行（本番 / ペーパートレード対応）
- 監視 (Monitoring)：システム稼働状況、注文ログ、リスク監視、Kill Switch
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算、セクター上限）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- AI を利用したニュース NLP（OpenAI）および市場レジーム判定
- ユーティリティ（ログ設定、プロセス優先度設定など）
- 複数の CLI ツール（設定ウィザード、設定検証、paper trading レポートなど）

設計上、DB を使った永続化は DuckDB（分析用）と SQLite（監視・ペーパートレード用）で分離されています。ペーパートレード時は実口座と DB/発注を完全に分離するよう配慮されています。

---

## 主な機能一覧

- 起動スクリプト
  - `run_execution.py` : ExecutionEngine の起動（KABUSYS_ENV によりペーパー/本番切替）
  - `run_monitoring.py` : SystemMonitor のポーリングループ起動
- 設定関連 CLI
  - `config_setup.py` : 対話式 .env 作成ウィザード
  - `validate_config.py` : 環境変数 / config YAML の事前検証
- 監視関連
  - `monitoring/monitoring_db.py` : SQLite の監視テーブル定義・ラッパー
  - `monitoring/system_monitor.py`, `trade_monitor.py`, `risk_monitor.py`：各種監視ロジック
  - `monitoring/kill_switch.py`：kill.flag による ExecutionEngine 停止機能
  - `monitoring/monitoring_engine.py`：複数監視の統合ループ
- 発注 / 実行（execution）関連
  - BrokerFactory/ExecutionEngine/OrderManager/RiskManager/Reconciler 等（発注の管理・リスク制御）
- ポートフォリオ（portfolio）
  - 銘柄選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算 / IC / 統計サマリ
- AI（ai）
  - `news_nlp.py`：記事を集約して OpenAI に投げセンチメント / ai_scores に書き込み
  - `regime_detector.py`：MA + マクロセンチメント合成による market_regime 判定
- ツール
  - `tools/paper_verification_report.py`：ペーパートレード DB から検証レポートを生成
- ユーティリティ
  - `utils/logging_setup.py`：統合ログ設定（コンソール + 日次ローテーションファイル）
  - `utils/process_priority.py`：プラットフォーム依存差分を吸収する優先度設定ユーティリティ

---

## 必要環境・依存パッケージ

推奨 Python バージョン: 3.10+

主な依存（抜粋）:
- duckdb
- openai (OpenAI SDK)
- psutil
- PyYAML（config 検証のため任意、インストールされていない場合は YAML 検証をスキップします）
- 標準ライブラリ: sqlite3, logging, pathlib 等

requirements ファイルがない場合は次のようにインストールしてください（例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai psutil pyyaml
```

※ 実行環境に合わせて適宜バージョンを固定してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する。
2. 依存パッケージ（上記）をインストールする。
3. 環境変数を準備する
   - 推奨: 対話式ウィザードで .env を作成する
     ```bash
     python -m kabusys.config_setup
     ```
   - または、`.env` をテキストで編集して各値を設定する。

4. 設定を検証する
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN （J-Quants API 用）
   - KABU_API_PASSWORD （kabuステーション API 用）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（`development` / `paper_trading` / `live`。デフォルト: development）
   - その他: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（必要に応じて）

.env の自動読み込みについて:
- 起動時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動ロードします。
- OS 環境変数の優先度が高く、`.env.local` は `.env` を上書きできます。
- テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（起動・主要コマンド）

- ExecutionEngine（発注エンジン）起動:
  - 本番 / ペーパートレードは KABUSYS_ENV に依存します。
  - 起動:
    ```bash
    python -m kabusys.run_execution
    ```
  - 停止はプロジェクトルート `data/stop_requested.flag` を作成すると監視しているプロセスが検知して停止します。
  - 実行時に `data/execution.pid` が作成されます。

- Monitoring（監視ループ）起動:
  - 起動:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト 60 秒。
  - 監視は常に本番 `sqlite_path` を参照します（監視 DB は環境に依存しない本番 DB を使う設計）。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能
  ```

- AI 機能
  - `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime` は OpenAI API キーが必要です（引数または環境変数 `OPENAI_API_KEY`）。詳細は該当モジュールの docstring を参照してください。

---

## 重要なファイル / フラグの位置

- 停止 / 停止要求フラグ
  - `data/stop_requested.flag` : run_* スクリプトがループ終了判定で参照
  - `data/kill.flag` : KillSwitch が書き込む（ExecutionEngine に停止を促す）
  - `data/execution.pid` : ExecutionEngine の PID ファイル（存在チェックに使用）

- デフォルト DB パス（環境変数で上書き可）
  - DuckDB: `data/kabusys.duckdb` (`DUCKDB_PATH`)
  - SQLite（監視）: `data/monitoring.db` (`SQLITE_PATH`)
  - SQLite（paper trading）: `data/paper_trading.db` (`PAPER_TRADING_SQLITE_PATH`)

- ログ
  - デフォルトログディレクトリ: `logs/`
  - ログファイル名: `<app_name>.log`（例: `execution.log`, `monitoring.log`）
  - 環境変数 `LOG_DIR` / `LOG_LEVEL` で上書き可能

---

## 主な環境変数（抜粋・説明）

- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: ペーパートレードの fill モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に `kill.flag` を自動クリアするか（`1` でクリア）

---

## 動作のポイント・運用上の注意

- run_monitoring は監視のために常に本番の sqlite_path を利用する設計になっています（環境にかかわらず）。
- run_execution は KABUSYS_ENV に応じて paper_trading 用 DB を使う（分離）。
- kill.flag や stop_requested.flag を使った外部からの停止シグナルを採用しています。これによりプロセス間の柔軟な停止/再起動運用が可能です。
- AI 機能は外部 API（OpenAI）に依存するため、API エラー時はフェイルセーフ（スコアを 0 にしたり処理スキップ）で継続する設計です。ただし API キーは必須になります。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します（警告ログあり）。

---

## ディレクトリ構成（主なファイル）

（ソースは `src/kabusys` に配置）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理 (.env 自動ロード含む)
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動
  - monitoring/
    - monitoring_db.py — SQLite スキーマ + ラッパー
    - system_monitor.py — システム/データ鮮度監視
    - trade_monitor.py — 注文ログ監視（詳細は該当ファイル参照）
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — （アラート送信のラッパー: LINE 等）
  - execution/  — 発注実行周りの実装（BrokerClientFactory, ExecutionEngine, OrderManager, RiskManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py — ニュースセンチメント集約 & OpenAI 呼び出し
    - regime_detector.py — 市場レジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py — 統一ログ設定
    - process_priority.py — 優先度 / CPU affinity 設定
    - __init__.py

---

## トラブルシューティング / よくある質問

- .env を作ったのに反映されない
  - ライブラリは起動時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` を自動ロードします。テスト等で自動ロードを無効にしている場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認してください。
- OpenAI の呼び出しが失敗する
  - `OPENAI_API_KEY` が正しく設定されているか、ネットワークやレート制限を確認してください。AI モジュールはリトライとフェイルセーフを持っていますが、キーが無いと動作しません。
- Monitoring のポーリング頻度を変えたい
  - 環境変数 `MONITOR_POLL_INTERVAL` を秒単位で設定してください（1 以上の整数）。無効値はデフォルト 60 秒にフォールバックします。
- paper_trading と live の DB が混ざってしまう
  - `KABUSYS_ENV=paper_trading` の場合、`PAPER_TRADING_SQLITE_PATH` を使用するよう `run_execution` は実装されています。監視は別途本番用 sqlite を参照する点に注意してください。

---

## 最後に

この README はソースコード中の docstring やコメントを基に作成しています。より詳細な設計・動作仕様は各モジュールの docstring を参照してください。開発や運用で追加の手順・要件（デプロイ手順、監視設定、LINE 通知設定等）が必要な場合は別途ドキュメントを作成することを推奨します。