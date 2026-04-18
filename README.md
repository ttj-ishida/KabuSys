# KabuSys

日本株向け自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、戦略リサーチ、ポートフォリオ構築、発注実行、監視、AI を用いたニュース解析などを含む自動売買基盤のサンプル実装です。設計方針としては、フェイルセーフ（API失敗や部分障害時の安全処理）やルックアヘッドバイアス回避、テスト容易性を重視しています。

バージョン: 0.1.0

---

内容の目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動例・ツール）
- 主要な環境変数
- ディレクトリ構成（ファイル一覧と説明）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコア部分を提供します。主な責務は以下です。

- ファクター計算 / 研究（DuckDB を用いた価格・財務データ処理）
- ポートフォリオ構築（候補選定、重みづけ、リスク調整、株数決定）
- Execution Engine（発注管理、ブローカー抽象化、ペーパートレード分離）
- Monitoring（システム/注文/リスク監視、Kill Switch）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定） — OpenAI を用いる
- CLI ユーティリティ（.env 設定ウィザード、設定検証、ペーパートレード検証レポート）

設計のキーポイント:
- Paper Trading（KABUSYS_ENV=paper_trading）時は本番 DB と分離して data/paper_trading.db を使用
- .env 自動ロード機能（プロジェクトルートを検出して .env / .env.local を読み込み）
- フラグファイルによる停止制御（data/stop_requested.flag, data/kill.flag）
- DuckDB を分析用 DB として利用、SQLite を監視・トレース用 DB として利用

---

## 主な機能一覧

- research/
  - ファクター計算 (momentum/value/volatility)
  - 将来リターン、IC、統計サマリー
- portfolio/
  - 候補選定 (select_candidates)
  - 重み付け (equal / score)
  - セクター制約適用 (apply_sector_cap)
  - レジーム乗数計算 (calc_regime_multiplier)
  - 位置サイズ計算（単元丸め、リスクベース等）
- execution/
  - ExecutionEngine（発注ライフサイクル、OrderManager、RiskManager 等）
  - ブローカーの抽象化（本番/モック切替）
- monitoring/
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働チェック・データ鮮度
  - TradeMonitor: 注文滞留・約定異常検出
  - RiskMonitor: ドローダウン監視、ポジション上限
  - KillSwitch: 異常検出時に data/kill.flag を書き込み、ExecutionEngine を停止させる仕組み
  - MonitoringDB: SQLite にログ永続化（マイグレーション含む）
  - MonitoringEngine: 複数モニタをまとめて定期実行
- ai/
  - news_nlp: raw_news を LLM（OpenAI）で評価して銘柄ごとにスコア化し ai_scores に書き込む
  - regime_detector: ETF とマクロニュースを組み合わせて市場レジーム判定
- utils/
  - logging_setup: 一貫したログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report: ペーパートレード DB を解析し PASS/FAIL レポート生成
- CLI
  - config_setup: .env を対話式で生成・更新
  - validate_config: .env と config/*.yaml の事前検証

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+（typing union | などを利用）
- Git およびネットワーク接続

推奨手順:

1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境を作成・有効化
   (例)
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   このリポジトリには requirements.txt が無い想定のため、最低限の依存を手動インストールします:
   ```
   pip install duckdb psutil openai
   ```
   追加で便利なパッケージ:
   ```
   pip install PyYAML
   ```
   - DuckDB: リサーチ・AI データ処理用
   - psutil: システム監視・プロセス優先度設定
   - openai: news_nlp / regime_detector の API 呼び出し
   - PyYAML: validate_config による config/*.yaml 検証（任意）

4. 環境変数の初期設定（.env 作成）
   対話式ウィザードを使って .env を作成するのが推奨です:
   ```
   python -m kabusys.config_setup
   ```
   もしくは `.env.example` を参照して `.env` を手動作成してください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   必須項目が足りない場合はメッセージに従って修正してください。--strict オプションで警告も失敗扱いにできます。

6. データディレクトリの準備（自動作成されることが多いですが確認）
   ```
   mkdir -p data logs
   ```
   SQLite / DuckDB のデフォルトパス:
   - data/monitoring.db (SQLite)
   - data/paper_trading.db (paper_trading 用)
   - data/kabusys.duckdb (DuckDB)
   - logs/（ログファイル出力先）

---

## 使い方（実行・主要コマンド）

注意: 実行スクリプトはパッケージモードで起動します（モジュールとして実行）。

- Execution Engine を起動（デーモンではなくフォアグラウンド）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV によって挙動が変わります:
    - paper_trading: MockBrokerClient を使用し、paper_trading 用 SQLite に書き込む（本番 DB と分離）
    - live/development: settings に従って本番 sqlite_path を使用
  - 実行中の停止は data/stop_requested.flag を作成すると処理が検知して停止します（外部からの停止シグナル用）。

- Monitoring を起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトは 60 秒間隔でポーリング。環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- .env の作成/更新（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading の検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは環境変数または --db オプションで指定可能:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI 関連関数（ライブラリ呼び出し）
  - news_nlp.score_news / ai.regime_detector.score_regime は DuckDB 接続と target_date、OpenAI API キーが必要です。
  - 環境変数: OPENAI_API_KEY を設定するか、呼び出し側で api_key を渡してください。

---

## 主要な環境変数（抜粋）

必須（最低限設定してください）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

一般設定
- KABUSYS_ENV — 実行環境: development | paper_trading | live (default: development)
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（default: logs/）

データベースパス
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（default: data/paper_trading.db）

AI
- OPENAI_API_KEY — OpenAI 呼び出しに使用（news_nlp / regime_detector）

モニタリング関連
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動で削除するか（0/1）

その他
- PID_FILE_PATH — 実行エンジンの PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（default: data/kill.flag）

---

## 制御ファイル（data/ ディレクトリ）

- data/stop_requested.flag
  - run_execution、run_monitoring スクリプトが存在を検知すると安全にループを抜けて終了します（手動停止用）。
- data/kill.flag
  - KillSwitch が書き込むファイル。発見されたら ExecutionEngine の停止を意図します（安全のため本番では自動クリア設定に注意）。
- data/execution.pid
  - ExecutionEngine が PID を書き込む場所（設定により変更可能）。

---

## ディレクトリ構成（主要ファイル説明）

概略:
```
src/
  kabusys/
    __init__.py
    config.py                 # 環境変数 / .env 自動読み込み / Settings
    config_setup.py           # .env 対話ウィザード CLI
    validate_config.py        # 設定検証 CLI

    run_execution.py          # ExecutionEngine 起動スクリプト
    run_monitoring.py         # SystemMonitor ポーリング起動スクリプト

    utils/
      logging_setup.py        # ログ設定ユーティリティ
      process_priority.py     # プロセス優先度・CPU affinity ユーティリティ

    monitoring/
      monitoring_db.py        # SQLite テーブル定義・永続化 API
      system_monitor.py       # システム状態 / データ鮮度監視
      trade_monitor.py        # (注文監視) ※コード内に実装あり
      risk_monitor.py         # ドローダウン・ポジション上限監視
      kill_switch.py          # kill.flag 書き込みロジック
      monitoring_engine.py    # 各モニタを束ねるエンジン
      alert_manager.py        # アラート送信（LINE など）※実装参照

    execution/                # Execution に関連するモジュール群（発注・リスク等）
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
      broker_factory.py       # ブローカークライアント生成（本番/モック）

    research/                 # DuckDB を使ったファクター計算・探索
      factor_research.py
      feature_exploration.py

    portfolio/                # ポートフォリオ構築ロジック（純粋関数）
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    ai/                       # LLM を使ったニュース解析・レジーム判定
      news_nlp.py
      regime_detector.py

    tools/
      paper_verification_report.py

    data/                     # データ・フラグ・DB が配置される（実行時に使用）
```

（注）上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。

---

## 運用上の注意点 / ベストプラクティス

- KABUSYS_ENV を正しく設定すること（特に live 時は十分な注意を払ってください）。
- .env を絶対に Git にコミットしない（config_setup 内でも注意喚起あり）。
- 本番 (live) では KILL_FLAG_CLEAR_ON_START を 0 にすることを強く推奨します（自動クリアは危険）。
- OpenAI を利用する AI 機能は API 呼び出し失敗時にフォールバックするよう設計されていますが、API キー管理とコスト制御を必ず行ってください。
- run_monitoring / run_execution は stop_requested.flag を見て安全に終了します。手動停止時はこのフラグを利用してください。
- monitoring の DB 初期化/マイグレーションは init_monitoring_db で行われます。既存の DB に対しては後方互換のための ALTER が一部行われますが、運用前にバックアップを推奨します。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR を環境変数で変更可能です。

---

必要な追加情報や README に加えたい具体的な補足（例: サンプル .env、docker-compose 構成、CI 設定など）があれば教えてください。README をそれに合わせて拡張します。