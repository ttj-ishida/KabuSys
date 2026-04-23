# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
このドキュメントはリポジトリ内の主要スクリプト／モジュール群（実行エンジン、監視、設定管理、リサーチ、ポートフォリオ構築、AI 補助など）の概要と使い方をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール化されたシステムです。主な責務は以下の通りです。

- 実行エンジン（ExecutionEngine）: ブローカーとのやり取り、注文管理、リスク管理、リコンシリエーションなどを担う。
- 監視（Monitoring）: システム状態、発注ログ、リスク指標を定期監視し、Kill Switch（停止フラグ）やアラートを発行する。
- リサーチ（Research）: DuckDB 上の時系列データを用いてファクター計算、特徴量探索を行う。
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ計算、セクター制限などの純粋関数群。
- AI モジュール: ニュースの NLP によるセンチメント評価や市場レジーム判定（OpenAI API を利用）。
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度設定など。

設計方針の一部:
- 環境変数 / .env による設定管理
- DuckDB（分析用）と SQLite（監視・注文ログ用）の併用
- Paper Trading（ペーパートレード）環境向けに本番 DB と分離
- LLM/API 呼び出しは失敗に対してフェイルセーフ（スキップ・フォールバック）で設計

---

## 主な機能一覧

- 実行
  - 実売買／ペーパートレード切替（`KABUSYS_ENV`）
  - ブローカークライアントの抽象化（本番 or モック）
  - 注文管理・リスク管理・約定リコンシリエーション

- 監視
  - CPU / メモリ / ディスク使用率監視
  - Execution プロセス死活検知
  - 注文滞留・約定異常・ドローダウン・ポジション上限監視
  - Kill Switch（flag ファイルによるエンジン停止指示）
  - 監視ログを SQLite に永続化

- リサーチ & ポートフォリオ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
  - 候補選定、等重/スコア重み、リスクベースのポジションサイズ計算
  - セクターキャップ・レジーム乗数の適用

- AI（OpenAI）
  - ニュース記事の銘柄別センチメント評価（ai_scores テーブルへ格納）
  - マクロニュース + 指標の合成による市場レジーム判定

- ツール
  - 設定ウィザード（.env の対話式作成）
  - 設定検証 CLI（必須環境変数・YAML 等のチェック）
  - Paper Trading 検証レポート生成スクリプト

---

## 必要要件（推奨）

（プロジェクトに依存するライブラリをインストールしてください。requirements.txt がある場合はそちらを利用）
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定 YAML 検証を行う場合）
- （SQLite は標準で含まれます）

インストール例（参考）:
```bash
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトする。

2. 必要パッケージをインストールする（上記参照）。

3. ディレクトリ作成（初回のみ）:
```bash
mkdir -p data logs
```

4. 環境変数を設定する（.env を用意するか環境変数で設定）。
   - 対話式ウィザードで .env を作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - 主要な必須変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV（development | paper_trading | live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）

5. 設定検証（推奨）:
```bash
python -m kabusys.validate_config
# 警告も厳密に FAIL にしたい場合
python -m kabusys.validate_config --strict
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒, run_monitoring の上書き）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — =1 にすると自動で .env をロードしない

（詳しくは `kabusys.config.Settings` を参照してください）

---

## 使い方（起動例）

- 実行エンジン（ExecutionEngine）を起動:
  - 本番または開発環境（KABUSYS_ENV に応じて動作が変わります）
  ```bash
  python -m kabusys.run_execution
  ```
  - paper_trading 環境で起動（MockBrokerClient を使用し、data/paper_trading.db に記録）
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  注意:
  - 実行開始時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中は `data/execution.pid`（デフォルト）に PID を書きます。

- 監視ループを起動:
```bash
python -m kabusys.run_monitoring
# ポーリング間隔を変更する例（秒）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 設定ウィザード（.env を対話的に作成）:
```bash
python -m kabusys.config_setup
```

- 設定検証:
```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- Paper Trading 検証レポート生成:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを明示する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

---

## 監視 / 停止制御について

- Kill Switch:
  - `KillSwitch` は `data/kill.flag` を作成することで ExecutionEngine 停止のトリガーになります（監視側で判定・書き込み）。
  - ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` の設定に応じてクリアを行うオプションがあります（本番では無効推奨）。

- 停止フラグ:
  - 監視・実行スクリプトは `data/stop_requested.flag` の存在を見てループを終了します（外部運用での停止通知用）。

---

## ログ設定

- `kabusys.utils.logging_setup.setup_logging` で統一的にログを設定します。
  - stdout（StreamHandler）と日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに登録します。
  - デフォルトログディレクトリ: `logs/`
  - 環境変数 `LOG_LEVEL` / `LOG_DIR` で調整可能。

---

## AI 機能（OpenAI を使う箇所）

- ニュース NLP（kabusys.ai.news_nlp）やレジーム判定（kabusys.ai.regime_detector）は OpenAI API を利用します。利用するには `OPENAI_API_KEY` を設定してください。
- API 呼び出しはリトライ、バックオフ、レスポンス検証、スコアのクリップ等のフェイルセーフが入っていますが、API キー未設定だとエラーになります（スクリプト側で例外が投げられる場合あり）。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内 `src/kabusys` を基準に主要ファイル／パッケージ:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード、Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                — 実行エンジン周り（BrokerFactory, ExecutionEngine, OrderManager 等）
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
  - data/ (実行時に使用するファイル群が置かれる想定)
  - config/ (YAML 設定ファイル群: system_config.yaml など)

（ファイル一覧はソースに基づく抜粋です。実際のリポジトリではさらに補助モジュール等が存在します）

---

## 注意事項 / 運用上のヒント

- .env は絶対にリポジトリにコミットしない（Secrets を含むため）。`config_setup.py` のヘッダにもその旨が記載されています。
- 本番（KABUSYS_ENV=live）での実行前に `python -m kabusys.validate_config` で設定を念入りに確認してください。LINE 通知設定漏れなど本番特有の注意喚起が出ます。
- paper_trading では mock ブローカー・別 DB により本番 DB と完全分離されるため安全に検証できます。
- プロセス優先度設定（高優先度）を行うため、一部環境では権限不足で設定に失敗する場合があります（警告が出ますが継続します）。
- DuckDB / SQLite のパスやログディレクトリは事前に親ディレクトリが存在するか確認してください。`validate_config` は親ディレクトリの存在を警告しますが、起動時に自動作成されることもあります。

---

必要に応じて、この README に運用手順（systemd ユニット例、Dockerfile、CI/CD のセットアップ等）を追記できます。追加で欲しい内容（例: systemd サービス定義、より詳細な .env.example、デバッグ手順など）があれば教えてください。