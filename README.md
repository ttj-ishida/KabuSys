# KabuSys

日本株向け自動売買システムのライブラリ／運用スクリプト群です。  
このリポジトリには取引エンジン起動スクリプト、監視（Monitoring）周り、ポートフォリオ構築・ポジションサイジング、リサーチ（ファクター計算）、AI（ニュースセンチメント / レジーム判定）などの実装が含まれています。

バージョン: 0.1.0

---

## プロジェクト概要

- 自動売買のコアロジック（ExecutionEngine 系）は実装済み（broker 抽象化により本番 / ペーパートレード切替可能）。
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）でシステム安定性や注文異常、ドローダウン等を自動検知。
- Kill Switch（data/kill.flag）により危険条件で ExecutionEngine を安全に停止。
- DuckDB を用いたリサーチ用ファクタ計算、OpenAI を使ったニュース NLU（センチメント）および市場レジーム判定。
- ペーパートレードの検証用レポート生成ツール。

---

## 主な機能一覧

- 実行系起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番／ペーパー切替）
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループを起動
  - MonitoringEngine: 各 Monitor を束ねたポーリング処理、アラート送信、Kill Switch 評価
  - SystemMonitor / TradeMonitor / RiskMonitor: CPU/メモリ/ディスク、データ鮮度、注文滞留、約定異常、ドローダウンなどの監視
  - AlertManager: LINE Messaging API で通知（トークン未設定時はログのみ）
- 環境設定・検証ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml の妥当性チェック
- リサーチ / ポートフォリオ
  - research.factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB）
  - portfolio.*: 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- AI 関連
  - ai.news_nlp: ニュース記事を OpenAI でスコアリングして ai_scores に書き込み
  - ai.regime_detector: ma200 とマクロニュースの LLM 判定を合成して市場レジーム判定を行い DB に保存
- ユーティリティ
  - utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- 運用ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポート生成

---

## 前提・準備

- Python 3.10+
- 推奨インストール（例）:
  - pip install duckdb psutil openai requests PyYAML
  - （必要に応じて）その他ライブラリをインストールしてください。

備考:
- psutil: プロセス優先度や CPU 情報取得に使用。権限不足だと設定がスキップされ警告が出ます。
- DuckDB: リサーチ向けの分析 DB（ファイルは env で指定）。
- OpenAI: ニュース NLP / レジーム判定を使う場合は OPENAI_API_KEY が必要。

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を準備
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .\.venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests PyYAML

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 生成された .env は絶対に Git にコミットしないでください。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live） — デフォルト development
     - DUCKDB_PATH, SQLITE_PATH（監視 DB）, PAPER_TRADING_SQLITE_PATH
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信）

4. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. DB 初期化
   - run_execution/run_monitoring を起動すると内部で monitoring DB（SQLite）のテーブル作成（マイグレーション含む）を行います。手動での準備は通常不要です。

---

## 使い方

- ExecutionEngine 起動（本番 or ペーパートレード）
  - 実行:
    - python -m kabusys.run_execution
  - KABUSYS_ENV による振る舞い:
    - paper_trading: MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。本番 DB と分離されます。
    - live: 本番ブローカークライアントを使用（Kabu API 等）。
  - 起動時に data/stop_requested.flag が存在する場合はエンジンを起動せず終了します。
  - 実行中は data/execution.pid が作成され、SystemMonitor がプロセス存在をチェックします。

- Monitoring 起動
  - 実行:
    - python -m kabusys.run_monitoring
  - 仕様:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックします。
    - 監視は常に settings.sqlite_path（本番の monitoring DB）を使用します（KABUSYS_ENV に依存しません）。
    - 停止: data/stop_requested.flag を作成すると次のループで停止します。

- Kill Switch（ExecutionEngine を停止させる仕組み）
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）に理由文字列を書き込みます。
  - ExecutionEngine 側はこのフラグを監視し、存在時に安全に停止します。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 を使うと起動時に kill.flag を自動クリアします（本番では推奨しません）。

- 停止のトリガー管理
  - 管理者や外部プロセスから監視・停止を行うには下記のフラグファイルを操作します:
    - data/stop_requested.flag：run_execution/run_monitoring を安全に停止させるためのフラグ（スクリプトが存在を検知して終了）。
    - data/kill.flag：Kill Switch による ExecutionEngine 停止要求（自動で書かれることが多い）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 簡易的に稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定を出します。
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能
  - OpenAI を使う処理は API キーが必要です（環境変数 OPENAI_API_KEY または関数引数で指定）。
  - ai.score_news / ai.regime_detector.score_regime といった関数が公開 API（モジュール経由で呼び出し可能）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（monitoring.db）のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — ペーパー取引の約定モード: instant | partial | never | reject（デフォルト instant）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知に必要（任意）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（"1" で有効、開発用途）

---

## 運用上の注意

- process priority 設定:
  - run_execution / run_monitoring は最初に set_process_priority("high") を試みます。psutil による設定が権限不足で失敗しても警告ログを出し処理は継続します。
- DB 書き込みは各モジュールで commit を行います。複数プロセスから同一ファイルへ同時アクセスする場合はロックや運用フローに注意してください（特に本番環境）。
- AI 呼び出し（OpenAI）はレート制限・エラー耐性を持つよう実装されていますが、API キーやコストを含めて運用ポリシーを設定してください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0（無効）にすることを推奨します。

---

## ディレクトリ構成

（抜粋: 主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings 管理（.env 読み込みロジック含む）
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py          — monitoring 用 SQLite テーブル初期化 + DB ラッパ
    - system_monitor.py         — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py          — 注文滞留 / 約定異常監視
    - risk_monitor.py           — ドローダウン・ポジション上限監視（Kill イベント発火等）
    - monitoring_engine.py      — 各 Monitor を束ねるエンジン
    - alert_manager.py          — LINE への通知
    - kill_switch.py            — kill.flag 制御ロジック
  - execution/                   — Execution 系（Engine / OrderManager 等）*
    - (実装ファイル群: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager, order_record ...)
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 発注株数算出ロジック
    - risk_adjustment.py        — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py        — モメンタム / ボラ / バリュー計算（DuckDB）
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py               — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py        — ma200 + LLM による市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/                       — 運用時に生成されるファイル群（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid）

  *execution 以下（発注ロジック等）はこの README で概要のみ記載しています。詳細はソースコード内の docstring を参照してください。

---

## よく使うコマンド例

- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば以下も作成します:
- サンプル .env.example（各環境変数のテンプレート）
- requirements.txt（依存パッケージ固定）
- 運用手順（デプロイ / systemd ユニット / コンテナ化例）

ご希望があれば、目的に合わせて追記・テンプレート作成します。