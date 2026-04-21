# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買基盤（KabuSys）の一部実装です。  
本READMEはコードベースの主要コンポーネント、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、シグナル生成 → ポートフォリオ構築 → 発注（Execution）→ 監視（Monitoring）というワークフローを想定した自動売買フレームワークです。  
主な設計方針：

- DuckDB を用いた分析（価格・財務データ参照）
- SQLite による軽量な監視 / 発注ログ永続化
- 本番 / ペーパートレードの分離（環境変数で切替）
- OpenAI を用いたニュース NLP によるセンチメント評価（任意）
- ログ・監視・Kill Switch（フラグファイル）による安全運用

バージョン: `0.1.0`

---

## 機能一覧

- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（実運用は kabuステーション、paper_trading ではモック）
  - リスク管理（RiskManager）、注文管理（OrderManager）、再整合（Reconciler）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視エンジン
  - SQLite に監視・ログを永続化（monitoring_db）
  - Kill Switch（条件を満たすと data/kill.flag を書き込み、Execution 停止）
  - run_monitoring.py による定期ポーリング起動
- portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ適用などの純粋関数群
- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン、IC、統計サマリ等のユーティリティ
- ai (任意)
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores へ保存）
  - regime_detector: マクロ＋ETF MA を合成して市場レジーム判定
- tools
  - paper_verification_report: ペーパートレードの検証レポート生成スクリプト
- 開発ツール
  - config_setup: .env を対話的に作成・更新するウィザード
  - validate_config: 設定・ファイル存在チェック CLI

---

## 必要条件（推奨）

- Python 3.9+
- SQLite（標準ライブラリに含まれる）
- pip パッケージ:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証を厳密に行う場合に推奨）
- （任意）kabuステーション API 環境（実運用時）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成し依存関係をインストール
   - 例は上記「必要条件」を参照

3. .env を作成（対話式ウィザード推奨）
   - 実行:
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザードは .env を生成します（`.env` は必ず Git 管理に含めないでください）。

4. 設定検証
   - 生成後に次を実行して設定の健全性を確認します:
     ```bash
     python -m kabusys.validate_config
     ```
   - 警告を厳格に扱いたい場合は `--strict` を付けてください。

5. DB の初期化
   - 実行スクリプト（run_execution / run_monitoring）内で必要テーブルの作成（冪等）が行われます。手動での準備は不要です。

---

## 環境変数（主要）

自動読み込み:
- プロジェクトルートにある `.env` と `.env.local` は起動時自動で読み込まれます（OS 環境変数より優先度低）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

主なキー（説明 / デフォルト）:

- J-Quants / kabu
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)

- OpenAI / AI
  - OPENAI_API_KEY (AI 機能を使う場合に必須)

- 環境・ログ
  - KABUSYS_ENV : execution モードを指定（development / paper_trading / live） default=development
  - LOG_LEVEL : ログレベル（DEBUG/INFO/...） default=INFO
  - LOG_DIR : ログ出力先ディレクトリ（default: logs/）

- DB / ファイルパス
  - DUCKDB_PATH : DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（default: data/paper_trading.db）
  - PID_FILE_PATH : Execution の PID ファイル（default: data/execution.pid）
  - KILL_FLAG_PATH : Kill Switch の flag ファイル（default: data/kill.flag）

- Paper Trading 固有
  - PAPER_FILL_MODE : instant | partial | never | reject（default: instant）

- Monitoring
  - MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒） default=60

- 安全設定
  - KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするか（0/1, default: 0）。本番では 0 推奨。

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合、モックブローカーを用い、PAPER_TRADING_SQLITE_PATH に書き込まれます（本番 DB と分離）。

- 監視ループを起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は `MONITOR_POLL_INTERVAL` で上書きできます（秒）。デフォルト 60 秒。
  - 監視は常に本番用の sqlite_path（SQLITE_PATH）を使用します（監視 DB は環境に依らず同一）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - または DB 指定: --db PATH
  - 簡易実行例:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```

---

## 監視・停止 (Kill Switch / Stop Flag)

- Kill Switch:
  - リスク条件を満たした場合、監視側（KillSwitch）が `KILL_FLAG_PATH`（デフォルト `data/kill.flag`）に理由を書き込みます。ExecutionEngine は起動時または稼働中にこのファイルの有無をチェックし、存在すれば停止します。
  - 本番で `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動でこのフラグを消すため、誤って自動復旧する恐れがあります。live 環境では 0 を推奨します。

- 強制停止/再起動補助ファイル:
  - `data/stop_requested.flag` : run_monitoring / run_execution のループを終了させるためのファイルとして利用されています（停止用の別フラグ）。

- PID ファイル:
  - `data/execution.pid` に ExecutionEngine の PID が書き込まれます（プロセス停止検出や外部連携に利用）。

---

## ログ設定

- 共通のログ初期化ユーティリティが用意されています:
  - kabusys.utils.logging_setup.setup_logging(app_name="...")

- 出力:
  - コンソール（stdout）
  - 日次ローテートされたファイル（logs/<app_name>.log）、デフォルト 30 日分保持
  - LOG_DIR 環境変数で変更可能

---

## OpenAI（AI 機能）について

- news_nlp / regime_detector などの AI モジュールは OpenAI API（モデル: gpt-4o-mini を想定）を使用します。利用するには `OPENAI_API_KEY` を設定してください。
- API 呼び出しはリトライ・バックオフやレスポンスバリデーションを行いますが、APIキーが未設定の場合は例外またはスキップ動作になります。開発・テスト時はモック化してテスト可能です。

---

## Paper Trading（ペーパートレード）

- KABUSYS_ENV=paper_trading の場合は実注文を行わず MockBrokerClient を使用します。
- ペーパートレード用 DB: `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）にすべて記録され、本番 DB と完全に分離されます。
- PAPER_FILL_MODE により約定シミュレーションの動作を制御できます（instant/partial/never/reject）。

---

## ディレクトリ構成（主要ファイル）

以下はこの README が対象としたコード内の主要ファイル・モジュールの一覧です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                  — 設定読み込み・Settings クラス
  - config_setup.py            — .env 対話型ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB（スキーマ初期化・読み書き）
    - monitoring_engine.py     — Monitor を束ねるエンジン
    - system_monitor.py        — システム状態・データ鮮度監視
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みユーティリティ
    - (その他: trade_monitor, alert_manager など)
  - execution/                  — Execution 関連（Engine, OrderManager など）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数計算・配分
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum/volatility/value）
    - feature_exploration.py   — IC計算・統計まとめ
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング
    - regime_detector.py       — 市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

（実際のリポジトリには上記以外の補助モジュールや更に多くの実装ファイルがあります。）

---

## 備考 / トラブルシューティング

- .env の自動読み込みはデフォルトで有効です。ユニットテストなどで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- PyYAML がない場合、validate_config は YAML ファイルの内容検証をスキップします（ファイル存在チェックは行います）。
- run_monitoring は監視 DB（SQLITE_PATH）を「常に」使用します。monitoring 側の DB は環境に依らず本番の sqlite_path へ書き込みます（運用上の注意）。
- process_priority の設定は OS によって失敗することがあります（権限不足等）。その場合は警告ログが出ますが起動は継続します。
- OpenAI API 呼び出しエラー（429 / ネットワーク等）は自動リトライしますが、上限が来るとそのチャンクはスキップされます。

---

必要に応じてこの README を拡張します。特定の機能（例: ExecutionEngine の外部ブローカー連携方法、DB スキーマ詳細、単体テスト手順など）についてドキュメントが必要であれば知らせてください。