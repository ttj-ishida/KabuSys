# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買フレームワーク（データ取得・ファクター計算・ポートフォリオ構築・発注実行・監視・AIベースのニュース解析など）をまとめたものです。  
README は主要な使い方、設定、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

- データ分析用に DuckDB、運用ログ／監視用に SQLite を利用する設計。
- 発注処理（ExecutionEngine）は本番 / ペーパートレードを切り替え可能。
- 監視 (Monitoring) は独立したプロセスとして稼働し、システム状態・注文状態・リスクを監視してアラートや Kill Switch を発動する。
- ニュースの NLP 評価や市場レジーム判定は OpenAI（gpt-4o-mini）を利用するオプション機能を持つ。
- ポートフォリオ構築・ポジションサイズは純粋関数群として実装され、テストしやすい設計。

---

## 主な機能一覧

- 実行（Execution）:
  - ExecutionEngine を起動してブローカーへ発注（本番 / ペーパートレード切替）
  - OrderManager / RiskManager / Reconciler 等で発注管理とリスク管理
- 監視（Monitoring）:
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス稼働チェック
  - TradeMonitor: 注文滞留（stale orders）、約定価格異常の検出
  - RiskMonitor: ドローダウンやポジション上限の監視
  - MonitoringEngine: 各監視を束ねポーリング実行、KillSwitch で停止シグナル発行
- ポートフォリオ:
  - 銘柄選定、等重・スコア加重、リスク調整、ポジションサイズ算出
- 研究/ファクター:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン・IC（情報係数）計算、統計サマリー
- AI（任意）:
  - ニュースセンチメント（news_nlp）で OpenAI を使った銘柄別スコアリング
  - 市場レジーム判定（regime_detector） — ETF の MA200 とマクロニュースを合成
- ツール:
  - ペーパートレード検証レポート生成スクリプト（paper_verification_report）
- 設定支援:
  - 対話式 .env 作成ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）

---

## 必要条件 / 依存パッケージ

- Python 3.9+ 推奨（ソースは typing | match 機能の制約を受けない範囲）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - requests (LINE 通知)
  - PyYAML（config/*.yaml のパース検証に必要だが必須ではない）
- SQLite は標準ライブラリ経由で使用
- インストール例:
  - pip install duckdb psutil openai requests pyyaml

（プロジェクトには requirements.txt は含まれていません。必要に応じて環境に合わせて pip でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests pyyaml

4. .env の用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動でルートに `.env` を作成（例は下記）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い:
     - python -m kabusys.validate_config --strict

デフォルトの DB ファイル/パス（.env を設定しない場合の既定値）
- DuckDB: data/kabusys.duckdb
- SQLite（監視）: data/monitoring.db
- Paper trading SQLite: data/paper_trading.db
- PID / flag ファイル: data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## .env の例

以下は最低限必要な環境変数例（実運用では秘密情報は決して Git に入れないこと）:

```
# 実行環境
KABUSYS_ENV=development  # development | paper_trading | live

# 必須トークン / パスワード
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_station_password_here

# OpenAI（AI 機能を使う場合）
OPENAI_API_KEY=sk-xxxxx

# DB / ファイルパス（任意で上書き）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# Paper trading の約定モード（instant|partial|never|reject）
PAPER_FILL_MODE=instant

# ログ / 通知
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=     # LINE 通知を使う場合に設定
LINE_USER_ID=
```

.env はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）に配置してください。自動読み込みはデフォルトで行われますが、テスト等で無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 実行方法（主要コマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV で切替
  - 例（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行中は data/execution.pid が作成されます。
  - 事前に stop フラグファイルが存在すると起動を中止します（data/stop_requested.flag）。

- Monitoring（監視プロセス）起動
  - ポーリングループを起動:
    - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - 監視は Settings の sqlite_path（監視用DB）を常に参照します（環境にかかわらず本番用 DB を使用します）。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI系関数（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を用いる

停止方法（運用）
- ExecutionEngine を外部から即座に停止させたい場合:
  - 監視コンポーネントが kill.flag を書き込む（data/kill.flag）
  - 手動停止: data/stop_requested.flag を作成すると run_execution と run_monitoring のメインループが検知して終了します
  - 実行中に Ctrl+C を送ると安全にシャットダウン処理が走ります

---

## 環境変数一覧（重要なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## ディレクトリ構成

以下は src/kabusys ディレクトリの主要ファイルと機能の概観です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の読み込み・Settings クラス
  - config_setup.py          — .env 対話式作成ウィザード
  - validate_config.py       — 起動前設定検証ツール
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングスクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/               — 発注関連コンポーネント（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ + 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/                    — 実行時に生成される DB / flag ファイル（data/kabusys.duckdb、data/monitoring.db 他）

---

## トラブルシューティング / 注意事項

- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が未設定だと起動前検証で失敗します。
- OpenAI を利用する機能は API キーが必須です。未設定の場合は例外を投げる箇所があります。
- DuckDB / SQLite ファイルは初回実行時に自動生成されますが、親ディレクトリが存在しないと警告が出ます。`data/` ディレクトリを作成しておくと安全です。
- run_monitoring は MONITOR_POLL_INTERVAL で間隔を制御します。0 以下はデフォルト（60秒）にフォールバックします。
- process priority / cpu affinity の設定には管理者権限が必要な場合があります。psutil の例外は警告ログに変換して処理を継続するため、必ずしも致命的な失敗にはなりません。
- YAML 設定ファイル（config/*.yaml）は必須ではありませんが、validate_config はパース検証のため PyYAML を利用します。インストールがない場合は YAML チェックがスキップされます。

---

## 開発者向けメモ

- 監視・発注・AI モジュールはいずれも外部接続を伴うため、ユニットテストでは依存部分（OpenAI クライアントや DB 接続）をモックする設計になっています。
- 多くのモジュールは純粋関数（副作用を持たない）で構成されており、ユニットテストが書きやすく設計されています（例: portfolio/*, research/*）。
- DB スキーマは monitoring_db.init_monitoring_db に集約されており、スキーマ変更時のマイグレーション対応が一部実装されています。

---

必要であれば、README に含めるサンプル運用手順（systemd unit、Dockerfile、cron 例）や、より詳細な各モジュールのドキュメント（API、設定項目の完全リファレンス）も作成できます。どの情報を追加したいか教えてください。