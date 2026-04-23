# KabuSys

軽量な日本株自動売買システム（ライブラリ + 実行スクリプト群）  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行（本番／ペーパートレード分離）・監視・AI 補助（ニュース NLP / レジーム判定）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

- 株取引の戦略・ポートフォリオ構築（pure functions）
- ExecutionEngine による発注ロジック（本番 / ペーパートレード切替）
- 監視サブシステム（System / Trade / Risk Monitor）と Kill Switch
- DuckDB / SQLite を使ったデータ解析・ログ永続化
- OpenAI を用いたニュースセンチメント（news_nlp）と市場レジーム判定
- 各種 CLI（.env ウィザード、設定検証、レポート生成）

設計方針として、ルックアヘッドバイアス回避、部分失敗時のフェイルセーフ、環境分離（paper_trading 用 DB）を重視しています。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証ツール（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、data/paper_trading.db に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - 定期的にシステム・注文・リスクをチェックし kill.flag を書き込む等の処理を実行
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）
- ニュース NLP スコアリング（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- ポートフォリオ構築ユーティリティ（kabusys.portfolio.*）
- 研究用ファクター計算 / 特徴量解析（kabusys.research.*）

---

## 前提（推奨環境）

- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML を検証したい場合に必要）
- OS: Linux / macOS / Windows（プロセス優先度制御や CPU affinity は OS により挙動が異なります）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトの requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成し依存パッケージをインストール
3. .env を作成（対話式ウィザード推奨）

対話式で .env を作成:
```bash
python -m kabusys.config_setup
```

自動ロードについて:
- パッケージ読み込み時にプロジェクトルートを検出できれば `.env` および `.env.local` が自動的に読み込まれます（OS 環境変数が優先）。
- テスト等で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env に設定する主要な環境変数（例・説明）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (news_nlp / regime_detector を使う場合必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード DB、デフォルト: data/paper_trading.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
- PAPER_FILL_MODE (paper_trading 時のモック約定モード: instant|partial|never|reject)

---

## 設定検証

作成した .env / config/*.yaml を検証:
```bash
python -m kabusys.validate_config
# 警告をエラー扱いにする（CI 等）
python -m kabusys.validate_config --strict
```

PyYAML がインストールされていない場合、YAML 内容検証はスキップされます（警告が出ます）。

---

## 使い方（主要 CLI / スクリプト）

- ExecutionEngine を起動（本番 / ペーパートレードの切替は KABUSYS_ENV で行う）:
```bash
python -m kabusys.run_execution
```
- Monitoring を起動（監視ループ。MONITOR_POLL_INTERVAL で間隔指定可能）:
```bash
# デフォルト 60 秒
python -m kabusys.run_monitoring

# 環境変数でオーバーライド
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

停止・フラグ関連:
- 監視・実行ループの外部停止にはプロジェクトの data/stop_requested.flag を作成します（run_* スクリプトは起動時の親パスから data/stop_requested.flag を参照してループを終了します）。
- Kill Switch（監視がリスク閾値を検出した場合に書き込む）: Settings.kill_flag_path のデフォルトは data/kill.flag。Monitoring は条件を満たすとこのファイルを書き、ExecutionEngine 側で検出して停止する設計です。
- run_execution は起動時に kill/stop フラグを確認します。起動時に kill を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START を設定できますが、本番では 0 を強く推奨します。

ログ:
- ログはデフォルト `logs/` に出力されます（ログ名は app_name: execution.log, monitoring.log 等）。
- LOG_DIR 環境変数で出力先を変更可能。
- ログ出力は daily ローテーション（30 日保持）とコンソール出力（stdout）を両方行います。

Paper Trading レポート:
```bash
# レポート生成（期間指定可能）
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パス指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

AI 機能（OpenAI API キーが必要）:
- ニュース NLP（ai_scores テーブルへ書き込み）:
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - CLI のラッパーはありませんが、スクリプトやジョブから呼び出して利用できます。
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 開発 / デバッグノート

- Settings は環境変数から値を読み取ります。Settings クラスは .env 自動ロード機構を内蔵しています（プロジェクトルート検出に `.git` または `pyproject.toml` を利用）。
- 自動ロードを無効にする場合: `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- ロギングを統一するため、各起動スクリプトは kabusys.utils.logging_setup.setup_logging(app_name=...) を呼び出します。
- プロセス優先度や CPU affinity は psutil を使って設定しますが、権限や OS により失敗することがあります（警告ログのみ）。

---

## 主要ファイル / ディレクトリ構成

（抜粋）src/kabusys の内部構成:

- kabusys/
  - __init__.py                # バージョン、パッケージ公開 API
  - config.py                  # 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py            # .env 対話ウィザード CLI
  - validate_config.py         # 設定検証 CLI
  - run_execution.py           # ExecutionEngine 起動スクリプト
  - run_monitoring.py          # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  # Paper Trading レポート生成 CLI
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              # ニュース NLP（OpenAI）
    - regime_detector.py       # 市場レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py         # SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py         # （アラート送信ロジックがあればここ）
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで作成されることが多い)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kill.flag, stop_requested.flag, execution.pid

（実際のリポジトリには上記以外のモジュール・実装が含まれます。ここは主要ファイルの概要です）

---

## よくある質問 / 注意点

- Q: ペーパートレードと本番 DB は分離されていますか？  
  A: はい。KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。監視 DB（monitoring.db）は監視用に別途使われます。

- Q: OpenAI を使うには？  
  A: OPENAI_API_KEY を .env に設定してください。news_nlp や regime_detector は API 呼び出しでキーを参照します。API 呼び出しはリトライやフェイルセーフを備えていますが、未設定の場合は関数が例外を投げます。

- Q: 監視のポーリング間隔を変えたい  
  A: MONITOR_POLL_INTERVAL 環境変数（秒）を設定してください（1 以上の整数）。不正値はデフォルト（60 秒）にフォールバックします。

- Q: 監視／実行を終了させる方法は？  
  A: run_* スクリプトは data/stop_requested.flag の存在を監視して安全に終了します。kill.flag は監視により書き込まれ、ExecutionEngine の停止トリガーになります。

---

## 参考 / 次のステップ

1. .env を作成（python -m kabusys.config_setup）
2. 設定の検証（python -m kabusys.validate_config）
3. 必要なデータベース（data/）ディレクトリを作成
4. まずは開発モード（KABUSYS_ENV=development）でユニットテスト・個別関数を実行
5. ペーパートレードでフルフローを検証（KABUSYS_ENV=paper_trading）
6. 本番移行時は KABUSYS_ENV=live にし、LINE 通知等の設定を確認

---

この README はリポジトリ内のドキュメント代替ではなく概要です。各モジュールの docstring に詳細設計や挙動の注記が含まれているため、実装を変更する際は該当モジュールの docstring を参照してください。