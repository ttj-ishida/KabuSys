# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」の実装を含みます。  
本 README はコードベース（src/kabusys 以下）から抜粋して、導入・実行・開発に必要な情報を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた自動売買フレームワークです。

- 株価データの集計・ファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine による発注管理（paper/live を分離）
- 監視コンポーネント（System/Trade/Risk Monitor）と Kill Switch
- ニュース NLP（OpenAI を用いた銘柄センチメント評価）および市場レジーム判定
- ペーパートレード検証レポート生成ツール

設計上の注意点：
- 環境変数・.env ファイルで設定を行います（自動ロード機能あり）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離され、data/paper_trading.db に記録されます。
- ロギングは共通ユーティリティで設定され、logs/<app>.log に日次ローテートで保存されます。

---

## 機能一覧（ハイライト）

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
- Execution 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper DB に記録
- Monitoring 起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- AI モジュール:
  - kabusys.ai.score_news: ニュース記事を LLM（OpenAI）でスコア化して ai_scores テーブルへ保存
  - kabusys.ai.regime_detector.score_regime: マクロセンチメント + ETF ma200 乖離でレジーム判定
- ポートフォリオ関連関数（純関数）:
  - 候補選定 / 等重・スコア重み / セクター上限 / レジーム乗数 / 株数決定（ロット丸め、aggregate cap）
- 監視 DB（SQLite）ラッパー: テーブル作成（マイグレーション対応）・ログ記録用 API
- ユーティリティ:
  - ロギング設定（stdout + ファイルローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - Linux / macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 依存パッケージのインストール  
   主な依存:
   - duckdb
   - psutil
   - openai
   - （任意）PyYAML（config YAML の検証に使用）
   - （テスト用に）pytest など

   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```

   ※ requirements.txt が存在する場合は `pip install -r requirements.txt` を推奨。

3. .env の作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env（デフォルトはプロジェクトルート/.env）を生成します。`.env` は絶対に Git に含めないでください。

   自動ロードについて:
   - 起動時に .env（→ .env.local）の自動読み込みが行われます（OS 環境変数を上書きしない）。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告を FAIL と見なす
   ```

5. ログディレクトリの確認  
   デフォルトのログ出力先は `logs/`、ファイル名はアプリ名（例: execution.log, monitoring.log）です。

---

## 主要な環境変数（よく使うもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）※必須ではないが検証される
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）

---

## 使い方（実行例）

- ExecutionEngine を起動（通常）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 起動前に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると kill.flag を自動クリアします（本番では 0 推奨）。
  - 実行中に停止させる方法:
    - `data/stop_requested.flag` を作成すると実行ループが検出して終了します（run_execution/run_monitoring 両方で使用）。
    - またはプロセスに SIGINT（Ctrl+C）を送る。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒で指定できます（例: export MONITOR_POLL_INTERVAL=30）。
  - Monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示的に指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- AI モジュール（プログラムから利用）
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026,4,1), api_key="sk-...")
  ```

---

## 停止・Kill Switch

- stop_requested.flag
  - run_execution.py / run_monitoring.py はプロジェクトルート/data/stop_requested.flag を監視しています。これを作成すると安全にループを抜けます。
- kill.flag（Kill Switch）
  - RiskMonitor 等が条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine 停止トリガーとして機能します。KillSwitch クラスで制御されます。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

---

## 監視 DB の初期化 / マイグレーション

- monitoring_db.init_monitoring_db(conn) は以下のことを行います：
  - 必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）とインデックスを冪等に作成
  - 既存 DB に `peak_value` カラムや `latency_ms` が無ければ ALTER TABLE で追加（簡易マイグレーション）

---

## プログラム的な利用（ライブラリ API 例）

- ポートフォリオ構築
  ```py
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)
  ```

- 研究用（DuckDB 経由）
  ```py
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,4,1))
  ```

- AI ニューススコアリング（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None) を呼び出す（api_key 指定なければ環境変数 OPENAI_API_KEY を使用）。
  - OpenAI API 呼び出しはリトライ・バックオフ処理を実装しています。失敗時は安全にフォールバックして例外を吐かない設計です（一部ケースで ValueError を投げる場合あり）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な構成を抜粋します（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings クラス、.env 自動ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI + ma200）
  - portfolio/
    - __init__.py
    - portfolio_builder.py    — 候補選定、等重/スコア重み
    - risk_adjustment.py      — セクター上限、レジーム乗数
    - position_sizing.py      — 株数決定、aggregate cap、lot丸め
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリー
  - monitoring/
    - monitoring_db.py        — SQLite による監視ログ永続化層（テーブル作成・API）
    - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （発注ログ監視）※コードベースに含まれる想定モジュール
    - risk_monitor.py         — ドローダウン・ポジション数の監視
    - kill_switch.py          — Kill Switch 書き込みユーティリティ
    - alert_manager.py        — （アラート送信）※実装が存在する想定
  - execution/
    - execution_engine.py     — ExecutionEngine（発注ループ）
    - order_manager.py        — Order 管理
    - order_repository.py     — Order 永続化
    - reconciler.py           — ブローカーとの整合処理
    - broker_factory.py       — ブローカークライアント生成（Mock/Real 切替）
    - risk_manager.py         — リスク判定ロジック
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - data/                     — 実行時に生成される（データベース・フラグ・PID 等）
  - config/                   — 各種 YAML 設定ファイル（system_config.yaml など）

※ 実際のファイルは repo によって差異がありますが、上記が本コードベースで中心となるモジュール群です。

---

## 開発・運用の注意点

- 本番環境（KABUSYS_ENV=live）では LINE 通知や Kill Switch の取り扱いなどを十分検討してください。validate_config は live 時に追加の注意喚起を出します。
- .env は機密情報を含むため Git にコミットしないこと。config_setup.py も README 内で示した通り .env を生成します。
- OpenAI API を使用する機能は API キーの管理（レート・課金）に注意してください。API 呼び出しはリトライやクリッピング等の安全弁を備えていますが、運用上の検討は必要です。
- Monitoring は本番 SQLite（Settings.sqlite_path）を参照します。Paper Trading を行う場合は KABUSYS_ENV=paper_trading により paper DB に切り替わる箇所を理解してください（run_execution では紙取引専用の sqlite を使用）。

---

## 問い合わせ / 貢献

- バグ報告、改善提案、プルリクエストはリポジトリの Issue / Pull Request を通じてお願いします。
- 大きな機能追加（API 変更・データスキーマ変更等）は事前に Issue で議論してください。

---

README は以上です。必要があれば「インストール手順をさらに詳しく」「各設定項目の .env 例」「CLI の出力例」など追記します。どの情報を優先して追加しますか？