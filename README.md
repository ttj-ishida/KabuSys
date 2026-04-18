# KabuSys

日本株自動売買システムのコードベース。ポートフォリオ構築、発注実行、監視、研究（ファクター計算）、ニュースNLP を組み合わせて運用できるモジュール群を含みます。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール化された自動売買システムです。

- 発注・約定の実行（実運用 / ペーパートレード切替）
- 実行中プロセス・システム健全性の監視とアラート、Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター制限、レジーム調整）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー など）
- ニュースを LLM（OpenAI）で解析して銘柄別スコアを生成
- ペーパートレード検証レポート生成ツール
- .env 対話式ウィザードおよび設定検証ツール

設計方針として、リサーチ・AI 関連は実口座・発注 API にアクセスしないよう分離し、設定/環境ファイルを通じて動作モード（development / paper_trading / live）を切り替えられるようになっています。

---

## 機能一覧

- Execution
  - ExecutionEngine による発注処理（本番は kabuステーション、paper_trading は MockBrokerClient）
  - リスク管理（最大ポジション比率・利用率・サーキットブレーカ等）
  - 注文履歴（SQLite: trade_logs）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor / RiskMonitor: 滞留注文やドローダウンなどの監視とログ化
  - KillSwitch: しきい値超過時に `data/kill.flag` を書き込み ExecutionEngine を停止
  - ログ / メトリクスの永続化（SQLite）

- Portfolio construction
  - 候補選定、等重・スコア重み、score→株数変換（lot 単位丸め）、セクター上限、レジーム乗数

- Research
  - DuckDB を利用したファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄別センチメント（ai_scores）を書き込み
  - regime_detector: ETF（1321）の MA200 乖離 + マクロニュース LLM 結果で market_regime を判定

- Tools
  - ペーパートレード検証レポート生成ツール（`kabusys.tools.paper_verification_report`）
  - 対話式 .env ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）

---

## セットアップ手順

前提: Python 3.10 以降（ソース内の型記法から推奨）。SQLite は標準ライブラリで利用します。

1. リポジトリをクローン / 展開
   - プロジェクトルートに移動します。

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合に任意で）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt が無い場合は上記を個別にインストールしてください。

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主なオプション / 例:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LOG_LEVEL=INFO
     - KILL_FLAG_CLEAR_ON_START=0

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     - python -m kabusys.validate_config --strict

6. データディレクトリ・ログディレクトリ
   - デフォルトで `data/` と `logs/` にファイルを出力します。必要に応じて .env のパスを変更してください。

---

## 使い方（主要コマンド）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作モードは `KABUSYS_ENV` に依存:
    - `paper_trading`: MockBrokerClient を使用し `data/paper_trading.db` に記録（本番 DB と分離）
    - `live`: 実ブローカークライアントを使用

  - 停止方法:
    - `data/stop_requested.flag` を作成するとループが検知して終了します（run_* スクリプト両方で使用）。
    - KillSwitch が作動すると `data/kill.flag` が書き込まれ、ExecutionEngine 起動時に検出/停止されます。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path（`SQLITE_PATH`）を使用します（環境に依らず）。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) 扱い

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （`PAPER_TRADING_SQLITE_PATH` より優先）

- AI / リサーチ用関数（ライブラリとして利用）
  - ニューススコア生成:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要:
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使用する場合）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

詳細は `kabusys.config.Settings` クラスのプロパティ定義を参照してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - (その他の monitor 実装)
  - execution/              — ExecutionEngine / OrderManager 等（発注ロジック）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

- data/                     — データベース / フラグファイル等（起動時に作成）
  - kill.flag
  - stop_requested.flag
  - execution.pid
  - monitoring.db / paper_trading.db（デフォルトパス）

- logs/                     — ログ出力（`kabusys.utils.logging_setup` による）

---

## 実運用上の注意 / トラブルシューティング

- paper_trading モードは本番 DB と完全に分離し、`PAPER_TRADING_SQLITE_PATH` にデータを書きます。誤って本番 DB を上書きしないよう .env を確認してください。
- OpenAI を使う機能を動かす場合は `OPENAI_API_KEY` を設定してください。API のレート制限やネットワークエラーはリトライ処理がありますが、キー未設定だと例外が発生します。
- `psutil` による優先度設定や CPU affinity は環境によって例外が出ることがあります（権限不足など）。警告ログが出た場合は無視されますが、必要に応じて権限設定を確認してください。
- DuckDB / SQLite 関連のファイルパスは .env で設定できます。`kabusys.validate_config` で親ディレクトリの存在チェックや YAML のパースチェックが行えます（PyYAML が未インストールの場合は YAML 検証はスキップされます）。
- 監視ループ・実行ループの強制停止には `data/stop_requested.flag`（run_* スクリプトがポーリング内で参照）を利用してください。Kill Switch（リスク閾値超過等）は `data/kill.flag` を使います。起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動で clear されますが、本番では 0 を推奨します。

---

## 開発メモ / 拡張ポイント

- position_sizing の lot_size は現状共通の単元（例:100）を想定。将来的には銘柄単位のロット情報を導入する設計余地あり。
- news_nlp と regime_detector は OpenAI クライアント呼び出し周りを分離しており、テスト時にモック差し替えや置換が容易です。
- monitoring_db はマイグレーション処理を簡易的に含む（ALTER TABLE の追加入力処理あり）。スキーマ変更時はここを拡張してください。

---

何か特定のコマンドやファイルの説明を README に追記したい、あるいは運用手順（デプロイ/サービス化、systemd ユニット例など）を加えたい場合は、その要件を教えてください。README をそれに合わせて拡張します。