# KabuSys — 日本株自動売買システム（README）

本リポジトリは日本株向け自動売買システム KabuSys のコアユーティリティ群（設定・監視・ポートフォリオ構築・リサーチ・AI アシスト等）を提供します。本 README はプロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な次の機能を含むモジュール群を提供します。

- 環境設定ウィザード（.env 生成）
- 設定検証 CLI（起動前チェック）
- ExecutionEngine（発注エンジン）起動スクリプト
- Monitoring（システム・注文・リスク監視）と Kill Switch
- ポートフォリオ構築（候補選定・重み計算・単元丸め・リスク適用）
- リサーチ（ファクター計算、特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム検出）
- Paper Trading 用検証レポート生成ツール

設計の特徴：
- 設定は .env または環境変数で管理。プロジェクトルートを基準に自動で .env を読み込みます（無効化可能）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して専用 SQLite を使用。
- OpenAI API を使った NLP 機能を備えていますが、APIキーの提供が必須です。
- DuckDB を分析用データベースとして利用し、SQLite を監視・ログ保存に利用します。

---

## 主な機能一覧

- 設定関連
  - config_setup.py: 対話式ウィザードで .env を生成／更新
  - validate_config.py: .env および config/*.yaml の整合性チェック

- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV による挙動分岐）
  - run_monitoring.py: SystemMonitor を定期ポーリングして監視ログを保存

- 監視・アラート
  - monitoring_engine: System / Trade / Risk モニタを束ねてアラート送信や Kill Switch 評価
  - Kill Switch: drawdown やポジション上限に達した際に停止フラグを作成

- 取引・注文関連（実装は execution パッケージ）
  - OrderManager / OrderRepository / Reconciler / RiskManager 等

- ポートフォリオ構築（pure functions）
  - 候補選定、等重・スコア重み、ポジションサイズ計算（単元丸め、キャップ制御）
  - セクター上限適用、レジーム乗数計算

- リサーチ
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン・IC・統計サマリ等

- AI（OpenAI）
  - news_nlp: 銘柄ごとのニュースを LLM でセンチメント付与して ai_scores に書き込み
  - regime_detector: マクロ記事と ETF MA200 を組み合わせた市場レジーム判定

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

---

## セットアップ手順

1. Python（推奨: 3.9+）をインストールしてください。

2. 仮想環境（推奨）を作成・有効化：
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール（例）：
   - 最低限必要なライブラリ（duckdb, psutil, openai 等）:
   ```
   pip install duckdb psutil openai
   ```
   - 設定検証で YAML を検査したい場合:
   ```
   pip install PyYAML
   ```
   - 実運用や開発用の requirements.txt がある場合はそれを使ってください:
   ```
   pip install -r requirements.txt
   ```

4. ディレクトリを作成（ログ・DB 保存用）:
   ```
   mkdir -p data logs
   ```
   ※ログディレクトリは環境変数 LOG_DIR で変更可能（デフォルト "logs"）。

5. .env の作成:
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を手動で作成してください（下の「環境変数一覧」を参照）。

6. 設定検証（起動前のチェック）:
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションを付けると警告も失敗扱いになります。

注意（本番環境）:
- 必須環境変数 JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD を絶対に設定してください。
- .env は機密情報を含むため Git にコミットしないでください。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV: one of "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading: MockBroker を用い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使う
    - live: 本番モード（注意して設定を確認すること）

- DB / ファイル
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: Execution 用 PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch のフラグファイル（デフォルト: data/kill.flag）

- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）

- モニタリング
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

- Paper Trading 振る舞い
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）

例 (.env の抜粋):
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（主要なコマンド／スクリプト）

- 環境設定ウィザード（.env 作成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は pid ファイル（既定: data/execution.pid）を扱います。停止は監視側が kill.flag を書くか stop flag を置く運用になります。

- Monitoring 起動（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を秒で上書き可能（デフォルト 60秒）。
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを記録します。
  - 停止は data/stop_requested.flag を作成することで行います（監視スクリプトはこれを検出して終了します）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照します。

- AI モジュール利用（プログラム内 API）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=None)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY を環境変数で渡すか、api_key 引数で明示的に渡してください。

注意点:
- AI モジュールは OpenAI を呼び出します。API キーと使用コスト、レートリミットに注意してください。失敗時はフェイルセーフ設計（部分的に 0.0 でフォールバック等）になっていますが、API の呼出し回数や課金は運用で管理してください。
- 本番モード（KABUSYS_ENV=live）では Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START）が危険なのでデフォルト 0 を推奨します。

---

## ディレクトリ構成（抜粋）

以下は本リポジトリの主要なファイル／ディレクトリの構成（src/kabusys 配下）です。実際のプロジェクトルートに src/ を持つ構成になっています。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — 市場レジーム判定（ETF + マクロ記事）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ定義とラッパー
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py        — （trade 関連の監視; 実装ファイルあり）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信のラッパー）
  - execution/                — 発注エンジン関連（OrderManager 等）
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/               — 監視用ロジック（上記）
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

（注）上記はコードベースからの抜粋です。実際には更に細かいモジュールや補助スクリプトが存在します。

---

## 運用上のヒント / 注意事項

- 本番運用（KABUSYS_ENV=live）は慎重に行ってください。validate_config.py の警告は必ず確認し、LINE 通知などアラート経路を確保してください。
- kill.flag（Settings.kill_flag_path）と stop_requested.flag（data/stop_requested.flag）は停止制御に使われます。運用時に誤って削除しないよう注意してください。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。権限やディスク容量を監視してください。
- Paper Trading を利用することで発注実装の動作検証ができますが、本番 API との差分に注意してください（遅延や部分約定など実際の挙動は異なります）。

---

## 参考コマンドまとめ

- 仮想環境作成・有効化
  - macOS / Linux:
    ```
    python -m venv .venv
    source .venv/bin/activate
    ```
  - Windows:
    ```
    python -m venv .venv
    .venv\Scripts\activate
    ```

- インストール（例）:
  ```
  pip install duckdb psutil openai PyYAML
  ```

- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行（デバッグ／開発）:
  ```
  python -m kabusys.run_execution
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

何か特定の手順（Docker 化、systemd ユニット作成、CI 設定、詳細な設定ファイル例など）が必要であれば教えてください。README を用途に合わせて拡張して提供します。