# KabuSys

日本株向け自動売買システムのコアライブラリ群（開発用ドキュメント）。  
このリポジトリは戦略構築、発注実行、監視、AI を用いたニュース解析などのモジュールで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、ロジック（シグナル生成・銘柄選定・ポジションサイズ計算）と実行層（ブローカー連携）、運用監視・アラート、研究用ユーティリティ（DuckDB を利用したファクター計算や特徴量解析）、およびニュースの NLP スコアリング（OpenAI）を備えた日本株自動売買向けのモジュール群です。

主な設計方針:
- DuckDB / SQLite を組み合わせたデータ分析と監視ログの永続化
- .env ベースの環境設定（ワークフロー: config_setup → validate_config）
- Paper Trading 環境と Live 環境の分離（DBを別にする等）
- フェイルセーフ重視（API失敗時のフォールバック、Kill Switch）
- テストしやすい純粋関数実装（ポートフォリオ計算等）

---

## 機能一覧

- 環境設定 / 検証
  - 対話式 `.env` 生成ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config (--strict)
- 実行 / 監視
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
  - Monitoring（監視）ポーリング: python -m kabusys.run_monitoring
    - 環境にかかわらず本番用 sqlite_path を監視 DB として利用
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視サブシステム
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセスの生存確認
  - TradeMonitor: 発注ログ・滞留注文などのチェック（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch: 条件を満たした場合に data/kill.flag を書き込み ExecutionEngine に停止シグナルを送る
  - MonitoringEngine: 各モニタを束ねて定周期で実行・アラート送信
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重 / スコア加重配分、リスクベースの株数算出、セクター上限、レジーム乗数等
- 研究用モジュール（DuckDB）
  - ファクター計算 (momentum / volatility / value)
  - 将来リターン・IC・統計サマリ
- AI 関連
  - ニュース NLP（OpenAI）で銘柄ごとにセンチメントスコアを算出し ai_scores に保存
  - 市場レジーム判定（ETF & マクロニュースを組み合わせる）
- ユーティリティ
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（開発向け）

前提:
- Python 3.10 以上を推奨（型注釈の構文等）
- system に sqlite3 は標準同梱。外部ライブラリを以下でインストールしてください。

推奨依存（例）:
- duckdb
- psutil
- openai
- PyYAML（設定ファイル YAML の検証に使用）
- （任意で）その他戦略 / execution 用のライブラリ

pip 例:
```
python -m pip install duckdb psutil openai PyYAML
```

環境変数 / .env の準備:
1. 対話式ウィザードで .env を生成
   ```
   python -m kabusys.config_setup
   ```
   - 生成先はプロジェクトルートの `.env`（デフォルト）。既存の `.env` を読み込み、Enter で既存値を再利用できます。
2. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

主要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading 時は paper_trading 用 DB に記録され、本番 DB と分離されます
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 時の DB, デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- OPENAI_API_KEY（AI 関連を利用する場合に必須）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（注意: 本番では 0 推奨）

ログ:
- デフォルト出力先: stdout と logs/<app_name>.log（日次ローテーション）
- LOG_DIR でログディレクトリを上書き可能

---

## 使い方

各種エントリポイントはモジュール実行形式で利用できます。プロジェクトルートで実行してください。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  動作:
  - 起動時にプロセス優先度を "high" に設定（可能な場合）
  - KABUSYS_ENV=paper_trading の場合、paper_trading DB を使用し MockBrokerClient が利用される
  - 起動時に data/stop_requested.flag が既にある場合は起動せず終了
  - 実行中に data/stop_requested.flag が作成されるとエンジンを停止する
  - PID ファイル: data/execution.pid（Settings.pid_file_path）

- Monitoring（監視）起動
  ```
  python -m kabusys.run_monitoring
  ```
  動作:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）
  - デフォルトで Settings.sqlite_path（監視 DB）を使用（環境にかかわらず本番 sqlite_path を参照）
  - 停止は data/stop_requested.flag を置くか Ctrl+C

- 停止 / Kill Switch
  - Monitoring / Execution はプロセス起動中にプロジェクトルートの data/stop_requested.flag を作成することで安全に停止できます（run_execution/run_monitoring が定期的に存在確認）。
  - KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で検知して停止する仕組みです。
  - kill.flag を自動クリアしたい場合は .env の KILL_FLAG_CLEAR_ON_START を設定します（本番では推奨しません）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB: data/paper_trading.db。オプション --db で指定可能。

- AI 機能（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY が必要。呼び出しはコード API を通じて行います（例: kabusys.ai.score_news）。
  - 実行例（スクリプト提供時）:
    - AI スコア生成: 実行用ラッパーがあればそちらを利用してください。直接呼ぶ場合、DuckDB 接続と target_date を与えて kabusys.ai.score_news を呼び出します。

---

## 重要なファイル / 動作上の注意

- stop フラグ: data/stop_requested.flag — run_execution / run_monitoring が監視して停止するためのフラグ
- kill フラグ: data/kill.flag — KillSwitch が書き込む停止シグナル（Execution 側で検知）
- PID ファイル: data/execution.pid — ExecutionEngine が PID を書き込む（管理用）
- 監視 DB スキーマ: monitoring_db.init_monitoring_db() によって自動作成 / マイグレーションを実行します
- DuckDB 用パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- Paper Trading DB は paper_trading 環境時に別 Path を使用します（PAPER_TRADING_SQLITE_PATH）

---

## ディレクトリ構成

概ね以下のような構成を想定しています（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings 管理
    - config_setup.py           — .env ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring 起動スクリプト
    - ai/
      - news_nlp.py             — ニュース NLP スコアリング
      - regime_detector.py      — 市場レジーム判定
    - monitoring/
      - monitoring_db.py        — SQLite 監視ログ層（スキーマ定義）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py        — （アラート送信ロジック、コード内参照）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/                      — 実行時生成データ（DB, pid, flags, logs など）
- logs/                          — ログファイル（デフォルト）

※ 実際のリポジトリは上記以外に strategy / data / scripts 等のディレクトリが存在する可能性があります。

---

## サンプル .env（最小）

.env.example 相当の最小例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```
注意: `.env` は機密情報（トークン・パスワード）を含むため、絶対にバージョン管理にコミットしないでください。

---

## トラブルシューティング / よくある質問

- Q: Monitoring が期待通り動かない（ログが出ない）  
  A: LOG_DIR の書き込み権限や logs/<app>.log の作成可否を確認。utils.logging_setup はログディレクトリ作成に失敗するとコンソールのみで継続します。

- Q: OpenAI を使うと失敗する  
  A: OPENAI_API_KEY が設定されているか確認。API 呼び出しはリトライやフォールバックを備えていますが、キーが無い場合は例外になります。

- Q: run_execution がすぐ終了する  
  A: data/stop_requested.flag が存在しないか確認。存在する場合は起動せず終了します。

---

この README はコードの要点をまとめたものであり、各モジュールの細かいパラメータや実装詳細は該当ソース（src/kabusys/**）の docstring を参照してください。追加の説明やサンプルの要望があれば教えてください。