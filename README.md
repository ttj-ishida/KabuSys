# KabuSys

日本株自動売買システムの一部を抜粋した実装リポジトリです。  
この README はリポジトリ内のコードベース（src/kabusys）を元に、日本語で概要・機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

重要: .env ファイルにはシークレット（API トークン・パスワード等）を含むため、決して Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買および関連ツール群です。本リポジトリには次の主要機能を含みます。

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - 本番／ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ブローカークライアント抽象化（実運用では kabuステーション / テストでは Mock）
  - 注文管理、リスク管理、整合処理などのコンポーネントを組み立てて実行
- 監視（Monitoring）コンポーネント（run_monitoring / monitoring パッケージ）
  - システム状態、注文滞留、リスク指標（ドローダウン等）を定期ポーリングし永続化
  - Kill Switch（条件を満たした場合に flag ファイルを書き ExecutionEngine を停止）
- ポートフォリオ構築ロジック（portfolio パッケージ）
  - 候補選定、配分計算、リスク調整、ポジションサイズ決定等の純粋関数群
- リサーチ／ファクター計算（research パッケージ）
  - Momentum / Volatility / Value 等のファクター算出、IC や将来リターン計算
- AI 支援モジュール（ai パッケージ）
  - ニュースの NLP スコアリング（OpenAI API を使用）
  - 市場レジーム判定モジュール（regime_detector）
- ユーティリティ・ツール
  - .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

データ永続化:
- DuckDB: 主に時系列価格やニュースなど解析用（デフォルト: data/kabusys.duckdb）
- SQLite: 監視ログ・ペーパートレード履歴等（デフォルト: data/monitoring.db、ペーパー用: data/paper_trading.db）

---

## 主な機能一覧

- 設定関連
  - .env ウィザード（kabusys.config_setup.run_wizard）
  - 設定検証（kabusys.validate_config）
  - 自動 .env ロード（プロジェクトルートの .env / .env.local、必要時無効化可能）
- 実行エンジン
  - ブローカー抽象化（本番 / ペーパーの切替）
  - OrderRepository / OrderManager / RiskManager / Reconciler 等の連携
  - PID ファイル管理・外部停止（stop flag）対応
- 監視
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch + AlertManager による自動停止・通知連携
  - MonitoringEngine による定期ポーリング（MONITOR_POLL_INTERVAL で間隔指定可）
- ポートフォリオ構築
  - 候補選定、等分配 / スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め / aggregate cap / cost buffer）
- リサーチ
  - ファクター（モメンタム・ボラティリティ・バリュー）計算（DuckDB 利用）
  - 将来リターン、IC、統計サマリー
- AI（OpenAI）
  - ニュースを LLM でセンチメントスコアリング（バッチ・リトライ・バリデーション実装）
  - マクロニュースと ETF MA を合成した市場レジーム判定（冪等 DB 書き込み）
- ツール
  - Paper Trading の検証レポート出力（成功率・レイテンシ・稼働率等）

---

## セットアップ手順（ローカル開発向け）

以下は一般的な手順です。プロジェクトに requirements.txt がある想定で書きます（なければ必要なパッケージをインストールしてください）。

1. リポジトリをチェックアウト
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - 必要な主要パッケージ（参考）:
     - duckdb, psutil, openai, PyYAML（config 検証用は任意）

4. .env の初期作成
   - python -m kabusys.config_setup
     - ウィザードに従い J-Quants、kabu API パスワード、DB パス等を設定
   - または手動で .env を作成（例は下記参照）

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数が足りない場合は補完してください

6. DB ファイルの初期化
   - run_monitoring / run_execution を実行すると、init_monitoring_db により SQLite のスキーマが作成されます
   - DuckDB は既存ファイルを使うか、新規作成されます

注意:
- 自動で .env を読み込む機能は kabusys.config が実装しています。テスト等で自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主な環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
  - paper_trading の場合は MockBroker を使用し、ペーパー用 DB（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動でクリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で使用、デフォルト: 60）

---

## 使い方（よく使うコマンド例）

- .env を作る（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗にする）: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定することで MockBroker を使い、ペーパー用 DB に記録します:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ExecutionEngine は data/execution.pid（デフォルト）を使用し、停止は data/stop_requested.flag を作成するか kill.flag によって行われます。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を指定する（例 30 秒）:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（監視 DB）を使ってログを保存します。monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照します。

- Paper Trading の検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- AI スコアリング / レジーム判定（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

バックグラウンド実行例（Linux）:
- nohup env $(cat .env | xargs) python -m kabusys.run_execution > logs/execution.log 2>&1 &

停止フラグ:
- 実行中プロセス停止を促すにはプロジェクト内の data/stop_requested.flag（run scripts が参照）や data/kill.flag（KillSwitch 用）を利用します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／ディレクトリ構成です（実際のリポジトリに合わせて調整してください）。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env 読み込みと Settings クラス
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 設定検証 CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（OpenAI 呼び出し、スコア保存）
    - regime_detector.py            — 市場レジーム判定
  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（スキーマ作成含む）
    - monitoring_engine.py          — 各 Monitor を束ねるエンジン
    - system_monitor.py             — システム状態・データ鮮度監視
    - trade_monitor.py              — 注文滞留/約定異常監視
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag 管理
    - alert_manager.py              — （未完/要実装の可能性）
  - execution/
    - (OrderRepository, ExecutionEngine, BrokerFactory 等 — 実行関連コンポーネント)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py            — プロセス優先度・CPU affinity 設定
    - __init__.py
  - data/                            — 既定のデータ置き場（実行時に使用）
    - monitoring.db (デフォルト: data/monitoring.db)
    - kabusys.duckdb (デフォルト: data/kabusys.duckdb)
    - paper_trading.db (ペーパートレード用)

---

## 実装上の注意点 / 補足

- .env の自動読み込み:
  - config._find_project_root() によりプロジェクトルートが検出される場合、.env / .env.local が自動で読み込まれます。
  - テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ペーパートレード:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、ペーパー用 SQLite に結果を記録して本番 DB と分離します。
- 監視（Monitoring）は監視用の sqlite_path を常に使用します（KABUSYS_ENV に影響されません）。
- OpenAI 利用:
  - API 呼び出しはリトライとエラーハンドリングが盛り込まれていますが、API キーと利用料金には注意してください。
  - レスポンスのバリデーション（JSON 抽出・キー検査等）を行っていますが、完全に LLM の出力を保証するものではありません。
- DB マイグレーション:
  - init_monitoring_db は冪等にテーブルを作成し、既存スキーマに列がない場合は ALTER TABLE で追加する簡易マイグレーション処理を行います。
- 権限・実行優先度設定:
  - utils.process_priority.set_process_priority はプラットフォーム差異に配慮していますが、権限不足により設定が失敗する場合があります（警告ログ）。

---

README はここまでです。実際に運用・デプロイする際は、本 README に加えて運用ドキュメント（起動スクリプトの supervisor/systemd 設定、ログローテーション、バックアップ、監視・通知チャネルの設定）を用意してください。必要であれば、上記のコマンドや .env のサンプルテンプレート（.env.example）を追加で作成することを推奨します。