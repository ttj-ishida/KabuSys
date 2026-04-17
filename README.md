# KabuSys

日本株向けの自動売買フレームワーク（モジュール群）のサンプル実装です。  
このリポジトリは、発注エンジン、監視・アラート機構、ポートフォリオ構築・サイズ決定ロジック、研究用ファクター計算、LLM を使ったニュースセンチメント評価などのコンポーネントを含みます。

注意: 本 README はコードベース（src/kabusys 以下）に基づいて作成しています。実際に運用する場合は各コンポーネントの動作・安全性を十分に確認してください。

## 主要機能

- ExecutionEngine（発注エンジン）起動スクリプト（run_execution）
  - 本番 / Paper Trading を切り替え可能（KABUSYS_ENV）
  - Broker クライアントの抽象化、OrderManager / RiskManager / Reconciler を備える
- Monitoring（監視）関連
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / プロセス生存チェック
  - TradeMonitor: 注文滞留・約定異常価格の検出
  - RiskMonitor: ドローダウンやポジション上限監視（kill switch と連携）
  - AlertManager: LINE Messaging API を使ったプッシュ通知（クールダウンあり）
  - MonitoringEngine / run_monitoring スクリプト: 定期ポーリング・永続化
  - Streamlit ベースの監視ダッシュボード（read-only）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等重・スコア重み、セクター上限の適用、ポジションサイズ計算（単元丸め、リスク制約考慮）
- Research（研究用）
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索、将来リターン計算、IC 計算、統計サマリ
- AI（LLM）連携
  - news_nlp: raw_news を集約して OpenAI API（gpt-4o-mini）で銘柄ごとのセンチメントを生成・ai_scores へ書込
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントを合成して市場レジーム判定を行い market_regime に書込
- ユーティリティ
  - .env の自動読み込み（config.py）、プロセス優先度 / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

## 要件（目安）

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite は Python 標準ライブラリで使用
- ネットワークアクセス（API 利用時）

インストール例:
```bash
python -m pip install duckdb psutil requests openai streamlit
```

## セットアップ手順

1. リポジトリをクローン / 取得して、スクリプト実行環境を用意します。
2. Python 3.10 以上の仮想環境を作成・有効化します。
3. 必要パッケージをインストールします（上記参照）。
4. プロジェクトルートに `.env`（もしくは `.env.local`）を作成して必要な環境変数を設定します。自動読み込みはデフォルトで有効です（config.py がプロジェクトルートを探索して読み込みます）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

代表的な環境変数（主なもの）
- KABUSYS_ENV: 実行モード。`development`（デフォルト） / `paper_trading` / `live`
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須のプロパティ参照あり）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant/partial/never/reject、デフォルト: instant）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で上書き可）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（詳細は config.Settings を参照）

例（.env の一部）:
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

## 起動・使い方

※各コマンドはプロジェクトルート（src を含む場所）で実行してください。

- 監視ループを起動（run_monitoring）
  - デフォルトは MONITOR_POLL_INTERVAL=60 秒
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 停止方法:
    - キーボード割込み（Ctrl+C）
    - プロジェクトルート/data/stop_requested.flag ファイルを作成するとループが検出して終了します（ファイル名: stop_requested.flag）。

- ExecutionEngine を起動（run_execution）
  - Paper Trading に切り替える例:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 本番（live）では本番 DB / 実ブローカークライアントが使用されます。paper_trading の場合は専用の paper_sqlite_path（data/paper_trading.db 等）へ記録され、本番 DB と分離されます。
  - 停止:
    - data/stop_requested.flag を作成すると実行中のエンジンを停止させる処理が走ります。
    - kill.switch（KillSwitch）が条件に達した場合は data/kill.flag が書き込まれ、ExecutionEngine 側で検知して停止します。

- Streamlit ダッシュボード（監視 UI）
  - 起動例:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 読み取り専用で、MonitoringEngine が作成した monitoring.db を参照します（可能なら read-only URI を使用して開きます）。

- Paper Trading 検証レポート生成ツール
  - 実行例:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB は data/paper_trading.db。`--db` オプションで指定可能。

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY）。
  - 関数呼び出し例（Python API）:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...) で取得
    count = score_news(duckdb_conn, target_date)
    ```
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date)
    ```
  - 失敗時はフェイルセーフ（多くのケースでスコア 0.0 等で継続）を設計に組み込んでいますが、API キー未設定の場合は例外になります。

- Research / Portfolio モジュール（ライブラリとして利用）
  - duckdb 接続を渡して各種計算関数を利用できます（例: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic など）。
  - ポートフォリオ/サイズ決定関数は純粋関数で副作用なし（ユニットテストしやすい）。

## データファイル / フラグ

- data/monitoring.db — 監視ログ（SQLite）
- data/paper_trading.db — Paper Trading 用 SQLite（paper_trading モード）
- data/kabusys.duckdb（あるいは指定した DUCKDB_PATH）— DuckDB による価格・ファイナンス・ニュース等の集計テーブル
- data/execution.pid — ExecutionEngine が書き込む PID ファイル（SystemMonitor が生存チェックに使用）
- data/stop_requested.flag — run_monitoring / run_execution のループ終了を促すファイル（存在を検出するとループを終了）
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine 側で検出して停止）

kill.flag の削除（手動）:
```bash
rm data/kill.flag
```
またはコード側で KillSwitch.clear() を呼ぶことにより削除できます。

## ディレクトリ構成（要約）

以下は主要ファイル/ディレクトリと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env 読み込み・Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI ベースの銘柄センチメント）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ（テスト用 run_once / 本番 run）
    - streamlit_dashboard.py — Streamlit ダッシュボード（read-only）
  - execution/
    - order_manager.py — 発注フロー管理（OrderManager）
    - order_repository.py — Orders DB アクセス（SQLite） — （実装ファイルの一部は省略）
    - reconciler.py — 再起動時のリコンシリエーション
    - ...（BrokerFactory や Engine 等のコンポーネント）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・リスク制限・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラ / バリュー等のファクター計算
    - feature_exploration.py — 将来リターン，IC，統計サマリ
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルの抜粋です。実際のコードはさらに詳細なモジュールを含みます。）

## 開発メモ / 注意点

- Settings（config.py）はプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を自動検出して `.env` / `.env.local` を読み込みます。OS 環境変数を上書きしない、もしくは `.env.local` で上書きする挙動があります。
- run_monitoring と run_execution は起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限不足時は警告を出してスキップします。
- AI モジュールは外部 API（OpenAI）に依存します。API 呼び出しはリトライ・バックオフ・バリデーションなど堅牢性を考慮した実装になっていますが、料金・レート制限に注意してください。
- DuckDB / SQLite のスキーマはコード内の init 関数で作成・マイグレーションされます（冪等）。ただし、スキーマ変更時は既存 DB の互換性に注意してください。
- Paper Trading と本番データは分離するよう設計されています。KABUSYS_ENV を設定して Paper / Live を切り替えてください。

---

この README はコードベースの概要説明を目的としており、詳細な API 仕様や設計文書（PortfolioConstruction.md 等）が別途ある前提です。実運用・本番接続の際は、認証情報・注文ロジック・リスク設定を厳重に検証してください。必要なら README の追加修正やセクションの拡充を行います。