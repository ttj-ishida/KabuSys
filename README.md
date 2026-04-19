# KabuSys

日本株向けの自動売買システム（リサーチ・ポートフォリオ構築・発注・監視・AI アシスト）です。  
このリポジトリには、Execution Engine（発注実行）、Monitoring（監視）、Research（ファクター計算 / 分析）、Portfolio（銘柄選定・サイズ計算）、AI モジュール（ニュース NLP / レジーム判定）、および各種ユーティリティ・ツールが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の要素で構成される自動売買基盤のプロジェクトです。

- データベース
  - DuckDB: 分析・ファクター計算（デフォルト `data/kabusys.duckdb`）
  - SQLite: 監視ログ / 発注ログ（デフォルト `data/monitoring.db`、ペーパートレード用は `data/paper_trading.db`）
- ExecutionEngine: 実際の発注処理（kabuステーション や MockBroker を使用）
- Monitoring: システム健全性 / 注文状況 / リスクの定期監視とアラート発行、Kill Switch
- Research: ファクター計算、特徴量探索、IC 計算など（DuckDB を利用）
- Portfolio: 候補選定、重み算出、ポジションサイズ計算、セクターキャップ／レジーム調整
- AI モジュール: OpenAI を用いたニュースセンチメント（ai.score_news）、レジーム判定（ai.score_regime）
- ユーティリティ: ログ設定、プロセス優先度、環境設定ウィザード、設定検証ツール、ツールスクリプト（ペーパートレード検証レポート）

設計上の特徴:
- .env ファイルの自動読み込み（プロジェクトルートの `.env` / `.env.local`、OS 環境変数を優先）
- 設定検証 CLI（設定不足・危険な本番設定の検出）
- Monitoring は環境（development / paper_trading / live）にかかわらず本番の SQLite パスを使用して監視を行う（実行スクリプトにより挙動が異なる部分あり）
- AI 呼び出しは外部キー（OPENAI_API_KEY）が必要。失敗時はフェイルセーフで続行する実装が多い

---

## 主な機能一覧

- Execution
  - 実口座（kabuステーション）とペーパートレード（MockBroker）を切り替えて実行
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカー等）
- Monitoring
  - CPU / メモリ / ディスク / Execution プロセス監視
  - 注文ログ監視（滞留注文、約定異常、レイテンシ）
  - リスク監視（ドローダウン、ポジション上限）と Kill Switch（`data/kill.flag`）
  - アラート通知（LINE など：未設定時は無効）
- Portfolio
  - 候補選定、等金額・スコア加重、リスクベースのポジションサイズ計算
  - セクター集中の除外（apply_sector_cap）、レジームに基づく投入資金スケール
- Research
  - モメンタム、ボラティリティ、バリュー等ファクターの DuckDB ベース計算
  - 将来リターン、IC、統計サマリ等
- AI
  - ニュース記事を LLM（gpt-4o-mini）でセンチメント化して ai_scores に保存
  - ETF の MA とマクロニュースを用いた市場レジーム判定
- 管理ツール
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - ペーパートレード検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）

---

## 必要要件（推奨）

- Python 3.10 以上（型ヒントや一部モダン API を使用）
- 必要 Python パッケージ（最低限）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証用：任意）
- SQLite は標準ライブラリで利用可

pip の requirements ファイルはリポジトリに含まれていない場合があります。仮に手動でインストールする例:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリへ移動

2. 仮想環境の作成（任意だが推奨）

3. 必要パッケージをインストール（上記参照）

4. 環境変数設定
   - 対話式ウィザードで .env を生成:
     ```bash
     python -m kabusys.config_setup
     ```
     生成された `.env` をプロジェクトルートに保存してください（.env は Git にコミットしないでください）。
   - あるいは環境変数を直接設定してください。必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     （.env.example がある場合は参照してください）

5. 設定検証（推奨）
   ```bash
   python -m kabusys.validate_config        # 警告は OK
   python -m kabusys.validate_config --strict  # 警告も失敗として扱う
   ```

6. データディレクトリの準備
   - デフォルトの DB やログディレクトリは `data/` と `logs/`。起動時に自動作成されますが、権限等で失敗する場合は手動で作成してください。

---

## 環境変数（主要）

（一部のみ抜粋、詳細は config_setup ウィザードを参照）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 専用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR）
- OPENAI_API_KEY（AI 機能を使用する際に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア）

ログ出力先デフォルト: logs/<app_name>.log

---

## 使い方（主要スクリプト）

実行スクリプトはモジュールとして起動できます。

- 実行エンジン（Execution Engine）起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV により切替
  - ペーパートレード時は MockBroker を使い、`data/paper_trading.db` を使用（本番 DB と完全分離）
  ```bash
  # ペーパートレード例
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  # 本番（注意して使用）
  KABUSYS_ENV=live python -m kabusys.run_execution
  ```

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します
  ```bash
  python -m kabusys.run_monitoring
  # 例: 30 秒間隔
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼び出す）
  - ニュース NLP（指定日分をスコアリングして ai_scores テーブルへ書き込み）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect('data/kabusys.duckdb')
    n = score_news(conn, target_date=date(2026, 4, 10), api_key='sk-XXXX')
    print(f"scored {n} codes")
    ```
  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    # duckdb 接続を渡して利用
    ```

- 停止 / Kill Switch
  - Monitoring の KillSwitch は条件を満たすと `data/kill.flag` を書き込みます。ExecutionEngine 側はこれを監視して停止します（設定による）。
  - 手動で停止シグナルを送るなら `data/kill.flag` を作成してください（通常は監視が自動で作成する）。

---

## ロギング

- 共通の logging セットアップ関数: `kabusys.utils.logging_setup.setup_logging(app_name="execution")`
- デフォルトログディレクトリ: `logs/`
- 日次ローテーション（30 日分保持）
- コンソール出力は stdout（cron 等のリダイレクトに配慮）

ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソールのみで出力されます。

---

## ディレクトリ構成

（主なファイル／パッケージのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / .env の読み込みと Settings
  - config_setup.py                   — .env 対話式ウィザード
  - validate_config.py                — 設定検証 CLI
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py    — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py              — 市場レジーム判定（AI 合成）
  - research/
    - __init__.py
    - factor_research.py              — momentum/value/volatility 等
    - feature_exploration.py          — forward returns / IC / summary
  - portfolio/
    - __init__.py
    - portfolio_builder.py            — 候補選定、等分/スコア重み
    - position_sizing.py              — 株数計算・スケールダウン・ロット丸め
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py                — SQLite 用永続化層
    - system_monitor.py               — CPU/メモリ/データ鮮度監視
    - trade_monitor.py (参照)         — 注文監視（ファイル内参照あり）
    - risk_monitor.py                 — ドローダウン・ポジション数監視
    - monitoring_engine.py            — 監視を束ねるエンジン
    - kill_switch.py                  — kill.flag 書き込みユーティリティ
    - alert_manager.py (参照)         — 通知処理（LINE など）
  - utils/
    - logging_setup.py                — ログ共通設定
    - process_priority.py             — プロセス優先度 / CPU アフィニティ
  - execution/                        — 発注周りの実装（BrokerFactory, Engine, OrderManager 等）
  - data/                             — データパイプライン / DB 操作用モジュール（prices_daily 等）

注意: ここに示したファイル群はコードベースの一部を抜粋したものです。パッケージ内で更に細分化されたファイルが存在します。

---

## 注意点 / トラブルシューティング

- 実行時に psutil のプロセス優先度設定で権限不足になることがあります（特に nice 値や Windows の優先度設定）。エラーは WARN ログで無視され、処理は継続します。
- DuckDB / SQLite のファイルパスは `.env` または環境変数で調整可能。監視はデフォルトで `SQLITE_PATH` を使用するため、監視対象 DB を分離したい場合は設定を確認してください。
- OpenAI を利用する機能は API キーが必須です。API コールはリトライ処理やフェイルセーフ実装があるものの、API 利用料が発生します。
- 本番（KABUSYS_ENV=live）での起動は十分に注意してください。`validate_config` は本番特有の危険設定（kill flag の自動クリア等）を警告します。

---

この README はコード中の docstring / コメントを元にまとめた概観です。各モジュールの詳細な挙動や拡張方法については該当ファイルの docstring を参照してください。必要であれば、導入手順の細分化（systemd / Docker / CI 用のセットアップ例）も追加できます。