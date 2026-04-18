# KabuSys

日本株向け自動売買システムのライブラリ／実行スクリプト群です。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・稼働監視・研究用ユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントを備えたモジュール群です。

- 実行エンジン（ExecutionEngine）: 発注ロジック・リスク管理・OrderManager などを組み合わせて発注を行う。
- 監視（Monitoring）: システム状態・注文ログ・リスク監視を定期ポーリングしてログ保存・アラート・Kill Switch を実行。
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ決定、セクター上限等の純関数群。
- 研究（Research）: ファクター計算、特徴量探索、IC計算など DuckDB を使った分析ユーティリティ。
- AI モジュール（AI）: ニュースの NLP スコアリング（OpenAI）と市場レジーム判定。
- ユーティリティ: 設定読み込み、対話式 .env ウィザード、設定検証、ログ設定、プロセス優先度調整など。
- ツール: ペーパートレード検証レポート生成スクリプト等。

設計方針の要点:
- データ永続化: SQLite（監視用等） + DuckDB（分析用）
- 本番・ペーパートレード分離: KABUSYS_ENV に応じて DB を分離
- LLM 呼び出しはフェイルセーフ（失敗時はスキップ or デフォルト値）
- ルックアヘッド対策（日時参照の取り扱いに注意）

---

## 主な機能一覧

- 環境設定ウィザード（.env）: `python -m kabusys.config_setup`
- 設定検証 CLI: `python -m kabusys.validate_config`（--strict オプションあり）
- ExecutionEngine 起動スクリプト: `python -m kabusys.run_execution`
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading DB に記録
- Monitoring 起動スクリプト: `python -m kabusys.run_monitoring`
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート: `python -m kabusys.tools.paper_verification_report`
  - --from / --to / --db オプションで期間や DB を指定可能
- AI: ニュース NLP スコアリング（OpenAI）とレジーム判定
  - プログラム API: `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime`
- ポートフォリオ関連純粋関数群:
  - 候補選定: `select_candidates`
  - 重み計算: `calc_equal_weights`, `calc_score_weights`
  - ポジションサイズ決定: `calc_position_sizes`
  - セクター制約/レジーム乗数: `apply_sector_cap`, `calc_regime_multiplier`

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストールします（プロジェクトに requirements ファイルがある想定、ない場合は以下を参考に必要パッケージをインストールしてください）。
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定 YAML の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. 対話式で .env を作成（推奨）
   - python -m kabusys.config_setup
   - 作成された `.env` は絶対に Git にコミットしないでください。

4. 設定検証を実行
   - python -m kabusys.validate_config
   - 問題がある場合はメッセージに従って修正してください。
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリの確認
   - デフォルト DB 等は `data/` に置かれます（存在しない場合は起動時に自動作成される場合があります）。
   - ログは `logs/` がデフォルトです（`LOG_DIR` 環境変数で変更可能）。

注意:
- 一部機能（OpenAI 連携など）は API キーが必要です（環境変数 `OPENAI_API_KEY`）。
- システム優先度設定や CPU affinity は OS 権限によって失敗することがあります（警告ログのみ出力されます）。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要オプション:
- KABUSYS_ENV — 実行環境（development|paper_trading|live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパー約定モード (instant|partial|never|reject)（デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動削除するか（1 = 有効、デフォルト 0）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY — OpenAI を使う機能で使用（任意だが AI 機能を使う場合は必須）

---

## 使い方（起動例）

- .env を作成し、設定検証を実行:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ExecutionEngine を起動（通常モードまたは paper_trading）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - 起動時に data/execution.pid を書き、data/stop_requested.flag や data/kill.flag を使って外部から停止できます。

- Monitoring を起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - 停止は data/stop_requested.flag を作成するか Ctrl+C

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを直接指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）。

- AI 機能（プログラム経由）:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=...)  — DuckDB 接続と日付を渡して実行

- ログ設定:
  - 全起動スクリプトは `kabusys.utils.logging_setup.setup_logging(app_name=...)` を使用して統一的にログを出力します。
  - デフォルトでは stdout と logs/<app_name>.log（日次ローテーション）が使われます。

---

## 注意点 / 運用上のヒント

- KABUSYS_ENV=paper_trading の場合、発注は実際のブローカーに送られず、paper_trading 用の SQLite に記録されます（本番 DB と完全に分離）。
- Monitoring は常に本番用の sqlite_path を使用して監視データを記録します（環境に依存しない設計）。
- OpenAI を使用するモジュールは API の失敗に対してフォールバックを取る実装ですが、API キーの管理とコストに注意してください。
- プロセス優先度の設定はプラットフォーム依存・権限依存です。設定に失敗した場合は警告ログのみ出ます。
- Kill Switch（data/kill.flag）は本番環境で特に重要です。KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI

起動スクリプト:
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリング起動スクリプト

utils/
- logging_setup.py — ログ設定ユーティリティ
- process_priority.py — 優先度 / CPU affinity 設定

monitoring/
- monitoring_db.py — SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py — システム状態・データ鮮度監視
- risk_monitor.py — ドローダウン・ポジション上限監視
- kill_switch.py — kill.flag 書き込みユーティリティ
- monitoring_engine.py — 各モニタの統合実行
- trade_monitor.py — （存在する想定）注文滞留・約定異常監視
- alert_manager.py — （存在する想定）通知管理

portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数算出・aggregate cap 処理
- risk_adjustment.py — セクターキャップ・レジーム乗数

research/
- factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB ベース）
- feature_exploration.py — 将来リターン・IC・統計サマリ等

ai/
- news_nlp.py — ニュース NLP スコアリング（OpenAI）
- regime_detector.py — マクロ + ma200 による市場レジーム判定

tools/
- paper_verification_report.py — ペーパートレード検証レポート生成

その他:
- data/ — デフォルトの DB / PID / フラグファイル等（git に含めない）
- logs/ — ログ出力先（デフォルト）

---

## 開発・拡張のポイント

- DuckDB 接続を渡す設計にしているため、データソースやスキーマを変えずに分析ロジックをテストできます。
- AI モジュールの OpenAI 呼び出しは小さなラッパー関数になっており、テスト時はパッチして差し替え可能です。
- monitor / engine などの起動スクリプトは PID / flag によって外部制御（停止、再起動）できます。
- ポートフォリオの計算関数は純関数化されており、ユニットテストが容易です。

---

もし README に追記してほしい点（例: インストール用の requirements.txt、具体的な運用手順、CI/テストコマンド例、より詳細なディレクトリツリーなど）があれば教えてください。必要に応じてサンプル .env のテンプレートや運用チェックリストも作成できます。