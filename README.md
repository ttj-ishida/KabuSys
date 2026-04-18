# KabuSys

日本株自動売買システムのモジュール群（ライブラリ + 起動スクリプト / 管理ツール群）

この README はリポジトリ内の主要スクリプト・モジュールをまとめた簡易ドキュメントです。  
（実装の一部を抜粋した形のコードベースに基づいて作成しています）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム群です。主に以下の機能を持ちます。

- 注文実行エンジン（ExecutionEngine）とブローカー抽象化（paper/live 両モード）
- 監視/アラート（System / Trade / Risk の監視、Kill Switch）
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイジング、セクター調整）
- リサーチ（ファクター計算、特徴量探索、IC計算）
- AI/LLM を使ったニュースセンチメント（OpenAI 経由）
- 運用支援ツール（.env ウィザード、設定検証、ペーパー検証レポート等）
- ログ設定・プロセス優先度設定などのユーティリティ

設計の指針として、
- 本番 / ペーパートレードのデータ分離
- ルックアヘッド回避（日時参照を固定化）
- フェイルセーフ（API障害時のフォールバック）
- 冪等な DB 操作・マイグレーション対応
が考慮されています。

---

## 主な機能一覧

- 起動スクリプト
  - `python -m kabusys.run_execution` : ExecutionEngine（発注エンジン）を起動
    - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、`data/paper_trading.db` に記録
  - `python -m kabusys.run_monitoring` : SystemMonitor のポーリングループを起動
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
- 設定管理 / ツール
  - `python -m kabusys.config_setup` : 対話的 .env 作成ウィザード
  - `python -m kabusys.validate_config` : .env と `config/*.yaml` の事前チェック CLI
  - `python -m kabusys.tools.paper_verification_report` : ペーパートレード実行の検証レポート生成
- 監視（monitoring）
  - SystemMonitor : CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの健全性チェック
  - TradeMonitor / RiskMonitor : 注文の滞留・約定異常・ドローダウン等の監視（DB ログへ永続化）
  - KillSwitch : しきい値超過時に `data/kill.flag` を作成して ExecutionEngine を停止させる
- ポートフォリオ（portfolio）
  - 銘柄選定、等比率／スコア加重の重み付け、ポジションサイズ計算、セクター集中抑制、レジーム乗数
- リサーチ（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- AI（ai）
  - news_nlp: OpenAI を使ったニュースの銘柄別センチメント評価（結果を ai_scores テーブルへ）
  - regime_detector: ETF 等の指標と LLM を組み合わせた市場レジーム判定（bull/neutral/bear）
- ユーティリティ
  - ロギングの統一セットアップ（console + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発向け）

想定 Python バージョン: 3.10 以上（型アノテーションに新版構文を利用のため）

1. 仮想環境作成・有効化（任意だが推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

2. 依存パッケージをインストール
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を有効にする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （このリポジトリに requirements.txt がない場合は上記を手動で管理してください）

3. .env の作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
   - もしくは `.env.example` を参照して `.env` を作成（存在しない場合は config_setup を推奨）
   - 重要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード時の専用 DB、デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY（AI機能を使う場合）
     - LOG_LEVEL（例: INFO）
     - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 追加で `--strict` を付けると警告も失敗扱いになります

5. データディレクトリ作成（必要に応じて）
   - デフォルトで使用されるディレクトリ:
     - data/ (DB・PID・flag 等)
     - logs/ (ログ出力)
   - 存在しない場合は自動で作成される箇所もありますが事前に作ると安全です

---

## 使い方（起動・コマンド例）

- ExecutionEngine を起動（本番 or ペーパートレードは KABUSYS_ENV で切替）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution

  挙動メモ:
  - paper_trading のときは MockBrokerClient を使い、書き込み先は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）
  - 起動時に `data/stop_requested.flag` が存在すると起動をしない
  - `data/execution.pid` に PID を書き込む（プロセス管理用）

- Monitoring を起動（SystemMonitor のポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - `MONITOR_POLL_INTERVAL` が未設定ならデフォルト 60 秒

  挙動メモ:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使って監視ログを永続化する
  - 停止は `data/stop_requested.flag` を作ることで検知可能

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定: --db path/to/paper_trading.db

---

## よく使う環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用アクセストークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API を使用する場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_DIR: ログ保存先（デフォルト logs/）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒。run_monitoring で使用）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行・停止管理関連

---

## 重要なファイル・ディレクトリ構成（抜粋）

リポジトリ内の主要なモジュール構成の例:

src/kabusys/
- __init__.py
- config.py                — 環境変数/設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングスクリプト

- ai/
  - news_nlp.py            — ニュースの LLM センチメント処理
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 構造と DB 操作ラッパー
  - system_monitor.py      — システム監視
  - risk_monitor.py        — ドローダウン・ポジション数監視
  - kill_switch.py         — kill.flag 制御
  - monitoring_engine.py   — 監視コンポーネントの統合実行
- portfolio/
  - portfolio_builder.py   — 候補選定、重み付け
  - position_sizing.py     — 株数計算・集計制約処理
  - risk_adjustment.py     — セクターキャップ・レジーム乗数
- research/
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py       — 統一ロギング設定（stdout + 日次ファイルローテート）
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

data/              — デフォルトの DB / flag / pid 等
logs/              — ログ出力先（デフォルト）

> 上記は抜粋です。実際のファイルはさらに execution/ や data/ など細分化されています。

---

## 開発時の注意点 / 運用におけるポイント

- DB の切り分け:
  - ペーパートレード時は専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使い、本番データと分離します。
- フラグファイル管理:
  - `data/kill.flag` や `data/stop_requested.flag` などのファイルを使ってプロセス間で停止シグナルを送ります。運用時に誤って残さないよう注意してください。
  - `KILL_FLAG_CLEAR_ON_START=1` を本番で使うと危険（自動で Kill Flag をクリアしてしまう）。本番は `0` を推奨します。
- LLM / OpenAI
  - OpenAI 経由の処理は API の失敗に対してフォールバックを多く入れてありますが、APIキー／料金管理に注意してください。
  - レスポンス形式や JSON パースに不確実性があるため、バリデーションとクリッピング処理を実装しています。
- ログ・監査
  - `kabusys.utils.logging_setup.setup_logging` を各起動スクリプトで呼び出してログ出力を統一しています。ログディレクトリの権限/ディスク容量には注意してください。
- テスト
  - OpenAI 呼び出し等はユニットテストでモックできるよう設計されています（例: _call_openai_api を patch）。

---

## 参考コマンドまとめ

- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate
- 依存インストール（例）:
  - pip install duckdb psutil openai PyYAML
- .env 作成（ウィザード）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README をプロジェクトのルート README.md として整える、あるいは各機能ごとに詳細な運用手順（systemd ユニット / Docker / サンプル .env）を追加したい場合は、その用途に合わせて追記します。どの形式・詳細度が必要か教えてください。