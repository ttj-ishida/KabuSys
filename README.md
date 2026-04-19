# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリには実運用／ペーパートレード両対応の実行エンジン、監視（Monitoring）、研究用ユーティリティ、AI を用いたニュース解析などが含まれます。

## 主な特徴
- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカー抽象化（paper_trading 時は MockBroker）
  - リスク管理（RiskManager）、注文管理（OrderManager）、再整合（Reconciler）
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視ログ（monitoring.db）と DuckDB（分析用）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み Execution を停止）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- Research（研究）
  - DuckDB を使ったファクター計算（Momentum, Value, Volatility 等）
  - 将来リターン、IC 計算、統計サマリ
- AI（OpenAI を利用したスコアリング）
  - ニュースのセンチメントスコア付与（ai_scores テーブルへ保存）
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）
- ユーティリティ
  - 設定ウィザード（.env 生成）、設定検証 CLI、ログ設定、プロセス優先度／CPU affinity

---

## 依存 / 前提
- Python 3.9+
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - pyyaml（config YAML 検証のため任意）
- SQLite（組み込み）
- ネットワーク（OpenAI / ブローカー API を利用する場合）

インストール例（pipenv / poetry 等の仮想環境推奨）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意して依存をインストールします。

2. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードで入力された値はプロジェクトルートの `.env` に保存されます。`.env` は絶対に Git にコミットしないでください。

3. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が未設定の場合はエラーになります。`--strict` を付けると警告も失敗扱いになります。

4. データディレクトリの作成（必要に応じて）
   - デフォルトの DB / PID / FLAG 等のパスは `data/` 下を想定しています。起動時に自動作成されることもありますが、権限等で失敗する場合は手動で用意してください。

---

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、発注は MockBroker を使用し data/paper_trading.db に保存
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db） — Monitoring 用（注意: Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1、デフォルト: 0）

その他は `python -m kabusys.config_setup` のウィザードや `config/*.yaml` を参照してください。

---

## 実行方法（代表例）

- ExecutionEngine を起動（通常はデーモンや systemd 等で管理）
  ```
  python -m kabusys.run_execution
  ```
  動作:
  - プロセス優先度を "high" に設定（可能な範囲で）
  - KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用し paper_trading 用 DB に記録
  - 起動前に data/stop_requested.flag が存在する場合は起動しない
  - 停止は data/stop_requested.flag によるシグナル、または内部の kill.flag による停止

- Monitoring を起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト 60 秒）
  特記事項:
  - Monitoring は sqlite_path（data/monitoring.db 等）を本番のパスとして常に使用します（環境に依らず）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DBパス指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（プログラム内で使用）
  - ニューススコアリング: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - これらは programmatic に呼び出す設計です。`api_key` が None の場合は環境変数 `OPENAI_API_KEY` を参照します。

---

## 使い方のポイント / 運用上の注意
- Monitoring と Execution の DB は切り分け可能:
  - Monitoring（監視ログ）は `SQLITE_PATH`（一般に data/monitoring.db）
  - ペーパートレードは `PAPER_TRADING_SQLITE_PATH`（data/paper_trading.db）
- Kill Switch:
  - RiskMonitor 等が条件を満たすと `data/kill.flag` を書き込みます。ExecutionEngine はこれを検出して安全停止できます。
  - `KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは危険です（自動で kill.flag を消してしまうため）。
- 停止リクエスト:
  - `data/stop_requested.flag` の存在は run_monitoring / run_execution スクリプトに外部停止指示として使われています。
- ロギング:
  - デフォルトでコンソール出力（stdout）と `logs/<app_name>.log` に日次ローテーションで出力します。ログディレクトリは `LOG_DIR` またはデフォルト `logs/`。
- OpenAI 使用:
  - API 呼び出しで 429/ネットワーク障害/5xx が発生した場合、内部でリトライ（指数バックオフ）を実装しています。
  - OpenAI 利用はコストや利用制限に留意してください。

---

## ディレクトリ構成（主要ファイル）
プロジェクトルートから見た主要モジュールの構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロード・Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュースセンチメント判定（OpenAI）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — （注文系監視 — 実装参照）
    - risk_monitor.py — ドローダウン/ポジション制限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — （通知周りの抽象）
  - execution/ — 発注関連（OrderManager, ExecutionEngine 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity

（詳細は各ファイルの docstring/comments を参照してください）

---

## 開発・デバッグヒント
- 設定検証: `python -m kabusys.validate_config` で起動前の問題を洗い出せます。
- .env 自動ロード: プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を自動読み込みします。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- DB マイグレーション: `monitoring_db.init_monitoring_db` は冪等でテーブルと基本的なカラム追加（マイグレーション）を行います。
- ロギング: 既存ハンドラがあると重複出力するため、setup_logging は既存ハンドラをクリアしてから設定します。
- テスト時:
  - AI 呼び出し部分は `_call_openai_api` をモックして動作確認できます（unit test 向けに設計されています）。
  - MonitoringEngine.run_once を呼べば一度だけ監視処理を実行できます（テスト用）。

---

## よくあるトラブルと対処
- .env の必須キーがない → `python -m kabusys.config_setup` で作成、`python -m kabusys.validate_config` で確認
- OpenAI でエラーが出る → `OPENAI_API_KEY` を確認。API レートや課金状況を確認
- `data/` 下のファイルにアクセスできない・作成できない → ファイル/ディレクトリのパーミッションを確認
- Monitoring が意図せず本番 DB を参照しているように見える → Monitoring は KABUSYS_ENV にかかわらず `SQLITE_PATH` を使用します（設計仕様）

---

必要に応じて README に追記します。特に導入手順（パッケージ化・systemd ユニット例・Docker 化）や ExecutionEngine の詳細な設定例が必要であれば教えてください。