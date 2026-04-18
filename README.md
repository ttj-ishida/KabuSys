# KabuSys

日本株向け自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、戦略の研究（ファクター計算・特徴量解析）、ポートフォリオ構築、発注実行（本番／ペーパートレード）、および稼働監視・アラートに必要なモジュールを含む統合フレームワークです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を提供します。

- DuckDB / SQLite を用いたデータ解析 & 永続化層
- ファクター算出（Momentum / Volatility / Value 等）
- 特徴量探索・IC 計算などのリサーチユーティリティ
- ポートフォリオ構築（候補選定・重み算出・株数決定）
- 発注実行エンジン（本番 / ペーパートレード切替）
- 監視エンジン（システム状態・注文ログ・リスク監視）
- AI（OpenAI）を利用したニュースセンチメント評価・レジーム検出
- CLI ユーティリティ（.env ウィザード、設定検証、検証レポート生成）

設計上のポイント:
- 本番 DB とペーパートレード DB を分離（環境により切替）
- DuckDB による分析処理（prices_daily, raw_financials 等を前提）
- 外部 API 呼び出し（kabuAPI / J-Quants / OpenAI）は明示的な環境変数で制御
- フェイルセーフ: API エラー時は処理をスキップまたはデフォルト値で継続

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine（発注エンジン）を起動。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、専用の paper DB に記録。
  - run_monitoring.py: SystemMonitor のポーリングループを起動。ポーリング間隔は `MONITOR_POLL_INTERVAL` で上書き可。

- 設定・検証
  - config_setup.py: 対話式で `.env` を作成／更新するウィザード。
  - validate_config.py: `.env` および `config/*.yaml` 等の設定チェック CLI。

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成（稼働率 / 注文成功率 / レイテンシ等）。

- 監視
  - monitoring/*: MonitoringDB（SQLite スキーマ）, SystemMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager（参照）等。
  - kill.flag / stop_requested.flag を用いた停止 / 停止検出仕組み。

- ポートフォリオ関連（純粋関数）
  - portfolio/*: 候補選定、重み付け、リスク調整、ポジションサイズ計算（単元丸め・上限・スケールダウン等）

- リサーチ
  - research/*: ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリー 等

- AI
  - ai/news_nlp.py: ニュースを OpenAI へ送り銘柄ごとのセンチメントスコアを生成して ai_scores に書き込む
  - ai/regime_detector.py: ETF（1321）MA とマクロセンチメントを合成して市場レジーム（bull/neutral/bear）を判定

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.9+（DuckDB, psutil, openai 等が必要）。実行環境に合わせて適宜バージョンを調整してください。

1. リポジトリをクローンしてカレントディレクトリをプロジェクトルートにする
   - 本コードは `src/` 配下にパッケージが配置されています。パッケージとして使用する場合は PYTHONPATH に `src` を含めるか、適宜インストールしてください。
     例:
     - export PYTHONPATH=$(pwd)/src

2. 必要なパッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml
   - （オプション）ユニットテストなどで必要な追加パッケージがあれば別途インストールしてください。

3. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 手動で作成する場合は `.env.example` を参考に `.env` を作成し、以下の必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合、必須）
   - 注意: `.env` は絶対に Git にコミットしないでください。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格にチェックする場合:
     - python -m kabusys.validate_config --strict

5. データベース初期化
   - 起動スクリプト（run_execution/run_monitoring）は内部で必要なテーブルを作成する処理を呼びます（monitoring_db.init_monitoring_db など）。事前に空ディレクトリ `data/` を用意しておくと良いです。

---

## 使い方（起動例）

- ExecutionEngine（発注エンジン）の起動
  - 本番/ペーパートレードは `KABUSYS_ENV` で切替。
  - 例（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 例（本番）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution

  実行時の挙動:
  - paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を使用
  - 起動時に `data/stop_requested.flag` が存在する場合は起動を中止
  - 実行中は `data/execution.pid` に PID を書き込む

- Monitoring（監視ループ）の起動
  - 例:
    - python -m kabusys.run_monitoring
  - オプション:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更（デフォルト 60 秒）
    - 監視は Settings に定義された sqlite_path（デフォルト data/monitoring.db）を使用（環境にかかわらず本番 sqlite を参照する設計）
  - 停止:
    - プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）、デフォルト development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant | partial | never | reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" で有効。production では注意）

---

## 停止・Kill Switch 説明

- 実行中に強制停止やリモート停止が必要な場合は `data/kill.flag` を用いる設計（KillSwitch）。
- KillSwitch はリスク（ドローダウン、ポジション上限等）を検知した場合に `kill.flag` を書き込み、ExecutionEngine 側で検知して安全停止します。
- `data/stop_requested.flag` は起動スクリプト（run_execution/run_monitoring）の外部停止要求フラグとして使われます（存在を検知するとループを終了）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - (trade_monitor.py 等、監視関連モジュール)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/
    - (ExecutionEngine / BrokerFactory / OrderManager 等: 実行ロジック)
  - data/                    — 実行時に作成される想定のディレクトリ（logs/, sqlite 等）

注: 上記はリポジトリ内の一部ファイルを抜粋した構成です。実際のファイルはさらに存在します（execution/*.py, data 管理等）。

---

## 開発上の注意点・推奨事項

- .env を絶対にリポジトリにコミットしないこと（Secrets を含む）。
- 本番（KABUSYS_ENV=live）を起動する前に、必ず `python -m kabusys.validate_config` で検証すること。
- AI 機能を利用する場合は OpenAI の API キーのレート制限や課金に注意すること。news_nlp/regime_detector はリトライ・クリップ処理等の保護機構を持ちますが、運用上の制御は別途必要です。
- ログはデフォルトで `logs/` に日次ローテーションで出力されます。ログディレクトリが作成できない環境ではコンソールのみの出力となります。
- process_priority.set_process_priority を用いて起動直後にプロセス優先度を高める処理が行われます。プラットフォームにより権限不足で設定できない場合は警告が出ます。

---

## よく使うコマンドまとめ

- PYTHONPATH 設定（プロジェクトルートで実行する場合）
  - export PYTHONPATH=$(pwd)/src
- .env 作成（対話）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、README に以下を追記します:
- requirements.txt の推奨内容
- CI / デプロイ手順（systemd や supervisor での永続化起動例）
- 各テーブルスキーマの詳細（monitoring_db の説明拡張）
- ExecutionEngine / Broker インターフェースの利用方法（発注 API の実装契約）

どの情報を優先して追加しますか？