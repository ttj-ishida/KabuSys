# KabuSys

日本株自動売買システム（KabuSys）のソースコードリポジトリ向け README（日本語）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムの骨組みを実装したプロジェクトです。  
主な責務は以下の通りです。

- 発注・実行エンジン（ExecutionEngine）による注文管理とブローカ連携
- 監視（Monitoring）コンポーネントによるプロセス/データ/リスク監視とアラート／Kill Switch
- ポートフォリオ構築（選定・重み付け・株数算出）の純粋関数群
- 研究用モジュール（ファクター計算・特徴量解析）
- ニュースの NLP スコアリング（OpenAI を利用したセンチメント評価）
- ペーパートレード用レポート生成ツール 等

設計方針として、可能な限り副作用を限定した純粋関数群と、DB（SQLite / DuckDB）を用いた永続化を組み合わせています。

---

## 機能一覧

- Execution
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBroker は paper_trading 用）
  - リスク管理（利用率・ドローダウン・レートリミット等）
- Monitoring
  - システムリソース監視（CPU/MEM/DISK）
  - プロセス稼働検出、データ鮮度チェック
  - トレード/リスク監視（滞留注文・約定異常・ドローダウン・ポジション上限）
  - Kill Switch：フラグファイルで ExecutionEngine の停止を指示
- Portfolio
  - 候補選定、等比率／スコア加重の重み計算
  - ポジションサイズ計算（リスクベース / 等配分 等）、lot 単位丸め・aggregate cap
  - セクター制約・レジーム乗数（市場レジーム考慮）
- Research
  - ファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメントスコア化して ai_scores に保存
  - 市場レジーム判定（ETF ma200 とマクロセンチメントを合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 前提 / 必要条件

- Python 3.9+
- 必要な主なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML を検証する場合）
- SQLite（Python 標準ライブラリで利用）
- 環境により kabuステーション等の接続先が必要（本番運用時）

（注）requirements.txt はこのリポジトリに含まれていない想定のため、上記パッケージを仮想環境に手動でインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール（前述）

3. .env の作成
   - 対話式ウィザードを使う（推奨）
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成し、必要な環境変数を設定する。

4. 設定の検証
   ```bash
   python -m kabusys.validate_config
   # 警告も厳密に扱う場合
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの確認
   - デフォルトの DB / PID / ログ等のパスはプロジェクトルート配下の `data/` / `logs/` 等です。必要に応じて `.env` で上書きします。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: execution モード。`development` / `paper_trading` / `live`（デフォルト: development）
  - `paper_trading` の場合、MockBrokerClient を使い DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に分離されます
- OPENAI_API_KEY: OpenAI API キー（AI モジュール実行時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

---

## 使い方（代表的なコマンド）

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 本番/テストは KABUSYS_ENV の値で切り替え
  ```bash
  python -m kabusys.run_execution
  ```
  - 注意:
    - 起動時に `data/stop_requested.flag` が存在すると起動しません。
    - Execution は PID ファイル（デフォルト data/execution.pid）を使用します。
    - ペーパートレード時は MockBroker を使い DB を分離します。

- Monitoring 起動（ループ）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - Monitoring は監視ログ（SQLite）へ永続化し、必要に応じて Kill Switch（data/kill.flag）を作成します。
  - 停止フラグ: `data/stop_requested.flag`

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB path を使う
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- AI モジュール（プログラムから呼び出し）
  - ニューススコアリング:
    ```py
    from kabusys.ai import score_news
    score_news(conn=duckdb_conn, target_date=date(2026,4,20), api_key="...")
    ```
  - 市場レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn=duckdb_conn, target_date=date(2026,4,20), api_key="...")
    ```

---

## ロギング

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を全起動スクリプトから呼び出してログを統一しています。
- デフォルトは stdout 出力（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）を併用します。
- ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`。

---

## 停止フラグ / Kill Switch

- 実行停止シグナル:
  - `data/stop_requested.flag` — run_monitoring / run_execution が監視している停止フラグ（手動で作成するとループ停止等のトリガー）
  - `data/kill.flag` — KillSwitch により Execution を停止させるために作られるフラグ。内容は理由のテキスト
- `KILL_FLAG_CLEAR_ON_START=1` をセットすると起動時に kill.flag を自動クリアしますが、本番では危険なので 0 を推奨します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定取得ロジック（Settings クラス）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py — ニュースの NLP スコアリング（OpenAI 呼び出し含む）
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite のテーブル作成・永続化層
  - system_monitor.py — CPU/MEM/DISK・データ鮮度・プロセス監視
  - trade_monitor.py — （トレード監視ロジック）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — Kill Switch 実装（flag ファイル書込）
  - monitoring_engine.py — 各 Monitor をまとめるループ
  - alert_manager.py — （アラート送信ロジック）
- execution/
  - execution_engine.py — ExecutionEngine / EngineConfig
  - broker_factory.py — Broker クライアント生成（Mock or 実ブローカ）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出（lot 単位丸め・スケール調整）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — forward returns, IC, 統計サマリ
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI

（上記は主要ファイルのみ抜粋。実際のリポジトリ内にさらに補助モジュール・スクリプトが含まれます）

---

## 備考 / 運用上の注意

- 本番運用時は KABUSYS_ENV=live により設定が切り替わります。LINE 通知等の設定を必ず確認してください。
- OpenAI API を使うモジュールは API キーを必要とし、呼び出しは失敗耐性（リトライ）やレスポンスバリデーションを持ちますが、API 利用制限・費用に注意してください。
- DB 変更（スキーマ追加等）は monitoring_db.init_monitoring_db でミグレーションを最小限担保しますが、バックアップを取ってから運用してください。
- .env は絶対に Git にコミットしないでください（config_setup でも注意喚起あり）。

---

必要があれば、README の英語版・より詳細な運用手順（systemd ユニット例、コンテナ化、CI/CD 設定）や、各モジュールの API ドキュメントを追記します。どの情報を優先して追加しますか？