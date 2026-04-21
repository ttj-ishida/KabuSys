# KabuSys — 日本株自動売買システム

このリポジトリは、日本株の自動売買システム「KabuSys」のコアライブラリと起動スクリプト群を含みます。  
主な目的は、戦略の研究・信号生成・ポートフォリオ構築・発注管理・監視・レポート生成までを一貫して提供することです。

バージョン: 0.1.0

---

## 概要

- Python モジュール群として機能を提供し、起動スクリプトはモジュールとして実行可能（`python -m kabusys.*`）。
- 発注エンジン（ExecutionEngine）と監視プロセス（MonitoringEngine）を分離して運用可能。
- Paper Trading（ペーパートレード）モードをサポートし、本番 DB と分離して動作させられます。
- DuckDB を分析用 DB として使用し、SQLite を監視 / トレードログ保存用に使用。
- OpenAI API を利用したニュース NLP / レジーム判定モジュールを実装（任意）。

---

## 主な機能一覧

- 起動関連スクリプト
  - run_execution: 発注エンジン起動
  - run_monitoring: 監視ループ起動
- 設定支援
  - config_setup: .env 対話ウィザードで初期設定を作成
  - validate_config: 環境変数と config/*.yaml の検証 CLI
- 監視
  - MonitoringDB: SQLite による監視ログ永続化
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch
  - MonitoringEngine: 各モニタを束ねたポーリング実行
- 発注関連（Execution）
  - ブローカーファクトリ（本番 / モック切替）
  - OrderManager / OrderRepository / RiskManager / ExecutionEngine
- ポートフォリオ構築（純粋関数）
  - 候補選定、重み付け、ポジションサイズ計算（等分・スコア重み・リスクベース）
  - セクター上限適用、レジーム乗数
- リサーチ＆統計
  - factor_research: Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC、統計サマリ等
- AI（任意）
  - news_nlp: ニュースを LLM で評価して銘柄スコア化
  - regime_detector: マクロ + 指数 MA で市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード検証レポート生成

---

## 必要条件 (概略)

- Python 3.9+
- 必要な Python パッケージ（一例）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML (config 検証時に推奨)
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（kabuステーション API / J-Quants / OpenAI を使う場合）

（実際の requirements.txt がある場合はそれを使ってください）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成して依存をインストール（上記参照）
3. 環境変数の作成
   - 対話で .env を作る:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードに従い、`JQUANTS_REFRESH_TOKEN` や `KABU_API_PASSWORD` など必須値を入力してください。
   - 既に .env がある場合はそれを編集してください。
   - 注意: `.env` は機密情報を含むため Git にコミットしないでください。

4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   問題がなければ OK が表示されます。警告を厳密に扱いたい場合は `--strict` を付与します。

5. データ / ログディレクトリ
   - デフォルト DB / ログパス:
     - DuckDB: `data/kabusys.duckdb`
     - Monitoring SQLite: `data/monitoring.db`
     - Paper trading SQLite: `data/paper_trading.db`
     - ログ: `logs/`
   - 必要に応じて .env で上書きしてください（`DUCKDB_PATH`, `SQLITE_PATH` 等）。

---

## 重要な環境変数（代表）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 動作モード
  - KABUSYS_ENV — `development` | `paper_trading` | `live`（デフォルト: development）
    - `paper_trading` の場合、発注は MockBrokerClient を使用し、データは paper_trading 用 DB に記録
- DB / ファイル
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- ロギング / 監視
  - LOG_LEVEL（例: INFO）
  - LOG_DIR（ログ出力先フォルダ）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- Paper Trading 固有
  - PAPER_FILL_MODE — `instant` | `partial` | `never` | `reject`（デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector を使う場合に必要

---

## 使い方（起動例）

1. Execution Engine（発注エンジン）起動
   - 通常起動:
     ```
     python -m kabusys.run_execution
     ```
   - 注意:
     - `KABUSYS_ENV=paper_trading` の場合、発注はモック実行され paper_trading DB に記録されます。
     - 起動時に `data/stop_requested.flag` が存在すると起動を行わず終了します。
     - 実行中は `data/execution.pid` が作成されます。

2. Monitoring（監視）起動
   ```
   python -m kabusys.run_monitoring
   ```
   - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
   - 監視は Settings に依存して本番の sqlite_path を使用（環境に依らず同じ監視 DB を使う設計）。
   - 停止は `data/stop_requested.flag` を作成するか、Ctrl+C。

3. 設定ウィザード / 検証
   - .env 作成:
     ```
     python -m kabusys.config_setup
     ```
   - 検証:
     ```
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict
     ```

4. ツール（Paper Trading レポート）
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - `--db` で SQLite ファイルを指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可能。

5. ライブラリとして利用（例）
   - Python REPL から factor 計算:
     ```py
     from datetime import date
     import duckdb
     from kabusys.research import calc_momentum

     conn = duckdb.connect("data/kabusys.duckdb")
     res = calc_momentum(conn, date(2026, 4, 1))
     ```
   - AI スコアリング（OpenAI API キーが必要）:
     ```py
     from kabusys.ai.news_nlp import score_news
     score_news(conn, target_date, api_key="sk-...")
     ```

---

## Kill Switch / 停止フラグ

- KillSwitch は `data/kill.flag` を書くことで発注エンジンの停止指示を行います（ExecutionEngine は起動時にこのフラグの有無や起動中のフラグを確認）。
- `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では推奨されません（安全のため `0` を推奨）。
- `data/stop_requested.flag` は run_* スクリプトの外部停止リクエストに使用されます（手動で作成すると監視・実行ループが終了します）。

---

## ログ

- デフォルトログディレクトリ: `logs/`
- ログは console（stdout）と日次ローテートされたファイルに出力されます（`logs/<app_name>.log`）。
- ログレベルは `LOG_LEVEL` で制御（`setup_logging` を通じて統一設定）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装による)
  - execution/
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで生成されることが想定)
  - logs/ (ランタイムで生成されることが想定)
- config/
  - *.yaml (system_config.yaml 等のテンプレート / 実設定ファイル)

（実際のリポジトリには上記に加えて他の補助モジュールが含まれている可能性があります）

---

## よくある問題と対処

- OpenAI を使うときに API キーがない
  - `OPENAI_API_KEY` を .env に設定するか、関数呼び出し時に `api_key` を渡してください。
- ログディレクトリ・DB ファイルの作成に失敗する
  - 実行ユーザのファイル書き込み権限を確認してください。`logs/` や `data/` の親ディレクトリを作成し、書き込み可能にしてください。
- psutil によるプロセス優先度設定が失敗する（AccessDenied）
  - 権限が不足している可能性があります。警告が出ますが処理は継続します。
- DuckDB / PyYAML が無いと一部機能（リサーチ・config 検証）が制限されます
  - 必要に応じてパッケージをインストールしてください。

---

## 注意事項

- `.env` に含まれる機密情報は Git 等で共有 / コミットしないでください。
- `KABUSYS_ENV=live` での運用は本番取引を行う設定です。設定値（特に API パスワード・通知先）を十分に確認してください。
- Kill Switch と監視アラートは本番で重要な安全機構です。監視設定や通知設定は必ず確認してください。

---

以上がこのコードベースの README（日本語）です。  
追加してほしい情報（例: 実行時のログ出力例、詳しい設定パラメータ一覧、各モジュールの API 参照など）があれば教えてください。必要に応じて追記・整備します。