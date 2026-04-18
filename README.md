# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ（バージョン 0.1.0 相当）。  
このリポジトリは以下の主要機能を持つモジュール群を含みます：戦略リサーチ、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視・アラート、AI を利用したニュース NLP / レジーム検出、各種ユーティリティ。

---

## プロジェクト概要

KabuSys は日本株自動売買システムを構成するコンポーネント群を提供します。主に次の責務を持ちます。

- 市場データ（DuckDB の prices_daily 等）を使ったファクター計算・リサーチ
- シグナルからの銘柄選定・配分・株数決定（ポートフォリオ構築）
- 発注エンジン（本番／ペーパートレード対応）と注文管理・リスク管理
- システム稼働監視・トレード監視・キルスイッチ機能
- OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- .env の対話式生成 / 設定検証スクリプト / 検証レポート等のツール群

設計方針の要点：
- DuckDB（分析用）と SQLite（監視・履歴用）を分離
- Paper Trading（ペーパートレード）と Live（本番）を明確に分離
- LLM（OpenAI）呼び出しはフェイルセーフに配慮（失敗時はフォールバック）
- 自動テストや CLI で利用しやすい純粋関数を多用

---

## 機能一覧

- 環境設定管理
  - 対話式 .env 生成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 起動スクリプト
  - ExecutionEngine 起動（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient、別 DB に記録
  - Monitoring 起動（run_monitoring.py）
    - 定期的に各種モニタ（System / Trade / Risk）を実行しログ・アラートを発行
- 監視（monitoring）
  - system_monitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
  - trade_monitor: 滞留注文・約定異常などの検出（コードはリポジトリ内）
  - risk_monitor: ドローダウン・ポジション上限監視とリスクログ
  - kill_switch: フラグファイル（data/kill.flag）による Execution 停止シグナル
  - monitoring_engine: 各モニタを束ねてループ実行
- ポートフォリオ（portfolio）
  - 銘柄選定、重み計算（等配分・スコア加重）、ポジションサイズ計算、セクター上限等のリスク調整
- リサーチ（research）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン・IC 計算、ファクター統計サマリ
- AI（ai）
  - news_nlp: OpenAI を使ったニュースセンチメントのスコアリング（ai_scores に書き込み）
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM 評価を合成して market_regime を算出
- ツール
  - paper_verification_report: ペーパートレード DB を解析して検証レポート生成
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
  - config: .env 自動ロード・設定アクセスラッパー
  - monitoring_db: 監視用 SQLite スキーマと永続化層

---

## セットアップ手順

前提
- Python 3.9+（typing の書式に合わせているためなるべく新しい 3.x）
- OS: Linux / macOS / Windows（ただしプロセス優先度 / CPU affinity の挙動はプラットフォーム依存）

1. リポジトリをクローン / 配布パッケージを用意
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 最低依存例（pip を使う）:
     pip install duckdb psutil openai
   - 追加で便利:
     pip install pyyaml
   - ※ requirements.txt がある場合はそれを使用してください。
4. 初期設定ファイル (.env) を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照してください）。必須変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env を絶対にリポジトリにコミットしないでください。
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
6. データディレクトリの準備
   - デフォルトで使用されるファイル:
     - data/kabusys.duckdb  (DuckDB; 分析用)
     - data/monitoring.db   (監視用 SQLite)
     - data/paper_trading.db（ペーパートレード時）
     - logs/                （ログ出力先）
   - 必要に応じて環境変数でパスを上書き（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH など）

---

## 使い方

主要な実行例と説明を示します。

- 実行前にログ設定を行い、プロセス優先度を上げる仕組みが各起動スクリプト内で呼ばれます。

1. ExecutionEngine を起動する（通常は daemon / systemd 等で起動）
   - 本番またはペーパートレードは KABUSYS_ENV で切替
   - コマンド:
     python -m kabusys.run_execution
   - ペーパートレード時は .env で KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します。
   - 実行中停止: data/stop_requested.flag を作成すると安全に停止します（run_execution はこのファイルを監視）。

2. Monitoring を起動する（監視ループ）
   - コマンド:
     python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で上書き:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - run_monitoring は監視 DB（SQLite）と DuckDB に接続し、SystemMonitor.check_once を定期実行します。
   - data/stop_requested.flag を置くとループを終了します。

3. .env の対話式生成
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

5. Paper Trading 検証レポート生成
   - コマンド:
     python -m kabusys.tools.paper_verification_report
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

6. AI 機能（news_nlp / regime_detector）
   - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数経由）
   - 例: kabusys.ai.score_news を呼ぶ際に api_key を渡す、または環境変数にセット
   - API 呼び出しはレート制限や一時エラーに対してリトライ実装あり。失敗時はフェイルセーフで継続します。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY (AI 機能を使う場合必須)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数を上書き)
- KILL_FLAG_CLEAR_ON_START (0/1) — Execution 起動時の kill.flag 自動クリア設定（本番では 0 推奨）
- Kill / stop フラグ:
  - data/kill.flag: KillSwitch による Execution 停止トリガ（監視コンポーネントが書き込む）
  - data/stop_requested.flag: 起動スクリプトが監視する停止要求フラグ（手動停止など）

ログ
- デフォルトログディレクトリ: logs/
- 各アプリケーションは app_name（例: execution, monitoring）でログファイルが生成され、日次ローテーション（30 日保持）

プロセス優先度
- 起動スクリプトは set_process_priority("high") を呼び出して優先度を上げようとします。権限がない場合は警告を出して継続します。

---

## ディレクトリ構成

リポジトリの代表的な構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / Settings ラッパー（.env 自動ロード含む）
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py         — ログ設定ユーティリティ
      - process_priority.py      — 優先度 / CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py         — SQLite スキーマ / 永続化層
      - system_monitor.py        — システム状態・データ鮮度監視
      - risk_monitor.py          — ドローダウン / ポジション上限監視
      - kill_switch.py           — フラグファイルで Execution を停止
      - monitoring_engine.py     — 各 Monitor を束ねるエンジン
      - (trade_monitor.py 等 他ファイル)
    - execution/                  — 発注エンジン周辺（BrokerFactory / OrderManager / ExecutionEngine 等）
    - portfolio/
      - portfolio_builder.py     — 候補選定・重み算出
      - position_sizing.py       — 株数決定ロジック
      - risk_adjustment.py       — セクター制限・レジーム乗数
    - research/
      - factor_research.py       — ファクター計算（momentum/value/volatility）
      - feature_exploration.py   — 将来リターン / IC / 統計サマリ
    - ai/
      - news_nlp.py              — ニュースセンチメントスコアリング（OpenAI）
      - regime_detector.py       — レジーム判定（MA200 + マクロセンチメント）
    - tools/
      - paper_verification_report.py  — ペーパートレード検証レポート
    - data/ (runtime)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - kill.flag
      - stop_requested.flag
    - logs/ (runtime)

※ 実際のファイルは上記説明と一致するように配置されています。プロジェクトルートは .git または pyproject.toml を基準に自動検出します。

---

## 注意事項 / トラブルシューティング

- 必須環境変数が未設定だと起動時にエラーになります。まずは python -m kabusys.config_setup で .env を生成し、python -m kabusys.validate_config でチェックしてください。
- OpenAI を使用するモジュール（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）が必須です。キーがない場合は ValueError を投げます。
- psutil によるプロセス優先度設定や CPU affinity は権限が必要な場合があります。失敗すると警告を出して処理は継続します。
- logging_setup はログディレクトリの作成に失敗するとファイル出力をスキップしてコンソール出力のみになります。stderr に警告が出ます。
- DuckDB / SQLite のテーブルスキーマは初回接続時に自動で作成・マイグレーションされます（init_monitoring_db）。
- run_execution と run_monitoring はそれぞれ data/stop_requested.flag を監視して終了します。安全に停止したい場合はこのファイルを作成してください。
- KABUSYS_ENV=paper_trading の場合、発注処理はモック化され、本番 DB と分離して data/paper_trading.db に記録されます。デフォルトで本番 DB（data/monitoring.db）とは別です。

---

## ライセンス / バージョン

- 本 README はコードベース（__version__ = "0.1.0"）に基づいて作成しています。商用利用や配布に関するライセンスはリポジトリルートの LICENSE を参照してください（存在する場合）。

---

必要であれば、README に含める具体的な .env のサンプルや systemd / docker-compose の起動例、より詳細な API ドキュメント（各モジュールのパブリック関数一覧）を追加できます。どの情報を優先して追加しますか？