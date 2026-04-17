# KabuSys

KabuSys は日本株向けの自動売買システムのリファクタ向けコードベースです。戦略（ファクター計算 / ポートフォリオ構築）・実行エンジン・監視・AI（ニュースセンチメント / レジーム判定）・運用ツールを含むモジュール群から構成されています。

この README ではプロジェクト概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株の自動売買パイプライン（シグナル生成 → 発注 → 監視 / リスク管理 / 再同期）を提供する。
- 設計方針:
  - DuckDB / SQLite を用いたローカルデータ管理（価格テーブルや監視ログ等）
  - 本番 (live) / paper_trading / development 環境を切り替え可能
  - OpenAI（gpt-4o-mini 等）でニュースのセンチメント評価やマクロ判定を行う拡張を用意
  - 監視コンポーネントは独立して DB にログを書き、アラート（LINE）送信や ExecutionEngine 停止フラグ作成を行う
  - 外部 API 呼び出しや日付参照でルックアヘッドバイアスを起こさないよう注意

---

## 主な機能一覧

- Execution（実行エンジン）
  - ExecutionEngine / OrderManager / Reconciler による注文発行・状態同期・再起動後のリコンシリエーション
  - paper_trading モードでは MockBroker を使い本番 DB と完全分離（デフォルト: `data/paper_trading.db`）
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス存在チェック
  - TradeMonitor: 滞留注文チェック・約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクイベント記録
  - KillSwitch: 条件を満たしたら `data/kill.flag` を書き込み ExecutionEngine 停止シグナルを送る
  - AlertManager: LINE push によるアラート送信（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード（読み取り専用）
- Portfolio / Strategy Helper
  - 候補選定、重み計算（等配分 / スコア重み）、ポジションサイズ計算、セクター上限・レジーム乗数
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
- AI
  - news_nlp: raw_news を OpenAI に渡して銘柄別センチメントを `ai_scores` テーブルへ書き込み
  - regime_detector: ETF の MA とマクロニュースから日次レジーム判定を行い `market_regime` に書き込む
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）
- ユーティリティ
  - Settings: 環境変数 / .env 読み込み（自動ロード。`.env` / `.env.local`）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発環境）

> 前提: Python 3.10 以上（型注釈に `X | Y` を使用しているため）

1. リポジトリをクローンしてワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成 / 有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要な Python パッケージをインストール
   - このリポジトリには requirements.txt がない想定のため、最低限必要なライブラリをインストールしてください:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit (ダッシュボードを使う場合)
   例:
   ```
   pip install duckdb psutil openai requests streamlit
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。自動で `.env` → `.env.local` の順にロードされ、OS 環境変数が優先されます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 主要な環境変数（抜粋）
   - 必須:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
   - OpenAI:
     - OPENAI_API_KEY — news_nlp / regime_detector の API キー
   - 実行環境・パス:
     - KABUSYS_ENV — one of `development`, `paper_trading`, `live`（デフォルト: development）
     - DUCKDB_PATH — DuckDB DB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH — KillSwitch が書き込む flag（デフォルト: data/kill.flag）
   - その他:
     - PAPER_FILL_MODE — paper_trading 時の約定挙動（instant|partial|never|reject、デフォルト: instant）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - モニタリング調整:
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

6. DB 初期化
   - 監視用 SQLite は実行スクリプトが起動時に `init_monitoring_db()` を呼んで必要テーブルを作成します。まずは `data/` ディレクトリを作成しておくと良いです:
   ```
   mkdir -p data
   ```

---

## 使い方（主なコマンド）

- 実行エンジンを起動（本番/ペーパートレードは KABUSYS_ENV で切替）
  ```
  python -m kabusys.run_execution
  ```
  - Paper trading モード: `export KABUSYS_ENV=paper_trading`（または `.env` に設定）
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします（停止制御）。
  - 実行中、同フラグを作成するとエンジンを安全に停止します。
  - プロセス優先度は起動時に `high` に設定されます（`psutil` による）。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）。
  - 監視は常に本番の sqlite_path を参照（環境に依らず監視用 DB に書き込み）。
  - `data/stop_requested.flag` を検知するとループを終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを直接指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
  - 照会対象 DB は `--db` オプション > 環境変数 `PAPER_TRADING_SQLITE_PATH` > デフォルト `data/paper_trading.db` の優先順位で決まります。

- 監視ダッシュボード (Streamlit)
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ダッシュボードは監視 DB を読み取り専用で開きます。DB が無い場合は起動メッセージを表示します。

- AI バッチ処理（スコアリング / レジーム判定）
  - news_nlp:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - 必要: OpenAI API キー（引数または環境変数 OPENAI_API_KEY）
  - regime_detector:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 必要: OpenAI API キー

注意: AI 呼び出しは外部 API（OpenAI）を用います。API 制限・エラー時のリトライ挙動やフェイルセーフが組み込まれていますが、API キーと通信環境を整備してください。

---

## ファイル / ディレクトリ構成（主なもの）

（ルート: src/kabusys 以下）

- __init__.py
  - パッケージ基本情報（__version__ など）
- config.py
  - Settings クラス（環境変数 / .env の読み込み・検証）
- run_execution.py
  - ExecutionEngine 起動スクリプト（threaded）
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト
- ai/
  - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py — マクロ + MA による市場レジーム判定（OpenAI）
- monitoring/
  - monitoring_db.py — SQLite を使った監視ログの永続化（テーブル作成 / API）
  - system_monitor.py — CPU/メモリ/データ鮮度 / 実行 PID チェック
  - trade_monitor.py — 滞留注文 / 約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の作成 / クリア
  - alert_manager.py — LINE push 通知
  - monitoring_engine.py — 各モニタを束ねるエンジン（run / run_once）
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 注文状態遷移の上位 API
  - reconciler.py — 起動時の自動復旧 / 突合処理
  - （その他: broker_factory, order_repository, order_record, execution_engine 等 - 実装の残り）
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数計算 / ロット丸め / 集約キャップ
  - risk_adjustment.py — セクターキャップ / レジーム乗数
- research/
  - factor_research.py — momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

data/（実行時に使用される、プロジェクトルート直下）
- data/monitoring.db（デフォルトの監視 SQLite）
- data/paper_trading.db（paper trading 用 DB）
- data/execution.pid（ExecutionEngine の PID）
- data/kill.flag（KillSwitch が書き込む停止指示）
- data/stop_requested.flag（run_* スクリプト停止用フラグ）

---

## 運用上の注意点 / Tips

- 環境切替:
  - KABUSYS_ENV により動作モードを切替できます。特に `paper_trading` は実際のブローカーと接続せずペーパーデータベースを利用します。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は起動時にテーブル作成および簡単なカラム追加（マイグレーション）を行います。既存データベースのバックアップを推奨します。
- 停止制御:
  - 実行中のプロセスを停止させたい場合は `data/stop_requested.flag` を作成（任意のファイル）してください。run_* スクリプトは検知して安全に終了します。
  - ExecutionEngine を強制停止させる基準（DD 超過など）により `data/kill.flag` が書き込まれます。起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に既存の kill.flag を自動クリアできます（Settings.kill_flag_clear_on_start）。
- 権限:
  - プロセス優先度や CPU affinity の変更は OS と権限に依存します。権限が不足すると警告が出てスキップされます。
- ログ:
  - 基本は標準出力に INFO レベルで出ます。必要に応じ LOG_LEVEL 環境変数で調整してください。
- セキュリティ:
  - API キーやパスワードは `.env` に保管する場合、アクセス制御に注意してください。`.env` を git にコミットしないでください。

---

## 追加情報 / 開発

- テスト: 各モジュールは依存を注入できる設計（DB 接続や OpenAI クライアントの差し替え）になっているため、ユニットテストやモックに適しています。
- 拡張:
  - Broker の実装差替え（本番 / モック）
  - 銘柄別 lot_size の導入（現在はグローバル lot_size）
  - ファクターやリスクモデルのパラメータ調整はコードの設定値／引数から可能

---

必要であれば、サンプルの .env.example、requirements.txt、起動スクリプトの systemd 用ユニットファイル例、または開発者向けのコマンド（テストの実行方法等）を追加で作成します。どれを追加しますか？