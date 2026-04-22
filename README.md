# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ。  
本リポジトリは戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、および AI を利用したニュース NLP／レジーム判定などのユーティリティ群を含みます。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成された自動売買基盤です。

- データ分析（DuckDB）を用いたファクター計算・研究（research）
- ポートフォリオ構築（候補選定・重み算出・枚数決定）
- 発注エンジン（ExecutionEngine） — 本番 / ペーパートレード切替対応
- 監視サブシステム（MonitoringEngine） — システム状態・注文・リスク監視、Kill Switch
- AI モジュール — OpenAI を用いたニュースのセンチメント評価、レジーム判定
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード / 検証 CLI 等）
- 開発用ツール（ペーパートレード検証レポート生成など）

目的は「研究〜戦略実行〜運用監視」を同一コードベースで扱うことです。運用時は環境変数 / .env による設定で動作を切り替えます。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env, config/*.yaml の簡易チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替あり）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db を使用
- Monitoring ポーリング（System / Trade / Risk のチェック）: python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
- AI:
  - ニュース NLP（OpenAI を用いた銘柄毎センチメント -> ai_scores）: kabusys.ai.news_nlp.score_news
  - レジーム判定（ETF MA + マクロニュースの LLM スコア合成）: kabusys.ai.regime_detector.score_regime
- 研究 / ファクター計算（DuckDB に保存された prices_daily / raw_financials を使用）:
  - momentum / volatility / value 等の計算
  - 前方リターン・IC 計算・統計サマリ
- ペーパートレード検証レポート生成ツール:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

## 前提条件 / 推奨環境

- Python 3.10+（Union 型記法（X | Y）を使用しているため）
- 主要依存パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の中身を検証したい場合）
- ログ出力ディレクトリ: デフォルト `logs/`（環境変数 LOG_DIR で変更可）
- SQLite / DuckDB のデフォルトパス:
  - DuckDB: `data/kabusys.duckdb`
  - SQLite(monitoring): `data/monitoring.db`
  - ペーパートレード SQLite: `data/paper_trading.db`（KABUSYS_ENV=paper_trading 時）

---

## 環境変数（主要）

必須（運用に必須なもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用 / 動作切替に使う主な環境変数（デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB, デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR（ログ保存先ディレクトリ）
- OPENAI_API_KEY（AI 機能利用時）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒）
- PAPER_FILL_MODE（paper_trading の mock ブローカ挙動: instant|partial|never|reject）

注意:
- .env は絶対に Git にコミットしないでください（config_setup でも注意文が出ます）。
- required な環境変数が欠けていると Settings または validate_config によって起動前に検出されます。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   - git clone <repo_url>
   - cd <repo_root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （実運用に合わせて追加パッケージをインストールしてください）

   ※ requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは `.env.example` を参考に手動作成（存在する場合）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合: python -m kabusys.validate_config --strict

6. 初回起動時の DB 等
   - run_execution / run_monitoring は起動時に必要なテーブルを作成します（init_monitoring_db）。
   - DuckDB / SQLite の親ディレクトリがない場合は警告が出ます。手動で `mkdir -p data logs` を作ることを推奨します。

---

## 使い方（よく使うコマンド例）

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番またはペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 通常（development/live）: python -m kabusys.run_execution
  - 実行中に停止させるにはプロセスに KeyboardInterrupt（Ctrl+C）または監視・Kill Switch 経由で停止

- Monitoring を起動（ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 既定は 60 秒。停止は Ctrl+C またはプロジェクトの `data/stop_requested.flag` を作成するとループが終了します。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定: --db /path/to/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（OpenAI 利用）
  - 必須: OPENAI_API_KEY 環境変数を設定
  - ニュース NLP: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

---

## 運用上の注意

- Kill Switch:
  - 監視サブシステムはリスク条件（ドローダウン、ポジション上限等）で `data/kill.flag` を書き込み、ExecutionEngine 側が検出して安全停止するよう設計されています。
  - 手動で Kill を解除するには `data/kill.flag` を削除してください。
  - run_execution/run_monitoring は `data/stop_requested.flag` の存在でループを終了します（優雅なシャットダウン）。

- ログ:
  - setup_logging 関数でログは stdout と `logs/<app_name>.log`（日次ローテーション）に出力します。LOG_DIR で変更可能。
  - ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。OS によっては権限不足で警告が出ます（無害）。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は起動時に必要なテーブルと簡易マイグレーション（カラム追加等）を行います。

- セキュリティ:
  - .env や API キーを安全に管理してください。`.env` は決してリポジトリへコミットしないでください。

---

## ディレクトリ構成（抜粋）

以下は本コードベースの主要ファイル / モジュールと役割（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポートツール
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 経由で銘柄別スコア）
    - regime_detector.py     — レジーム判定
  - research/
    - factor_research.py     — ファクター計算（momentum/volatility/value 等）
    - feature_exploration.py — IC / forward returns / 統計サマリ
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 枚数算出・資金配分
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
  - monitoring/
    - monitoring_db.py       — SQLite ベースの永続層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（存在）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - monitoring_engine.py   — 各 Monitor をまとめる
    - kill_switch.py         — kill.flag 書込ユーティリティ
    - alert_manager.py       — 通知管理（存在）
  - execution/               — Execution エンジン関連（BrokerFactory, OrderManager 等）
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

（注）上記は主要ファイルの抜粋です。実際のリポジトリにはさらに細分化されたモジュールや補助スクリプトが含まれます。

---

## よくあるトラブルシューティング

- Settings による起動時エラー:
  - 必須環境変数が未設定だと ValueError が発生します。`python -m kabusys.validate_config` で早期検出できます。

- ログファイルが作れない:
  - 権限やパスの問題で logs ディレクトリの作成に失敗するとファイル出力は無効化され、コンソールのみ出力されます。

- OpenAI API 呼び出し失敗:
  - OPENAI_API_KEY の設定を確認してください。API の過負荷・レート制限時は内部でリトライが行われますが、失敗時はフェイルセーフでスコアを記録しない/中立扱いにフォールバックする実装です。

- プロセス優先度の設定に失敗:
  - 権限不足（non-root）や OS 非対応のため警告が出ますが、処理は続行します。

---

## 開発 / 貢献

- 既存モジュールのユニットテスト追加、AI 呼び出しのモック化、DuckDB SQL の最適化等が貢献ポイントです。
- 大きな変更を行う際は config 検証ロジックや init_monitoring_db の後方互換性に注意してください（テーブル/カラムの変更はマイグレーション設計が必要）。

---

この README はコードベースの主要点をまとめた概要ドキュメントです。より詳細な設計や仕様（PortfolioConstruction.md / StrategyModel.md 等）がリポジトリ内にある場合はそちらを参照してください。必要であれば README に追記したい項目（例: デプロイ手順、CI 設定、具体的な設定例）を教えてください。