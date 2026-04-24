# KabuSys

日本株向けの自動売買システム（骨格）。戦略・発注・監視・リサーチ・AI 補助を分離して実装しています。  
このリポジトリはランタイムスクリプト（Execution / Monitoring）・設定ウィザード・検証ツール・分析ユーティリティなどを含みます。

---

## プロジェクト概要

- 名称: KabuSys
- 目的: 日本株の自動売買システムを構成する共通ライブラリと起動スクリプト群を提供する
- 主なコンポーネント:
  - ExecutionEngine（発注処理・リスク管理・注文管理）
  - Monitoring（システム状態・注文・リスクの継続監視）
  - Portfolio コンポーネント（候補選定・重み・サイズ計算・セクター制限）
  - Research（ファクター計算・特徴量解析）
  - AI モジュール（ニュースセンチメント、レジーム判定：OpenAI を利用）
  - CLI ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

---

## 機能一覧

- 実行系
  - ExecutionEngine をスレッドで起動し、ブローカークライアント経由で注文（本番/ペーパートレードの分離）
  - RiskManager によるポジション上限・利用率・ドローダウンの管理
  - OrderManager / Reconciler による注文の追跡・再整合

- 監視系
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常などの検出（trade_logs 参照）
  - RiskMonitor: ダッシュボード（portfolio_value 等）からドローダウン監視・アラート登録
  - KillSwitch: しきい値超過時に flag ファイルを書いて ExecutionEngine を停止する仕組み
  - MonitoringEngine: 各モニタの定期起動・アラート連携

- ポートフォリオ構築
  - 候補選定、等分配／スコア加重配分
  - リスクベースのポジションサイズ計算（単元株丸め、aggregate cap）
  - セクター上限適用、レジーム乗数

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）計算、特徴量統計

- AI（OpenAI）
  - ニュース記事をまとめて LLM に投げ、銘柄別センチメントスコアを ai_scores テーブルへ書込む
  - マクロニュース + ETF MA200 乖離を合成して市場レジーム（bull/neutral/bear）を判定・保存

- ツール
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 前提条件

- Python 3.9+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定ファイルの検証を行う場合）
- OS 標準のほか、psutil によるプロセス優先度設定や CPU affinity が使われます（権限により失敗することがあります）。

インストール例（仮）:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. .env の初期作成（ウィザード推奨）
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env`（および任意で `.env.local`）を用意する
5. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   問題があれば指摘に従って修正してください。

6. 必要に応じて data／logs ディレクトリの作成（多くは自動作成されますが、権限等の理由で作れない場合があります）
   - デフォルト DB/ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/<app_name>.log

---

## 主要な環境変数（主なもの）

- 必須（運用時）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 推奨／利用可能
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（PAPER_TRADING 用 DB、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（paper_trading の MockBroker の動作: instant|partial|never|reject、デフォルト: instant）
  - OPENAI_API_KEY（AI 機能利用時）
  - LINE_CHANNEL_ACCESS_TOKEN、LINE_USER_ID（本番通知）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動でクリアするか、デフォルト 0）

- Monitoring 特有
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）

- 自動 .env 読み込み
  - プロジェクトルートにある `.env` と `.env.local` を自動ロードします（OS 環境変数が優先）。
  - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

最小の .env（例）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 起動・使い方

- ExecutionEngine（発注エンジン）起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV に依存します
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離して記録します。
    - 起動時に data/execution.pid に PID を書きます。
    - data/stop_requested.flag が存在すると起動を中止・停止します。

- Monitoring（監視ループ）起動
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - 挙動:
    - 設定ファイルに関係なく monitoring は本番の sqlite_path（Settings.sqlite_path）を使用します（監視ログは共通 DB に保存）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で変更できます（デフォルト 60 秒）。
    - data/stop_requested.flag を検知するとループを終了します。

- .env ウィザード（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  ```

- AI 関連（プログラムから呼び出す）
  - ニューススコア付与:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: OpenAI API を使用するため OPENAI_API_KEY が必要。API 失敗時は安全にフォールバックする設計だが、キーが未設定だと例外になります。

- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine の停止を要求します（Execution 側は起動時のフラグ確認やループ内で stop を検知します）。
  - 監視スクリプトも data/stop_requested.flag を使って自身の停止を制御します（stop_requested.flag と kill.flag は用途が異なります）。

---

## ログと DB

- ログ
  - デフォルト出力先: stdout と logs/<app_name>.log（日次ローテーション、30 日保持）
  - ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name, log_dir, level)

- データベース
  - DuckDB: 分析用（prices_daily / raw_financials / market_regime / ai_scores 等を格納想定）
    - デフォルト: data/kabusys.duckdb
  - SQLite: 監視ログ（monitoring.db）および（ペーパートレード時）paper_trading.db
    - 監視用 SQLite 初期化は init_monitoring_db() で実行されます（冪等）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys を基準）

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込み（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — マクロ + ETF 乖離によるレジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite DB 永続化層（monitoring テーブル群）
    - system_monitor.py      — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py       — (注文滞留等のチェック) ※詳細実装ファイルあり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — flag による停止制御
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — (アラート送信ロジック) ※実装あり

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み算出
    - position_sizing.py     — 発注株数計算（リスク調整・単元丸め）
    - risk_adjustment.py     — セクター上限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py     — Momentum/Value/Volatility の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計
    - __init__.py

  - execution/
    - execution_engine.py    — ExecutionEngine 本体（run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py

  - tools/
    - paper_verification_report.py — Paper Trading レポート生成
    - __init__.py

  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

備考: 上記は主要モジュールの一覧で、実際はさらに補助モジュール（data.pipeline 等）があります。

---

## 注意事項 / 運用上のヒント

- ペーパートレードは本番 DB と完全分離するように設計されています。KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用します。
- monitoring は監視ログのために常に本番 sqlite_path を参照します（環境による切替は行いません）。
- OpenAI を使う機能は API 利用制限や課金が発生します。API キーの管理には注意してください。
- プロセス優先度設定や CPU affinity は権限のある環境でのみ完全に機能します。権限不足時は警告が出てスキップされます。
- .env を絶対に Git にコミットしないでください（config_setup.py も README に警告を出力します）。
- kill.flag / stop_requested.flag の操作は意図しない停止を招くため、運用手順を明確にしておくことを推奨します。

---

もし README に追加したい項目（例: CI 手順、デプロイ例、詳細な設定説明、API ドキュメントの自動生成方法など）があれば教えてください。必要に応じて追記・整形します。