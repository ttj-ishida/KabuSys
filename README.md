# KabuSys — README (日本語)

簡潔な説明と使い方をまとめた README です。KabuSys は日本株自動売買のための内部ライブラリ群と運用用コンポーネントを含むコードベースです。本 README はソース内にある設計意図・エントリポイント・設定項目に基づいて作成しています。

目次
- プロジェクト概要
- 主な機能一覧
- 必須要件 / 推奨環境
- セットアップ手順
- 環境変数（主なもの）
- 使い方（起動例）
- 開発者向け備考
- ディレクトリ構成（主要ファイル）

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する以下の機能を提供するモジュール群です。

- 注文作成・送信・状態管理（Execution Engine）
- 監視（Monitoring）：プロセス・システムリソース・注文滞留・リスク監視・アラート送信
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・将来リターン・IC 等）
- AI を利用したニュース NLP（OpenAI を用いたセンチメントスコア）
- 運用支援ツール（paper trading の検証レポート、Streamlit ダッシュボード 等）

設計における重要点：
- production / paper_trading / development の環境モード対応（KABUSYS_ENV）
- DuckDB（時系列ファクター等の処理）と SQLite（監視・注文ログ）を併用
- OpenAI API との連携（ニュース評価 / レジーム判定）
- フェイルセーフ：API/DB エラーでもシステムが継続する設計や、部分失敗時の局所的更新

---

## 主な機能一覧

- Execution
  - OrderManager、ExecutionEngine、Reconciler による発注と再同期処理
  - paper_trading モードでは MockBroker を使い production DB と分離
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態 / データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクイベント記録
  - KillSwitch：条件発生時に flag ファイルを書き出して Execution を停止
  - AlertManager：LINE Push によるアラート送信（クールダウン機構あり）
  - Streamlit ダッシュボード（監視用）
- Portfolio
  - 候補選定、等重/スコア重み算出、セクターキャップ適用、ポジションサイズ計算（単元丸め等）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily/raw_financials を参照）
  - 特徴量探索／IC 計算
- AI
  - news_nlp.score_news：ニュース記事をまとめて OpenAI に投げ、ai_scores を更新
  - regime_detector.score_regime：ETF（1321）MA200 乖離 + マクロニュースで市場レジーム判定

---

## 必須要件 / 推奨環境

- Python 3.10 以上（Union 型表記などの使用を想定）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite 標準ライブラリ（Python に同梱）
- ネットワークアクセス（OpenAI / LINE API を使う場合）

pip でのインストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成して依存をインストール（上記参照）
3. プロジェクトルートに `.env` を用意（任意だが推奨）
   - 自動ロードはデフォルトで有効。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
4. 必須環境変数を設定（下記「環境変数」を参照）
5. 必要なデータベースファイルの準備
   - DuckDB（prices_daily, raw_financials, raw_news 等のテーブルが必要）
   - SQLite（監視用・paper_trading 用 DB は自動的に作成・マイグレーションされる箇所あり）
6. 実行（下記の「使い方」参照）

---

## 環境変数（主なもの）

主要な設定は環境変数経由で与えられます。主要キーとデフォルト値・説明は以下の通り。

- アプリ環境
  - KABUSYS_ENV: "development" | "paper_trading" | "live" （デフォルト: development）
- API キー等
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能利用時に必須)
  - LINE_CHANNEL_ACCESS_TOKEN (アラート送信用)
  - LINE_USER_ID (アラート送信用)
- DB / ファイルパス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
- その他
  - PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（paper_trading の約定挙動）
  - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 起動時、デフォルト 60）
  - LOG_LEVEL: DEBUG/INFO/…（Settings で検証）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env ファイル自動ロードを無効化

.env の例（最小）:
```
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
JQUANTS_REFRESH_TOKEN=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

注意:
- .env の読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して行います。
- .env.local は OS 環境変数を保護した上で上書きされます。

---

## 使い方（起動コマンド例）

- Execution Engine（本番/ペーパー両対応）
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV が `paper_trading` の場合、専用の paper DB（PAPER_TRADING_SQLITE_PATH）を使い MockBroker を利用します（本番 DB と完全分離）。

- Monitoring（単独で監視ループを起動）
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB に集約）。

- Streamlit ダッシュボード（監視 UI を起動）
  - 実行:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

- Paper Trading 検証レポート
  - 実行:
    ```bash
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB: `data/paper_trading.db`（`--db` または PAPER_TRADING_SQLITE_PATH 環境変数で指定可）

- AI スコアリング / レジーム判定（ライブラリ関数呼び出し）
  - news_nlp.score_news(conn, target_date, api_key) — DuckDB 接続を渡して実行
  - regime_detector.score_regime(conn, target_date, api_key)
  - これらは OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）

---

## 開発者向け備考

- Process 優先度設定:
  - run_execution / run_monitoring の起動時にプロセス優先度を "high" に設定する処理が実行されます（utils/process_priority.py）。権限や OS により成功しないことがありますがその場合は警告になります。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は複数のマイグレーション（カラム追加等）を冪等に行います。初回起動時には監視テーブルが作成されます。
- フェイルセーフ/ロールバック:
  - AI スコア書き込みや regime 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等に行われる設計です。失敗時は ROLLBACK を試行します。
- テスト:
  - OpenAI 呼び出し部分はテスト時に差し替えられるよう設計されています（関数 _call_openai_api を patch）。

---

## ディレクトリ構成（主要ファイル）

（ソースルート: src/kabusys 以下）

- __init__.py
  - パッケージ定義 / バージョン

- config.py
  - Settings クラス（環境変数読み取り・検証・自動 .env ロード）

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading を分離）

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - order_manager.py, reconciler.py, order_repository.py, execution_engine.py 等
  - 注文状態管理、再同期、リスク管理など（部分的にソース参照）

- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム/データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常検出
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — flag ファイルによる停止シグナル
  - alert_manager.py — LINE 通知（クールダウンあり）
  - monitoring_engine.py — 各 Monitor を束ねる
  - streamlit_dashboard.py — Streamlit ダッシュボード

- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 発注株数計算（単元丸め、aggregate cap 等）
  - risk_adjustment.py — セクター上限 / レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ

- ai/
  - news_nlp.py — ニュース集約 → OpenAI → ai_scores 書き込み
  - regime_detector.py — ETF MA + マクロニュース → レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ヘルパー

---

## 最後に / 注意事項

- OpenAI / LINE / 各種外部 API を利用する機能は API キーやアクセストークンが必要です。API 利用に伴う料金や規約を確認してください。
- 本リポジトリには実際のブローカー連携用の実装（kabu API クライアント等）がある前提ですが、paper_trading モードや MockBroker により安全に動作確認ができます。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news / news_symbols / ai_scores 等）はリサーチ・AI モジュールで参照されます。実運用前に必要テーブルとデータの整備が必要です。

質問や追加で README に載せたい項目（例: 詳細なデータスキーマ、サンプル .env.example、CLI オプション表など）があれば教えてください。必要に応じて追記・整形します。