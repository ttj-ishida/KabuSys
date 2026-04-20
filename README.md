# KabuSys

日本株向け自動売買システムのコードベース（README）。このドキュメントはソースコードから自動作成しています。実行・開発の際の参照にしてください。

---

## 概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。主な責務は以下のとおりです。

- ExecutionEngine：発注ロジック、リスク管理、注文管理（paper/live 切替対応）
- Monitoring：システム状態、注文状況、リスクの常時監視とアラート、Kill Switch
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI：ニュースを LLM（OpenAI）で解析してセンチメント・レジーム判定
- Portfolio：候補選定、重み付け、ポジションサイズ計算
- ユーティリティ：ロギング設定、プロセス優先度設定、設定読み込み（.env）

プロジェクトは環境変数と `.env` による設定管理を基本とし、paper_trading モードでは本番 DB と分離された専用 SQLite を使用して安全に検証できます。

---

## 機能一覧

- Execution
  - Paper trading / Live 切替（KABUSYS_ENV）
  - BrokerClientFactory 経由のブローカー抽象化（Mock を含む）
  - OrderRepository / OrderManager / Reconciler / RiskManager の組み合わせで発注フローを実現
- Monitoring
  - システムリソース監視（CPU・メモリ・ディスク）
  - データ鮮度チェック（DuckDB に格納された価格データを参照）
  - 取引ログ監視（滞留注文・異常約定などの検出）
  - リスク監視（ドローダウン・ポジション上限等）と Kill Switch（data/kill.flag の書き込み）
  - 監視ループ・ログ永続化（SQLite）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI
  - ニュース記事を LLM（OpenAI）でスコアリングし ai_scores に保存
  - マクロニュース + ETF MA による市場レジーム判定（bull/neutral/bear）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- ツール
  - インタラクティブな `.env` 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper trading 検証レポート生成ツール

---

## セットアップ手順

以下はローカル開発 / 実行に必要な一般的手順です。実プロジェクトでの最終的な要件はプロジェクトの requirements.txt 等を参照してください。

1. Python 環境を準備（推奨: Python 3.10+）
   - virtualenv / venv を使うことを推奨します
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix
     .venv\Scripts\activate     # Windows
     ```

2. 必要なパッケージをインストール
   - 主な依存（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - 実際はプロジェクトで提供される requirements.txt があればそちらを使用してください。

3. プロジェクトのルートに `data/` と `logs/` ディレクトリを作成（多くは自動作成されますが明示的に作ると安心）
   ```
   mkdir -p data logs
   ```

4. 環境変数設定（`.env` を作成）
   - 対話式ウィザードでの作成:
     ```
     python -m kabusys.config_setup
     ```
   - or 手動で `.env` を作成。主なキーとデフォルト（コード参照）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)
     - OPENAI_API_KEY（AI 機能利用時必須）
     - PAPER_FILL_MODE（paper_trading 時の約定モード: instant|partial|never|reject）
     - KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

5. 設定検証（オプション）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

代表的な起動・ユーティリティ例を示します。

- ExecutionEngine を起動（paper/live は KABUSYS_ENV で切替）
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に PID ファイル (data/execution.pid) を作成し、停止は data/stop_requested.flag を作成すると検出して終了します。
  - paper_trading モードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。

- Monitoring を起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで検出してループ終了します。
  - Monitoring は Settings の sqlite_path（デフォルト data/monitoring.db）を使用してログを永続化します（環境に依らず本番監視 DB を使用する仕様あり）。

- Kill Switch 操作（手動で Execution を止めたい場合）
  - kill.flag を作成すると ExecutionEngine 側で停止トリガーとして扱う仕組みがあります（KillSwitch が評価して作成することが多い）。
  - ファイルパスは Settings.kill_flag_path（デフォルト data/kill.flag）。

- .env の作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定：
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI / Research の利用（ライブラリ呼び出し）
  - ニューススコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...) による接続
    score_news(duckdb_conn, target_date=<date>, api_key="...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date=<date>, api_key="...")
    ```
  - ファクター計算:
    ```py
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    calc_momentum(duckdb_conn, target_date=<date>)
    ```

---

## 運用上の注意

- 本番運用時は KABUSYS_ENV=live に設定し、LINE 通知等のアラート設定を必ず確認してください。
- KILL_FLAG_CLEAR_ON_START=1 は本番では危険（Kill Switch を自動でクリアしてしまう）ため設定しないことを推奨します。
- OpenAI API を使う機能は API キー（OPENAI_API_KEY）が必要です。失敗時はフェイルセーフで代替処理やスキップする実装が多く含まれますが、API 利用料金・レート制限に注意してください。
- ログは `logs/<app_name>.log` に日次でローテートされます。ログディレクトリが作れない場合はコンソール出力のみになります。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主なファイル・ディレクトリと役割です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper trading 検証レポート生成
  - execution/ — 発注エンジン関連（BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等）
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 取引ログの監視（滞留注文等）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor の統合ループ
    - alert_manager.py — （アラート送信）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・集計上限処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム／ボラティリティ／バリュー等の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マーケットレジーム判定（OpenAI + ETF MA）
  - utils/
    - logging_setup.py — 一貫したログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定

プロジェクトルート（リポジトリ）には通常以下が存在します（コードから参照されるファイル・ディレクトリ）：
- .env, .env.local（設定ファイル）
- config/ （YAML 設定ファイル群, 例: system_config.yaml 等）
- data/（SQLite / pid / flag 等）
- logs/（ログファイル）

---

## 参考コマンドまとめ

- .env 作成ウィザード：
  ```
  python -m kabusys.config_setup
  ```
- 設定検証：
  ```
  python -m kabusys.validate_config
  ```
- 実行エンジン起動：
  ```
  python -m kabusys.run_execution
  ```
- 監視ループ起動：
  ```
  python -m kabusys.run_monitoring
  ```
- Paper trading レポート：
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に追加してほしい項目（依存関係の固定バージョン、CI 設定、デプロイ手順、テストの実行方法など）があれば教えてください。README をプロジェクトで使う形式に合わせて調整します。