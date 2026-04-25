# KabuSys

日本株向け自動売買システムのコアライブラリ群および起動スクリプト群。  
この README はリポジトリ内の主要コンポーネント、セットアップ方法、よく使うコマンド例、ディレクトリ構成をまとめたものです。

※ 本ドキュメントはコードベースのソースコメントおよびモジュール実装に基づいて作成しています。

---

## プロジェクト概要

KabuSys は以下の機能を持つ自動売買プラットフォームのライブラリ群です。

- 戦略（ファクター計算・特徴量解析）を実行するための research モジュール（DuckDB を利用）
- 銘柄選定・配分・株数計算を行う portfolio モジュール（等配分・スコア加重・リスクベース等）
- 実売買のための ExecutionEngine（kabuステーション連携／ペーパートレード対応）
- 実運用監視（System / Trade / Risk の監視、Kill Switch）
- ニュース NLP によるセンチメント評価（OpenAI API 経由）
- 設定ウィザード（.env 生成）と設定検証 CLI
- ペーパートレード検証レポート生成ツール

設計方針の例：
- DuckDB を分析用 DB として利用（prices_daily / raw_financials 等）
- 監視ログや発注ログは SQLite に永続化
- ペーパートレード時は本番 DB とは切り離した専用 SQLite を使用
- OpenAI 等外部 API 呼び出しは明示的にキーを渡すか環境変数で管理し、失敗時はフェイルセーフで継続する

---

## 主な機能一覧

- 設定管理
  - .env ファイルの自動読み込み / 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

- 実行（Execution）
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント生成
  - リスク管理（RiskManager）、注文管理（OrderManager）、リコンシリエーション

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor のポーリング
  - Kill Switch（data/kill.flag を書き込んでエンジン停止）
  - 監視用 SQLite 初期化（monitoring_db）
  - 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - アラート発行フック（AlertManager 経由）

- ポートフォリオ構築
  - 銘柄選定 select_candidates
  - 重み算出（等配分 / スコア加重）
  - ポジションサイズ決定（risk_based 等）
  - セクター上限適用、レジーム乗数計算

- リサーチ / 指標計算
  - momentum / volatility / value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（ニュース NLP / レジーム判定）
  - raw_news を集約して OpenAI（gpt-4o-mini 等）でセンチメントを算出
  - 市場レジーム判定（ETF + マクロニュースの合成）

- ツール
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

---

## 必要な依存ライブラリ（例）

実行には以下のような主要ライブラリが必要です（バージョンはプロジェクト要求に合わせて調整してください）：

- Python 3.9+
- duckdb
- psutil
- openai
- sqlite3（標準）
- （開発/オプション）PyYAML（config YAML チェック時に使用）

インストール例（pip）:
```bash
pip install duckdb psutil openai PyYAML
```

注意:
- OpenAI API を利用する機能を使う場合は `OPENAI_API_KEY` が必要です（コストに注意してください）。
- パッケージ管理は requirements.txt / poetry / pipenv 等のプロジェクト方針に従ってください（本リポジトリには明示的な requirements ファイルの記載はありません）。

---

## セットアップ手順（ローカルで簡易に動かす場合）

1. リポジトリをクローン / コピー
2. Python 環境を作成（仮想環境推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb psutil openai PyYAML
   ```
3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする:
   python -m kabusys.validate_config --strict
   ```

5. データファイルとログディレクトリ（必要に応じて）
   - デフォルトの DB/ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/<app_name>.log
   - .env で上書き可能

---

## 起動・使い方

主要なエントリポイントと実行方法の例を示します。

- ExecutionEngine を起動（本番・ペーパーは KABUSYS_ENV で切替）
  ```bash
  # 例: デフォルト .env で設定済みの状態
  python -m kabusys.run_execution
  ```
  動作:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用し data/paper_trading.db に記録
  - 起動時に data/stop_requested.flag があれば起動せず終了
  - 実行中は data/execution.pid を使用

- Monitoring を起動
  ```bash
  # MONITOR_POLL_INTERVAL 秒でポーリング（デフォルト 60 秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  動作:
  - 監視ループは Settings.sqlite_path（monitoring DB）を用いる（環境に依らず本番 DB パス）
  - stop_requested.flag を検知するとループ終了

- 設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB 指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - ai.score_news:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数か `OPENAI_API_KEY` 環境変数で指定
  - ai.score_regime:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- OpenAI を使う呼び出しは API 費用が発生します。テスト時はモック化（patch）してください。
- 実行スクリプトは logging を統一的に設定します（kabusys.utils.logging_setup.setup_logging）。

---

## Kill Switch / 停止フラグの扱い

- 実行停止用にフラグファイルを使用します（data/kill.flag, data/stop_requested.flag）。
- KillSwitch（監視側）から `data/kill.flag` が書かれると ExecutionEngine に停止シグナルを送る運用を想定。
- ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアする（本番では推奨しない）。

---

## 開発 / デバッグのヒント

- logging: 全スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出し、stdout とログファイルへ出力します。LOG_LEVEL, LOG_DIR は環境変数で制御可能です。
- DB マイグレーション: monitoring_db.init_monitoring_db は既存テーブルのカラム追加（簡易マイグレーション）を行います。
- テスト時は外部 API 呼び出し（OpenAI、ブローカー）をモック化してください（関数内部で呼び出し箇所が明確に分離されています）。

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの一覧（src/kabusys 配下を抜粋）です。ファイルは機能ごとに整理されています。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト

  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py      — momentum/volatility/value 等の計算（DuckDB）
    - feature_exploration.py  — forward returns / IC / summary

  - ai/
    - news_nlp.py             — raw_news を OpenAI でスコア化して ai_scores へ書き込み
    - regime_detector.py      — ETF MA + マクロニュースでレジーム判定

  - monitoring/monitoring_db.py (監視用 DB 初期化・API)
  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py
    - その他ユーティリティ

- data/                       — デフォルトのデータベース/フラグファイル置き場（git 管理しないこと）
  - monitoring.db
  - paper_trading.db
  - kill.flag
  - execution.pid
  - stop_requested.flag

- logs/                       — ログファイル（logs/<app_name>.log）

---

## よくある操作例

- 監視を 30 秒間隔で起動（バックグラウンドは各自環境で管理）
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- ペーパートレードで Execution を起動（.env で KABUSYS_ENV=paper_trading にする）
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- .env を編集したら設定検証を行う
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading の検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 注意点 / 運用上の留意事項

- 本番（KABUSYS_ENV=live）での起動前に validate_config を実行し、LINE 通知や kill flag 設定等を特に確認してください。
- OpenAI API を利用するモジュールは API 費用が発生します。キーの扱いや使用頻度に注意してください。
- data/*.db および .env（機密情報）は絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存で失敗するケースがあります（警告ログで通知されます）。
- DuckDB / SQLite へのバインドや executemany の空リスト制約など、バージョン差異に注意して運用してください（コード中に互換性対策あり）。

---

この README はコードベースの各モジュールの説明をまとめたものです。運用ポリシーや環境依存のセットアップ（systemd / Supervisor / コンテナ化 等）は別途運用設計書に従ってください。質問や追加ドキュメントが必要であれば具体的な用途（例: systemd ユニットファイル例、Dockerfile、テスト手順）を教えてください。