# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株自動売買システム KabuSys のコアモジュール群です。  
主に以下の機能を含み、ローカル開発・ペーパートレード・本番運用の各モードに対応します。

- シグナル生成・ポートフォリオ構築・ポジションサイズ算出（portfolio）
- 実際の発注実行エンジン（ExecutionEngine）と発注ログ管理（paper_trading 時はモック）
- 監視（System / Trade / Risk）と Kill Switch 機構
- 研究用ファクター計算・特徴量解析（research）
- ニュース NLP / 市場レジーム判定（OpenAI を利用する AI モジュール）
- 環境設定ウィザード / 設定検証 / ツール（設定ファイル生成、ペーパートレード検証レポート等）
- ロギング・プロセス優先度等のユーティリティ

---

## 主な機能一覧

- 環境管理
  - .env の自動読み込み / 対話式ウィザード（kabusys.config_setup）
  - 起動前検証ツール（kabusys.validate_config）

- 実行・監視
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading DB に記録（本番 DB と分離）
  - Monitoring 起動スクリプト（kabusys.run_monitoring）
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒）
  - Kill Switch（データベースやリスク条件による停止フラグ書き込み）
  - 監視 DB（SQLite）用永続化層（monitoring_db）・アラート連携

- ポートフォリオ構築（純粋関数）
  - 候補選定 / 等金額・スコア重み / セクター上限 / レジーム乗数 / 株数計算（lot 単位の丸め、aggregate cap）

- 研究・分析
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン / IC（Information Coefficient）算出・特徴量要約

- AI（OpenAI 経由）
  - ニュースセンチメント集約・スコアリング（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
  - API 呼び出しはリトライ・バリデーション・フェイルセーフを備える

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

- ユーティリティ
  - 統一ログ設定（logs/<app>.log、日次ローテーション、デフォルト保持 30 日）
  - プロセス優先度 / CPU アフィニティ設定ユーティリティ

---

## セットアップ手順（開発向け）

前提:
- Python 3.10 以上（PEP 604 の型記法 `X | Y` を使用）
- SQLite は標準搭載
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - （検証で YAML を使う場合）PyYAML

例: 仮想環境作成とパッケージインストール
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai
# 任意: pip install pyyaml
```

環境変数の初期化（対話式）
```
python -m kabusys.config_setup
```
- 対話ウィザードで .env を生成します（デフォルトはプロジェクトルートの `.env`）。
- `.env` は機密情報を含むため、絶対に Git にコミットしないでください。

設定検証（起動前チェック）
```
python -m kabusys.validate_config
# 警告も失敗扱いにしたい場合:
python -m kabusys.validate_config --strict
```

ログディレクトリ作成は自動で行われます（デフォルト: logs/）。必要に応じて環境変数 `LOG_DIR` を設定してください。

---

## 使い方（主要コマンド例）

- ExecutionEngine を起動
  - Paper Trading（モックブローカー、専用 DB に記録）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 本番 / 開発
    ```
    KABUSYS_ENV=development python -m kabusys.run_execution
    KABUSYS_ENV=live python -m kabusys.run_execution  # 本番時は注意して実行
    ```

- Monitoring を起動
  - デフォルトポーリング間隔 60 秒。環境変数で変更可:
    ```
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

- Paper Trading 検証レポート（任意期間）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # デフォルト DB は data/paper_trading.db。別ファイルを使う場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール呼び出し（スクリプト内 API）
  - OpenAI API を利用する機能を実行するには `OPENAI_API_KEY` を環境変数に設定してください。
  - 例（Python から）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

停止方法:
- ランタイムの即時停止: キーボード割込み（Ctrl+C）
- Graceful 停止（run_execution / run_monitoring がチェックするフラグ）
  - プロジェクトルートの `data/stop_requested.flag` を作成するとループを抜けます。
  - Kill Switch（自動的に `data/kill.flag` を書き込む）により ExecutionEngine を停止させる運用も可能です。

ログ:
- 標準出力（stdout）にログが出ます。ファイルはデフォルト `logs/<app_name>.log` に日次ローテーションで保存されます。

---

## 主な環境変数（抜粋）

- 基本
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
  - LOG_DIR: ログファイル保存先（任意）

- データベース
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）

- API / 認証
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI機能を使う場合）

- モード / 実行制御
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）。run_monitoring で使用（デフォルト 60）。
  - PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア）

---

## ディレクトリ構成（主なファイル）

以下はこの README 作成時点での主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP / OpenAI ラッパー
    - regime_detector.py      — 市場レジーム判定（OpenAI）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py         # （trade_monitor の詳細はここでは省略）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         # （実際の通知ロジックはここにある想定）
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py

data/ と logs/ はランタイムで生成・利用されます:
- data/
  - monitoring.db (デフォルト)
  - paper_trading.db (paper mode)
  - kill.flag / stop_requested.flag / execution.pid などの制御ファイル
- logs/
  - execution.log, monitoring.log, ... （日次ローテーション）

---

## 運用上の注意点

- .env は機密情報を含みます。必ず .gitignore に登録してリポジトリへコミットしないでください。
- KABUSYS_ENV=live（本番）で実行する場合は、JQUANTS / kabu API 情報や通知設定（LINE）を十分に確認してください。
- Monitoring は監視用 SQLite を参照します。run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する点に注意してください（監視は本番設定を前提）。
- OpenAI 利用部分は API コストとレート制限を考慮してください。API 失敗時はフェイルセーフとして一部機能はデフォルト値で継続しますが、ポリシーと課金に注意してください。
- プロセス優先度や CPU affinity の設定は OS 権限やプラットフォーム依存のため、設定に失敗する場合は警告ログが出ます（起動は中断されません）。

---

## 開発者向けメモ

- 主要関数やクラスは純粋関数設計（副作用をなるべく排除）で書かれている箇所が多く、ユニットテストを書きやすい構造になっています（例: portfolio/*.py, research/*.py）。
- DuckDB を使った集計・調査処理は SQL と Python の組み合わせで実装されています。テスト時は DuckDB のメモリ DB を使うと高速に検証できます。
- AI モジュールの外部 API 呼び出し部分は個別の内部関数でラップしており、テスト時はそれらをモックしやすく設計されています。

---

ご不明点があれば、どのコマンドや機能について詳しく知りたいか教えてください。README の内容を追記・調整します。