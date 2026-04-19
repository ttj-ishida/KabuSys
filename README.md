# KabuSys

日本株自動売買システムの軽量なコア実装（ライブラリ＋起動スクリプト群）。

このリポジトリには、実行エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ポートフォリオ構築・ポジション決定ロジック、リサーチ/ファクター計算、LLM を使ったニュースセンチメント評価などの主要コンポーネントが含まれます。

※ 本 README はソースツリー（`src/kabusys`）のコードを元に作成しています。

---

## 主な特徴（概要）

- ExecutionEngine
  - 本番 / ペーパートレード切替（`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、DB を分離）
  - 注文管理、リスク管理、再整合（Reconciler）などの組立て済みエンジン起動スクリプト（`run_execution.py`）
- Monitoring
  - システム状態監視（CPU / メモリ / ディスク・プロセス生存チェック）
  - 取引ログ・リスクログ・ダッシュボードの SQLite 永続化
  - Kill Switch（ドローダウンやポジション上限超過時に `data/kill.flag` を書いて Execution を停止）
  - 監視ポーリングループ起動スクリプト（`run_monitoring.py`）
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重配分、リスクベース配分、単元株丸め等の関数群（副作用なしの純粋関数）
- ポジションサイジング（リスク制限、aggregate cap、lot 単位でのスケーリング）
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を用いた SQL ベース）
  - 将来リターン・IC 計算などの統計ツール
- AI（LLM）統合
  - ニュース記事を LLM（OpenAI）でセンチメント評価して ai_scores テーブルへ書き込み
  - 市場レジーム判定（ETF の MA200 乖離 + マクロニュースセンチメントの合成）
- ツール
  - Paper Trading の検証レポート生成スクリプト（`tools/paper_verification_report.py`）
- ユーティリティ
  - 環境変数の .env 自動読み込み / 対話式設定ウィザード / 設定検証 CLI
  - ロギング設定ユーティリティ（コンソール + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## 必要条件（推奨）

- Python 3.10 以上（PEP 604 の union 型記法などを使用）
- SQLite（標準ライブラリ）
- 推奨パッケージ（主にランタイムで必要なもの）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証を行う場合）
- その他：ネットワーク接続（kabuステーション / OpenAI 等を使う場合）

インストール例（仮に requirements.txt が無い場合）:
```
pip install duckdb psutil openai pyyaml
```

---

## 環境変数（主要なもの、デフォルト）

（フル一覧は `src/kabusys/config.py` を参照）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 運用関連
  - KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: `development`）
  - LOG_LEVEL — ログレベル（`INFO` 等、デフォルト: `INFO`）
  - LOG_DIR — ログファイル出力ディレクトリ（デフォルト: `logs/`）
- DB パス（デフォルト）
  - DUCKDB_PATH: `data/kabusys.duckdb`
  - SQLITE_PATH: `data/monitoring.db`
  - PAPER_TRADING_SQLITE_PATH: `data/paper_trading.db`（`paper_trading` モード時に利用）
- モニタリング/制御
  - KILL_FLAG_PATH: `data/kill.flag`
  - PID_FILE_PATH: `data/execution.pid`
  - KILL_FLAG_CLEAR_ON_START: `0` または `1`（本番では `0` 推奨）
  - MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、`run_monitoring.py` で参照。デフォルト: 60）
- OpenAI
  - OPENAI_API_KEY — OpenAI を利用する場合に必須

.env は `src/kabusys/config_setup.py` のウィザードで対話的に作成できます。

---

## セットアップ手順

1. リポジトリをクローンしてワークツリーへ
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows PowerShell では .venv\Scripts\Activate.ps1)
3. 依存パッケージをインストール
   - (推奨) requirements.txt があれば: pip install -r requirements.txt
   - なければ: pip install duckdb psutil openai pyyaml
4. .env の作成（対話式）
   - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成し必要な値を設定
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いにできます（exit code 1）
6. （paper_trading で検証する場合）`KABUSYS_ENV=paper_trading` を設定すると MockBroker が使われ、デフォルトで `data/paper_trading.db` に記録します。

注意:
- `.env` は機密情報（API トークン）を含むため絶対に Git にコミットしないでください。

---

## 使い方（起動例）

- 監視ループを起動（監視は常に本番 sqlite_path を使用）
```
python -m kabusys.run_monitoring
```
- ポーリング間隔を変更する（秒）
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Execution エンジンを起動
```
python -m kabusys.run_execution
```
- Paper Trading の検証レポートを生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```
- .env の作成・編集ウィザード
```
python -m kabusys.config_setup
```
- 設定検証 CLI
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

停止制御 / フラグファイル:
- ExecutionEngine の停止は `data/kill.flag`（KillSwitch）または `data/stop_requested.flag`（停止フラグ）で制御されます。
  - 監視プロセス（または管理側のツール）が `data/kill.flag` を書き込むと ExecutionEngine 側で検出して安全停止します。
  - `data/stop_requested.flag` が存在すると `run_monitoring.py` / `run_execution.py` のループが終了する実装箇所があります。

ログ:
- ログは標準出力（stdout）と日次ローテートファイル（デフォルト: `logs/<app_name>.log`）へ出力されます。
- ログ設定は `kabusys.utils.logging_setup.setup_logging` で統一されています。

AI（OpenAI）関連:
- `kabusys.ai.news_nlp.score_news` / `kabusys.ai.regime_detector.score_regime` を利用するには `OPENAI_API_KEY` が必要です。
- LLM 呼び出しはリトライやバリデーションを備え、部分失敗時にも他データを保護する設計になっています。

---

## 主要ディレクトリ構成

（プロジェクトルートの `src/kabusys` 配下を抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / Settings 管理 (.env 自動読み込み機能含む)
  - config_setup.py — .env 作成ウィザード（対話式）
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算・スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン計算・IC 等
  - ai/
    - news_nlp.py — ニュースセンチメントの LLM スコアリング
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（テーブル作成・読み書き）
    - system_monitor.py — システム状態 / データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （取引ログ監視、コードベースに含まれる想定モジュール）
    - kill_switch.py — kill.flag の書き込み / 評価ロジック
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - execution/ — ExecutionEngine 関連（OrderManager, BrokerFactory, Reconciler, RiskManager など）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py — プロセス優先度 / CPU affinity
  - data/ — 実行時に作成される DB / フラグファイル / pid ファイル（`data/*.db`, `data/kill.flag`, `data/execution.pid` など）

---

## 開発・デバッグ時のヒント

- 設定を変更したら `python -m kabusys.validate_config` で検証してください。
- `.env` の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- Logging は `LOG_LEVEL` / `LOG_DIR` で制御可能。ログがファイル作成に失敗した場合はコンソールのみで継続します。
- OpenAI を使う機能は API 失敗時にフェイルセーフ（0.0 などの中立スコア）で継続する設計です。テストではネットワークを切っても致命的にならないようになっています。
- DuckDB は分析用（prices_daily, raw_financials など）。Research モジュールは DuckDB 接続を受け取って計算します。
- ペーパートレード実行は本番 DB と完全分離されます。`KABUSYS_ENV=paper_trading` を指定すると `paper_sqlite_path` が使われます。

---

## ライセンス / 注意事項

- この README はソースコードからの推察をまとめたものです。外部 API キーや実売買を行う設定を扱う際は十分に注意してください。
- 本システムを本番口座で運用する場合は、事前に十分な監査・バックテスト・ログ確認・フェイルセーフ対応を行ってください。

---

必要であれば、README に含めるサンプル .env、systemd / supervisor のサービス定義例、Dockerfile や CI 設定テンプレートなども作成します。どの補助ドキュメントが欲しいか教えてください。