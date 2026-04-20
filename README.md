# KabuSys

日本株向け自動売買システム「KabuSys」のコードベース README（日本語）。

本ドキュメントはリポジトリ内の主要コンポーネントと使い方、セットアップ手順、ディレクトリ構成の概要を説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買 / リサーチ / モニタリングを統合するシステムです。  
主な用途は以下のとおりです。

- 戦略に基づく銘柄選定、ポジションサイズ計算、発注実行（ExecutionEngine）
- システム健全性 / 注文状態 / リスク（ドローダウン・ポジション上限等）の常時監視（Monitoring）
- Research 用のファクター計算・特徴量解析（DuckDB を利用）
- Paper Trading 用の分離された検証サポート
- OpenAI を使ったニュース NLP（センチメント付与）や市場レジーム判定（AI モジュール）
- 運用補助ツール（設定ウィザード、設定検証、Paper Trading 検証レポート 等）

設計方針の一部：
- DuckDB/SQLite をデータ層に利用（分析と稼働ログの分離）
- Paper Trading は本番データベースと分離（`data/paper_trading.db`）
- 環境変数 / .env による設定管理、対話式ウィザードと検証ツールを提供
- OpenAI 呼び出しは失敗時フェイルセーフ（例: スコアをデフォルトにする等）

---

## 機能一覧

- Execution（発注実行）
  - Broker クライアントの抽象化（paper_trading の場合は Mock）
  - OrderManager / RiskManager / Reconciler / ExecutionEngine による発注・監視
  - PID / stop フラグ対応

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度を監視
  - TradeMonitor: 注文の滞留・約定異常などを検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション上限を監視しリスクイベントとして保存
  - KillSwitch: 条件により停止フラグ（data/kill.flag）を書き込み Execution を停止
  - MonitoringEngine: 各モニタをまとめて定期実行、アラート連携

- Research（調査）
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン計算・IC（Information Coefficient）計算・統計サマリ

- Portfolio（ポートフォリオ構築）
  - 候補選定、均等配分 / スコア配分、セクター制限、ポジションサイズ計算（単元丸め含む）

- AI（OpenAI 連携）
  - news_nlp: ニュースを集約して LLM で銘柄別センチメントを生成し ai_scores に格納
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定と永続化

- Tools
  - config_setup: .env 対話式ウィザード
  - validate_config: 起動前チェック（必須環境変数・ファイルの存在・YAML 構文等）
  - paper_verification_report: Paper Trading の検証レポート生成

---

## 動作環境 / 前提

- Python 3.10 以上（型ヒントの union 省略記法など）
- 必要な外部ライブラリ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite は標準ライブラリを使用

実際のインストール時はプロジェクトの requirements.txt があればそれを利用してください。なければ代表的なパッケージを pip で入れてください:

例:
```
python -m pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   もしくは最低限:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. 環境変数設定（.env）
   - 対話式ウィザードを利用すると簡単に作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI モジュール使用時）
     - KABUSYS_ENV: development / paper_trading / live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - LOG_LEVEL / LOG_DIR
   - 作成後は設定検証を実行:
     ```
     python -m kabusys.validate_config
     ```

5. データディレクトリ作成（自動で行われる場合あり）
   - デフォルトの DB / logs / data フォルダが必要です。起動時に自動作成されますが、権限等で失敗する場合は手動で用意してください。

---

## 起動・使い方

- ExecutionEngine（発注実行）起動
  - 通常起動:
    ```
    python -m kabusys.run_execution
    ```
  - 動作モード
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用の DB（デフォルト: data/paper_trading.db）に記録します（本番 DB と完全分離）。
  - 停止方法
    - 実行中に `data/stop_requested.flag` を作成すると、プロセスは検知して停止します。
    - ExecutionEngine は `data/execution.pid` を使用（PID ファイル）。

- Monitoring（監視）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60 秒）。
  - Monitoring は KABUSYS_ENV に関係なく本番の sqlite_path（`SQLITE_PATH`）を使用して監視ログを記録します。
  - 停止は `data/stop_requested.flag` を配置することで検知してループを抜けます。

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も失敗扱い
  ```

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は `PAPER_TRADING_SQLITE_PATH` 環境変数（未指定時は `data/paper_trading.db`）。

- AI 関連（プログラム的利用）
  - ニュース NLP（銘柄スコア付与）:
    ```
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=None)  # api_key None で環境変数 OPENAI_API_KEY を参照
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)
    ```

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J‑Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（INFO 等）
- LOG_DIR — ログ保存先ディレクトリ
- MONITOR_POLL_INTERVAL — 監視のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — モニタリング/停止フラグ関連

.env の作成は `python -m kabusys.config_setup` を使うと安全で簡単です。`.env.example` があれば参照してください（リポジトリにあれば）。

---

## 停止フラグ・PID ファイル

- 停止要求（外部からの強制停止シグナル）は flag ファイルで実現:
  - stop 用フラグ: `data/stop_requested.flag`（run_execution/run_monitoring が監視）
  - kill スイッチ: `data/kill.flag`（KillSwitch が書き込むと ExecutionEngine に停止シグナル）
- ExecutionEngine は `data/execution.pid` を PID ファイルとして使用（run_execution 内定義）。
- Kill Switch の評価条件は RiskMonitor 等による（ドローダウン超過、ポジション数上限など）。

---

## ログ

- logging は共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` を使用。
- デフォルトで stdout（コンソール）と日次ローテートされたファイルログ（logs/<app_name>.log）を出力。
- ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/`。
- ログレベルは `LOG_LEVEL`（あるいは setup_logging の引数で指定可能）。

---

## ディレクトリ構成（主要ファイル）

下記はリポジトリ内 `src/kabusys` に相当する主要モジュールとファイル例です（実際のファイルはこの一覧に準拠しています）。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring ポーリングループ起動スクリプト
    - monitoring/
      - monitoring_db.py           — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
      - system_monitor.py          — システム / データ鮮度監視
      - trade_monitor.py           — （存在）注文監視ロジック
      - risk_monitor.py            — ドローダウン・上限監視
      - monitoring_engine.py       — 各 Monitor をまとめるエンジン
      - kill_switch.py             — kill.flag 管理
      - alert_manager.py           — （存在想定）通知管理（LINE等）
    - execution/
      - execution_engine.py        — 実行エンジン本体
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
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
      - news_nlp.py                 — OpenAI によるニュースセンチメント
      - regime_detector.py          — 市場レジーム判定
      - __init__.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

（補足）上記にあるファイルのうち TODO 記載・将来的拡張予定の部分や、実装の依存関係で外部モジュールが必要な個所があります。

---

## 運用上の注意点 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では .env にプレースホルダ値を置かないこと。`validate_config` の警告・エラーを必ず確認してください。
- Kill Switch 周り（KILL_FLAG_CLEAR_ON_START）は本番で `1` にしないこと（自動クリアは危険）。
- OpenAI の呼び出しはコストが発生するため、実運用時は適切な API キー管理とレート制御を行ってください。
- Paper Trading は本番 DB と分離されています。検証やバックテストの前に PAPER_TRADING_SQLITE_PATH を確認してください。
- ログファイルの保護・ローテーションと DB バックアップを運用ルールに組み込んでください。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

問題や不明点、README に追加したい内容（デプロイ手順や Dockerfile 例、詳細な設定テンプレートなど）があれば教えてください。README を目的に合わせて拡張します。