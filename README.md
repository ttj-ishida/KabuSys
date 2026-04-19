# KabuSys

日本株向けの自動売買システム（ライブラリ／起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・研究ツール・AI を組み合わせた自動売買基盤の一部です。  
README は主要コンポーネントと、ローカルで動かすための基本的なセットアップ／使用方法をまとめています。

---

## プロジェクト概要

KabuSys は以下の機能を持つコンポーネント群から構成されます。

- 発注実行エンジン（ExecutionEngine）とブローカー抽象化（paper/live 切替）
- 監視サービス（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定・セクター制約）
- リサーチ（ファクター計算、将来リターン、IC 等）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 運用ユーティリティ（ログ設定、プロセス優先度、設定ウィザード、設定検証）
- 運用向けツール（Paper Trading の検証レポート生成 等）

設計上のポイント：
- 環境は `KABUSYS_ENV`（development / paper_trading / live）で切替可能
- Paper Trading は本番 DB と完全に分離（デフォルト: `data/paper_trading.db`）
- OpenAI を利用する機能は API キーが必要（`OPENAI_API_KEY`）
- 設定は `.env` から読み込まれる。自動ロード機能を持つ（必要に応じて無効化可能）

---

## 主な機能一覧

- Execution
  - 実取引（live）・ペーパートレード（paper_trading）対応
  - リスク管理（利用率・ドローダウン・サーキットブレーカー等）
  - 注文履歴の永続化（SQLite / DuckDB 組合せ）
- Monitoring
  - システムリソース（CPU/メモリ/ディスク）監視
  - データ鮮度チェック（株価データ等）
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（条件を満たすと `data/kill.flag` を書いて Execution を停止）
  - アラート送信フック（LINE 等設定可能）
- Portfolio
  - 候補選定（スコア順）、等重・スコア重み、リスクベース配分、単元株丸め
  - セクター集中制限、レジーム乗数
- Research
  - Momentum / Value / Volatility 等のファクター計算（DuckDB 使用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI
  - ニュース記事を LLM（gpt-4o-mini）でスコアリングして `ai_scores` に保存
  - マクロニュース + ETF MA200 を元にした市場レジーム判定
- ユーティリティ
  - 環境設定ウィザード（対話式で .env を作成）
  - 設定検証 CLI（.env / config/*.yaml のチェック）
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル）

前提：
- Python 3.10 以上（型注釈や `X | None` の記法、match ではないがモダンな構文に合わせるため）
- git 等でリポジトリをクローン済み

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （必要に応じて他ライブラリを追加。SQLite は標準ライブラリに含まれます。）

3. `.env` の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動で `.env` をプロジェクトルートに置く（※Git にコミットしないこと）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI 機能を使う場合は:
     - OPENAI_API_KEY=<your_key>
   - 例（最小）:
     ```
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_pw
     KABUSYS_ENV=development
     ```

4. データディレクトリ
   - デフォルトの DB・フラグファイルは `data/` に作られます。権限を確認してください。
   - ログはデフォルト `logs/` に出力されます（`LOG_DIR` で変更可）。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗扱い（exit(1)）

---

## 使い方（起動例）

- ExecutionEngine（取引エンジン）を起動
  - python -m kabusys.run_execution
  - 注意:
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、ペーパートレード専用 DB（デフォルト: `data/paper_trading.db`）に記録します。
    - 起動時に `data/stop_requested.flag` が存在すると起動を拒否します（停止フラグ）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  - 監視は本番 sqlite_path を環境に関係なく使用します（監視ログの永続化先）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - 環境変数: PAPER_TRADING_SQLITE_PATH を設定しておくことも可

- Kill Switch 操作（運用）
  - `kabusys.monitoring.kill_switch` と連携して一定の閾値を超えると `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では推奨しません）。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（必須ではないが妥当な値にすること）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使用する機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数・投下計算
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP による銘柄別センチメント（OpenAI）
    - regime_detector.py — レジーム判定（ETF ma200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py — SQLite を使った永続化層
    - system_monitor.py — システム・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 操作
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 動作上の注意・運用メモ

- DB とログの書き込み先（`data/`、`logs/`）はプロセス実行ユーザーが書込可能であることを確認してください。
- 実行中のプロセス優先度を上げようとします（`set_process_priority("high")`）。権限不足の場合は警告が出ますが処理は続行します。
- OpenAI 周りは呼び出し回数・レート制限に注意してください（内部で指数バックオフを実装）。
- `.env` をリポジトリに含めないでください（機密情報を含むため）。
- 監視・運用系は `kill.flag` による外部停止フラグを使う設計です。自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）は本番では危険なためデフォルト 0 を推奨します。
- Paper Trading は本番データベースと分離されています。安全に検証できます。

---

## トラブルシューティング（よくある問題）

- ログファイルが作れない / ログディレクトリ作成に失敗する
  - `LOG_DIR` 環境変数を設定するか、`logs/` ディレクトリを手動で作成して権限を与えてください。
- psutil による優先度/affinity 設定で AccessDenied
  - 非 root/管理者では変更できないことがあります。警告が出ますが処理は継続します。
- OpenAI 呼び出しで失敗する
  - `OPENAI_API_KEY` が正しいか、ネットワーク・レート制限を確認してください。
- SQLite / DuckDB 関連のエラー
  - DB ファイルパス（`SQLITE_PATH` / `DUCKDB_PATH`）が正しいか、ファイルが壊れていないか確認してください。

---

必要であれば、README に示したコマンドの具体的な実行例や、各モジュール（ExecutionEngine、MonitoringEngine、AI 周り）の詳細な設計ドキュメントを追記します。どの部分のドキュメントを拡充したいか教えてください。