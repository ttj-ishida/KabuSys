# KabuSys

日本株向け自動売買フレームワーク（ライブラリ + 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI支援の各コンポーネントを持つ自動売買システムのコア実装です。設計方針として「できる限り副作用を避け、テスト可能な純粋関数群と、SQLite/DuckDBを用いたデータ永続化」を重視しています。

バージョン: 0.1.0

---

## 主な機能（抜粋）

- 実行エンジン（ExecutionEngine）による注文の管理・発注（本番 / ペーパートレード切替）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- モニタリング用 SQLite 永続化レイヤ（monitoring_db）
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ計算、セクター制限）
- リサーチ機能（ファクター計算 / 将来リターン / IC 計算）
- AI モジュール（ニュースの NLP スコアリング / 市場レジーム判定：OpenAI 利用）
- 環境設定ウィザード（.env の対話式生成）および設定検証ツール
- 解析用ツール（ペーパートレード検証レポート出力）

---

## 動作環境（推奨）

- Python 3.10 以上
- 必須パッケージ（一例）:
  - duckdb
  - psutil
  - openai
- 任意／開発用:
  - PyYAML（config ファイル検証用）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（requirements.txt は本リポジトリに含まれていないため、プロジェクトに合わせてパッケージを調整してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・パッケージインストール（上記参照）

3. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで生成される `.env` には API トークンや DB パスなどが書かれます。`.env` は絶対にソース管理にコミットしないでください。

4. 設定の検証
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションを付けると警告を FAIL 扱いにできます。

5. 必要なディレクトリ（data, logs など）は起動時に自動作成されますが、権限等で失敗する場合があるため手動で作ることを推奨します。
   ```
   mkdir -p data logs
   ```

---

## 環境変数（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用モード:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading: MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録
    - live: 実際の発注を行うので注意深く設定すること

- データベース／ログ:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、default: data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR (default: logs/)

- AI / 外部:
  - OPENAI_API_KEY（AI モジュール利用時）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）

- 監視系:
  - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔、秒。デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START（本番で 1 にすると Kill Flag を起動時に自動クリア）

- 自動 .env 読み込みの無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主要な使い方（コマンド例）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（実行エンジン）
  - デフォルトでは KABUSYS_ENV に応じて本番/ペーパートレード DB を切替
  ```
  python -m kabusys.run_execution
  ```
  - 起動前に data/stop_requested.flag が存在すると起動を中止します
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止シグナルを送れます

- Monitoring（監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒、デフォルト 60）
  - 監視は常に本番 sqlite_path を参照（環境に依存せず監視 DB を共有）

- Paper Trading 検証レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  - DB パスは引数、環境変数、デフォルトの順で決定されます

- AI モジュールの利用（プログラムから呼び出す）
  - ニュース NLP スコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と target_date を渡して使います。APIキーは引数または環境変数 OPENAI_API_KEY から取得されます。

---

## 停止・Kill Switch に関する注意

- プロセス停止用フラグ:
  - data/stop_requested.flag: run_execution / run_monitoring の起動ループがチェックして終了または停止します
  - data/kill.flag: KillSwitch が書き込み、ExecutionEngine に停止シグナルを送ります（設定により起動時に自動クリアを行うかどうかを制御）

- 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って自動クリアすると安全装置が効かなくなります）

---

## ログ

- ロギングは共通ユーティリティで設定され、以下を行います:
  - コンソール出力（stdout）
  - 日次ローテートされたファイル出力（logs/<app_name>.log、30 日分保持）
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL または setup_logging 呼出し時の引数で指定できます

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定の読み込み／ラッパー
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュースの NLP スコア化（OpenAI）
    - regime_detector.py      — 市場レジーム判定（AI + 指標合成）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 発注株数計算・スケーリング
    - risk_adjustment.py      — セクター上限・レジーム乗数
  - research/
    - factor_research.py      — モメンタム/ボラティリティ/バリュー等ファクター計算
    - feature_exploration.py  — 将来リターン/IC/統計サマリー
  - monitoring/
    - monitoring_db.py        — SQLite 永続化レイヤ（schema/migrations）
    - system_monitor.py       — システム状態／データ鮮度監視
    - trade_monitor.py        — （trade に関する監視ロジック）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みユーティリティ
    - monitoring_engine.py    — 各モニタを束ねる実行エンジン
    - alert_manager.py        — （通知の抽象化）
  - execution/
    - execution_engine.py     — 発注セッションのライフサイクル（Engine）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - ... (上記)
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - data/                     — 実行時に使用される（または自動生成される）データ/ログ/DB ファイル

（上記は主要ファイルの要約です。詳細は各モジュールの docstring を参照してください）

---

## 開発・デバッグのヒント

- .env の自動読み込み:
  - デフォルトでプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を読み込みます
  - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください

- 典型的なエラー:
  - OPENAI_API_KEY 未設定 → AI モジュールの呼び出しで ValueError 発生
  - DB ファイルが存在しない / スキーマ違い → monitoring_db.init_monitoring_db がスキーマを作成／マイグレーションしますが、DuckDB / SQLite のバージョン差による問題に注意
  - psutil で権限エラーが出る場合は、プロセス優先度設定や CPU affinity の呼び出しが失敗します（警告扱いで継続）

- 単体テスト・モック:
  - AI API 呼び出し箇所（news_nlp._call_openai_api, regime_detector._call_openai_api 等）はテスト時に patch して差し替え可能なように実装されています

---

## ライセンス / 貢献

README に記載が無い場合は、リポジトリルートの LICENSE を参照してください。貢献する際は issue / pull request にて設計意図やテストケースを添えてください。

---

必要であれば、導入手順のステップごとに具体的なコマンド列（systemd ユニット例、Dockerfile / docker-compose の参考、CI 用のテストコマンドなど）を追記します。どの情報を優先して追加しましょうか？