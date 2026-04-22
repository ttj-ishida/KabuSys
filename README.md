# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのシステムです。  
主なコンポーネントは以下です。

- Execution Engine：発注・約定管理・リスク管理を行うエンジン
- Monitoring：システム健全性・注文状況・リスクを監視し、必要に応じて Kill Switch を作動
- Research：DuckDB 上の市場データからファクター計算や特徴量解析を実行
- AI モジュール：OpenAI を用いたニュースのセンチメントスコアリングや市場レジーム判定
- Portfolio：銘柄選定・配分・株数決定などの純粋関数群
- CLI ツール：`.env` ウィザードや設定検証、Paper Trading 検証レポートなど

設計方針として、可能な限り副作用を抑えた純粋関数群、DB の冪等初期化、環境変数による設定などを採用しています。

---

## 機能一覧

- Execution
  - 実際の発注は kabuステーション API（本番）または MockBrokerClient（ペーパートレード）で実行
  - リスク管理（利用率、ポジション上限、ドローダウンなど）
  - 注文の Reconciler / OrderManager / OrderRepository による管理
- Monitoring
  - CPU / メモリ / ディスク使用率監視
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - 発注ログ・約定ログ・リスクログの永続化（SQLite）
  - Kill Switch（flag ファイルによる Execution 停止）
  - アラート送信（LINE など、設定が必要）
- Research
  - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - ニュース記事の LLM ベースセンチメント（OpenAI）
  - マクロニュース + 指標を使った市場レジーム判定
- Tools
  - Paper Trading の検証レポート生成スクリプト
- Utilities
  - ログ設定ユーティリティ（コンソール＋日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - .env 対話ウィザード / 設定検証 CLI

---

## セットアップ手順

前提：
- Python 3.10 以上を想定（typing の表現に依存）
- システムにより追加で psutil 等が必要

1. リポジトリをクローンして、仮想環境を作成・有効化します（例: venv / pyenv / conda）。

   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストールします。プロジェクトの requirements.txt がある場合はそれを使用してください。無い場合は最低限以下をインストールしてください。

   pip install duckdb psutil openai

   - optional:
     - PyYAML（config YAML の検証用）: pip install pyyaml

3. 初期設定（.env）:
   - 対話式ウィザードを使って .env を生成・更新できます：

     ```
     python -m kabusys.config_setup
     ```

   - 必須の環境変数（代表）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
   - 実行環境: KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか
   - Paper Trading 用の DB（分離）: PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
   - 監視 DB（SQLite）デフォルト: data/monitoring.db
   - DuckDB path デフォルト: data/kabusys.duckdb

4. 設定検証（起動前チェック）:

   ```
   python -m kabusys.validate_config
   # 警告を FAIL として扱いたい場合
   python -m kabusys.validate_config --strict
   ```

5. ログディレクトリ:
   - デフォルトで `logs/` に出力します。環境変数 LOG_DIR で変更可能。
   - ログレベルは LOG_LEVEL（例: INFO, DEBUG）

---

## 使い方

主要なエントリポイント（モジュールとして実行）:

- Execution Engine を起動

  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV により振る舞いが変わります。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。

  ```
  python -m kabusys.run_execution
  ```

  実行前に stop フラグ file（data/stop_requested.flag）が存在すると起動をスキップします。Execution の PID はデフォルトで data/execution.pid に書き込まれます（Settings.pid_file_path で変更可）。

- Monitoring（ポーリング監視）を起動

  - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用します。

  ```
  # 例: 30秒間隔で監視
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 設定ウィザード

  ```
  python -m kabusys.config_setup
  ```

- 設定検証

  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）

  ```
  # デフォルト DB または環境変数 PAPER_TRADING_SQLITE_PATH を使用
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB を直接指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（プログラム API）
  - OpenAI を用いたニューススコアリングやレジーム判定はモジュール関数を呼び出して使用します（例: kabusys.ai.score_news）。
  - API キーは引数で渡すこともできますが、環境変数 OPENAI_API_KEY を設定しておくのが簡便です。

注意・補足:

- kill.flag（Settings.kill_flag_path のデフォルトは data/kill.flag）を作成すると ExecutionEngine に停止シグナルを送る仕組みがあります（KillSwitch）。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では推奨されません。
- Monitoring 側で stop を検知するために data/stop_requested.flag を使用します（run_* スクリプトと整合）。

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログ出力レベル（例: INFO）
- LOG_DIR: ログファイル出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）

---

## よくあるトラブルと対処

- OpenAI API キーがない／未設定:
  - AI 機能（news_nlp, regime_detector）実行時に ValueError が発生します。OPENAI_API_KEY を設定してください。
- 必須環境変数未設定:
  - validate_config を実行してエラー・警告を確認してください。
- DuckDB / SQLite ファイルの親ディレクトリがない:
  - validate_config が警告を出します。自動作成される場合もありますが、手動で data/ や logs/ を作成しておくと安全です。
- psutil 関連の権限エラー:
  - set_process_priority で権限不足の警告が出ますが、致命的ではありません。必要に応じて実行権限を高める（root など）かスキップしてください。

---

## ディレクトリ構成

（抜粋）

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                 # 環境変数・設定読み取り
   ├─ config_setup.py           # .env 対話ウィザード
   ├─ validate_config.py        # 起動前の設定検証 CLI
   ├─ run_execution.py          # Execution エントリポイント
   ├─ run_monitoring.py         # Monitoring エントリポイント
   ├─ utils/
   │  ├─ logging_setup.py       # ログ設定ユーティリティ
   │  └─ process_priority.py    # プロセス優先度 / CPU affinity
   ├─ monitoring/
   │  ├─ monitoring_db.py       # SQLite 永続化層
   │  ├─ system_monitor.py
   │  ├─ trade_monitor.py
   │  ├─ risk_monitor.py
   │  ├─ kill_switch.py
   │  └─ monitoring_engine.py
   ├─ execution/
   │  ├─ execution_engine.py
   │  ├─ order_manager.py
   │  ├─ order_repository.py
   │  ├─ broker_factory.py
   │  └─ ...                    # 発注系
   ├─ portfolio/
   │  ├─ portfolio_builder.py
   │  ├─ position_sizing.py
   │  └─ risk_adjustment.py
   ├─ research/
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   ├─ ai/
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   ├─ tools/
   │  └─ paper_verification_report.py
   └─ data/                      # 実行時に使用するファイル（DB、flag 等）
```

---

## 開発メモ / 重要な設計注意点

- Monitoring の DB 初期化（init_monitoring_db）は冪等であり、既存スキーマへのマイグレーション（カラム追加）も行います。
- ペーパートレードは本番データと完全に分離されるよう設計されています（別 SQLite ファイル）。
- AI 関連は OpenAI のレスポンス壊れに備えた堅牢な処理（リトライ、パース保護、部分成功の DB 保護）を実装しています。
- ログはコンソール出力（stdout）と日次ローテートファイルに出力されます。ログディレクトリ作成に失敗した場合はファイル出力はスキップされますがコンソール出力は行われます。

---

この README はコードベース（src/kabusys 以下）を参照して作成しています。実運用前には必ず `python -m kabusys.validate_config` で設定を確認し、.env の値（特に本番環境用の秘密情報）を適切に管理してください。必要であれば README の補足・手順追加を行います。