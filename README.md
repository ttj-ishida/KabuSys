# KabuSys

日本株自動売買システムの一部モジュール群。ポートフォリオ構築、発注エンジン、監視、リサーチ、ニュースNLP等のユーティリティを含みます。

注意: このリポジトリはアプリケーションコアのロジックとユーティリティ群を示すもので、実際のブローカー接続や運用は環境に応じた設定が必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。主な関心領域は以下：

- 発注（Execution）関連：注文生成・状態管理・リコンシリエーション
- 監視（Monitoring）：システム状態、注文滞留、リスク監視、Kill Switch、アラート（LINE）
- ポートフォリオ構築：候補選定、重み算出、ポジションサイズ計算、セクター制約等
- リサーチ：ファクター計算、将来リターン、IC 計算、統計サマリー
- AI 支援：ニュース記事のセンチメント評価（OpenAI を利用）、市場レジーム判定
- ツール：Paper Trading 検証レポート生成、Streamlit ダッシュボードなど

重要設計方針の例：
- DuckDB / SQLite をデータソースに用いる（prices_daily / raw_financials / raw_news 等）。
- 時刻の参照はルックアヘッドバイアスを避ける設計（呼び出し側から target_date を渡す等）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離された SQLite を使用。

---

## 機能一覧（抜粋）

- 実行系
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager（発注フロー、重複チェック）
  - Reconciler（再起動後の注文・ポジション照合）
- 監視系
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor：滞留注文・約定異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に基づき停止フラグを書き込み（ExecutionEngine を停止）
  - AlertManager：LINE push を用いた通知（クールダウン管理）
  - MonitoringEngine：上記モニタを束ねたポーリングループ
  - streamlit_dashboard：監視ダッシュボード（Streamlit）
- ポートフォリオ
  - 候補選定（score ソート）
  - 等重・スコア重み、リスクベース配分
  - セクター上限適用、レジーム乗数
  - ポジション数量決定（単元株丸め、aggregate cap）
- リサーチ
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン、IC 計算、統計サマリー
- AI
  - news_nlp.score_news：OpenAI でニュースを銘柄毎にスコアリングし ai_scores に書き込み
  - regime_detector.score_regime：MA200 とマクロニュースの LLM センチメントを合成してレジーム判定
- ツール
  - tools.paper_verification_report：Paper Trading DB を集計して Pass/Fail 判定レポート出力

---

## 前提・依存関係（想定）

- Python 3.9+（一部の型注釈により 3.10 を想定する場合があります）
- ライブラリ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (監視ダッシュボード利用時)
- 標準ライブラリ: sqlite3, threading, logging, argparse 等

requirements.txt の例（プロジェクトに合わせて調整してください）:
```
duckdb
psutil
requests
openai
streamlit
```

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリへ移動:
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（例: venv）:
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール:
   - pip install -r requirements.txt
   - または最低限: pip install duckdb psutil requests openai streamlit

4. 環境変数設定（ウィザード推奨）:

   対話式ウィザードで `.env` を作成できます:
   ```cmd
   python -m kabusys.config_setup
   ```
   手動設定する場合は `.env.example` をコピーして `.env` を作成してください。
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動ロードされます。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. YAML 設定ファイルの生成:
   ```cmd
   python scripts/generate_config.py
   ```
   `config/` 配下に `system_config.yaml` など 6 ファイルが生成されます（既存ファイルはスキップ）。

6. 設定を検証:
   ```cmd
   python -m kabusys.validate_config
   ```
   必須環境変数の欠落・YAML ファイルの異常・`live` 環境特有の警告を検出します。

7. データディレクトリの作成:
   - mkdir -p data

### 実行環境（KABUSYS_ENV）の使い分け

| 値 | 用途 | 発注 |
|----|------|------|
| `development` | ローカル開発・単体テスト | なし |
| `paper_trading` | 仮想発注・動作検証 | MockBrokerClient を使用 |
| `live` | 本番稼働（実際に発注） | kabuステーション API |

> ⚠️ `live` に切り替える前に必ず `python -m kabusys.validate_config --strict` で設定を確認してください。

### 必須環境変数

| 変数名 | 説明 |
|--------|------|
| `JQUANTS_REFRESH_TOKEN` | J-Quants API リフレッシュトークン |
| `KABU_API_PASSWORD` | kabuステーション API パスワード |
| `KABUSYS_ENV` | 実行環境（development / paper_trading / live） |

その他の変数とデフォルト値は `.env.example` を参照してください。

---

## 使い方（主要スクリプト）

- 監視ループ起動
  - 簡易:
    - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
    - 監視は常に本番の sqlite_path を参照します（環境に関わらず）。

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離します。
    - 実行中は data/execution.pid に PID が書かれ、KillSwitch 等が存在すると停止します。

- Paper Trading 検証レポート生成
  - 単発実行:
    - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - 出力: コンソールに Pass/Fail 判定と指標を印字

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルで監視 DB を読み取り専用で開き、ダッシュボードを表示します。

- AI モジュール例
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼ぶ（OpenAI API キー必須）。
  - 例:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=os.environ["OPENAI_API_KEY"])

---

## 環境変数（主要一覧・説明）

- KABUSYS_ENV: development | paper_trading | live（必須、Settings.env で検証）
- JQUANTS_REFRESH_TOKEN: J-Quants 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE push）用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定動作）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（Settings を参照）

設定ファイルの自動読み込み:
- プロジェクトルートに `.env` / `.env.local` があると自動で読み込まれます（OS 環境変数優先）。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 主要ファイル・ディレクトリ構成

（src/kabusys をルートとした抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env ローダ、Settings
  - run_monitoring.py — SystemMonitor を用いたポーリング起動スクリプト
  - run_execution.py  — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite のスキーマ初期化とラッパー（MonitoringDB）
    - system_monitor.py — CPU/Mem/Disk/データ鮮度/プロセス監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書込ロジック
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 複数 Monitor を束ねるポーリング実行
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注の外向き API（OrderManager）
    - reconciler.py — 再起動時のリコンシリエーション
    - （その他: broker_factory, execution_engine, order_repository 等が想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数決定ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し、バッチ・リトライ含む）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロNLP）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

データディレクトリ（実行時に使用）
- data/
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite)
  - kabusys.duckdb (DuckDB)
  - execution.pid
  - stop_requested.flag / kill.flag

---

## 監視 DB（monitoring_db）について（概要）

init_monitoring_db() により以下のテーブルが作成されます（冪等）:

- system_status: cpu_percent, memory_percent, disk_percent, process_ok, recorded_at
- trade_logs: logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions: code, qty, avg_price, current_price, updated_at
- risk_logs: logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard: 単一行の集計（id=1 で管理）

MonitoringDB クラスはこれらへの読み書きを行うユーティリティを提供します。

---

## 運用上の注意・トラブルシューティング

- PID / stop / kill フラグ:
  - ExecutionEngine は data/execution.pid を用いてプロセスの存在を確認します。
  - stop_requested.flag（run_* スクリプトが参照）や kill.flag（KillSwitch が作成）で停止処理を制御します。
- Paper Trading と本番 DB は分離されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI API 利用時は API キー管理に注意（環境変数で設定）。レート制限や一時エラーに対しては内部でリトライ実装がありますが、運用での監視を推奨します。
- psutil による優先度設定は権限に依存します。権限不足時は警告が出て処理をスキップします。
- DuckDB への executemany に空リストを渡すとエラーになるバージョンがあるため、モジュール側で空チェックを行っています。

---

## 開発・拡張メモ

- 局所的な改善候補:
  - lot_size を銘柄別に対応（マスタを導入）
  - 欠損価格時のフォールバック価格戦略（apply_sector_cap の TODO）
  - AI モデルやプロンプトの改善・安全性対策
- テスト:
  - 各モジュールは外部依存（OpenAI・ブローカー）を注入できるよう設計されています。ユニットテスト時はモックを使って API 呼び出しを差し替えてください。

---

README は概観・運用開始に必要な事項を中心にまとめています。追加で「環境変数の .env.example」や「requirements.txt」「デプロイ手順（systemd / supervisor）」などの具体的ファイルを用意したい場合は、要件を教えてください。