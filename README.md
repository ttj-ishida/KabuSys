# KabuSys — 自動日本株売買システム

このリポジトリは日本株の自動売買（発注・ペーパートレード・監視・リサーチ・AI ニューススコアリング）を目的としたモジュール群です。ここではローカルでのセットアップ方法、主要スクリプトの使い方、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は次のような機能を持つパッケージ化された自動売買システムです。

- 発注エンジン（ExecutionEngine）
  - 実際のブローカー接続および Mock ブローカー（ペーパートレード）の切り替え
  - リスク管理・注文管理・再整合化（reconciler）
- 監視（Monitoring）
  - システムリソース監視（CPU/メモリ/ディスク）
  - データ鮮度・ポジション・ドローダウン監視
  - Kill Switch（問題発生時に外部フラグでエンジン停止）
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重配分、ポジションサイズ計算
  - セクター上限・レジーム乗数などのリスク調整
- リサーチ機能
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン・IC（Information Coefficient）などの解析ユーティリティ
- AI（ニュース NLP / レジーム判定）
  - OpenAI API（gpt-4o-mini 等）を使ったニュースセンチメント評価・市場レジーム判定
- 各種運用ツール
  - .env 作成ウィザード、設定検証、Paper Trading 検証レポート生成 等

---

## 主な機能一覧

- 環境設定ウィザード（kabusys.config_setup）
- 起動前設定検証（kabusys.validate_config）
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV による paper_trading / live の切り替え
  - paper_trading 時は専用 SQLite（data/paper_trading.db）を使用
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - ポーリング監視（MONITOR_POLL_INTERVAL で間隔設定可）
  - 監視は本番の sqlite_path（data/monitoring.db）を常に参照
- Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
- DuckDB ベースのリサーチ（kabusys.research）
- AI ニューススコアリング / レジーム判定（kabusys.ai）
- ロギング・プロセス優先度設定ユーティリティ（kabusys.utils）

---

## 依存関係（代表）

少なくとも以下のライブラリが必要です（バージョンは適宜調整してください）:

- Python 3.9+
- duckdb
- psutil
- openai
- （オプション）PyYAML（config/*.yaml の検証に使用）

インストール例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリに移動
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. 環境変数ファイル（.env）を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     生成した .env は決して Git にコミットしないでください（機密情報含む）。
   - あるいは .env.example を参考に自分で作成する。

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   --strict をつけると警告も失敗として終了します:
   ```
   python -m kabusys.validate_config --strict
   ```

---

## 環境変数（代表・デフォルト）

主要な環境変数とデフォルト値（.env で設定）:

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使用する場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

自動的に .env を読み込む仕組み:
- プロジェクトルート (.git または pyproject.toml がある場所) を探索し、`.env` と `.env.local` を読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意:
- .env は機密情報を含むため絶対に Git にコミットしないでください。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン（ExecutionEngine）起動
  ```
  python -m kabusys.run_execution
  ```
  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中は data/execution.pid を生成します。
  - 停止は signal または `data/stop_requested.flag` の作成で行います（Kill Switch は別）。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  挙動:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path（SQLITE_PATH）を参照します（KABUSYS_ENV にかかわらず）。
  - 停止はプロジェクトの data/stop_requested.flag を作成することで行います。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB 指定:
  ```
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- AI スコアリング / レジーム判定（コード呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  いずれも OpenAI の API キーを引数または環境変数 OPENAI_API_KEY で指定します。

---

## ロギング / プロセス優先度

- ロギングは kabusys.utils.logging_setup.setup_logging() によって統一的に設定されます。
  - コンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力。
  - デフォルトで 30 日分のログを保持します。
- 起動スクリプトは最初に `set_process_priority("high")` を呼び出し、OS に応じてプロセス優先度（nice / Windows priority）を設定します（権限がない場合は警告出力してスキップ）。

---

## 停止・Kill Switch の仕組み

- Kill Switch:
  - RiskMonitor がドローダウンやポジション上限違反を検出すると、KillSwitch が data/kill.flag に理由を記録します。
  - ExecutionEngine 起動時には kill_flag_clear_on_start 設定に応じて kill.flag をクリアできます（本番では 0 推奨）。
- 外部停止フラグ:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが停止します。
  - run_execution は data/execution.pid を作成します（プロセス管理用）。

---

## ディレクトリ構成（抜粋）

以下はルートから見た主なファイル／ディレクトリ（src/kabusys 以下）です。実際のプロジェクトにはさらにファイルが含まれますが、代表的な構成を示します。

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 設定読み込み・Settings クラス
    - config_setup.py               # .env 対話ウィザード
    - validate_config.py            # 起動前検証 CLI
    - run_execution.py              # ExecutionEngine 起動スクリプト
    - run_monitoring.py             # Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py                 # ニュース NLP スコアリング
      - regime_detector.py          # 市場レジーム判定
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py            # （trade_monitor の実装ファイルが存在）
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py            # （アラート送信ロジック）
    - utils/
      - logging_setup.py
      - process_priority.py
    - execution/                     # 発注関連モジュール群（broker, engine, repo 等）
    - data/                          # データパイプライン / DB 初期化関連
    - research/                      # リサーチ用補助モジュール
    - ... その他

（実際のツリーは git の内容に準拠してください）

---

## 開発・運用上の注意事項

- .env（および .env.local）は機密情報を含むため絶対にコミットしないでください。
- KABUSYS_ENV=live の設定時は特に注意:
  - 本番では LINE 通知設定や kill flag の設定をよく確認してください。
  - validate_config は本番環境での警告チェックを行います（--strict オプション推奨）。
- Paper Trading は実装上「本番 DB と完全分離」されるよう設計されています（paper_sqlite_path を使用）。
- 監視（monitoring）は常に本番 monitoring DB を参照する仕様の箇所があるため、環境に応じたファイル配置に注意してください。
- OpenAI など外部 API 呼び出しは失敗時にフォールバック・スキップする設計ですが、API キーの保護・呼量管理には配慮してください。

---

## よく使うコマンドまとめ

- ウィザードで .env を作成
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  ```
- Execution（本番 / Paper）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- Monitoring
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば README にインストール手順の詳細（pip requirements.txt、systemd ユニット例、Dockerfile 例）や各モジュールの API 仕様（関数引数・戻り値）を追記できます。どの情報を追加したいか指示してください。