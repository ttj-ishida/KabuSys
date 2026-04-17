# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）です。戦略の研究・ファクター計算から発注エンジン、監視・アラート、ペーパートレード検証、LLMを使ったニュース評価などを含むモジュール群を提供します。

---

## プロジェクト概要

- 戦略研究（DuckDB を用いたファクター計算 / 特徴量評価）
- ポートフォリオ構築（候補抽出・重み計算・ポジションサイズ算出）
- ExecutionEngine（発注・オーダー管理・リスク管理・再調整）
- Monitoring（システム状態・注文滞留・ドローダウン監視、Kill Switch）
- AI モジュール（ニュース NLP による銘柄スコアリング、レジーム判定）
- ペーパートレード用 DB とレポート生成ツール

設計方針の一例：
- 本番とペーパートレードは DB を分離（KABUSYS_ENV により挙動が切り替わる）
- ルックアヘッドバイアス防止のため datetime.today() を直接参照しない実装
- OpenAI 呼び出しはリトライ・バリデーションを備えフェイルセーフを優先

---

## 主な機能一覧

- 設定ウィザード: `.env` の対話的作成（kabusys.config_setup）
- 設定検証: 環境変数 / config/*.yaml の事前チェック（kabusys.validate_config）
- Execution 起動スクリプト: `run_execution.py`（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
- Monitoring 起動スクリプト: `run_monitoring.py`（ポーリングで各種モニタを定期実行）
- Monitoring DB 永続化（SQLite）と API（monitoring_db.py）
- Risk Monitor / Trade Monitor / System Monitor と Kill Switch
- AI: ニュースのセンチメント評価（OpenAI）と市場レジーム判定
- Research: ファクター計算（momentum/value/volatility）・IC / 統計サマリー
- Portfolio: 候補選定・等配分 / スコア配分・ポジションサイズ算出
- ツール: ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要要件（依存パッケージ）

主に以下が必要です（プロジェクトの実際の requirements.txt を参照してください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config の検証で利用、任意）
- その他（プロジェクト固有のパッケージがある場合は requirements を参照）

仮想環境例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## セットアップ手順（開発者向けクイックスタート）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. 初期設定（対話式 .env 生成）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードに従って `JQUANTS_REFRESH_TOKEN` や `KABU_API_PASSWORD`、DB パス等を入力してください。
   - `.env` は絶対に Git にコミットしないでください。

4. 設定の検証
   ```bash
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. DB（DuckDB / SQLite）が必要な場合は設定に従ってファイルを準備してください。monitoring 用の SQLite はデフォルト `data/monitoring.db`、ペーパートレードは `data/paper_trading.db`、DuckDB は `data/kabusys.duckdb` がデフォルトです。

---

## 環境変数（代表例）

自動ロード:
- package の `kabusys.config` はプロジェクトルートに `.env` / `.env.local` があれば自動的に読み込みます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化可）。

必須（主なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants API
- KABU_API_PASSWORD — kabuステーション API
- OPENAI_API_KEY — OpenAI（AI モジュールを使用する場合）

主な任意 / 設定:
- KABUSYS_ENV — execution 動作モード（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — monitoring 用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 kill_flag クリア（0/1、本番では 0 推奨）

例（.env の一部）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
```

注意:
- `KABUSYS_ENV=paper_trading` の場合、Execution は MockBrokerClient を使い DB を `PAPER_TRADING_SQLITE_PATH` に記録して本番 DB と完全に分離します。
- `validate_config` が本番モード（live）のガードチェックを行います。live 設定は慎重に。

---

## 実行方法

- ExecutionEngine を起動（フォアグラウンド）
  ```bash
  python -m kabusys.run_execution
  ```
  - 実プロセスは `data/execution.pid` に PID を書きます（Settings.pid_file_path）。
  - 起動直後に `data/stop_requested.flag` が存在する場合は起動しません。
  - KABUSYS_ENV=paper_trading の場合は `PAPER_TRADING_SQLITE_PATH` に記録します。

- Monitoring を起動（フォアグラウンド、ポーリング）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を上書き可能（デフォルト 60）。
  - 監視コンポーネントは monitoring DB（Settings.sqlite_path）へログを書きます（Monitoring は環境にかかわらず本番 sqlite_path を使用する設計になっています）。
  - 停止は `data/stop_requested.flag` を作成するか Ctrl+C。

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで SQLite パスを指定できます（環境変数 `PAPER_TRADING_SQLITE_PATH` でも可）。

- 設定ウィザード／検証
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config [--strict]
  ```

---

## 停止・Kill Switch

- 実験的停止（監視プロセス / エンジンをやめさせる）:
  - `data/stop_requested.flag` を作成すると、`run_execution` および `run_monitoring` の監視ループが検知して終了します（実装上の stop flag）。
- Kill Switch（リスクトリガで ExecutionEngine を停止）:
  - `KillSwitch` は監視結果に基づき `data/kill.flag` を書き込みます。ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` を見てクリアするかを決めることができます（本番では自動クリアを無効にすることを推奨）。

---

## 開発者向けメモ / 実装上の注意点

- DB:
  - monitoring 用 SQLite: デフォルト `data/monitoring.db`。schema/マイグレーションは `monitoring_db.init_monitoring_db` に実装されています。
  - ペーパートレード SQLite は `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH`）に切り分けられます。
  - DuckDB は分析用データベース（`data/kabusys.duckdb`）。
- プロセス優先度: 起動スクリプトは最初に `set_process_priority("high")` を呼びます（`psutil` を使用、権限や OS により無視される場合あり）。
- AI モジュール:
  - `kabusys.ai.news_nlp` / `regime_detector` は OpenAI API を使用します。`OPENAI_API_KEY` が必須です。呼び出しはリトライ・バリデーション済み。
- ログレベルは環境変数 `LOG_LEVEL` で制御（Settings.log_level）。
- 自動 .env 読み込み:
  - プロジェクトルートを `.git` または `pyproject.toml` を基に探索して `.env` / `.env.local` を読み込みます。テスト時等は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

---

## ディレクトリ構成（抜粋）

以下は主なモジュールとファイルの構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (未表示の続きファイルあり)
  - execution/                  (発注関連コンポーネント群)
    - ... (OrderManager, ExecutionEngine, BrokerFactory 等)
  - utils/
    - __init__.py
    - process_priority.py

（上記はコードベースから抽出した主要ファイルの一覧です。実際のファイル群やサブパッケージをプロジェクト全体で確認してください）

---

## よくある質問 / 注意点

- Q: ペーパートレードと本番は DB が混ざりますか？
  - A: いいえ。run_execution は KABUSYS_ENV=paper_trading の場合 `paper_sqlite_path` を使用し、本番 DB と分離します。ただし Monitoring は環境に関わらず `sqlite_path`（デフォルト monitoring.db）を参照する実装になっています。
- Q: OpenAI を使いたくない／無い場合は？
  - A: AI 機能（news_nlp / regime_detector）は OpenAI API を必要とします。API キーが無い場合はこれらの機能は呼ばないか、呼び出しを避ける設計にしてください。validate_config は OpenAI の存在を必須にしていません。
- Q: 本番での Kill Flag 自動クリアはどうするべき？
  - A: 本番（live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨します。`validate_config` は live 環境でこの設定が `1` の場合に警告を出します。

---

## さらなる情報 / 貢献

- 各モジュール内の docstring やコメントに設計方針・注意点が詳述されています。実装を理解するときは該当モジュールの docstring をまずご覧ください。
- バグ修正・機能追加の際はテストを追加し、特に DB 書き込み・ロールバック周り・外部 API 呼び出しのフェイルセーフを意識してください。

---

以上がこのコードベースの README（日本語）です。必要であれば、実際の requirements.txt の内容や systemd / supervisor 用のユニットファイル例、Dockerfile、さらに詳細な設定例（.env.example）などを追加で作成します。ご希望があれば教えてください。