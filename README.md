# KabuSys

日本株自動売買システムの一部を含むライブラリ/実行スクリプト群です。  
このリポジトリには監視（Monitoring）、実行（Execution）、ポートフォリオ構築、リサーチ、AI ベースのニュース解析などの主要コンポーネントが含まれます。

---

## プロジェクト概要

KabuSys は、日本株の自動売買に必要な以下の機能をモジュール化したシステムです。

- システム稼働・データ鮮度の監視（Monitoring）
- 注文実行エンジン（ExecutionEngine）とリスク管理
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ファクター計算・特徴量探索（Research）
- ニュースの NLP によるセンチメントスコアリング（AI）
- ペーパートレード用の検証レポート生成ツール

主要な永続化は SQLite（監視／ペーパートレード DB）と DuckDB（時系列・分析用）で行います。

---

## 機能一覧

- 環境設定ウィザード（.env を対話的に生成）: kabusys.config_setup
- 起動前設定検証 CLI（.env, config/*.yaml の静的チェック）: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に記録
  - 停止はファイルフラグを利用（data/stop_requested.flag / data/kill.flag）
- 監視ループ起動スクリプト: run_monitoring.py
  - 定期ポーリングで System / Trade / Risk の監視を実施
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
- ポートフォリオ関連純粋関数群（銘柄選定、重み計算、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール
  - news_nlp: OpenAI に問い合わせて銘柄ごとのニュースセンチメントを ai_scores に保存
  - regime_detector: ETF MA とマクロニュースを組み合わせて市場レジーム判定
- tools: Paper Trading 検証レポート生成スクリプト（paper_verification_report）

---

## 必要環境 / 依存パッケージ

最低限必要な外部ライブラリ（実際の要求はプロジェクトの requirements に依存します）:

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証を行う場合）
- その他（標準ライブラリでまかなえる部分が多数）

※ 実稼働時は各モジュールが参照する API（kabuステーション、J-Quants、OpenAI など）の認証情報が必要です。

---

## 環境変数（主なもの）

必須:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（任意／デフォルトあり）:

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG/INFO/…） — デフォルト: INFO
- OPENAI_API_KEY: OpenAI API キー（AI モジュール実行時に必要）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring 用。デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 本番環境で kill.flag を起動時に自動クリアする場合は 1（デフォルト 0 推奨）

ログ / PID / フラグ関連パスは Settings クラスで取得されます（デフォルトは data/ 以下）。

---

## セットアップ手順（ローカルで試す最低手順）

1. リポジトリをクローン

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール

   （実際の requirements.txt があればそれを使用してください）

   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env を作成（対話式ウィザード推奨）

   ```
   python -m kabusys.config_setup
   ```

   または .env を手動で作成し、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。

5. 設定検証

   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

6. DB ファイルやログディレクトリは多くの場合実行時に自動作成されます。必要なら手動で作成して権限を整えてください。

---

## 実行方法（主要スクリプト）

- 監視ループ起動（Monitoring）

  ```
  python -m kabusys.run_monitoring
  ```

  オプション・環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。例: export MONITOR_POLL_INTERVAL=30

  停止:
  - 監視ループは実行中にプロジェクトルート/data/stop_requested.flag を検出すると終了します。
  - 監視は kill.flag を書き込む（KillSwitch）ことで ExecutionEngine 停止をトリガー可能（別目的）。

- 実行エンジン起動（ExecutionEngine）

  ```
  python -m kabusys.run_execution
  ```

  注意:
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、データは data/paper_trading.db に記録されます（本番 DB と分離）。
  - 起動時に既に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行停止は data/stop_requested.flag の作成、または監視側が kill.flag を書き込むことで行います。

- Paper Trading 検証レポート生成

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  オプション:
  - --db PATH: データベースファイルを明示する（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- 設定ウィザード

  ```
  python -m kabusys.config_setup
  ```

- 設定検証

  ```
  python -m kabusys.validate_config
  ```

---

## 停止 / 緊急停止の仕組み（ファイルフラグ）

- data/stop_requested.flag
  - run_monitoring / run_execution が監視しているフラグファイル。存在するとループを終了します（優雅な終了）。

- data/kill.flag
  - KillSwitch が書き込むことで ExecutionEngine に停止シグナル（Kill Switch）を送ります。
  - Settings.kill_flag_clear_on_start によって起動時に自動クリアする設定が可能ですが、本番では無効（0）を推奨します。

---

## ロギング

- 共通のログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）を設定
  - LOG_DIR 環境変数で保存先を変更可能
  - LOG_LEVEL でログレベルを指定

---

## 主要ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ情報
- config.py — 環境変数 / Settings 管理（.env 自動ロード機能含む）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

subpackages:
- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — マクロ + ETF MA から市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite を使った監視ログ永続化層
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 発注ログの監視（未記載のファイルも想定）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の読み書きユーティリティ
  - monitoring_engine.py — モニタ群を束ねるエンジン
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定（丸め・上限・スケーリング）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Value/Volatility ファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度/CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

その他:
- data/ — 実行中に生成される DB / PID / flag ファイル（デフォルト）
- logs/ — ログ出力（デフォルト）

---

## 注意事項 / 運用メモ

- 本リポジトリの一部は外部 API（kabuステーション、J-Quants、OpenAI 等）に依存します。実行には各 API の認証情報が必要です。
- .env（認証情報）は絶対にリポジトリにコミットしないこと。
- 本番運用（KABUSYS_ENV=live）時は kill_flag_clear_on_start を 0 にするなど安全設定を厳格にしてください。
- DuckDB / SQLite ファイルは起動時に自動作成・スキーママイグレーション処理が走る設計になっていますが、運用前にバックアップ・権限の確認を行ってください。
- OpenAI 呼び出しはレート制限や一時エラーに対してリトライ処理を備えていますが、API キーの利用料金には注意してください。

---

この README はコードベースの主要ポイントと起動手順をまとめたものです。より詳細な設計や仕様（PortfolioConstruction.md、StrategyModel.md 等）がプロジェクトに含まれている場合はそちらも参照してください。必要であれば README にさらに使い方（実行例・運用手順・トラブルシュート）を追加します。