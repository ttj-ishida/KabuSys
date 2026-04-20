# KabuSys

日本株自動売買システムの軽量実装（ライブラリ + 実行スクリプト群）。

このリポジトリはトレード戦略の研究・ポートフォリオ構築・注文実行・監視・ペーパートレード検証などを含むモジュール群で構成されています。実運用を想定した設計（ログローテーション、Kill Switch、監視 DB、Paper Trading の分離など）が組み込まれています。

---

## 主な機能

- 実行コンポーネント
  - ExecutionEngine（発注ロジック、リスク管理、注文管理、再突合）
  - ブローカークライアント切替（本番 / ペーパートレード：MockBrokerClient）
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク/プロセス）監視
  - 注文ログ監視（滞留注文・異常約定など）
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（条件に応じて data/kill.flag を書き込むことで ExecutionEngine を停止）
- ポートフォリオ構築（純関数群）
  - 候補選定、等金額/スコア重み付け、ポジションサイズ計算、セクターキャップ、レジーム調整
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC（Information Coefficient）計算、特徴量サマリ
- AI系（OpenAI）
  - ニュースセンチメントによる銘柄スコアリング（ai.news_nlp）
  - マクロ + ETF MA200 による市場レジーム判定（ai.regime_detector）
- 付帯ツール
  - .env 対話式セットアップウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - ペーパートレード検証レポート生成ツール（tools.paper_verification_report）
- ロギング
  - 統一的なログ設定（console + 日次ローテーションファイル）

---

## 依存・前提

- Python 3.10+
- 必要な Python パッケージ（最低限の例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の内容検証に必要、任意）
- （実運用）kabuステーション API、J-Quants API など外部サービスの認証情報

インストール例（仮）:
```bash
python -m pip install duckdb psutil openai pyyaml
```
プロジェクトに requirements.txt がある場合はそれを使用してください。

---

## セットアップ手順

1. リポジトリをクローン／展開
2. 仮想環境を作成し依存をインストール
3. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成できます：
     ```bash
     python -m kabusys.config_setup
     ```
   - 主要な環境変数（.env に記載される代表例）
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - LOG_LEVEL — ログレベル（デフォルト: INFO）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、production では 0 推奨）
4. 設定検証（任意だが推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 実行方法（使い方）

- ExecutionEngine（注文実行）起動:
  - 通常起動（環境変数 .env を適切に設定後）:
    ```bash
    python -m kabusys.run_execution
    ```
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録されます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
    - 実行中は PID ファイル（デフォルト data/execution.pid）に書き込みます。

- Monitoring（監視）起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず production 相当の sqlite_path（Settings.sqlite_path）を使用して監視 DB に書き込みます。
  - 停止は data/stop_requested.flag を作成すると監視ループが終了します。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI スコアリング・レジーム判定（ライブラリ呼び出し例）
  - ニューススコアリング（ai.news_nlp.score_news）
  - レジーム判定（ai.regime_detector.score_regime）
  - これらは DuckDB 接続と target_date、OpenAI API キーを引数に取ります（環境変数 OPENAI_API_KEY から取得可）。

---

## 実行停止・Kill Switch

- ExecutionEngine 停止
  - 管理用フラグファイル:
    - data/kill.flag — Kill Switch（監視が条件によりこのファイルを書き込むと ExecutionEngine 側で検出して停止します）
    - data/stop_requested.flag — run_execution / run_monitoring の外部停止フラグ（存在すると起動を抑止またはループを抜ける）
  - KillSwitch は監視結果（ドローダウンやポジション上限など）によって作成されます。Production では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。

---

## ログ

- ログは console に出力されるほか、デフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されます。
- ログ出力先ディレクトリは環境変数 LOG_DIR または引数で変更可能。ディレクトリ作成に失敗した場合はコンソールのみの出力にフォールバックします。

---

## .env の自動読み込み

- 起動時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、
  - .env（優先度低）をロード、
  - .env.local（優先度高）を上書きロードします。
- OS 環境変数は保護され、.env の値で上書きされません（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化可能）。

---

## ディレクトリ構成

以下は主要ファイル／ディレクトリの一覧（簡易）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (実装あり／拡張対象)
  - execution/  (注文実行・ブローカー関連)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ （実行時に生成されることが多い）
    - ローカル DB（data/monitoring.db、data/paper_trading.db など）
    - フラグファイル（kill.flag、stop_requested.flag）
  - config/ （YAML 設定テンプレート）
    - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml

（詳細はソース内ドキュメントや doc ファイルを参照）

---

## 開発・拡張メモ

- 多くの関数は純関数あるいは DuckDB/SQLite 接続を引数に取る形で実装されており、単体テストが行いやすい設計です。
- AI 呼び出し（OpenAI）は失敗時にフェイルセーフでスコア 0.0 を返す等の堅牢化が施されていますが、API キー・トークンの管理は慎重に行ってください。
- ペーパートレードは production DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。

---

## トラブルシューティング

- SQLite / DuckDB のファイルパスが不正（親ディレクトリがない等）の場合、`python -m kabusys.validate_config` で警告が出ます。必要に応じてディレクトリを作成してください。
- ログディレクトリ作成に失敗した際はコンソール出力のみが機能します。パーミッションやパスを確認してください。
- OpenAI 関連のエラーはネットワークやレート制限に起因することが多く、コード側で再試行ロジックを用意しています。API キー、料金枠、制限を確認してください。

---

README はプロジェクトの概要と基本操作に焦点を当てています。より詳細な内部設計や API 仕様は各モジュールの docstring とソースコードコメントに記載されています。必要であれば各コンポーネント（ExecutionEngine、MonitoringEngine、AI モジュール、Portfolio モジュール等）の利用方法や API 例を別途追記します。