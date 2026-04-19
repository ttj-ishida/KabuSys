# KabuSys

日本株向け自動売買システム（プロトタイプ）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール式システムです。  
主な役割はシグナル生成 → ポジション構築 → 発注管理 → 監視・リスク制御 です。  
研究（research）・ポートフォリオ構築（portfolio）・発注エンジン（execution）・監視（monitoring）・AI（ニュースセンチメント／レジーム判定）などのコンポーネントで構成されています。

設計方針の要点:
- モジュールは可能な限り副作用を持たない純粋関数を採用（research / portfolio 等）。
- 実行系（ExecutionEngine）は本番 / ペーパートレードを切り替え可能（環境変数 `KABUSYS_ENV`）。
- 監視は SQLite にログを永続化し、条件に応じて kill flag を書き込むことで Execution を停止できる。
- OpenAI を利用したニュース NLP / レジーム判定を実装（APIキー必須、フォールバック設計あり）。

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード切替（`KABUSYS_ENV`）
  - Broker クライアントの抽象化（Mock クライアントを提供）
  - 発注履歴の永続化（SQLite / DuckDB）
  - リスクチェック（ポジション上限、ドローダウンなど）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 発注ログ監視（滞留注文、約定異常等）
  - RiskMonitor: ダッシュボードを基にドローダウンやポジション数を監視
  - KillSwitch: 条件により `data/kill.flag` を書き込み Execution 停止指示
  - アラート送信フック（LINE 等）

- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計算、統計サマリ
  - 候補選定・等分配・スコア加重・リスクベースの株数決定
  - セクター制約、レジーム乗数

- AI
  - ニュースを LLM（gpt-4o-mini 等）でセンチメント評価して ai_scores に書き込み
  - マクロニュース + ETF MA を用いた市場レジーム判定（書き込み可）

- ユーティリティ
  - 対話式 `.env` 作成ウィザード（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）
  - ペーパートレード検証レポート生成ツール（`python -m kabusys.tools.paper_verification_report`）
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティなど

---

## 要件（概略）

- Python 3.10+
- 推奨パッケージ（抜粋）
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（設定ファイル検証を行う場合）
- その他: SQLite（標準ライブラリでOK）

requirements.txt は含まれていないため、必要なパッケージを環境に応じてインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# 必要に応じて他の依存を追加
```

---

## セットアップ手順（初期セットアップ）

1. リポジトリをクローン／展開
2. 仮想環境を作成して依存をインストール（上記参照）
3. 対話式ウィザードで .env を作成
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意: `OPENAI_API_KEY`（AI 機能を使う場合）

4. 設定検証（起動前のチェック）
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにしたい場合は --strict を付与
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ・ログディレクトリの準備（通常は自動作成される）
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - ログ: logs/<app>.log（日次ローテーション）

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時 kill flag を自動クリアするか（0/1）

注意: .env は Git 管理してはいけません（config_setup が警告表示します）。

---

## 使い方（コマンド例）

- 実行エンジン起動（本番 / ペーパートレードは KABUSYS_ENV に依存）
  ```bash
  # デフォルト: python -m 実行モジュール
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録され、本番 DB と完全分離されます。
  - 起動時に `data/stop_requested.flag` が存在する場合は起動を行わず終了します。
  - 実行中は `data/execution.pid` に PID を書き込みます。

- 監視ループ起動
  ```bash
  # ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを書きます。
  - `data/stop_requested.flag` が存在すると監視ループを終了します。

- .env 作成（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI 関連（プログラム的に利用）
  - ニュースセンチメント: `kabusys.ai.score_news(conn, target_date, api_key=...)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)`

---

## 停止 / Kill Switch 操作

- 外部から Execution を安全に停止させたい場合は `data/stop_requested.flag`（run scripts はこのファイルを監視）を作成します。
- モニタが条件を満たした場合は `data/kill.flag` を作成し、ExecutionEngine 起動側でこれを検出して安全停止（Kill Switch）を行います。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

---

## ログ

- ログは既定で `logs/` ディレクトリに出力されます（ローテーション: 日次、30日保持）。
- アプリごとにファイル名: `logs/execution.log`, `logs/monitoring.log` など。
- コンソール出力は stdout に出ます（ジョブスケジューラとリダイレクトしやすいように stderr ではない）。

---

## ディレクトリ構成（抜粋）

src 以下の主要構成:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（監視テーブル）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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

トップレベルの想定ディレクトリ（実行環境に作成されるもの）
- data/                      — DB ファイル・PID・flag 等（例: data/monitoring.db, data/paper_trading.db）
- logs/                      — ログファイル

---

## 注意点 / トラブルシューティング

- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）が未設定だと起動時にエラーになります。`config_setup` で設定し、`validate_config` によりチェックしてください。
- OpenAI を使う機能は `OPENAI_API_KEY` が必要です。未設定のときは API を呼ぶ関数が ValueError を投げますが、監視系は有用性を損なわないようフォールバック処理を含みます。
- `psutil` を使ったプロセス優先度設定は権限のある環境（Linux: nice の権限等）でないと警告が出ますが、フェイルオープンで処理は継続します。
- DuckDB / SQLite のファイルパスは `.env` で上書き可能。デフォルトは `data/` 配下。
- DuckDB と SQLite の接続はそれぞれ別ファイルを使う構成（paper_trading は専用 SQLite に分離）になっています。
- テストや CI で自動ロードを抑制するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます（config.py の .env 自動ロードを無効化）。

---

## 開発者向けメモ

- 多くの関数は副作用を最小化する設計（純粋関数）で書かれています。単体テストを書きやすく、外部資源（DB / API）を注入する設計になっています。
- AI 呼出し部分はリトライ・バックオフやレスポンス検証を実装しており、部分失敗時に既存データを保持するよう配慮されています。
- データベースマイグレーション（簡易）は `monitoring_db.init_monitoring_db` 内で行っています（カラム追加チェックなど）。

---

README は導入の指針をまとめたものであり、詳細は各モジュールの docstring を参照してください（例えば `kabusys/ai/news_nlp.py`、`kabusys/portfolio/position_sizing.py` 等）。必要であれば運用手順書やアーキテクチャ図の追加ドキュメントも作成できます。