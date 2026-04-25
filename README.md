# KabuSys

日本株向け自動売買システムのコードベースリポジトリ（README 日本語版）。

この README はリポジトリ内の主要モジュール・実行スクリプトに基づいて作成しています。実行前に .env を作成し、必須環境変数を設定してください（`python -m kabusys.config_setup` を推奨）。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したフレームワークです。シグナル生成・ポートフォリオ構築・ポジションサイズ計算・発注エンジン（ExecutionEngine）・監視（Monitoring）・リスク管理・研究用ツール群・AI（ニュース NLP / レジーム判定）などを含みます。DuckDB と SQLite をデータ保存に使用し、kabuステーション API（実売買）や OpenAI を用いた自然言語処理連携などの機能を備えています。

主な設計方針
- 環境変数による設定（.env をサポート）
- development / paper_trading / live の実行モード
- Paper Trading は本番 DB と分離（専用 SQLite）
- 監視コンポーネントは運用監視・Kill Switch を備えフェイルセーフ設計

---

## 主な機能一覧

- 実行エンジン (run_execution.py)
  - ブローカークライアント切替（paper_trading 時は MockBroker）
  - OrderManager / RiskManager / Reconciler などによる発注処理
  - PID ファイル（data/execution.pid）、停止フラグ監視（data/stop_requested.flag）
- 監視コンポーネント (run_monitoring.py, monitoring/...)
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - TradeMonitor / RiskMonitor：注文滞留・約定異常・ドローダウン・ポジション上限チェック
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager（通知の管理）と連携可能
- ポートフォリオ構築（portfolio/）
  - 候補選定、等重 / スコア加重の重み計算
  - セクターキャップ、レジーム乗数
  - 株数決定（単元株丸め・aggregate cap）
- リサーチ（research/）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
  - DuckDB を用いたデータ処理
- AI モジュール（ai/）
  - news_nlp：OpenAI を用いたニュースの銘柄別センチメントスコア算出（ai_scores へ保存）
  - regime_detector：ETF + マクロニュースを合成して日次の市場レジーム判定（market_regime テーブルへ保存）
- ツール（tools/）
  - paper_verification_report：ペーパートレード DB を解析して PASS/FAIL レポート出力
- 設定補助
  - config_setup.py：.env を対話式に生成／更新
  - validate_config.py：環境変数や config/*.yaml を起動前に検証
- 共通ユーティリティ
  - utils/logging_setup.py：統一ログ設定（stdout + 日次ローテーションファイル）
  - utils/process_priority.py：プロセス優先度 / CPU affinity の設定

---

## セットアップ手順（概略）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成しパッケージをインストール
   - Python 3.9+ を想定
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -r requirements.txt
   - 必須依存（コード参照）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config の YAML 検証に使用。任意）

   ※ requirements.txt は本リポジトリに含まれていない場合があるため、上の主要パッケージをインストールしてください。

3. .env を作成
   - 対話式での作成推奨:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に以下の必須変数を設定:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - 主要な環境変数（デフォルト値や説明は次節参照）

4. 環境変数自動ロード
   - config.py はプロジェクトルート（.git または pyproject.toml を探索）から .env を自動ロードします。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. ディレクトリ・ファイルの準備
   - デフォルトの DB / ログ保存先は `data/` と `logs/`
   - 必要に応じて手動で作成されますが、アクセス権等を確認してください

---

## 環境変数（代表的なもの）

（config_setup.py / config.py に基づく主要キー）

- KABUSYS_ENV: 実行モード（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。run_monitoring で利用。デフォルト 60
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）

---

## 主要コマンド / 使い方

リポジトリルートで実行することを前提とします。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 警告も失敗とみなす (--strict)
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の時は paper_trading 用 DB を使い MockBrokerClient で発注（本番 DB と分離）
    - PID ファイル: data/execution.pid を作成
    - 起動時に data/stop_requested.flag の存在を検知すると起動せず終了
    - 停止は data/stop_requested.flag を作成することで実行中エンジンに通知され、エンジンは停止処理を行う

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL を設定してポーリング間隔を秒単位で変更可能（デフォルト 60秒）
  - 監視は (config.Settings).sqlite_path（監視用 SQLite）を本番設定に関係なく使用します（常に同一 DB）
  - 停止フラグ: run_monitoring は data/stop_requested.flag の存在でループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを直接指定可能（未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または default）

- AI 機能（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（ai/news_nlp.py の仕様）と target_date を渡して ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへレジーム判定を書き込む
  - どちらも OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）

---

## 運用上の注意

- KABUSYS_ENV=live を設定すると実際の発注が行われます。設定値や通知先（LINE）の確認、Kill Switch の設定は必須です。
- Kill Switch（data/kill.flag）は ExecutionEngine の即時停止のための手段です。KILL_FLAG_CLEAR_ON_START を本番環境で 1 にするのは危険です（自動でクリアされるため）。
- run_execution / run_monitoring は起動直後にプロセス優先度を "high" に設定します（psutil を利用）。
- 監視は monitoring_db（SQLite）へ永続化します。バックアップ／ローテーションや権限設定に注意してください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。`LOG_DIR` 環境変数で保存先を変更可能です。

---

## ディレクトリ構成（抜粋）

以下はソースツリーの主要なディレクトリ/ファイル構成（src/kabusys 配下）です。実際のリポジトリルートには pyproject.toml 等がある想定です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数・設定管理
    - config_setup.py           — .env 対話ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring ポーリング起動スクリプト
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity
    - execution/                 — 発注関連（OrderManager 等）
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py        — 監視用 SQLite の永続化層
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
    - data/                      — 実行時に生成される想定ディレクトリ（DB / pid / flags）
    - logs/                      — ログが出力されるデフォルトディレクトリ

---

## .env（例／主要項目）

config_setup.py で生成される .env の主要キー（例）:

- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant

必須は JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD（validate_config.py でもチェックされます）。

---

## トラブルシューティング（よくある質問）

- 起動時に .env が読み込まれない
  - プロジェクトルートを探せない（.git または pyproject.toml が見つからない）場合、自動ロードがスキップされます。`KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認、または明示的に環境変数を export してください。

- run_monitoring が監視 DB に接続できない
  - Settings.sqlite_path（SQLITE_PATH）を確認。ファイルパーミッション / ディレクトリ存在も確認してください。

- OpenAI 呼び出しが失敗する
  - OPENAI_API_KEY を設定してください。API のレート制限・一時的なエラーは内部でリトライ処理がありますが、最終的に失敗すると該当処理はスキップされます（フェイルセーフ）。

- ペーパートレードの結果を検証する
  - python -m kabusys.tools.paper_verification_report を使って PAPER_TRADING_SQLITE_PATH を指定してレポートを出力できます。

---

README は概略です。詳しい設計・アルゴリズムの説明（PortfolioConstruction.md、StrategyModel.md 等）はリポジトリ内ドキュメントを参照してください。動作確認やデプロイの際は、まず `python -m kabusys.validate_config` で設定を検証することを推奨します。