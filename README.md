# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ + 起動スクリプト群）。

この README はソースツリー（src/kabusys 以下）に基づく簡易ドキュメントです。  
主要な機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ自動売買フレームワークです。

- 戦略研究（DuckDB を用いたファクター計算／特徴量解析）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- Execution Engine（ブローカークライアント経由で発注、ペーパートレード対応）
- Monitoring（システム状態・注文・リスクを定期監視しログ化／アラート／Kill Switch）
- AI モジュール（ニュースの NLP スコアリング／市場レジーム判定：OpenAI を利用）
- ユーティリティ（ログ設定・プロセス優先度設定・設定ウィザード・設定検証）
- 運用支援ツール（Paper Trading の検証レポート生成など）

設計上のポイント：
- DuckDB を分析用 DB、SQLite を監視／注文履歴用 DB として利用
- 環境（development / paper_trading / live）に応じた振る舞い（paper_trading は発注をモック）
- OpenAI（gpt-4o-mini など）を外部 API として利用する機能あり（API キー必須）

---

## 機能一覧（抜粋）

- config_setup: 対話式で `.env` を作成 / 更新
- validate_config: `.env` と config/*.yaml の事前検証 CLI（--strict オプションあり）
- run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV により mock/real broker を切替）
- run_monitoring: SystemMonitor のポーリング監視ループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
- monitoring:
  - system_monitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - trade_monitor: 注文の滞留 / 約定異常検知（trade_logs テーブル参照）
  - risk_monitor: ドローダウン・ポジション上限監視と risk_logs / dashboard 更新
  - monitoring_engine: 各 Monitor を束ねてポーリング・アラート送信・Kill Switch 評価
  - kill_switch: 条件成立で `data/kill.flag` を書き込み Execution 停止をトリガー
  - monitoring_db: SQLite スキーマ作成 / マイグレーション / CRUD ユーティリティ
- ai:
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとにセンチメントスコアを書き込み
  - regime_detector: ETF・マクロニュースを組み合わせて市場レジーム判定を行い DB に書込
- research: ファクター計算（momentum/value/volatility 等）、将来リターン／IC 計算など
- portfolio: 候補選定・重み計算・ポジションサイズ計算・セクター制限・レジーム乗数
- utils:
  - logging_setup: 統一ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- tools:
  - paper_verification_report: ペーパートレード用 DB から検証レポートを生成

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（設定検証で YAML を検証したい場合）
   例:
   - pip install duckdb psutil openai PyYAML

   > プロジェクトに requirements.txt があればそれを使ってください（このリポジトリには含まれていない可能性があります）。

3. プロジェクトルートに移動（.env を自動で読み込むため）
   - README のあるルート（pyproject.toml か .git が存在するディレクトリ）で操作してください。

4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - その他: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LINE_* 等

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - デフォルトでは data/、logs/ にファイルを作成します。起動ユーザに書き込み権限があることを確認してください。

---

## 使い方（起動・運用）

主要なスクリプトはパッケージモジュールとして実行可能です。

- Execution Engine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` を使う（本番 DB と分離）
    - PID ファイル: data/execution.pid（設定で変更可）
    - 停止: プロセスは `data/stop_requested.flag` の検知またはスレッド終了で停止

- Monitoring 起動（ポーリング監視）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（秒、デフォルト 60）
  - python -m kabusys.run_monitoring
  - 動作:
    - 常に本番 sqlite_path（Settings.sqlite_path）を使用して監視情報を記録
    - 停止: プロジェクトルート/data/stop_requested.flag を置くことでループを抜けて終了

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）

- AI 機能（ライブラリ呼び出し）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY も可）
  - 例: kabusys.ai.score_news を DuckDB 接続 & 日付を渡して呼ぶ
  - 注意: API 呼び出しはレート制限 / 再試行ロジックあり。キー未設定時は ValueError。

ログ:
- デフォルト: logs/<app_name>.log（日次ローテーション、30 世代保持）
- コンソールは stdout に出力（logging_setup で設定）

Kill Switch / 手動停止:
- kill_switch はリスク条件成立時に `data/kill.flag` を書き込みます（ExecutionEngine が検出して停止する仕組み）
- 手動で停止フラグを立てる場合は `data/stop_requested.flag`（run_*.py が検知して終了）
- kill.flag を手動でクリアするにはファイル削除（KillSwitch.clear() が実行中に呼ばれます）

重要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL / LOG_DIR でログ挙動を制御

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（自動 .env ロード機能）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / DB 操作ラッパー
    - system_monitor.py      — CPU/メモリ/プロセス/データ鮮度監視
    - trade_monitor.py       — 注文滞留 / 約定異常検知（ファイル内参照）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書込・評価ロジック
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — （アラート送信管理：LINE 等。プロジェクトによる実装）
  - execution/               — Execution 関連（BrokerFactory, Engine, OrderManager 等）
  - portfolio/               — ポートフォリオ構築ロジック（builder / sizing / risk_adjustment）
  - research/                — ファクター計算・特徴量解析モジュール
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 呼び出し・再試行・検証）
    - regime_detector.py     — 市場レジーム判定（MA + LLM 結合）
  - data/                    — デフォルトで DB / フラグファイルを置く想定（実行時に作成）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

（上記は主要ファイルの抜粋です。細分化されたモジュール群が多数あります。）

---

## 開発・運用の留意点

- DB 分離
  - Paper Trading（KABUSYS_ENV=paper_trading）は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番の monitoring.db と分離されます。誤って本番 DB を上書きしないよう設定に注意してください。

- ログ / 権限
  - logs/ と data/ ディレクトリは実行ユーザが作成・書込できること。ログファイルのローテーションや作成失敗時にはコンソール出力にフォールバックします。

- OpenAI API
  - AI モジュールは OpenAI API を呼び出します。API キーと使用量に注意してください。エラー時のリトライやフォールバックロジックがありますが、API コストやレート制限を考慮の上運用してください。

- Kill Switch
  - RiskMonitor 等で Kill Switch が発動すると `data/kill.flag` が作成され、ExecutionEngine はこれを検知して停止します。本番運用時は Kill Switch の条件や `KILL_FLAG_CLEAR_ON_START` の設定（自動クリア）に注意してください。

- 自動環境変数読み込み
  - config.py はプロジェクトルートを .git / pyproject.toml を基準に探索し `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## よく使うコマンド例

- .env を作る（対話式）
  - python -m kabusys.config_setup

- 設定を検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動（デーモン管理は OS のサービス側で行ってください）
  - python -m kabusys.run_execution

- Monitoring 起動（デフォルト：60秒間隔）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

## 追加情報 / 今後の拡張

- Broker クライアント抽象化により、異なるブローカー実装の追加を想定
- 単元（lot）や手数料モデルなどを銘柄別に管理する拡張（position_sizing の TODO）
- テスト用のモック・ユーティル（外部 API 呼び出しを差し替え可能な設計はすでに考慮済み）
- ドキュメント（API 仕様、運用手順書）の充実化推奨

---

必要に応じて README に追記します。特定の箇所（例: 実際の起動フロー、設定ファイルの例、詳しい DB スキーマ解説）を詳述したい場合は指示してください。