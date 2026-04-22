# KabuSys

日本株向け自動売買 / 研究フレームワーク（ドメインライブラリ群）。  
このリポジトリは、取引エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、LLM を用いたニュース解析などのコンポーネントを含む設計済みのシステムです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 取引実行エンジン（ExecutionEngine）と注文管理
- 監視コンポーネント（System / Trade / Risk）および Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング、セクター制限）
- データ解析・ファクター計算（DuckDB を利用）
- ニュースの NLP 評価（OpenAI API を利用した銘柄別センチメント）
- ペーパートレード用の分離 DB と検証レポート生成ツール
- 環境設定ウィザード、設定検証 CLI、ロギング設定ユーティリティ

設計上、実運用とペーパートレードは DB 等を分離し、LLM 呼び出し・外部 API は明示的に制御され、ルックアヘッドバイアスを避ける実装方針です。

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い、data/paper_trading.db に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視
- 監視ループ起動スクリプト（run_monitoring）
  - システム稼働監視（CPU/メモリ/ディスク、Execution プロセス監視）
  - RiskMonitor によるドローダウン監視・ポジション上限監視
  - Kill Switch（data/kill.flag）生成
- MonitoringDB（SQLite）による永続化テーブル（system_status, trade_logs, positions, risk_logs, dashboard）
- ポートフォリオ構築ユーティリティ
  - 候補選定（スコア降順）、等金額/スコア重み付け
  - セクター上限適用、レジーム乗数
  - ポジションサイジング（リスクベース / 等分 / スコア基準）、単元株丸め、集計上限スケーリング
- 研究系モジュール（DuckDB を受け取って計算）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 特徴量探索（forward returns, IC 計算, 統計サマリー）
- AI モジュール
  - ニュース NLP（OpenAI）で銘柄別センチメントを生成し ai_scores に保存
  - 市場レジーム判定（ETF MA とマクロセンチメントを合成）
  - 再試行・エラー時のフェイルセーフ実装
- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成ツール（tools/paper_verification_report）
  - 統一的ロギング設定（utils.logging_setup）

---

## 要件（推奨）

- Python 3.10+
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config 検証のため）
- OS: Linux / macOS / Windows（process priority はプラットフォーム差分を吸収する実装）

実際のパッケージは requirements.txt を使うか、以下のようにインストールしてください（環境に合わせて調整）:

pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動します。

2. Python 仮想環境を作成して有効化します（推奨）。

3. 必要パッケージをインストールします（上記参照）。

4. .env を用意する
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - .env.example があれば参考にして .env を作成してください。
   - 自動ロード: プロジェクトルートに .env / .env.local がある場合、起動時に自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. 設定検証（推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告もエラーとして扱います。

6. データディレクトリ等の作成
   - デフォルトの DB / ログパスは .env に指定されていない場合以下:
     - data/monitoring.db（SQLite 監視 DB）
     - data/paper_trading.db（ペーパー用 DB）
     - data/kabusys.duckdb（DuckDB）
     - logs/ 実行ログ（デフォルト）
   - 起動スクリプトは必要に応じてこれらディレクトリを作成しますが、パーミッション等が必要な場合は事前に作成してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な設定（代表例）:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB のパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連

.env 生成時は秘密情報（トークン・パスワード）を適切に扱ってください。 .env は Git にコミットしないこと。

---

## 使い方（起動コマンド例）

- 設定ウィザード（.env を対話式作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動（メイン実行エンジン）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い paper_trading DB を利用します。
  - 起動時に data/stop_requested.flag があると起動を行いません。
  - 停止は data/stop_requested.flag を作成すると安全に停止シグナルを送れます（または kill.flag を監視用途に使えます）。

- Monitoring（監視ループ）を起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（環境にかかわらず同じ監視 DB を使う設計）

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数 or data/paper_trading.db

- AI / 研究用関数
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルに書き込みます。OPENAI_API_KEY が必要。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム判定と market_regime テーブルへの書込み。

- ログ
  - ロギングは kabusys.utils.logging_setup.setup_logging を通じて標準化されています。
  - デフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力します。

---

## 停止 / Kill Switch

- 実行エンジンの安全停止:
  - Kill Switch: data/kill.flag を監視（存在すると ExecutionEngine に停止シグナルとして扱われる）。
  - 監視コンポーネントから条件を満たすと自動で kill.flag を書き込み、アラートを送出します（例: ドローダウン閾値超過）。
  - 既存の flag があれば再書き込みは行われません（冪等）。

- 外部からの停止:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します（スクリプト側でチェック済み）。

---

## ディレクトリ構成

以下は src/kabusys 以下の主なファイルと役割（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動ロード、Settings クラス
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み計算（等分・スコア重み）
    - risk_adjustment.py
      - セクター制限、レジーム乗数
    - position_sizing.py
      - 発注株数計算（risk_based / equal / score）
    - __init__.py
  - research/
    - factor_research.py
      - momentum / volatility / value ファクター計算（DuckDB）
    - feature_exploration.py
      - forward returns / IC / summary 等
    - __init__.py
  - ai/
    - news_nlp.py
      - ニュースの LLM による銘柄別センチメント生成
    - regime_detector.py
      - マクロセンチメント + ETF MA による市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py
      - SQLite テーブル初期化 / MonitoringDB クラス（読み書き）
    - system_monitor.py
      - CPU/メモリ/ディスク、Execution プロセス、データ鮮度監視
    - trade_monitor.py
      - （注文滞留や約定異常の検出ロジック）
    - risk_monitor.py
      - ドローダウン / ポジション上限監視
    - kill_switch.py
      - kill.flag 書き込みユーティリティ
    - monitoring_engine.py
      - 各モニタを束ねるループ
  - utils/
    - logging_setup.py
      - ルートロガーとファイルローテーションの統一設定
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    - （取引実行に関するコンポーネント群）
  - data/
    - pipeline, stats 等（DuckDB / pipeline 用ユーティリティ、R&D 用）

（注）一部ファイルはここに列挙していない補助モジュールがあります。上は主要構成の要約です。

---

## 注意事項 / 運用時のガイドライン

- 本番環境（KABUSYS_ENV=live）では必須環境変数や LINE 通知の設定などを十分に確認してください（validate_config で検出できます）。
- .env に秘密情報（API トークン等）を格納する場合は、Git 管理から除外してください。
- OpenAI API を利用する機能は API キーが必要で、レート制限や課金に注意が必要です。失敗時はフェイルセーフにより中立値で継続する設計ですが、運用時は監視を強化してください。
- ペーパートレードは本番 DB と分離されています。KABUSYS_ENV=paper_trading を必ず確認してください。
- ログディレクトリや DB ファイルのパーミッションは運用環境に合わせて適切に設定してください。

---

## 開発・拡張のヒント

- DuckDB 接続をテスト用に差し替えてファクター計算関数を単体テスト可能です。
- OpenAI 呼び出しは内部でラッパー関数化しており、テスト時はモック／patch で置き換えて挙動検証ができます（news_nlp/_call_openai_api 等）。
- monitoring の各コンポーネントは MonitoringEngine で組合せられているため、単体テストでは MonitoringEngine(run_once) を利用して統合検証を行えます。

---

README はここまでです。必要なら以下を提供できます:
- 例となる .env.example のテンプレート
- run/デプロイ用 systemd / Supervisor のサンプルサービス定義
- 主要モジュールの簡易 UML / 呼び出しフロー図

どれが必要か教えてください。