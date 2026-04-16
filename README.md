# KabuSys

日本株自動売買システムのコアライブラリ群（ライブラリ + 実行 / 監視ツール群）。

以下はこのリポジトリの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムのコアコンポーネント群です。  
主な責務は以下の通りです。

- 注文発行・状態管理（ExecutionEngine / OrderManager / BrokerClient）
- リコンシリエーション（再起動時の同期）
- ポートフォリオ構築（候補選定・重み計算・位置決め）
- 監視（System / Trade / Risk の定期チェック、アラート送信）
- 研究・ファクター計算（DuckDB ベース）
- AI 支援（ニュース NLP によるセンチメント、レジーム判定）
- Paper Trading 用の検証・レポート生成ツール
- Streamlit ベースの監視ダッシュボード

設計方針として、DB（SQLite / DuckDB）を利用した永続化、外部 API 呼び出しのフェイルセーフ化、ルックアヘッドバイアス回避（実行時の日付参照を抑える）などが取り入れられています。

---

## 主な機能一覧

- Execution
  - 注文作成 / 発注 / 状態同期（OrderManager, Reconciler）
  - RiskManager による発注抑制（制限・サーキットブレーカ）
  - Paper Trading モード（実ブローカーと分離された DB に記録）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス存在確認、データ鮮度チェック
  - TradeMonitor: 滞留注文 / 約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: しきい値超過時に停止フラグ（data/kill.flag）を出力
  - AlertManager: LINE Push による通知（クールダウン付き）
  - Streamlit ダッシュボード（リアルタイム閲覧用）
- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、特徴量サマリ
  - 候補選定・重み付け・ポジションサイズ決定（等分・スコア重み・リスクベース等）
  - セクターキャップやレジーム乗数の適用
- AI
  - ニュースを LLM（OpenAI）でスコアリングし ai_scores に保存
  - マクロニュース＋ETF MA200 を合成して市場レジームを判定
- ツール
  - Paper Trading 検証レポート生成スクリプト
  - Streamlit ダッシュボード起動スクリプト

---

## セットアップ手順

前提: Python 3.9+（ソースコードの型ヒントや一部 API を考慮）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   （requirements.txt があればそれを使用してください。なければ以下の主要依存をインストール）
   ```bash
   pip install duckdb psutil requests streamlit openai
   ```
   - duckdb: 研究・ファクター計算、ai データ集計用
   - psutil: プロセス / リソース監視
   - requests: LINE API 呼び出し
   - streamlit: 監視ダッシュボード
   - openai: ニュース NLP / レジーム判定（任意。AI 機能を使う場合に必須）

4. データディレクトリを作成
   ```bash
   mkdir -p data
   ```

5. 環境変数（.env）を準備
   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（必要な環境変数は下記参照）。  
   例（最小構成）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=your_jquants_token
   KABU_API_PASSWORD=your_kabu_api_password
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=            # LINE通知を使う場合に設定
   LINE_USER_ID=                          # LINE通知を使う場合に設定
   ```

   主要な環境変数（概要）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使う場合は必須）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の約定挙動）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT 等（詳細は config.Settings を参照）
   - MONITOR_POLL_INTERVAL（run_monitoring 起動時のポーリング間隔秒。デフォルト 60）

---

## 使い方

以下は主要な起動 / 実行コマンド例です。

1. 監視ループ（SystemMonitor を単体で常駐起動）
   - ポーリング間隔を環境変数で上書き可能: MONITOR_POLL_INTERVAL
   - 監視は monitoring DB（settings.sqlite_path）を使用（環境に依らず production path を使用する点に注意）
   ```bash
   python -m kabusys.run_monitoring
   # 例: 30秒間隔で起動
   MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   ```
   停止方法: プロジェクトルートの data/stop_requested.flag を作成するとループが検知して停止します。

2. ExecutionEngine（注文エンジン）起動
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します。
   ```bash
   python -m kabusys.run_execution
   ```
   停止方法:
   - data/stop_requested.flag を作成すると実行中スレッドが検知して安全停止を試みます。
   - kill.flag（Settings.kill_flag_path）を書き込むと起動中エンジンへ停止シグナルを送るための外部トリガーとして利用できます（KillSwitch 経由）。

3. Streamlit 監視ダッシュボード
   - 監視 DB を read-only で開いてダッシュボードを提供します。
   ```bash
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

4. Paper Trading 検証レポート
   - paper_trading DB（data/paper_trading.db）からレポートを生成します
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # または --db オプションで DB パスを指定
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```

5. AI 機能
   - ニューススコアリング / レジーム判定は `OPENAI_API_KEY` が必要です。
   - 直接関数を呼ぶ形（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）で利用します（CLI ラッパは提供されていませんが、スクリプトから呼び出せます）。

注意点
- 監視テーブル / スキーマの初期化は init_monitoring_db() で自動実行されます（冪等）。
- monitoring は Settings.sqlite_path を使用（監視は本番用 DB path を参照するため環境にかかわらず注意）。
- Execution は KABUSYS_ENV=paper_trading 時に専用 DB（PAPER_TRADING_SQLITE_PATH）へ切り替えます。

---

## 停止 / フラグ関連

- data/stop_requested.flag
  - run_monitoring / run_execution が定期的に存在をチェックし、あれば安全に終了します（手動停止用）。
- data/kill.flag（Settings.kill_flag_path）
  - KillSwitch によって書き込まれることがある停止フラグ。ExecutionEngine 起動時にクリアする設定が可能。
- PID ファイル: data/execution.pid（Settings.pid_file_path）
  - ExecutionEngine が自身の PID を書き、監視コンポーネントがプロセスの存否を確認します。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要モジュールと役割の簡易ツリーです。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定管理（Settings）
  - run_monitoring.py             — SystemMonitor ポーリングループの起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI 呼び出し）／ai_scores 書込
    - regime_detector.py          — マクロ + MA200 によるレジーム判定
  - data/  (参照先: data フォルダ、DB 等はプロジェクトルートに配置)
  - monitoring/
    - monitoring_db.py            — SQLite テーブル初期化 / MonitoringDB ラッパ
    - system_monitor.py           — システム／データ鮮度チェック
    - trade_monitor.py            — 注文滞留・約定異常監視
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - kill_switch.py              — kill.flag 操作ロジック
    - alert_manager.py            — LINE Push 経由の通知
    - monitoring_engine.py        — 複数 Monitor を束ねるエンジン
    - streamlit_dashboard.py      — Streamlit ダッシュボード
  - execution/
    - order_manager.py            — 注文作成 / 発注管理
    - reconciler.py               — 起動時の自動復旧 / 突合
    - ...（BrokerFactory, Engine, OrderRepository 等が存在）
  - portfolio/
    - portfolio_builder.py        — 候補選定 / 等重み・スコア重み
    - position_sizing.py          — 株数計算・スケーリング
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py          — Momentum / Volatility / Value の計算
    - feature_exploration.py      — 将来リターン計算 / IC / summary
  - utils/
    - process_priority.py         — プロセス優先度・CPU affinity セット

（上記は主要ファイルのみ抜粋しています。詳細はソースを参照してください）

---

## 注意事項・運用上のヒント

- 環境分離
  - paper_trading モードは本番口座とは DB を分離します。運用時は KABUSYS_ENV を適切に設定してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は既存 DB に対して冪等にカラム追加を行います（例: latency_ms, peak_value）。
- OpenAI 利用
  - API キーは必ず秘匿し、レート制限やエラー時のフォールトトレランスを考慮してください。実装はリトライやフォールバック（スコア 0.0）を含みます。
- プロセス優先度
  - run_* スクリプトは開始時に set_process_priority("high") を試みますが、権限不足などで失敗することがあります。その場合ログに WARN が出ます。
- ログ
  - run_* では logging.basicConfig(level=logging.INFO) が設定されます。より詳細なデバッグが必要な場合は LOG_LEVEL を設定してください。

---

## 参考コマンドまとめ

- 監視起動（デフォルト 60s）
  ```bash
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```

- Paper Trading レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

---

必要であれば README に追加したい具体項目（例: API ドキュメント、開発者向けセットアップ、ユニットテスト方法、CI 設定サンプル、requirements.txt の自動生成など）を教えてください。追加情報に基づき本文を拡張します。