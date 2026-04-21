# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。  
本ドキュメントは開発者向けにプロジェクトの概要、主要機能、セットアップ・起動手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注：このリポジトリはライブラリ／実行スクリプト群を含みます。実運用（KABUSYS_ENV=live）では十分な注意と事前検証を行ってください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 設定（.env）
- 使い方（起動・コマンド）
- 停止・Kill Switch の扱い
- ディレクトリ構成（主要ファイルの説明）
- 注意事項

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム向けフレームワークです。  
主に以下を提供します：

- 戦略に基づく銘柄選定・ポジションサイズ計算（ポートフォリオ構築）
- ExecutionEngine（実際の発注・ペーパートレードを含む）
- 監視（System / Trade / Risk）と Kill Switch（安全停止）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI を用いたニュースセンチメント（OpenAI 拡張）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計上、DuckDB を分析用 DB、SQLite を監視／注文ログ用に使い分けています。ペーパートレードは本番 DB と分離されます。

---

## 主な機能一覧

- Execution
  - ExecutionEngine による発注管理、OrderManager / RiskManager / Reconciler 等の組合せ
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、ペーパー用 DB（data/paper_trading.db）に記録
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスクやデータ鮮度、Execution プロセス生存の監視
  - TradeMonitor：滞留注文／約定異常などの検知（trade_logs）
  - RiskMonitor：ドローダウン、ポジション上限の監視とアラート記録
  - KillSwitch：一定条件で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine：上記モニタ群の定期実行・アラート連携
- Portfolio
  - 候補選定、スコア重みによる重み付け、セクター制約、ポジションサイズ計算（単元丸め/利用可能現金に応じたスケール等）
- Research
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
- AI
  - news_nlp: OpenAI を使ったニュースの銘柄別センチメント集計（ai_scores へ書き込み）
  - regime_detector: ETF（1321）MA・マクロニュースを合成して市場レジーム判定
- ユーティリティ
  - logging_setup：統一的なログ設定（コンソール + 日次ローテートファイル）
  - process_priority：プロセス優先度 / CPU affinity の設定
- ツール
  - config_setup: .env を対話的に作成／更新するウィザード
  - validate_config: 起動前に環境変数・config/*.yaml 等のチェック
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL レポート出力

---

## 必要条件

- Python 3.9 以上（型ヒントの書式やモジュール想定）
- 必須ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai
- 推奨／オプション:
  - PyYAML（config/*.yaml の検証、validate_config が YAML を検査する場合に使用）
- SQLite は標準ライブラリに含まれます

（上記はソースから推測した依存です。実際には requirements.txt や Poetry/Poetry.lock を参照してください。）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、作業ディレクトリへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - 任意: pip install pyyaml
4. ディレクトリ作成（必要に応じて）
   - デフォルトでは data/ と logs/ を使用します。起動時に自動作成される場合がありますが、権限エラー回避のため作成しておくとよいです。
     - mkdir -p data logs

---

## 設定（.env）

環境変数は .env / .env.local / OS 環境変数で指定できます。自動ロードの順序は OS 環境 > .env.local > .env（自動読み込みはデフォルトで有効）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（抜粋）:

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API
  - KABU_API_PASSWORD : kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV : development | paper_trading | live
    - paper_trading: MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード DB、デフォルト: data/paper_trading.db)
- ログ・運用
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR (ログ保存ディレクトリ、デフォルト: logs/)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか
- Paper Trading 固有
  - PAPER_FILL_MODE : instant | partial | never | reject （デフォルト: instant）
- モニタリング
  - MONITOR_POLL_INTERVAL : 監視ループのポーリング間隔（秒、デフォルト 60）
- OpenAI
  - OPENAI_API_KEY : AI 機能を使う場合に必要（news_nlp, regime_detector）

.env を対話的に作るには:
- python -m kabusys.config_setup

設定の検証:
- python -m kabusys.validate_config
  - --strict オプションを付けると警告も失敗として exit(1)

---

## 使い方（起動 / コマンド例）

各スクリプトはモジュール実行形式で提供されています。

1. ExecutionEngine（取引エンジン）起動
   - python -m kabusys.run_execution
   - 起動前に .env を設定し、KABUSYS_ENV を確認してください。
   - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、ペーパートレード用 DB に記録します。

2. Monitoring（監視ループ）起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書きできます（デフォルト 60 秒）。
   - monitoring は常に production の sqlite_path を使用して監視情報を記録します（KABUSYS_ENV に依存しません）。

3. 設定ウィザード
   - python -m kabusys.config_setup
   - 対話形式で .env を生成・更新します。

4. 設定検証
   - python -m kabusys.validate_config
   - 起動前に設定漏れやファイル配置をチェックします。

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を使用

6. AI 機能（プログラム呼び出し）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB 接続を受け取り、必要に応じて OPENAI_API_KEY を参照します。

---

## 停止・Kill Switch の扱い

- 強制停止（運用者用の停止フラグ）:
  - data/kill.flag : KillSwitch が存在するかで ExecutionEngine を停止させる契機として使います（kill.flag が存在すると Execution を停止させるため、慎重に扱ってください）。
  - KillSwitch は RiskMonitor 等の結果に基づき kill.flag を作成します（冪等）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- 管理用の stop フラグ（run_monitoring/run_execution の内部使用）:
  - data/stop_requested.flag を置くと run_monitoring / run_execution のループが検知して優雅に終了します。

- PID ファイル:
  - Execution は data/execution.pid（デフォルト）に PID を書きます。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
  - run_execution.py — ExecutionEngine を起動するスクリプト
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - config.py — 環境変数 / 設定の読み取りユーティリティ（Settings クラス）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に書き込む処理
    - regime_detector.py — マクロ + ETF MA による市場レジーム判定

  - monitoring/
    - monitoring_db.py — SQLite ベースの監視テーブル作成・読み書きクラス（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視（SystemMonitor）
    - trade_monitor.py — （ファイル内に定義あり）発注ログ系監視（TradeMonitor）
    - risk_monitor.py — ドローダウン / ポジション上限監視（RiskMonitor）
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - alert_manager.py — アラート配信（LINE 等。実装参照）

  - execution/
    - execution_engine.py — 実際の取引セッションを管理する Engine（EngineConfig など）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注関連コンポーネント

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・スケーリング
    - risk_adjustment.py — セクター上限、レジーム乗数
    - __init__.py — エクスポート

  - research/
    - factor_research.py — モメンタム/ボラ/バリュー等のファクター計算（DuckDB を使用）
    - feature_exploration.py — 将来リターン・IC・統計解析
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレード DB から PASS/FAIL レポートを生成
    - __init__.py

  - utils/
    - logging_setup.py — 共通のログ設定（stdout + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

- data/
  - デフォルトで使用されるディレクトリ（monitoring.db、paper_trading.db、kill.flag、stop_requested.flag、execution.pid などを格納）

- logs/
  - ログファイルが保存される（例: logs/execution.log, logs/monitoring.log）

---

## 注意事項 / 運用上のガイド

- KABUSYS_ENV が `live` の場合は本番取引となります。LINE 通知設定や kill flag の取り扱い、設定の十分な検証を必ず行ってください。
- .env は機密情報（API トークン・パスワード）を含むため、決してバージョン管理システムにコミットしないでください。
- OpenAI を使用する機能は API キーの漏洩に注意し、コスト管理・レート制限を考慮してください。
- モジュール内には「フェイルセーフ」「冪等性」を意識した実装がありますが、実際の運用前にステージング／ペーパートレードで十分に検証してください。
- DuckDB・SQLiteスキーマはコード中でマイグレーション（カラム追加など）を行いますが、本番データのバックアップを必ず取ってください。
- ログディレクトリ作成に失敗した場合、ファイル出力はスキップされコンソールのみで動作します（setup_logging の仕様）。

---

必要があれば、README にサンプル .env のテンプレートや systemd / Supervisor 用のサービス定義、デバッグのためのログの見方、よくあるトラブルシューティング（OpenAI API エラー、DuckDB 接続エラー、psutil の権限エラー等）も追加します。どの情報が欲しいか教えてください。