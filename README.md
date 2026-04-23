# KabuSys

日本株向け自動売買システムの Python コードベース（モジュール群）の README。  
本ドキュメントはリポジトリ内の主要スクリプト・モジュールを基に、導入・実行方法や各コンポーネントの概要を日本語でまとめたものです。

注意: この README はソースコードからの抜粋に基づく説明です。実行時は必ず .env を作成し、設定検証ツールで問題がないことを確認してください。

---

## 概要

KabuSys は日本株の自動売買および研究（ファクター計算・ポートフォリオ構築）を行うためのライブラリ／ランタイム群です。主要な要素は次のとおりです。

- ExecutionEngine（発注・注文管理・リスク管理） — run_execution.py で起動
- Monitoring（システム監視・トレード監視・Kill Switch） — run_monitoring.py で起動
- 研究モジュール（ファクター計算・特徴量探索）
- ポートフォリオ構築（候補選定・重み付け・ポジション決定）
- AI モジュール（ニュース NLP によるセンチメント / レジーム判定）
- SQLite / DuckDB によるデータ永続化・分析
- ユーティリティ（ログ設定・プロセス優先度設定など）

設計方針の一部：
- 本番とペーパートレードの DB を明確に分離（KABUSYS_ENV により切替）
- ルックアヘッドバイアスの回避（date.today() を直接参照しない箇所あり）
- フェイルセーフ：API 呼び出し失敗時は安全側のデフォルトで継続

---

## 主な機能一覧

- 実行環境起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動
  - python -m kabusys.run_monitoring : SystemMonitor を起動（ポーリング）
- 設定管理
  - config_setup.py : .env を対話式に作成・更新するウィザード
  - validate_config.py : 環境設定・config/*.yaml の事前検証ツール
- 監視
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine
  - kill_switch: ドローダウン等で `data/kill.flag` を書き込み Execution を停止可能
- 研究・分析
  - research.factor_research : momentum / volatility / value 等のファクター計算（DuckDB）
  - research.feature_exploration : 将来リターン計算、IC、統計サマリ
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定・重み計算
  - portfolio.position_sizing: 株数（ロット）算出・aggregate cap 処理
  - portfolio.risk_adjustment: セクター上限・レジーム乗数
- AI（LLM）支援
  - ai.news_nlp.score_news : ニュースから銘柄別センチメントを生成して ai_scores に保存
  - ai.regime_detector.score_regime : ETF の MA とマクロニュースで市場レジーム判定
- ツール
  - tools.paper_verification_report : ペーパートレード DB から検証レポート生成

---

## 前提 / 必要環境

- Python 3.10 以上（型ヒントに `X | None` を使用）
- 必要な Python パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- SQLite は標準ライブラリで提供

インストール例（仮想環境を推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用してください）

---

## セットアップ手順

1. レポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはルートに `.env` を作成して必要な環境変数を設定
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗として扱う
5. 必要なディレクトリ作成（通常はスクリプトで自動作成されますが、事前に用意する場合）:
   - data/ （SQLite ファイル、フラグファイル用）
   - logs/ （ログファイル出力先）
6. OpenAI を利用する場合は `OPENAI_API_KEY` を設定

---

## 主な環境変数（代表例）

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用関連
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）

- データベース
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）

- ペーパートレード
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで必要）

- その他
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  # strict モード（警告で exit(1)）
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（発注エンジン）
  - 本番 / 開発は KABUSYS_ENV に依存
  ```
  python -m kabusys.run_execution
  ```
  - paper_trading 用に分離された DB に記録する: KABUSYS_ENV=paper_trading を設定
  - 実行中は data/execution.pid が作成されます
  - 停止は data/stop_requested.flag の作成でスレッドを停止するか、Kill Switch により data/kill.flag が作成されると停止します

- Monitoring（ポーリング）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（環境に関わらず本番監視 DB を見る設計）
  - 停止: data/stop_requested.flag を作成

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（プログラムから呼び出す）
  - ニュース NLP（スコア書き込み）
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 20), api_key="あなたのAPIキー")
    ```
  - レジーム判定
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 20), api_key="あなたのAPIキー")
    ```

---

## 停止・Kill Switch の仕組み

- run_execution / run_monitoring はそれぞれ `data/stop_requested.flag` を監視しており、ファイルが存在すると安全に終了します。
- KillSwitch（監視側）はドローダウンやポジション過剰などの条件を満たすと `data/kill.flag` に理由を書き込み、ExecutionEngine 側で検出して停止動作を行います。
- 本番環境では `KILL_FLAG_CLEAR_ON_START=0`（デフォルト推奨）にして、自動クリアを無効にしてください。

---

## ディレクトリ構成（主要ファイル・モジュール）

以下はリポジトリ内 src/kabusys の主要ファイルと簡単な説明です（抜粋）:

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数/.env 読み込み・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ（Stream + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/Disk/データ鮮度/プロセス監視
    - trade_monitor.py — （注文滞留・約定異常等のチェック）
    - risk_monitor.py — ドローダウン監視・ポジション上限監視
    - kill_switch.py — kill.flag の読み書き
    - monitoring_engine.py — 各 Monitor の統合ポーリング
    - alert_manager.py — （LINE などへの通知管理）
  - execution/  (発注処理群)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py — 候補選定・重み
    - position_sizing.py — 株数算出・スケーリング・ロット丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum, volatility, value ファクター計算（DuckDB）
    - feature_exploration.py — forward returns, IC, 統計サマリ
  - ai/
    - news_nlp.py — raw_news を LLM でスコア化し ai_scores へ書き込み
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - data/ （ランタイムで使用される想定ディレクトリ）
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード用、KABUSYS_ENV=paper_trading）
    - kill.flag / stop_requested.flag / execution.pid などのフラグ・PID ファイル
  - logs/ （ログ出力、setup_logging により作成）

---

## 実践上の注意点

- .env は絶対にコミットしない（機密情報を含む）。
- 本番（KABUSYS_ENV=live）では LINE 通知設定や Kill Switch 設定を必ず確認すること。
- OpenAI を使用する処理は API コスト・レート制限に注意する（リトライ実装はあるが上限あり）。
- DuckDB / SQLite のパスとログディレクトリは .env / config によって調整可能。ログ出力先が作成できない場合はコンソールのみの出力になります。
- ペーパートレードは本番 DB と完全分離される（設定に従って PAPER_TRADING_SQLITE_PATH を使用）。

---

## 開発・テスト

- モジュールは比較的純粋関数が多く設計されており、ユニットテストの実装が容易です（DB をモック/一時ファイルで切り替えてテスト）。
- AI 呼び出しや外部 API 呼び出し箇所はテストでパッチしやすいよう分離されている（例: _call_openai_api を patch）。

---

本文書に書ききれなかった細かい実装仕様や API（ExecutionEngine の挙動・OrderRepository のスキーマ等）はソースコードの docstring / コメントを参照してください。追加で README に載せたいサンプル .env テンプレートや起動例（systemd ユニット / Dockerfile など）が必要であれば作成します。希望があれば教えてください。