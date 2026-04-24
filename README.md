# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買基盤「KabuSys」のコードベースです。  
本 README はコードを参照して作成した簡易ドキュメントで、起動スクリプト・設定・ツールの利用方法とディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は以下のような責務を持つコンポーネント群から構成されています。

- データ取得・分析（DuckDB を用いたファクター計算やリサーチ）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算）
- ExecutionEngine（実際の発注またはペーパートレード用の発注処理）
- 監視（System / Trade / Risk の定期チェック、Kill Switch）
- AI モジュール（OpenAI を用いたニュースセンチメント評価・レジーム判定）
- 開発補助ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

設計上のポイント：
- 本番環境とペーパートレードのデータは分離（paper_trading 用 SQLite）
- DuckDB を分析向けに使用
- モジュールは可能な限り純粋関数（副作用を最小化）で実装
- LLM 呼び出しはフェイルセーフ（API失敗時はゼロフォールバック等）

---

## 主な機能一覧

- 環境設定ウィザード（config_setup）
  - 対話式で `.env` を作成 / 更新
- 設定検証 CLI（validate_config）
  - .env と config/*.yaml の整合性チェック
- ExecutionEngine 起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて本番/ペーパートレード動作
  - 停止はフラグファイル（data/stop_requested.flag / data/kill.flag）で制御
- Monitoring（run_monitoring / monitoring engine）
  - システム・注文・リスクの定期チェック、Kill Switch 評価、アラート連携
- AI モジュール
  - news_nlp: OpenAI でニュースを評価し ai_scores に書き込み
  - regime_detector: マクロ + ETF MA200 を合成して市場レジームを判定
- リサーチ機能（research）
  - ファクター計算（Momentum / Volatility / Value）、IC 計算、統計サマリ
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム補正
- ツール
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポートを出力

---

## 前提 / 必要要件

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の内容検証用）
- SQLite（標準ライブラリで利用可能）
- ネットワークアクセス（kabuステーション API / OpenAI を使用する場合）

pip での例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実際の requirements.txt がないため、プロジェクトで必要なパッケージを適宜追加してください。

---

## 環境変数（主なもの）

重要な環境変数は `src/kabusys/config.py` および config_setup の項目を参照してください。主なものを抜粋します。

必須（アプリケーション実行に必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用関連（デフォルトあり）:
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 使用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（default logs/）

監視／実行制御:
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH（Settings 経由）

AI:
- OPENAI_API_KEY（news_nlp / regime_detector で使用）

paper_trading 動作:
- PAPER_FILL_MODE: instant | partial | never | reject（MockBroker の成行フィル履歴モード）

詳しい項目は `src/kabusys/config_setup.py` の _ITEMS セクションを参照してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードで作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは `.env.example` などを参照して手動作成
5. 設定検証（推奨）
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになる
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（起動・ツール）

- ExecutionEngine（エンジン）を起動
  - 本番 / ペーパートレードは KABUSYS_ENV で切り替えます。
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 停止:
    - プロセスに KeyboardInterrupt を送るか、ルートプロジェクトの data/stop_requested.flag を作成すると安全に停止できます。
    - Kill Switch（監視側が書く data/kill.flag）で強制停止シグナルを送る仕組みもあります。

- Monitoring（監視）を起動
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - 注意: run_monitoring は monitoring 用 DB のパス `SQLITE_PATH` を常に本番用として使用します（設定にかかわらず）。

- .env 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-10
  ```
  または環境変数 `PAPER_TRADING_SQLITE_PATH` を設定して使えます。

- AI モジュール（プログラム内 API）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、テーブル（raw_news / prices_daily など）を参照します。

ログ:
- デフォルトで logs/<app_name>.log に日次ローテートで出力（logs ディレクトリ）。`LOG_DIR` 環境変数で変更可。

停止フラグ:
- data/stop_requested.flag: run_execution / run_monitoring の外部停止トリガ（存在を検知して正常終了）。
- data/kill.flag: KillSwitch が作成するフラグ。ExecutionEngine 側は起動時や運用時にこれを検出して停止します。`KILL_FLAG_CLEAR_ON_START` により起動時に自動クリアも可能（本番では無効推奨）。

---

## 開発用チェックリスト

- LLM を利用する機能をテストする場合は `OPENAI_API_KEY` を設定するか、呼び出し箇所をモックしてください（テスト時は API 呼び出しをモックしています）。
- YAML 検証を有効にするには PyYAML をインストールしてください（validate_config で使用）。
- データベースファイル（data/*.db）はリポジトリに含めないでください。

---

## ディレクトリ構成（主要ファイル・モジュールの説明）

（ルートは `src/kabusys/` 想定）

- __init__.py
  - パッケージ初期化。バージョン情報等。

- config.py
  - 環境変数 / 設定の読み込みと Settings クラス（アプリ設定のアクセサ）
  - 自動 .env ロードのロジック

- config_setup.py
  - .env の対話式ウィザード（作成 / 更新）

- validate_config.py
  - 起動前チェック CLI（必須 env、パス、YAML の存在／パースなど）

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - BrokerClientFactory / ExecutionEngine / OrderManager / RiskManager 等を組み立てて実行

- run_monitoring.py
  - SystemMonitor ポーリングループの起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔上書き可

- utils/
  - logging_setup.py: ルートロガーの統一設定（Stream + TimedRotatingFileHandler）
  - process_priority.py: プロセス優先度・CPU affinity の設定ユーティリティ
  - その他ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite に対する永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py: （発注ログの健全性チェック等 — 実装参照）
  - risk_monitor.py: ドローダウン／ポジション上限監視
  - kill_switch.py: kill.flag の書き込み管理
  - monitoring_engine.py: 各 Monitor を統合して周期的に実行
  - alert_manager.py: アラート発行（LINE 等に送る実装が想定される）

- execution/
  - execution_engine.py: 実際の取引セッションを実行するメインロジック（EngineConfig 等）
  - broker_factory.py: 環境に応じた BrokerClient の生成（MockBroker を含む）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py: 発注管理・履歴・再整合・リスク管理

- portfolio/
  - portfolio_builder.py: 候補選定・スコアソート
  - risk_adjustment.py: セクターキャップ・レジーム乗数
  - position_sizing.py: 発注株数計算・単元丸め・aggregate cap 処理

- research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー計算（DuckDB ベース）
  - feature_exploration.py: 将来リターン計算、IC（スピアマン）計算、統計サマリ

- ai/
  - news_nlp.py: OpenAI を用いたニュースセンチメントの集約・スコアリング
  - regime_detector.py: ETF MA200 とマクロセンチメントを合成して市場レジームを判定

- tools/
  - paper_verification_report.py: Paper Trading DB を解析して検証レポートを出力
  - その他バッチ / レポート系ツール

- data/
  - 実行時に使用するフラグや DB（data/monitoring.db, data/paper_trading.db 等）
  - ※ データファイルは通常 Git 管理に含めない（.gitignore を推奨）

---

## よくある運用フローの例

1. 初期セットアップ
   - `python -m kabusys.config_setup` で .env を作成
   - `python -m kabusys.validate_config` で設定確認

2. ローカル検証
   - DuckDB/SQLite にテストデータを入れて research / portfolio 関数を検証
   - `python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-10`

3. 実運用（ペーパートレード）
   - KABUSYS_ENV=paper_trading を設定
   - `python -m kabusys.run_execution`
   - 監視は別プロセスで `python -m kabusys.run_monitoring`

4. Kill Switch
   - 監視が危険閾値を検知すると data/kill.flag を書き込み、ExecutionEngine を停止させる

---

## 参考 / 注意点

- 本 README はコードの内容に基づいて手早くまとめたものです。詳細な設計仕様（PortfolioConstruction.md, StrategyModel.md 等）はコードコメントや別ドキュメントを参照してください。
- 本番運用前に必ず設定検証とペーパートレードでの十分な検証を行ってください。
- LLM / 外部 API 呼び出しは料金・レイテンシ・信頼性の影響を受けます。API キーの管理とリトライ方針は運用要件に合わせて調整してください。

---

必要であれば、この README をベースにさらに詳細なセットアップ手順（systemd ユニット例、Dockerfile、CI 設定、requirements.txt 作成など）を追加で作成します。どこを拡張したいか教えてください。