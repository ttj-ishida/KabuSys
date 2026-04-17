# KabuSys

KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。  
本リポジトリには取引エンジン（ExecutionEngine）、監視（Monitoring）機構、ポートフォリオ構築・ポジションサイジング、ファクター計算・探索、ニュースNLP（OpenAI 利用）などの主要機能が含まれます。

注意: 本 README は src/kabusys 以下の実装に基づいています。

---

## 目次

- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（コマンド / 実行例）
- 環境変数（重要）
- ディレクトリ構成（概観）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を提供します。

- 自動発注を行う ExecutionEngine（本番・ペーパートレード対応）
- 実行状況・システム状態を記録・監視する Monitoring（Kill Switch, Alerts）
- ポートフォリオ構築（候補選定、重み付け、ポジション決定）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- ニュース NLP（OpenAI を利用した銘柄/マクロセンチメント評価）
- 各種ユーティリティ（プロセス優先度設定、DB ヘルパー等）
- 検証・セットアップ用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針の一部:
- 本番データとペーパートレード DB は分離（PAPER_TRADING モード）
- ルックアヘッドバイアスを避けるため日付参照を明示的に渡す設計
- OpenAI の呼び出しはリトライやバリデーションを備えフェイルセーフ（失敗時はスキップや中立値で続行）

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - RiskManager（ポジション上限、ドローダウン等）
  - Reconciler / OrderManager / OrderRepository
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス存在、データ鮮度
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件次第で data/kill.flag を作成して ExecutionEngine を停止
  - MonitoringDB: SQLite に監視ログを永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- Portfolio
  - 候補選定、等重・スコア重み、セクター制限、レジーム乗数、ポジション数算出（単元丸め・aggregate cap）
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC（Spearman）、統計サマリ
- AI（OpenAI 利用）
  - news_nlp: ニュースをまとめてセンチメントを取得・ai_scores へ保存
  - regime_detector: ETF MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env / config/*.yaml の事前検証
  - paper_verification_report: ペーパートレード DB から検証レポート生成

---

## セットアップ手順

前提
- Python 3.10+（型注釈に union 型 `|` を使用）
- Git でプロジェクトルートが判別できること（.git または pyproject.toml があることが推奨）

推奨ライブラリ（最低限、環境に応じてインストールしてください）:
- duckdb
- psutil
- openai（AI モジュールを使う場合）
- pyyaml（validate_config が YAML 検証を行う場合に任意だが推奨）

例: pip でインストール
```
pip install duckdb psutil openai pyyaml
```

初期セットアップ:
1. リポジトリをクローンし、プロジェクトルートに移動
2. data ディレクトリを作成（多くのスクリプトが data/*.db, data/*.flag を参照します）
   ```
   mkdir -p data
   ```
3. 対話式で .env を作成（必須環境変数入力のためのウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザード完了後、`.env` がプロジェクトルートに作成されます（.env は決して Git にコミットしないでください）。
4. 設定検証を実行
   ```
   python -m kabusys.validate_config
   # 必要なら --strict を付けて警告も失敗扱いにする
   python -m kabusys.validate_config --strict
   ```

データベース初期化:
- 実行時にモジュールが必要なテーブルを作成します（Monitoring の init_monitoring_db 等）。事前に空の DB ファイルを用意する必要は通常ありません。

---

## 簡単な使い方（起動 / コマンド）

- 実行エンジン（ExecutionEngine）を起動:
  - 本番モード / ペーパートレードは KABUSYS_ENV により切替
  - ペーパートレードでは専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient が使われます
  ```
  python -m kabusys.run_execution
  ```
  実行時、data/execution.pid に PID を書き込み、data/stop_requested.flag の存在で安全終了します。

- 監視ループを起動:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  ```
  python -m kabusys.run_monitoring
  ```
  監視は常に「本番用」sqlite_path を使用します（KABUSYS_ENV に依存せず）。

- .env 対話式セットアップ:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定・DB 指定が可能
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI 周り（ニュース / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を設定し、該当関数を呼び出す（score_news / score_regime）。これらは直接 CLI ではなく Python API レベルで呼び出します。
  - 例（サンプル）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="…")

---

## 主要な環境変数

必須（最低限 .env に設定するもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用上よく使うもの（デフォルト値あり）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH を使う
  - live: 本番（注意して設定すること）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject（デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動削除するフラグ（"1" で有効。warning: 本番では通常 "0" 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH — カスタムパスを使う場合に設定可能

補足: .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル・モジュール）

（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 読み込みロジックを含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成・CRUD）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の作成/管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信の抽象。実装に応じて通知する）
  - execution/  (発注周り: OrderManager, ExecutionEngine 等) — 実装ファイル群（参照元あり）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 発注株数算出・上限・単元丸め
  - research/
    - factor_research.py — momentum/value/volatility 等の計算（DuckDB を使用）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（ETF MA200 + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

---

## 運用上の注意

- kill.flag / stop_requested.flag / execution.pid
  - 制御用フラグ:
    - data/stop_requested.flag — run_execution / run_monitoring がプロセス停止を検知するためのフラグ
    - data/kill.flag — KillSwitch が作成（Execution を停止させる意図で作成）
    - data/execution.pid — 実行エンジンの PID（プロセス生存チェックに使用）
  - 本番では KILL_FLAG_CLEAR_ON_START を "0" にしておくことを推奨します。誤って kill.flag を消してしまうと Kill Switch の効果が無効化される恐れがあります。

- DB の切り分け
  - paper_trading（ペーパートレード）実行時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。本番監視 DB（monitoring.db）と分離されます。

- OpenAI 利用
  - AI モジュールは OPENAI_API_KEY が必要です。API 呼び出しはリトライ・バリデーションを行いますが、API コストやレスポンス変動に注意してください。
  - LLM 出力は JSON モードで取得し、厳密な形式を期待していますが、それでもパース失敗のケースを考慮してフェイルセーフ化されています。

- Python バージョン
  - 型注釈などから Python 3.10 以上を想定しています（`X | None` など）。

- 追加依存
  - validate_config の YAML 検証は PyYAML がインストールされている場合のみ行われます（未インストール時はスキップ）。

---

README は以上です。必要であれば以下を追加で作成できます:
- requirements.txt / poetry / pyproject.toml の例
- デプロイ手順（systemd ユニット例、Dockerfile）
- 実行フロー図 / シーケンス図
- API 使用例（AI スコア取得のサンプルスクリプト）

どの追加情報が欲しいか教えてください。