# KabuSys

日本株向け自動売買システムの小規模実装サンプル。  
このリポジトリは、戦略の研究・ファクター計算・ポートフォリオ構築・発注エンジン・監視・アラート・Paper Trading 検証などの主要コンポーネントを含みます。

## 概要
- ファクター計算と研究用に DuckDB を利用したデータ処理
- 実際の発注は kabuステーション API 経由（本番）または MockBroker（ペーパートレード）
- ExecutionEngine（発注）と Monitoring（監視）は独立したプロセスとして動作
- LINE 通知／OpenAI（ニュースNLP・レジーム検出）連携機能を備える
- 軽量な SQLite ベースの監視ログ（monitoring.db）で状態を永続化

## 主な機能一覧
- portfolio: 候補選定・重み算出・ポジションサイジング・セクター制限
- research: ファクター計算（Momentum / Volatility / Value）、将来リターン、IC 計算、統計サマリー
- ai:
  - news_nlp.score_news: ニュース記事を OpenAI に投げて銘柄ごとのセンチメントスコアを生成し ai_scores テーブルへ保存
  - regime_detector.score_regime: MA 乖離とマクロニュースを合成し市場レジーム（bull/neutral/bear）を判定して保存
- execution:
  - ExecutionEngine（発注エンジン） — 実際のブローカークライアント（または MockBroker）を利用して注文管理
  - リスク管理（RiskManager）、注文履歴の永続化
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - AlertManager（LINE Push）による通知
  - KillSwitch による安全停止（データ/kill.flag による）
- tools:
  - paper_verification_report: Paper Trading の検証レポート生成

## 前提 / 必須要件
- Python 3.9+
- 推奨インストールパッケージ（例）:
  - psutil
  - duckdb
  - openai
  - requests
  - PyYAML（config の検証を行う場合）
- ネットワーク接続（kabuステーション API / OpenAI を使う場合）

インストール例:
```bash
pip install psutil duckdb openai requests pyyaml
```

（プロジェクトに requirements.txt が無い場合は上記パッケージを適宜追加してください）

## 環境設定 (.env)
起動前に環境変数を設定します。プロジェクトルートに `.env` を置くと自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

重要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

その他（例・デフォルト）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 時の専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を利用する場合に必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

簡易的な .env 作成ウィザード:
```bash
python -m kabusys.config_setup
```

設定検証:
```bash
python -m kabusys.validate_config        # 警告は許容
python -m kabusys.validate_config --strict  # 警告も失敗扱い
```

## 実行方法

プロジェクトはパッケージとしてモジュール経由で起動できます（プロジェクトルートを PYTHONPATH に含める / カレントをプロジェクトルートにして実行してください）。

1. ExecutionEngine（発注エンジン）
- 通常の起動:
  ```bash
  python -m kabusys.run_execution
  ```
- KABUSYS_ENV=paper_trading の場合は MockBroker を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ保存されます。
- 起動時、data/execution.pid に PID が書き込まれます。停止は data/stop_requested.flag を作成するか、KillSwitch により data/kill.flag が書かれた場合に行われます。

2. Monitoring（監視ループ）
- 起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
- 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）。
- stop フラグファイル data/stop_requested.flag を作成すると監視ループが終了します。

3. Paper Trading 検証レポート
- レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- DB パス指定:
  ```bash
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

## プログラム的な利用（ライブラリ呼び出し）
- ai.score_news: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- ai.regime_detector.score_regime: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- research.calc_momentum 等: kabusys.research.calc_momentum(duckdb_conn, date)
- portfolio モジュール: kabusys.portfolio.select_candidates / calc_equal_weights / calc_position_sizes など

例（簡易）:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 4, 11))
```

## 停止・Kill Switch の動作
- KillSwitch は監視から評価されると data/kill.flag を書き込み、ExecutionEngine はこのファイルで停止する設計です。
- 手動で停止する場合:
  - 監視を止めたい: data/stop_requested.flag を作る（run_monitoring が検知して終了）
  - ExecutionEngine を停止したい: data/stop_requested.flag を作成するか、kill.flag を作成（KillSwitch が置く）／pid を参照してプロセスを終了する
- kill.flag を消す（起動前のクリーンアップ）:
  - 手動でファイルを削除
  - または ExecutionEngine の起動フラグ KILL_FLAG_CLEAR_ON_START=1（ただし本番では危険）

## データベース
- DuckDB: 分析用（data/kabusys.duckdb）
- SQLite（監視）: data/monitoring.db（監視ログ・トレードログ・リスクログ等）
- Paper Trading 用 SQLite（紙上でデータ分離）: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

注意: run_monitoring は常に Settings.sqlite_path を使用して監視データを操作します（環境に依らず本番監視 DB に書き込む仕様）。

## ログとプロセス優先度
- 起動スクリプトは起動直後に set_process_priority("high") を呼びます（psutil を使用）。権限不足の場合は警告を出し続行します。
- LOG_LEVEL 環境変数でログ出力レベルを制御できます。

## ディレクトリ構成（抜粋）
プロジェクトの主要ファイル / ディレクトリ（src/kabusys 配下）:
- __init__.py
- config.py — 環境変数と Settings
- config_setup.py — .env を対話式で作成するウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py, alert_manager.py, kill_switch.py
- execution/ (発注エンジン関連)
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py など
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

（上記はコードベースの主要モジュール。各サブモジュールにさらに実装ファイルがあります）

## 注意事項 / 運用上のポイント
- .env は絶対に Git にコミットしないでください（config_setup でもその旨が明記されています）。
- 本番運用時は KABUSYS_ENV=live を慎重に確認してください（validate_config の警告を参照）。
- OpenAI / LINE / kabuステーション の API キーやトークンは正しく設定してください。AI モジュールは API 利用量やレート制限に注意して運用してください。
- process priority の設定は OS に依存し、権限が必要な場合があります（Linux の nice を下げる/Windows の優先度変更など）。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を利用）。

---

README の内容はコードベースのコメント・設定・使用方法に基づいてまとめています。追加で「導入手順（Docker / systemd unit ファイル例）」「API キーの発行手順」「詳細な DB スキーマ ドキュメント」などを希望する場合は、必要な情報に応じて追記できます。