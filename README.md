# KabuSys

日本株向け自動売買システムのコードベース。ポートフォリオ構築・ポジションサイジング・実行エンジン・監視・研究用ユーティリティ・AIベースのニュース解析等を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は次の通りです。

- シグナル → ポートフォリオ候補選定 → 重み付け → 株数算出（単元株丸め、リスク制限を含む）
- 実行エンジン（ExecutionEngine）による発注管理（本番 / ペーパートレード分離）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- DuckDB を用いたリサーチ（ファクター計算・特徴量探索）
- OpenAI を用いたニュース NLP（センチメント集約・市場レジーム判定）
- 各種 CLI ツール（.env ウィザード、設定検証、paper trading レポート）

設計方針の一部:
- DB 関連は DuckDB（時系列・研究用）と SQLite（軽量永続化／監視ログ・ペーパートレード）を併用
- 本番／ペーパーを明確に分離（KABUSYS_ENV=paper_trading は paper DB を使用）
- ルックアヘッドバイアス対策（日時参照を明示的に行う設計）
- フェイルセーフ：外部 API 失敗時は安全にフォールバックする実装

---

## 機能一覧

- 環境設定ウィザード（kabusys.config_setup）
  - 対話式で `.env` を生成 / 更新
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数や config/*.yaml の存在・基本整合性をチェック
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - 本番 / ペーパートレード切替、専用 DB、PID ファイル、停止フラグ対応
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor のポーリング、停止フラグ検知、MONITOR_POLL_INTERVAL 指定可
- 監視コンポーネント
  - SystemMonitor：プロセス稼働・リソース・データ鮮度監視
  - TradeMonitor：注文状況・滞留・約定異常検出（コード上に実装）
  - RiskMonitor：ドローダウン・ポジション上限監視、リスクイベントログ
  - KillSwitch：条件に応じて `data/kill.flag` を書き込み ExecutionEngine を停止
  - MonitoringDB：監視用 SQLite のスキーマ初期化と読み書き API
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額／スコア加重、ポジションサイズ算出、セクター上限、レジーム乗数
- 研究用モジュール（kabusys.research）
  - ファクター計算（モメンタム・ボラティリティ・バリューなど）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI モジュール（kabusys.ai）
  - ニュース NLP（OpenAI を使った銘柄毎センチメント → ai_scores に保存）
  - 市場レジーム判定（ETF MA とマクロニュースを合成）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発 / ローカル実行向け）

前提: Python 3.9+ 想定。環境に応じて仮想環境を作成してください。

1. リポジトリをチェックアウトし、仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install -r requirements.txt
   - このコードベースで想定される主要依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証時に YAML のパースを行う場合）
   - （requirements.txt がない場合は必要なものを個別にインストール）

3. 環境変数設定（.env）
   - `python -m kabusys.config_setup` を実行して、対話形式で `.env` を作成できます。
   - 主要な環境変数（最低限設定が必要なもの）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)

5. DB 初期化
   - 監視 DB（SQLite）は起動スクリプト内で自動作成 / マイグレーションされます（init_monitoring_db）。
   - DuckDB ファイルは研究用のデータ投入が必要です（別途データパイプラインを実行）。

---

## 使い方（主要コマンド例）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（デフォルト動作）
  - python -m kabusys.run_execution
  - 停止方法: 実行中に `data/stop_requested.flag`（または実装に従う）を作成すると停止処理が走ります
  - ペーパートレード: KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、data/paper_trading.db に記録されます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL（秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings に定義された sqlite_path を常に使用します（環境に依存せず本番監視 DB）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パス指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラムから呼び出す例）
  - news_nlp を使ってニューススコアを書き込む:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="YOUR_OPENAI_KEY")
  - regime_detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="YOUR_OPENAI_KEY")
  - 注意: API キーは環境変数 OPENAI_API_KEY でも指定可能

- ログ
  - ログは `kabusys.utils.logging_setup.setup_logging` により統一的に出力されます
  - デフォルトログディレクトリ: logs/
  - 環境変数 LOG_DIR, LOG_LEVEL で上書き可能

---

## 重要な運用・挙動メモ

- KABUSYS_ENV（実行モード）
  - development: 開発用
  - paper_trading: ペーパートレード（実際の発注を行わず、専用の SQLite に記録）
  - live: 本番（実際に発注）
- paper_trading の DB は paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）で分離
- 監視（monitoring）は常に本番 sqlite_path を使用（環境に関係なく監視データを集約）
- Kill Switch
  - RiskMonitor 等の判定により `data/kill.flag` が書かれると、ExecutionEngine に停止シグナルとして作用します
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると自動クリア（本番では注意）
- プロセス優先度
  - 実行スクリプトは起動時に `set_process_priority("high")` を試みます（プラットフォーム依存・権限が必要）

---

## ディレクトリ構成（主要ファイル・モジュール説明）

- src/kabusys/
  - __init__.py — パッケージ情報（バージョン）
  - config.py — 環境変数/設定読み込みロジック。自動で `.env` をロード（必要であれば無効化可）
  - config_setup.py — 対話式 .env ウィザード（.env 作成／更新）
  - validate_config.py — 起動前の設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト（PID/停止フラグ/ペーパートレード対応）
  - run_monitoring.py — SystemMonitor のポーリングスクリプト（MONITOR_POLL_INTERVAL）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（等分配／スコア加重）
    - position_sizing.py — 株数算出、単元株処理、集約上限スケールダウン
    - risk_adjustment.py — セクター上限、レジーム乗数
    - __init__.py — 主要 API の再公開

  - monitoring/
    - monitoring_db.py — 監視用 SQLite スキーマ初期化 + DB 操作 API（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — リソース・プロセス・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み/管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py (参照あり) — アラート送信ロジック（LINE 等）※コード上で実装箇所あり

  - execution/ (発注関連: BrokerFactory, ExecutionEngine, OrderManager 等) — 実行ロジック（スケルトン/詳細は該当ファイルを参照）

  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
    - __init__.py — 研究用 API の再公開

  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に書き込むロジック
    - regime_detector.py — ETF MA とマクロニュースの LLM 評価を組み合わせたレジーム判定
    - __init__.py — AI API の再公開

  - tools/
    - paper_verification_report.py — ペーパートレード結果の検証レポート出力

  - utils/
    - logging_setup.py — 共通ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py

---

## 開発・拡張ポイント（参考）

- DuckDB 上のテーブル（prices_daily / raw_financials / raw_news 等）へのデータ投入パイプラインは別途実装が必要
- ExecutionEngine のブローカ実装は本番 API と Mock を切り替え可能（BrokerClientFactory を参照）
- AI API 呼び出しは OpenAI SDK に依存。テスト時は該当呼び出し関数をモックして挙動を確認可能
- ユニットテスト・統合テストの整備を推奨（特に外部 API・ファイル I/O 周り）

---

## ライセンス / 注意事項

- この README はコードベースの説明を目的としています。実際の運用では必ず十分なテストと安全対策（注文の取り扱い、API キー管理、Kill Switch の運用ポリシー等）を行ってください。
- `.env` を絶対に公開リポジトリにコミットしないでください。

---

必要であれば、README に含める具体的な .env のサンプルやコマンド例（systemd / cron での運用、ログローテーション設定例、CI用の設定検証手順など）を追加します。どの情報をより詳しく載せたいか教えてください。