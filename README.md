# KabuSys

日本株向け自動売買システムのライブラリ群 / 実行スクリプト集です。  
このリポジトリは戦略研究（Research）、ポートフォリオ構築（Portfolio）、発注実行（Execution）、監視（Monitoring）、および AI 支援（ニュース NLP・レジーム判定）を含むコンポーネントで構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は、以下の主要機能を持つモジュール群で構成されています。

- 株価・ファクター計算（research）
- ポートフォリオ構築・リスク調整・株数決定（portfolio）
- 発注ロジック・注文管理・リスク管理・ExecutionEngine（execution）
- システム監視・監視 DB（monitoring）
- ニュースの NLP によるセンチメントスコア生成・市場レジーム判定（ai）
- 開発支援ツール（対話式 .env 作成、設定検証、レポート生成など）
- 汎用ユーティリティ（ログ設定、プロセス優先度設定など）

設計上の特徴：
- DuckDB/SQLite を用いたデータ処理・永続化
- OpenAI API を用いたニュース NLP（オプション）
- 環境変数 / .env による設定管理（自動ロード機構あり）
- 本番／ペーパートレード環境の分離（KABUSYS_ENV）

---

## 機能一覧（抜粋）

- settings（kabusys.config）: 環境変数 / .env 読み込みと設定プロパティ
- config_setup: 対話式ウィザードで .env を生成・更新
- validate_config: .env および config/*.yaml の事前検証 CLI
- run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading で MockBroker 使用）
- run_monitoring: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
- monitoring: system_status / trade_logs / positions / risk_logs / dashboard を管理する永続層と各種モニタ
- ai.news_nlp: ニュース記事を LLM でスコアリングして ai_scores に書き込み
- ai.regime_detector: ETF とマクロニュースを合成して日次でレジーム判定
- research: momentum / volatility / value 等のファクター計算、IC や統計集計
- portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制約適用
- tools.paper_verification_report: ペーパートレード DB を対象とした検証レポート出力

---

## セットアップ手順

※ 以下は一般的な手順です。プロジェクト配布に合わせて適宜調整してください。

1. Python 環境を用意（推奨: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール  
   主に以下のパッケージが必要です（バージョンは適宜指定してください）。
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - pyyaml (validate_config で YAML 検証を行う場合)

   例:
   ```bash
   pip install duckdb psutil openai pyyaml
   ```

   （requirements.txt があれば `pip install -r requirements.txt` を推奨）

3. .env を作成する  
   対話式ウィザードで生成できます:
   ```bash
   python -m kabusys.config_setup
   ```
   生成後、設定を検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたいとき:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリ作成（必要に応じて）
   - デフォルトの SQLite / DuckDB / PID / kill.flag 等は `data/` に配置する想定です。スクリプト実行時に自動作成されることもありますが、権限に注意してください。

5. （AI 機能を使う場合）OpenAI API キーを設定
   - 環境変数 `OPENAI_API_KEY` に API キーを設定するか、関数呼び出し時に明示的に渡します。

---

## 主要な環境変数と設定の説明

主な環境変数（Settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API トークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知用（任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（instant|partial|never|reject、ペーパートレードでの約定モード）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか、0/1）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）が検出されると、`.env` と `.env.local` が自動で読み込まれます。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（よく使うコマンド例）

- 対話式 .env 作成:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（本番またはペーパーは KABUSYS_ENV に依存）:
  ```bash
  python -m kabusys.run_execution
  ```
  注意: `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、データは `data/paper_trading.db` に記録されます。

- Monitoring 起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視ループは `data/stop_requested.flag` が生成されると終了します（停止フラグ検知）。

- ペーパートレード検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  SQLite DB は `--db` オプション、または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定できます。

- AI スコア生成 / レジーム判定（ライブラリ関数として使用）
  - ニューススコア: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - レジーム: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

ログ設定:
- すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging(app_name=...)` を呼び出し、コンソール（stdout）と日次ローテーションファイル（logs/<app_name>.log）にログを出力します。

停止フラグ / Kill Switch:
- ExecutionEngine の停止は `data/stop_requested.flag` によるプロセス停止検知のほか、監視側の KillSwitch が `KILL_FLAG_PATH`（デフォルト `data/kill.flag`）を書き込むことで発動します。

---

## 監視 DB（monitoring_db）のスキーマ（主なテーブル）

- system_status:
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs:
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions:
  - code (PRIMARY KEY), qty, avg_price, current_price, updated_at
- risk_logs:
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard:
  - id=1 の単一行でポートフォリオ集計 (portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value など)

監視関連ユーティリティは `kabusys.monitoring.monitoring_db.MonitoringDB` クラス経由で永続化操作を行います。

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込みと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - research/
    - factor_research.py     — モメンタム等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計集計
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数算出、キャップ/スケーリング
    - risk_adjustment.py     — セクター上限、レジーム乗数
  - monitoring/
    - monitoring_db.py       — 監視 DB 定義・簡易 ORM
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 発注・約定監視（存在）
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — Kill Switch 制御
    - monitoring_engine.py   — 各モニタを束ねる Engine
    - alert_manager.py       — アラート送信（存在）
  - execution/               — 発注関連の実装（BrokerFactory, Engine, OrderManager, RiskManager 等）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ / logs/ / config/  — 実行時に利用するファイル群（プロジェクトルートに配置）

（注）上記は主要ファイルの抜粋です。細かい実装は各モジュールを参照してください。

---

## 運用上の注意・ベストプラクティス

- KABUSYS_ENV を正しく設定すること（特に `live` は本番発注につながります）。
- 本番環境では `KILL_FLAG_CLEAR_ON_START=0`（自動クリアを無効）を推奨。
- ログディレクトリに書き込み権限があることを確認してください。ログ設定は `kabusys.utils.logging_setup.setup_logging` を通じて統一されています。
- OpenAI を使う処理は API 失敗時にフェイルセーフ動作（スコアを 0 にする等）を行う実装がありますが、コストやレイテンシに注意してください。
- データベース（DuckDB/SQLite）はバックアップやローテーションを計画してください。特に production の DuckDB ファイルはサイズが大きくなる可能性があります。

---

## テスト / 開発

- 各モジュールは比較的独立しており、純粋関数的に実装されている箇所（portfolio、research など）はユニットテストが書きやすく設計されています。
- config の自動読み込みはテストで妨げになる場合があるため、テスト実行時に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。

---

質問や README の拡張（例: インストール手順を詳細化、依存関係の pinned version を追加、運用ランブックの作成など）が必要であれば教えてください。必要に応じてサンプル .env.example や systemd / supervisor 用のユニットファイル例も作成します。