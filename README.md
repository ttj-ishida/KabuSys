# KabuSys

日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージ。注文発行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI ベースのニュース評価・レジーム判定などの機能を備えています。

以下はコードベースの概要、セットアップ方法、使い方、主要ファイル・ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は次の目的を想定したモジュール群で構成されています。

- ExecutionEngine：発注処理・注文管理・リスク管理を実行するエンジン
- Monitoring：稼働状況・滞留注文・リスク指標の定期監視とアラート・Kill Switch
- Portfolio：銘柄選定、配分、ポジションサイジング、セクター制約などのポートフォリオ構築ロジック
- Research：DuckDB を用いたファクター計算・特徴量解析（モメンタム／バリュー／ボラティリティ等）
- AI：OpenAI を用いたニュースの NLP スコアリング（銘柄ごとのセンチメント）と市場レジーム判定
- Tools：ペーパートレード検証レポート生成などのユーティリティ

設計方針のポイント：
- 本番 DB とペーパートレード DB は分離（KABUSYS_ENV による切替）
- DuckDB を分析用途に利用、SQLite を監視・発注ログ等の永続化に使用
- 設定は .env / 環境変数で管理。対話式ウィザード・検証ツールあり
- ログはコンソール + 日次ローテーションで保存

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動/実行（run_execution.py）
  - Broker クライアントの切替（paper_trading 時は MockBroker）
  - リスク管理（ポジション上限、利用率、ドローダウン等）
- Monitoring
  - システム状態監視（CPU/メモリ/ディスク、Execution プロセス検出）
  - 取引ログ・ポジション・リスクログの永続化（SQLite）
  - Kill Switch（条件を満たしたら kill.flag を書き、Execution を停止）
  - 複数モニタをまとめる MonitoringEngine（ポーリング実行）
- Portfolio
  - 候補選定・スコア順ソート
  - 等分配 / スコア加重配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap、リスクベース）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）評価、統計サマリ
- AI
  - ニュースのセンチメントを OpenAI で評価し ai_scores テーブルへ書き込み
  - マクロニュース + 1321 の MA200 を組み合わせた市場レジーム判定
- Tools
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）

---

## 動作要件（概略）

- Python 3.10+
- 主要依存パッケージ（抜粋）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証に任意で使用）
- SQLite（標準ライブラリで動作）
- その他、ネットワーク接続（kabuステーション API / OpenAI 等）は実行機能に応じて必要

（実際の requirements.txt がある場合はそれに従ってください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env の初期作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードで J-Quants トークン、kabuステーション API パスワード、DB パス、KABUSYS_ENV などを設定します。
   - 出力先はプロジェクトルートの `.env`（引数で別パス指定可）。
   - `.env` は絶対に Git にコミットしないでください。

5. 設定検証（起動する前に実行を推奨）
   ```
   python -m kabusys.validate_config      # 警告は許容
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```

---

## 使い方（実行例）

- ExecutionEngine を起動
  - 標準起動：
    ```
    python -m kabusys.run_execution
    ```
  - 挙動：
    - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し、デフォルトで `data/paper_trading.db` に記録（本番 DB と分離）。
    - Execution は `data/stop_requested.flag`（プロジェクトルート data 配下）を監視し、存在すると安全に停止します。
    - PID ファイル: `data/execution.pid`（Settings.pid_file_path により変更可）
    - 起動時にプロセス優先度を high に設定（可能なら）

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は KABUSYS_ENV に関わらず本番用の sqlite_path（デフォルト `data/monitoring.db`）を使用して監視ログを保存
  - 停止は `data/stop_requested.flag` を作成することで行います（既存のフラグ検知でループ終了）

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で指定可能（デフォルト `data/paper_trading.db`）
  - 指標（稼働率、約定率、送信率、P95 レイテンシ等）について PASS/FAIL レポートを出力

- AI 機能（プログラム経由）
  - OpenAI API キーは環境変数 `OPENAI_API_KEY` で指定するか、関数引数で渡します
  - ニューススコアリング（コードから呼び出し）:
    from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant/partial/never/reject、デフォルト instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 本番起動時に kill.flag を自動削除するか（0/1、デフォルト 0）

---

## ロギング

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使用して、コンソール（stdout）と日次ローテーションされたファイル出力（logs/<app_name>.log）を設定します。
- ログの回転は日次、デフォルトで 30 世代保持。

---

## 停止 / Kill Switch の取り扱い

- 手動停止（run_* スクリプト共通）:
  - プロジェクトルート `data/stop_requested.flag` ファイルが存在すると、監視ループやエンジンスレッドは停止します。
- 自動 Kill Switch:
  - `kabusys.monitoring.kill_switch.KillSwitch` が条件（例: ドローダウン超過、ポジション上限超過）を満たすと `data/kill.flag` を書き込み、ExecutionEngine 側で検出して停止できます。
  - 本番環境では `KILL_FLAG_CLEAR_ON_START=0` を推奨（誤ってクリアしないよう保護）。

---

## ディレクトリ構成（主要ファイル一覧と簡単な説明）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数・設定管理（.env 自動ロード、Settings クラス）
- config_setup.py — .env 対話式ウィザード（CLI）
- validate_config.py — 設定検証 CLI

run スクリプト:
- run_execution.py — ExecutionEngine 起動スクリプト（PID 管理、stop flag 監視、paper_trading 切替）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

portfolio/
- portfolio_builder.py — 候補選定、等重/スコア重み計算
- position_sizing.py — 株数計算、aggregate cap、単元丸め
- risk_adjustment.py — セクター上限、レジーム乗数
- __init__.py — ポートフォリオ API エクスポート

research/
- factor_research.py — モメンタム／ボラティリティ／バリュー等ファクター計算（DuckDB）
- feature_exploration.py — 将来リターン、IC、統計サマリ
- __init__.py — 研究用 API エクスポート

ai/
- news_nlp.py — ニュースの LLM によるセンチメント評価、ai_scores 書込み
- regime_detector.py — MA200 とマクロニュースでレジーム判定
- __init__.py — AI API エクスポート

monitoring/
- monitoring_db.py — SQLite テーブル作成・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py — システム稼働・データ鮮度の監視
- trade_monitor.py — （取引）滞留注文や約定異常を検出するモジュール（ファイル内に実装あり）
- risk_monitor.py — ドローダウン・ポジション上限のチェック
- kill_switch.py — Kill Switch（flag 書き込み）
- monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
- alert_manager.py —（通知管理、LINE などを想定したアラート送信モジュール）

execution/（発注周り）
- broker_factory.py — Broker クライアントの生成（実ブローカ / Mock 切替）
- execution_engine.py — ExecutionEngine 実装（セッション実行）
- order_manager.py / order_repository.py — 注文管理、DB 保存
- reconciler.py — 注文状態同期
- risk_manager.py — リスク管理ロジック（Rate limiting / circuit breaker 等）

utils/
- logging_setup.py — ログ設定ユーティリティ
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

tools/
- paper_verification_report.py — Paper Trading の指標レポート生成スクリプト
- __init__.py

その他:
- デフォルト DB/ログ保存先はプロジェクト内の `data/`、`logs/` ディレクトリ（Settings で変更可）

---

## 開発上の注意点／運用ガイド

- .env の取り扱い:
  - `.env` は秘密情報（API キー等）を含むため Git 管理外にしてください。
  - `config_setup.py` で初期作成、`validate_config.py` で起動前の検証を行ってください。
- 本番運用時:
  - KABUSYS_ENV=live の場合、LINE 通知や kill flag 設定などを慎重に確認してください（validate_config が警告を出します）。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動クリアしますが、本番では推奨しません。
- AI 呼び出し:
  - OpenAI の API 呼び出しは失敗に対してフェイルセーフ設計（リトライ・フォールバック）ですが、API キー管理・コストに注意してください。
- ログ:
  - ログディレクトリ作成に失敗した場合、コンソール出力のみになる旨の警告が出ます。運用では LOG_DIR を十分な書き込み権限のある場所に設定してください。

---

必要であれば、README にインストール用の requirements.txt のテンプレートや、各モジュールの関数シグネチャ例、CI 用チェックリスト（lint/test 実行コマンド）などを追記できます。どの情報を優先的に追加しますか？