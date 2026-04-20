# KabuSys — README (日本語)

このドキュメントはリポジトリ内の主要スクリプト・モジュールを対象とした README です。  
本プロジェクトは日本株向けの自動売買システム（分析・ポートフォリオ構築・発注・監視・レポート生成）を目的としています。

---

## プロジェクト概要

KabuSys は以下の機能群を備えた日本株自動売買基盤です。

- 株価データや財務データを用いたファクター計算・特徴量解析（Research）
- ポートフォリオ構築（候補選定、重み計算、単元丸め、ポジションサイズ計算）
- Execution Engine（ブローカー抽象化、オーダー管理、リスク管理、照合）
- 監視サブシステム（System / Trade / Risk のモニタリング、Kill Switch）
- AI 支援モジュール（ニュースのセンチメントによるスコアリング、レジーム判定）
- ユーティリティ（環境設定ウィザード、設定検証、ペーパートレード検証レポート）

設計の要点：
- DuckDB（分析用）と SQLite（監視 / 発注ログ用）を併用
- Paper Trading と Live を明確に分離（ペーパートレード時は専用 DB を使用）
- OpenAI を用いたニュース解析機能を提供（API キー必須）
- ロギングは統一 API（console + 日次ローテートファイル）

---

## 主な機能一覧

- 環境セットアップウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
- Portfolio 構築ライブラリ（選定・重み計算・ポジションサイズ算出・セクター制限）
- Research（ファクター計算 / forward returns / IC / 統計サマリー）
- AI:
  - ニュース NLP（gpt-4o-mini を想定）による銘柄別センチメントスコアリング
  - レジーム検出（MA200 とマクロニュースの合成スコア）
- Tools:
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントの | 演算子を使用）
- Git, 基本的な UNIX コマンド（開発環境に応じて）

1. リポジトリをチェックアウト
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

3. 依存ライブラリをインストール  
   主要な依存例（実際の requirements.txt がない場合は以下をインストールしてください）:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - duckdb: 分析処理
   - psutil: システムメトリクス・プロセス優先度設定
   - openai: AI（ニュース NLP / レジーム判定）
   - PyYAML: 設定ファイル検証（optional）

4. 環境変数設定（.env を用意）
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を直接作成。最低必須:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - その他: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL など

5. DB の初期化
   - 多くの起動スクリプトは起動時に必要なテーブルを作成します（init_monitoring_db を呼ぶ）。
   - DuckDB（分析用）はデフォルト path: `data/kabusys.duckdb`
   - Monitoring SQLite はデフォルト path: `data/monitoring.db`
   - Paper Trading 用 SQLite: `data/paper_trading.db`

6. ログディレクトリ
   - デフォルト: `logs/`。環境変数 `LOG_DIR` で変更可能。
   - 権限やディスク容量に注意してください。

---

## 使い方

主要スクリプトの起動例（プロジェクトルートで実行）:

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告もエラー扱い
  ```

- Execution Engine 起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker が使われ paper_trading 用 DB に記録される:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 起動前に `data/kill.flag` を自動クリアしたくない場合は `.env` の `KILL_FLAG_CLEAR_ON_START=0` に設定してください（本番推奨）。

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔を変更:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` オプションで指定可能。

- AI 機能（ニュース NLP / レジーム判定）
  - 環境変数 `OPENAI_API_KEY` を設定の上、該当関数を呼び出すかスクリプトを作成して利用してください。
  - レート制限やネットワーク失敗に対しては内部でリトライが実装されていますが、API キー・クォータには注意してください。

停止・Kill フラグ:
- 監視ループやエンジンは project-root/data/stop_requested.flag を検知すると順次終了処理を行います（監視用 stop フラグ）。
- KillSwitch により `data/kill.flag` が書き込まれると ExecutionEngine に停止シグナルが送られます（`KillSwitch.clear()` でクリーンアップ可能）。

ログ:
- setup_logging により stdout と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- ログレベルは `LOG_LEVEL` 環境変数で設定可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール利用時必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの fill モード: instant | partial | never | reject（デフォルト instant）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

注意:
- 自動 .env ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env は絶対に Git にコミットしないでください（機密情報を含むため）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュール一覧です（抜粋）。プロジェクトルートに `src/` 配下に実装が置かれています。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（.env 自動読み込み）
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証ツール
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity 設定
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 発注株数計算・スケール調整
    - risk_adjustment.py          — セクター制限・レジーム乗数
  - research/
    - factor_research.py          — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py      — forward returns / IC / summary
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py          — 市場レジーム判定（MA200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（system_status / trade_logs 等）
    - system_monitor.py           — システム状態 / データ鮮度監視
    - trade_monitor.py            — 注文/約定関連監視（ファイル参照）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 書き込みユーティリティ
    - monitoring_engine.py        — 各モニタを束ねるループ
  - execution/
    - broker_factory.py          — ブローカークライアント生成（Mock/実ブローカー切替）
    - execution_engine.py        — 実行エンジン（session 実行ループ）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring (DB 関連・監視用)
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（実際の全ファイルはリポジトリ内の src/kabusys 以下を参照してください）

---

## 運用に関する重要な注意点

- KABUSYS_ENV が `live` の場合は本番環境扱いです。`validate_config` の警告を必ず確認してください（LINE 通知等の設定）。
- Kill Switch 機構（データ/kill.flag）により ExecutionEngine を強制停止できます。誤って削除/クリアしないよう注意してください。
- Paper Trading は本番 DB を汚染しないために専用 SQLite を使用します（PAPER_TRADING_SQLITE_PATH）。
- OpenAI の利用は API コストが発生します。rate limit・エラーに対するリトライは実装されていますが、運用ルールを設けてください。
- ログディレクトリや DB ファイルの権限・バックアップ計画を準備してください。

---

## 開発者向けメモ

- ログ設定は共通化されており、全スクリプトは start-up 時に setup_logging を呼びます。
- プロセス優先度設定（set_process_priority）を各起動スクリプト冒頭で行っています（権限により失敗する場合あり）。
- DuckDB 接続は分析系モジュールで使われ、SQL を直接投げる設計です（テスト容易性のため外部副作用を抑えています）。
- テスト時に外部 API 呼び出しをモックするため、OpenAI 呼び出しは内部で関数化されています（ユニットテストで patch 可能）。

---

必要であれば、README に含める具体的な .env のテンプレート、起動時のトラブルシューティング（例: ログディレクトリ作成失敗、DB マイグレーションエラー）、および各モジュールの詳細なインターフェース説明を追記します。どの情報が必要か教えてください。