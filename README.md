# KabuSys

日本株向け自動売買システムの骨組み実装です。  
このリポジトリは、戦略ファクター計算、ポートフォリオ構築、発注エンジン（実行）、監視、AI を使ったニュース解析などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を想定したモジュール群を提供します。

- データ分析 / リサーチ（DuckDB を利用）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- ExecutionEngine（発注管理、ブローカークライアントを抽象化）
- 監視（System / Trade / Risk モニタ、Kill Switch）
- Paper Trading 用の分離された DB と検証レポート出力
- OpenAI を使ったニュース NLP（センチメントスコア）／レジーム判定

設計上の特徴:
- 設定は環境変数（.env）ベース。プロジェクトルートを自動検出して `.env` / `.env.local` を読み込みます（自動ロードを無効化する env: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と完全分離された専用 SQLite を使用します。
- ログはコンソール（stdout）と日次ローテーションされたファイル（logs/*.log）に出力されます。
- OpenAI を使う機能は API キーが必須（`OPENAI_API_KEY`）。

---

## 主な機能一覧

- config 管理
  - `.env` 自動読み込み（.env, .env.local）と Settings 型ラッパー
  - 対話式ウィザードで `.env` を生成： `python -m kabusys.config_setup`
  - 起動前検証ツール： `python -m kabusys.validate_config`（`--strict` オプションあり）

- 実行 / 監視
  - 実行エンジン起動スクリプト: `python -m kabusys.run_execution`
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient と `data/paper_trading.db` を使用
    - 起動中は `data/execution.pid` を管理、停止は `data/stop_requested.flag`
  - 監視ループ起動スクリプト: `python -m kabusys.run_monitoring`
    - ポーリング間隔は `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）
    - 監視は本番 sqlite_path（環境に関わらず監視 DB を使用）

- 監視サブシステム
  - SystemMonitor: CPU/メモリ/ディスク・プロセス PID ファイル確認・データ鮮度チェック
  - TradeMonitor: 発注 / 約定ログ解析（滞留注文・異常約定の検出）
  - RiskMonitor: ドローダウン・ポジション数監視、dashboard の更新
  - KillSwitch: 条件（例: ドローダウン閾値超過）で `data/kill.flag` を書き、ExecutionEngine を停止

- リサーチ / ポートフォリオ
  - factor 計算（momentum, value, volatility）
  - portfolio builder、等金額・スコア加重・リスクベース配分
  - ポジションサイジング（単元株丸め、aggregate cap）

- AI（OpenAI）
  - ニュース NLP（銘柄ごとのセンチメント → `ai_scores` テーブルに保存）
  - レジーム判定（ETF の MA200 乖離 + マクロニュースセンチメントの合成）

- ツール
  - Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report`

---

## セットアップ手順（開発環境向け）

前提: Python 3.10+ を想定（typing の | 記法などを使用）。

1. 仮想環境を作成・有効化
   - (例) python -m venv .venv
   - source .venv/bin/activate あるいは .venv\Scripts\activate

2. 必要パッケージをインストール
   - 主要依存（最低限）:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML は設定 YAML 検証で使われる
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実プロダクションでは requirements.txt を用意して管理してください。

3. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに `.env` を作成（以下は例）:

     JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     OPENAI_API_KEY=sk-...

   - 秘密情報（トークン・パスワード）は絶対に Git 管理下に入れないでください（.gitignore に .env を追加推奨）。

4. データディレクトリの作成
   - scripts を通さずとも各スクリプトは必要に応じて `data/` や `logs/` を作成しますが、手動で作る場合:
     - mkdir -p data logs

5. 設定検証
   - python -m kabusys.validate_config
   - 本番慎重に確認するなら: python -m kabusys.validate_config --strict

---

## 使い方（よく使うコマンド）

- 環境設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗として扱う）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - 起動前に `data/kill.flag` が存在すると起動しない（停止フラグ）。
    - PID ファイル: デフォルト `data/execution.pid`（Settings で上書き可）
    - Paper trading:
      - KABUSYS_ENV=paper_trading を設定すると MockBroker を使い、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に記録されます。

- 監視ループ起動（Monitoring）
  - MONITOR_POLL_INTERVAL 環境変数で秒間隔を上書き可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は常に本番の sqlite_path を使用（環境に左右されない）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  - 下位指標: 稼働率、注文成功率、送信率、P95 レイテンシ等を出力し PASS/FAIL 判定を行います。

- OpenAI を使う機能
  - 環境変数 `OPENAI_API_KEY` を設定してください（または該当関数に api_key を渡す）。
  - ニュース NLP: kabusys.ai.score_news を用いて `ai_scores` テーブルへ保存
  - レジーム判定: kabusys.ai.regime_detector.score_regime

- 停止 / Kill Switch
  - `KillSwitch` により `data/kill.flag` が書かれると ExecutionEngine に停止シグナルが伝わります（また `data/stop_requested.flag` で強制停止ループを検出する箇所もあります）。
  - Kill Switch をクリアするには `data/kill.flag` を削除（`KillSwitch.clear()` を呼ぶか手動で rm）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番では 0 を推奨）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — 市場レジーム判定
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py       — （コード抜粋には省略あり）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （省略）
  - execution/
    - execution_engine.py    — （省略）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時に使う SQLite / pid / flag ファイルを置く想定（git 管理外推奨）
  - logs/                    — ログファイル（runtime）

（上記は本 README に含まれる主要ファイルの抜粋です。実装の詳細・追加ファイルはソースを参照してください。）

---

## 運用上の注意 / ベストプラクティス

- 本番で公開される `KABUSYS_ENV=live` の場合、LINE の通知設定や Kill Switch 設定などを慎重に確認してください。`validate_config.py` は本番向けのチェックを行います。
- .env に機密情報を含めるため、`.gitignore` に必ず追加してください。
- OpenAI 使用部分はコストと API レート制限に注意してください。ネットワーク障害・429 はリトライ戦略がありますが、運用ルールを決めてください。
- Paper Trading と Live は DB を分離して運用してください（デフォルトで分離される実装になっています）。
- ログは日次ローテーション（30日保持）です。ログディレクトリの容量管理を行ってください。

---

## 開発・拡張ガイド

- 追加のブローカークライアントは `execution/broker_factory.py` を拡張してください。
- 新しいモニタやアラートは `monitoring` 以下に追加し、`MonitoringEngine` に組み込んでください。
- DuckDB に入れるデータスキーマ（prices_daily / raw_financials / raw_news 等）を整備すれば、research モジュールの解析機能が動作します。

---

必要であれば、README の英語版やインストール手順を package 化した手順（requirements.txt / setup.cfg / pyproject.toml）も作成できます。どの部分を詳しく補足しますか？