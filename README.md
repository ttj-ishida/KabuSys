# KabuSys

日本株向け自動売買システムのリポジトリ（読み取り専用のミニマム実装群）。  
この README はリポジトリ内の主要スクリプト・モジュールを対象に、導入・起動方法、構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- Execution Engine：発注ロジック、注文管理、ブローカークライアント（実運用/ペーパートレード切替）
- Monitoring：システム稼働監視、注文ログ・リスク監視、Kill Switch によるエンジン停止
- Portfolio construction：銘柄選定・配分・ポジションサイズ計算（純粋関数群）
- Research：ファクター計算・特徴量探索、IC 等の計算（DuckDB を用いる）
- AI モジュール：ニュース NLP によるセンチメント評価、レジーム判定（OpenAI を使用）
- ツール：ペーパートレードの検証レポート生成スクリプト 等
- 設定ユーティリティ：.env の対話式生成（config_setup）、起動前チェック（validate_config）

設計方針の一部：
- 本番とペーパートレードの DB は分離（PAPER_TRADING_SQLITE_PATH）
- DuckDB は分析用（prices_daily, raw_financials 等の読み取り）
- LLM 呼び出しは耐障害に配慮（リトライ・フェイルセーフ）
- 可能な限りルックアヘッドバイアスを避ける実装（date/today を直接参照しない等）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading DB に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - システム状態、注文ログ、リスク監視をポーリング
  - MONITOR_POLL_INTERVAL で間隔を制御（デフォルト 60 秒）
- AI:
  - kabusys.ai.score_news: raw_news を LLM（OpenAI）でスコア化して ai_scores に書込
  - kabusys.ai.regime_detector: マクロ＋MA200 から日次レジーム判定を書込
- Research:
  - calc_momentum / calc_volatility / calc_value：DuckDB の価格・財務データからファクターを計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量評価ツール群
- Portfolio:
  - 候補選定、重み計算、リスク調整、株数算出（等金額・スコア・リスクベース）
- Tools:
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 必要条件（推奨）

- Python 3.10+
- 必須パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に YAML 検査を行う場合）
- （開発）pip install -e . または必要パッケージを個別にインストール

例:
```
pip install duckdb psutil openai PyYAML
```

※ requirements.txt が無い場合、上記を参考に必要なライブラリをインストールしてください。

---

## セットアップ手順

1. レポジトリをクローン / 取得
2. Python 環境を作成（venv 等）
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードで作成された `.env` は絶対に Git にコミットしないでください（認証情報を含む）。
   - もしくは `.env.example` を参考に手動で `.env` を作成
5. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   問題がある場合はメッセージに従って修正。--strict を付けると警告も fail 扱いになります。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意/重要:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker + data/paper_trading.db を使用（本番 DB と分離）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI モジュール使用時）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用 DB）
- PAPER_FILL_MODE: instant / partial / never / reject（ペーパートレードの約定挙動）
- LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）
- LOG_DIR: ログ出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか (0/1)

自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動読み込みします。自動ロードを無効化するには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 使い方（代表的なコマンド）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution Engine 起動
  - ペーパートレード:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    → MockBroker を使い、PAPER_TRADING_SQLITE_PATH にデータ記録（本番 DB と分離）
  - 本番（慎重に）:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更:
    ```
    MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
    ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
  ```
  `--db` で DB パス指定可（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

---

## 停止・Kill Switch の扱い

- run_monitoring / run_execution はどちらもプロジェクトの data ディレクトリにあるフラグファイルをチェックして停止します。
  - stop_requested.flag（手動停止指示）：両プロセスのループを安全に終了させるためのフラグ（スクリプトはこのファイルの存在でループを抜けます）
  - kill.flag：Monitoring の KillSwitch により生成され、ExecutionEngine を停止させる（致命的リスク検出時）
- ExecutionEngine の PID ファイル: data/execution.pid（プロセス管理用途）
- 起動時に kill.flag を自動的にクリアしたくない場合は KILL_FLAG_CLEAR_ON_START=0 を推奨（本番）

---

## ロギング

- 共通のロギング設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler） + 日次ローテーティングファイル（logs/<app_name>.log）
  - LOG_DIR 環境変数や引数でログディレクトリを変更可能
  - ディレクトリ作成に失敗した場合はコンソールログのみで継続

---

## 開発上の注意点 / 補足

- DuckDB 接続は分析用。prices_daily / raw_financials / raw_news 等のテーブルを参照する想定。
- AI（OpenAI）呼び出しは API キーが必要。呼び出しはリトライやエラーハンドリングを実装。
- 各モジュール（portfolio, research 等）は副作用を持たない純関数群として設計されている箇所が多く、単体テストが容易です。
- process priority / CPU affinity は kabusys.utils.process_priority 経由で設定（psutil 必須）。
- .env の自動ロードはプロジェクトルートの検出に .git または pyproject.toml を用いるため、パッケージ化後でも動作するように設計されています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（自動 .env ロード）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム監視（CPU/メモリ/ディスク、データ鮮度）
    - trade_monitor.py — （注文監視）※ソースに依存する処理あり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成/管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — LINE 等へ通知するモジュール（実装参照）
  - execution/ (発注関連の実装が入る)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py — ニュースを LLM でスコア化
    - regime_detector.py — レジーム判定
    - __init__.py
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - data/ — 実行時に使用する sqlite / pid / flag ファイル等（デフォルトパス）

---

## よくある運用フロー（例）

1. .env 作成（config_setup）
2. validate_config で事前チェック
3. 分析用 DuckDB / prices データを準備
4. KABUSYS_ENV=paper_trading で run_execution を起動（ローカルで検証）
5. run_monitoring を別プロセスで起動して監視・Kill Switch を有効化
6. 検証結果は tools/paper_verification_report で集計

---

必要であれば、インストール向けの requirements.txt や systemd / supervisor 用のサービス定義サンプル、詳しい設定項目一覧（.env.example 相当）を追加で作成します。どの情報を優先して追加しますか？