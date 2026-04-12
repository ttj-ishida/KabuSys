# KabuSys

小型の日本株自動売買プラットフォーム用ライブラリ / ツール群。  
このリポジトリは、取引実行系、監視系、ポートフォリオ構築、リサーチ、AI ベースのニュース評価などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群です。

- ExecutionEngine を使った発注フロー（ブローカー抽象化を通じた発注・同期・リコンシリエーション）
- モニタリング（システム状態、注文滞留、リスク監視、LINE 通知、kill flag）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクターキャップ）
- リサーチ（ファクター計算、将来リターン、IC 計算、特徴量の統計）
- AI（ニュースの NLP によるセンチメント評価、マーケットレジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計のポイント:
- DuckDB / SQLite によるローカルデータ参照を主体（外部資源への依存は限定）
- テスト・運用を考慮した環境分離（`KABUSYS_ENV=paper_trading` 等）
- フェイルセーフ（API 失敗時のフォールバック、部分失敗での DB 保護等）

---

## 主な機能一覧

- 実行（Execution）
  - OrderManager / Reconciler による発注・再同期処理
  - BrokerClientFactory による本番 / ペーパートレード切替
  - RiskManager によるレート制限・ドローダウン等のリスク制御

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限チェック、ダッシュボード更新
  - MonitoringEngine: 上記を束ねてポーリング
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: フラグファイルを書いて ExecutionEngine を停止させる仕組み
  - Streamlit ダッシュボード（簡易 UI）

- ポートフォリオ（Portfolio）
  - 候補選定・等配分 / スコア配分
  - セクター集中抑制
  - ポジションサイズ決定（単元丸め・集約上限処理）

- リサーチ（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC・統計サマリー

- AI（OpenAI 連携）
  - ニュース記事の銘柄別センチメント評価（ai_scores テーブルへ書き込み）
  - マクロニュース + ETF MA 乖離から日次レジーム判定（market_regime）

- ツール
  - Paper Trading 検証レポート出力スクリプト
  - Streamlit による監視ダッシュボード

---

## 必要条件（依存ライブラリ）

推奨: Python 3.10 以上

主な依存パッケージ（requirements.txt がない場合は下記を参考にインストールしてください）:

- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード使用時)
- sqlite3（標準ライブラリ）
- その他（プロジェクトにより追加ライブラリあり）

例:
pip install duckdb psutil requests openai streamlit

---

## 環境変数（主なもの）

アプリケーションは .env または環境変数から設定を取得します。自動ロードの仕組みがあり、プロジェクトルートの `.env` / `.env.local` が存在する場合に読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

主要な環境変数:

- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading` のとき発注は MockBrokerClient を使用し、Paper用 SQLite（PAPER_TRADING_SQLITE_PATH）に分離して記録します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: Kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
- PAPER_FILL_MODE: Paper Trading の fill 動作（instant | partial | never | reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で削除するか（"1" で有効）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒。デフォルト 60 秒。0 以下・無効値はデフォルトにフォールバック）

LINE 通知用:
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID

閾値（監視用）:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（%）

---

## セットアップ手順（ローカル実行向け・例）

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境作成（例）
   python -m venv .venv
   source .venv/bin/activate
3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb psutil requests openai streamlit
   （プロジェクトに requirements.txt がある場合はそれを使ってください）
4. .env を作成（.env.example を参考に必要なキーを設定）
   例（最小）:
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
5. データディレクトリを作成
   mkdir -p data
6. 初回 DB 初期化
   - monitoring 用 SQLite は run_monitoring.py / run_execution.py 起動時に自動で init_monitoring_db() が実行され、テーブルが作成されます。
   - DuckDB スキーマや各種テーブル (prices_daily, raw_financials, raw_news, etc.) は別途データ投入が必要です（本 README ではデータ準備手順は含みません）。

---

## 使い方（コマンド & 実行例）

- ExecutionEngine（取引実行）起動
  - run: python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV に応じて paper_trading モードでは paper 用 SQLite に記録
    - プロセス優先度を high に設定を試みる
    - duckdb と sqlite に接続して ExecutionEngine を起動

- Monitoring（監視ループ）起動
  - run: python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更（例: export MONITOR_POLL_INTERVAL=30）
  - 動作:
    - 常に本番の sqlite_path（Settings.sqlite_path）を使って monitoring DB を操作する（KABUSYS_ENV に依らず）
    - SystemMonitor.check_once(), TradeMonitor.check_once(), RiskMonitor.check_once() 相当のループを実行

- Streamlit ダッシュボード
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - read-only で monitoring DB を開き、Overview / Positions / Orders / System のタブを表示

- Paper Trading 検証レポート生成
  - スクリプト: python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 既定 DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可能）

- AI 機能（ライブラリ関数として）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=None)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=None)
  - 注意:
    - api_key を指定しない場合は環境変数 OPENAI_API_KEY を参照
    - API 呼び出し失敗時はフォールバック処理が組まれており、例外を必ず発生させるわけではありません（ログに記録）

---

## 運用上の注意 / トラブルシューティング

- PID / kill.flag
  - ExecutionEngine は PID ファイルを作成します（Settings.pid_file_path、既定 data/execution.pid）。
  - KillSwitch は kill.flag（Settings.kill_flag_path、既定 data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送ります。Monitoring 側は kill.flag の存在を検出してアラートや通知を行います。
  - Settings.kill_flag_clear_on_start=1 にすれば起動時に kill.flag を自動で削除できます。

- Paper Trading
  - KABUSYS_ENV=paper_trading のとき、実際のブローカーではなく MockBrokerClient を使い、発注ログは PAPER_TRADING_SQLITE_PATH に保存されます（本番 DB と分離）。

- OpenAI
  - API 呼び出しは再試行やバックオフを実装していますが、API キーが未設定だと呼び出し前に ValueError を投げます。
  - レスポンスのバリデーションを厳格に行っており、不正な応答はスキップされます。

- プロセス優先度 / CPU affinity
  - set_process_priority は psutil を使います。OS 権限によっては設定に失敗することがあり、その場合はログに警告が出ます（処理は継続します）。

- MONITOR_POLL_INTERVAL が不正な値（0以下や文字列）の場合はデフォルト 60 秒にフォールバックします。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — Settings クラス（環境変数読み込み、自動 .env ロード、各種プロパティ）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 単体のポーリング起動スクリプト

src/kabusys/execution/
- order_manager.py — OrderManager（発注ワークフロー）
- reconciler.py — 起動時リコンシリエーション（注文/ポジション照合）
- （その他 execution 関連モジュール: broker_factory, execution_engine, order_repository ...）

src/kabusys/monitoring/
- monitoring_db.py — SQLite ベースの永続化層（テーブル作成 / CRUD ユーティリティ）
- system_monitor.py — システム状態・データ鮮度監視
- trade_monitor.py — 注文滞留・約定異常監視
- risk_monitor.py — ドローダウン / ポジション上限監視
- monitoring_engine.py — 各 Monitor を束ねるエンジン
- kill_switch.py — kill flag 管理
- alert_manager.py — LINE 通知
- streamlit_dashboard.py — Streamlit ダッシュボード

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数決定（単元丸め・集約上限）
- risk_adjustment.py — セクター制限・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum/Volatility/Value 等のファクター計算
- feature_exploration.py — 将来リターン・IC・統計

src/kabusys/ai/
- news_nlp.py — ニュース記事の LLM による銘柄別センチメント評価
- regime_detector.py — マーケットレジーム判定（MA + マクロセンチメント）

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート出力（CLI）

src/kabusys/utils/
- process_priority.py — process priority / cpu affinity のユーティリティ

data/
- デフォルトの SQLite / DuckDB ファイルパス（data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb など）

---

## 開発 / 貢献メモ

- .env.example を用意しておき、機密値（API キー等）はローカルの .env.local に置く運用を推奨します。
- テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動 .env 読み込みを無効化できます。
- DB マイグレーションは簡易的に monitoring_db.init_monitoring_db() 内で行われます（列追加処理等）。複雑なスキーマ変更が必要な場合は専用のマイグレーションツールを検討してください。

---

README でカバーしてほしい追加項目や、実行環境（本番での systemd / supervisor 用のユニットファイル例、CI 用のテストコマンド等）があれば教えてください。必要に応じてサンプル .env.example や systemd ユニットのテンプレートも作成します。