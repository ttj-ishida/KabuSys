# KabuSys

日本株自動売買システムの軽量ライブラリ兼実行スクリプト群です。  
このリポジトリは戦略・ポートフォリオ構成、発注実行（実環境／ペーパートレード）、監視、リサーチ、AI を使ったニュース NLP 等のコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 日次/リアルタイムでの銘柄選定・配分・株数決定ロジック（portfolio）
- 発注実行エンジン（ExecutionEngine） — 本番とペーパートレードを分離
- システム監視（SystemMonitor / MonitoringEngine）と Kill Switch（安全停止）
- DuckDB を用いたファクター計算／リサーチ機能
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント・レジーム判定
- 簡易的な CLI ツール群（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針のキーポイント:
- 環境変数／.env による設定管理
- 本番 DB とペーパートレード DB の明確な分離
- 外部 API 呼び出しは明示的にラップし、失敗時は安全にフォールバック
- DuckDB を分析用に採用（SQL＋Python の併用）

---

## 主な機能一覧

- 設定関連
  - 対話式 .env ウィザード（kabusys.config_setup）
  - 起動前チェック（kabusys.validate_config）

- 実行／発注
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）で MockBroker を使用し DB を分離
  - 発注履歴・イベントを SQLite（trade_logs 等）に永続化

- 監視
  - SystemMonitor：CPU/メモリ/DISK、データ鮮度、Execution プロセス監視
  - TradeMonitor / RiskMonitor：滞留注文、約定異常、ドローダウンやポジション上限監視
  - MonitoringEngine：複数モニタのポーリングとアラート連携
  - KillSwitch：条件に基づき data/kill.flag を書き込み Execution を停止

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスクベース単位の株数算出
  - セクターキャップ、レジーム乗数の適用

- リサーチ（DuckDB）
  - ファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI（OpenAI）
  - ニュース記事のセンチメントスコア化（ai.news_nlp）
  - マクロニュース＋ETF MA200 乖離による市場レジーム判定（ai.regime_detector）

- ツール
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

推奨 Python バージョン: 3.10 以上（型注釈で `|` が使われているため）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .\.venv\Scripts\activate    (Windows)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - 必要な主なパッケージ:
     - duckdb
     - openai
     - psutil
     - PyYAML（config 検証で YAML をパースしたい場合に必要）
   - 例:
     - pip install duckdb openai psutil pyyaml

   （注）標準ライブラリの sqlite3 は別途インストール不要です。

4. 環境変数／.env の準備
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（例は後述）。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトで logs/ および data/ 以下を使用します。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH を変更してください。

---

## 環境変数（主なもの）

以下はコード内で参照される主な環境変数とデフォルト挙動です。

必須（運用に応じて設定）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意／デフォルトあり
- KABUSYS_ENV — 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- OPENAI_API_KEY — OpenAI 呼び出しに必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant/partial/never/reject、デフォルト: instant）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行制御用

監視用ポーリング間隔（監視プロセス向け）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト: 60 秒）

---

## 使い方

基本的な起動例・ツールの利用方法を示します。各スクリプトはモジュール実行を想定しています。

1. .envを作成
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラーにする: python -m kabusys.validate_config --strict

3. ExecutionEngine（発注エンジン）起動
   - 本番モード（KABUSYS_ENV=live と .env を整備済みの場合）:
     - python -m kabusys.run_execution
   - ペーパートレード（KABUSYS_ENV=paper_trading）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 実行中に停止させたい場合はプロジェクトルートの data/stop_requested.flag を作成（run_execution はこのフラグを検知して停止）。
   - Kill Switch による強制停止は monitoring が data/kill.flag を作成して実行エンジンを停止します。

4. 監視プロセス起動
   - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を上書き:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB ファイルを指定:
     - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

6. AI 関連（ニューススコア／レジーム判定）
   - ai.news_nlp.score_news や ai.regime_detector.score_regime は DuckDB 接続と target_date を渡して呼び出します。
   - 直接 CLI 用エントリは提供していませんが、スクリプトやジョブからインポートして利用可能です。
   - OpenAI APIキーが必要です（OPENAI_API_KEY または引数で渡す）。

7. ログ
   - デフォルトで logs/<app_name>.log に日次ローテーションで出力されます（logs/ ディレクトリを参照）。

---

## 停止 & 制御フラグ

- data/stop_requested.flag
  - run_monitoring/run_execution のループはこのファイルの存在を監視し、存在時は安全に終了します（手動停止用）。

- data/kill.flag
  - KillSwitch がトリガー条件を満たすとこのファイルを書き込み、ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の設定に応じてこのフラグをクリアできます（安全のため本番では 0 推奨）。

- PID ファイル
  - 実行エンジンは data/execution.pid（デフォルト）等に PID を書きます。設定は .env の PID_FILE_PATH で変更可能。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル／パッケージです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py              — ニュース NLP (OpenAI) による銘柄センチメント
    - regime_detector.py       — マクロ + ETF MA200 によるレジーム判定

  - monitoring/
    - monitoring_db.py         — SQLite テーブル定義 / 永続化層
    - system_monitor.py        — CPU/メモリ/Disk、データ鮮度、プロセス監視
    - risk_monitor.py          — ドローダウン／ポジション上限監視
    - trade_monitor.py         — （注文関連の監視ロジック）
    - monitoring_engine.py     — 各 Monitor をまとめる
    - kill_switch.py           — kill.flag 書込ロジック
    - alert_manager.py         — （アラート送信ラッパー）
  
  - execution/                 — 発注エンジン関連（OrderManager 等）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 株数算出・スケーリング・単元丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（DuckDB）
    - feature_exploration.py   — 将来リターン、IC、統計
  - data/                      — （実行時に使用する data/ ディレクトリ: DB・フラグ等）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

（実際のリポジトリではさらに細かなファイルや実装が存在します。上は主要部の一覧です。）

---

## 例: 最小 .env（参考）

以下は .env の一例（必須値は適切に置き換えてください）。

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

注意: .env は絶対にバージョン管理に含めないでください（config_setup.py のヘッダにも同様の注意あり）。

---

## 開発／テストに関する注意

- DuckDB と SQLite を使うためローカルに DB ファイルが作成されます（data/ 下）。
- OpenAI など外部 API 呼び出しを含む機能は、ユニットテストではモック化して検証する設計になっています（呼び出しラッパーを patch する想定）。
- 設定検証脚本は PyYAML がある場合に config/*.yaml のパース検証を行います。ない場合は警告を出してスキップします。

---

## サポート / 参考

- 設定や起動に関するエラーはまず `python -m kabusys.validate_config` でチェックしてください。
- ログは logs/<app_name>.log に出力されるため問題解析に利用してください。
- 監視ループや実行エンジンは stop フラグ（data/stop_requested.flag）や kill.flag による制御をサポートしています。運用時はこれらの利用を検討してください。

---

README の内容はコードの現在の実装（src/kabusys）に基づいて作成しています。実行・運用前に必ず .env の設定と validate_config による検証を行ってください。