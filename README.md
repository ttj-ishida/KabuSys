# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README（日本語）

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買 / 研究フレームワークです。  
主な目的は以下です：

- 戦略リサーチ（DuckDB を用いたファクター計算・探索）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 注文実行エンジン（kabuステーション等のブローカーに発注）
- 監視・アラート（プロセス・データ鮮度・リスク監視、Kill Switch）
- Paper Trading（模擬発注）と本番運用の分離
- ニュース NLP / LLM を用いたセンチメント解析とレジーム判定

設計の特徴として、DB（SQLite / DuckDB）を利用した永続化、OpenAI API によるニュース解析（ai モジュール）、テスト可能なモジュール分割、環境変数による柔軟な設定が挙げられます。

---

## 主な機能一覧

- config 管理・ウィザード
  - `.env` の対話的作成・更新（kabusys.config_setup）
  - 起動前設定検証（kabusys.validate_config）
- 実行エンジン（ExecutionEngine）
  - 本番 / Paper Trading の切替（KABUSYS_ENV）
  - Risk Manager（ポジション上限・使用率等の制御）
  - Order Manager / Reconciler（発注管理・整合性）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - TradeMonitor: 注文滞留や約定異常の検出（trade_logs テーブル）
  - RiskMonitor: ドローダウンやポジション上限の監視、ダッシュボード更新
  - KillSwitch: 条件に応じて `data/kill.flag` を生成し ExecutionEngine を停止
  - MonitoringEngine: 上記 Monitor を束ねてポーリング・アラート送信
- ポートフォリオ構築
  - 候補選定 / スコア重み付け / 等分配（portfolio.portfolio_builder）
  - セクターキャップ・レジーム乗数（portfolio.risk_adjustment）
  - ポジションサイズ算出（portfolio.position_sizing）
- リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算 / IC（Information Coefficient）計算 / 統計サマリー
- AI / ニュース解析（ai）
  - news_nlp: raw_news を集約して OpenAI でセンチメント評価、ai_scores に格納
  - regime_detector: ETF MA とマクロニュースセンチメントを合成して市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード実行結果の検証レポート出力

---

## 前提（Prerequisites）

- Python 3.9+
- 必要な Python パッケージ（依存関係の一部）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証で YAML の検査を行う場合）
- ネットワーク接続（OpenAI 利用時）
- kabuステーション等、発注先の実行環境（本番運用時）

パッケージのインストールは通常の方法（pip / poetry 等）で行ってください。

例（pip）:
pip install duckdb psutil openai pyyaml

---

## 環境変数（主要）

必須：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（デフォルトあり）:
- KABUSYS_ENV: execution コンテキスト ("development" / "paper_trading" / "live")。デフォルト: development
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI 利用時に必要
- LOG_LEVEL: ログレベル（例: INFO）

Paper Trading 固有:
- PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（デフォルト: "instant"）

監視・制御:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0" / "1"、本番では 0 推奨）

詳しいキーや説明は `kabusys.config.Settings` を参照してください。

---

## セットアップ手順（最小）

1. リポジトリをクローン・チェックアウト
2. Python 仮想環境を作成し依存パッケージをインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt  （ある場合）
     もしくは個別に: pip install duckdb psutil openai pyyaml
3. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは手動で `.env` をプロジェクトルートに作成（.env.example を参照）
4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番前は --strict を付けて警告も FAIL 扱いにする: python -m kabusys.validate_config --strict
5. ディレクトリの準備
   - デフォルトで `data/` と `logs/` は自動作成されますが、権限や配置を確認してください
6. OpenAI を使用する場合は `OPENAI_API_KEY` を設定

---

## 初回起動・DB

- 起動スクリプトは起動時に監視 DB を初期化します（`init_monitoring_db` によりテーブル作成・マイグレーション）。
- DuckDB と SQLite のパスは環境変数で指定可能。デフォルト:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper Trading DB: data/paper_trading.db

---

## 実行方法（主要スクリプト）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper_trading DB（data/paper_trading.db）へ記録します（本番 DB と分離）。
    - 停止は `data/stop_requested.flag` を作成するか、Kill Switch により `data/kill.flag` が作られると停止します。
    - プロセス PID を data/execution.pid に記録します。

- 監視ループ（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト: 60秒）。
  - 監視プロセスは duckdb, sqlite に接続し、SystemMonitor.check_once() を定期実行します。
  - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用します（監視 DB は本番 DB を参照）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱いになります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）

- AI / レジーム判定・ニューススコアリング
  - これらは主にライブラリ関数（kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）として提供されています。CLI は用意されていませんがスクリプトやジョブから呼び出して利用してください。
  - OpenAI 利用時は `OPENAI_API_KEY` を設定してください。

---

## よく使うフラグ / ファイル

- data/stop_requested.flag
  - run_execution / run_monitoring の外部停止フラグ。存在すると起動中のループが終了します。
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine の即時停止を要求するために使用します。
- data/execution.pid
  - 実行エンジンの PID を保存（起動時に設定されます）
- logs/
  - ログファイル（run_execution は logs/execution.log、monitoring は logs/monitoring.log 等）を出力します。ログの日次ローテートが有効です。

注意: KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると起動時に kill.flag が自動クリアされるため危険です（本番では 0 を推奨）。

---

## トラブルシューティング / 補足

- パーミッション: `psutil` を使ったプロセス優先度や CPU affinity の設定は権限が必要な場合があります。`set_process_priority` は失敗しても警告を出して続行します。
- .env の自動ロード: `kabusys.config` はプロジェクトルート（.git または pyproject.toml）を自動検出し `.env` / `.env.local` を読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB マイグレーション: `init_monitoring_db` は既存 DB に対する簡単なマイグレーション（カラム追加）を行いますが、大規模なスキーマ変更は別途対応が必要です。
- OpenAI 利用:
  - API のレート制限や 5xx 系エラーに対してはリトライロジック（指数バックオフ）を組み込んでいますが、APIキーや料金設定は運用者の責任で準備してください。
  - LLM を使うモジュールはフェイルセーフで失敗時はスコアに 0 を使う等の設計になっています（例: regime_detector）。
- テスト: 各モジュールはできるだけ副作用を少なく分離されています。ユニットテストやモック差し替えが可能な形になっています（例えば OpenAI 呼び出しをモック）。

---

## ディレクトリ構成（抜粋）

（ファイル数が多いため主要ファイルのみ記載）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / Settings
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py         — ロギングセットアップ
      - process_priority.py      — プロセス優先度 / CPU affinity
    - execution/
      - execution_engine.py      — ExecutionEngine 本体（実行ロジック）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py         — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - data/                       — デフォルト DB / フラグ保存先（実行時に利用）

- data/ (実行時に使用される場所、デフォルトファイル)
  - monitoring.db                — SQLite 監視 DB（デフォルト）
  - paper_trading.db             — Paper Trading 用 DB（paper_trading モード）
  - kabusys.duckdb               — 分析用 DuckDB（デフォルト）
  - kill.flag / stop_requested.flag / execution.pid 等

---

## 開発メモ / 注意点

- KABUSYS_ENV を `live` にすると本番運用挙動になります。LINE 通知設定や Kill Switch 設定など、本番向けのチェックを必ず実施してください。
- Paper Trading 時はデータベースが分離され、MockBrokerClient を用いるため本番ブローカーへの発注は発生しません。
- モジュールは可能な限り副作用の少ない純粋関数や明確な I/O 層（DB）で設計されています。ユニットテストの実装・拡充を推奨します。

---

もし README に追加したいサンプルコマンド、設定例、あるいは運用手順（systemd / cron での起動例やログローテーションの運用方針など）があれば教えてください。必要に応じて追記します。