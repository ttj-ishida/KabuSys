# KabuSys

日本株自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）／監視（Monitoring）までを含む自動売買プラットフォームのコア部分です。DuckDB を用いたリサーチ／ファクター計算、SQLite ベースの監視ログ、OpenAI を用いたニュース NLP（任意）、ペーパートレード用の分離 DB 等の機能を備えています。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境管理
  - .env 自動読み込み（プロジェクトルートの `.env` / `.env.local`、OS 環境変数優先）
  - 対話式設定ウィザード: `kabusys.config_setup`
  - 設定検証 CLI: `kabusys.validate_config`
- 実行コンポーネント
  - ExecutionEngine 起動スクリプト: `run_execution.py`
    - `KABUSYS_ENV=paper_trading` の場合は MockBroker を用い、本番 DB と分離された `data/paper_trading.db` を使用
    - 停止フラグ（`data/stop_requested.flag`）および PID 管理（`data/execution.pid`）
  - Monitoring 起動スクリプト: `run_monitoring.py`
    - System / Trade / Risk モニタを束ねて定期チェック、kill flag 書き込みによるエンジン停止サポート
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- 監視・ログ
  - SQLite ベースの監視 DB（`monitoring_db.py`）: system_status / trade_logs / positions / risk_logs / dashboard
  - ログ出力ユーティリティ: 日次ローテーションのファイルハンドラ + コンソール出力
- ポートフォリオ構築（純粋関数）
  - 候補選定 / 重み計算 / ポジションサイズ計算 / セクター制限 / レジーム倍率
- リサーチ
  - DuckDB を使ったファクター計算: モメンタム、ボラティリティ、バリュー等
  - 特徴量探索・IC 計算ユーティリティ
- AI（任意）
  - ニュースセンチメント分析（OpenAI）で銘柄ごとのスコアを生成して `ai_scores` へ保存
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（LLM を利用）
  - OpenAI が未設定／失敗でもフェイルセーフで処理継続する設計
- ツール
  - Paper Trading の検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

---

## 必要要件（主な依存パッケージ）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定 YAML 検証を行う場合、`validate_config` が任意で利用）

（requirements.txt はこのリポジトリに含まれていないため、上記パッケージを環境に応じてインストールしてください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. `.env` の準備
   - 対話式ウィザードで作成: `python -m kabusys.config_setup`
   - またはプロジェクトルートに手動で `.env` を置く（`.env.example` を参照）
   - 必須環境変数
     - `JQUANTS_REFRESH_TOKEN`
     - `KABU_API_PASSWORD`
   - (AI 機能を利用する場合) `OPENAI_API_KEY`
4. 設定検証（推奨）
```bash
python -m kabusys.validate_config
# 警告を FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```
5. 必要なディレクトリ（`data/`, `logs/`）は通常スクリプトが自動作成しますが、権限等で問題がある場合は事前に作成してください。

環境変数自動読み込みを無効にする（テストなど）:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（起動 / CLI）

基本的にモジュールを Python のモジュール実行で起動します。

- Monitoring を起動
```bash
# デフォルト (MONITOR_POLL_INTERVAL=60)
python -m kabusys.run_monitoring

# ポーリング間隔を変更
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
監視は停止フラグファイル `data/stop_requested.flag` を検出するとループを抜けます。

- ExecutionEngine を起動
```bash
# 本番・開発環境を .env で切り替え
python -m kabusys.run_execution

# ペーパートレード用に起動（MockBroker を使用し DB を分離）
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
起動時に `data/stop_requested.flag` が存在すると起動せず終了します。実行中は `data/execution.pid` に PID を書きます。停止は `data/stop_requested.flag` を作成するか（monitoring が kill switch を書く）、ExecutionEngine 側で受け付ける停止手順を呼んでください。

- 設定ウィザード（.env 作成）
```bash
python -m kabusys.config_setup
```

- 設定検証
```bash
python -m kabusys.validate_config
```

- Paper Trading 検証レポート
```bash
# デフォルト DB (data/paper_trading.db)
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# 別 DB を指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

---

## 主要な環境変数（まとめ）

重要なものだけ抜粋します。詳しくは `kabusys.config.Settings` を参照してください。

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI を使う機能で必要（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill flag を自動で消すか（0/1、開発向け）

---

## ロギング / DB（デフォルトパス）

- ログディレクトリ: logs/
  - 日次ローテーション、30 日分保持
  - ファイル名は `<app_name>.log`（例: `execution.log`, `monitoring.log`）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- ペーパートレード SQLite: data/paper_trading.db

---

## 重要なファイル・フラグ

- data/stop_requested.flag — スクリプト（monitoring / execution）が監視する停止フラグ
- data/kill.flag — Kill Switch が書き込むフラグ（ExecutionEngine を停止させるための理由を保持）
- data/execution.pid — ExecutionEngine の PID（`run_execution` が書き込む）

---

## ディレクトリ構成

（src/kabusys をルートにした主要ファイル構成）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings クラス (.env 自動読み込み含む)
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 永続層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文関連監視ロジック）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装
    - monitoring_engine.py — Monitor を束ねるエンジン
    - alert_manager.py —（通知管理）
  - execution/ — ExecutionEngine / Broker 関連（注文管理、リコンシリエーション等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py — ニュースの NLP（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py — マクロ + MA200 による市場レジーム判定
  - data/（実行時に生成されることが多い）
    - *.db, kill.flag, stop_requested.flag, execution.pid など

---

## 運用上の注意 / ベストプラクティス

- 本番環境では `KABUSYS_ENV=live` を使用。設定ミスに注意（`validate_config` を必ず実行）。
- `.env` は絶対に git にコミットしないこと。
- OpenAI を使う処理は外部 API 呼び出しを伴うため、API キー・レート制限・料金に注意してください。API エラー発生時にも安全にフォールバックする実装になっていますが、想定外の挙動に備えて監視アラートを設定してください。
- `psutil` を使ったプロセス優先度変更や CPU affinity は OS 権限に依存します。権限不足の場合は警告ログを出して処理を継続します。
- `logs/` や `data/` への書き込み権限を確保してください。ログディレクトリ作成失敗時はコンソールに警告が出ます（ファイル出力は無効化されます）。
- 停止手順は `data/stop_requested.flag` の作成（外部からファイルを置く）や、Monitoring の Kill Switch によって `data/kill.flag` が書き込まれるフローがあります。運用時はこれらのファイル存在を確認してください。

---

## 開発・テストのヒント

- 環境自動読み込みを無効にしてユニットテストを実行する:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```
- ログ設定は `kabusys.utils.logging_setup.setup_logging` を利用して統一してください。
- DuckDB 接続を渡す設計なので、テスト時は一時的な DuckDB ファイルや in-memory を使って関数単体テストが可能です。
- OpenAI の呼び出し部分は内部で `_call_openai_api` をラップしているため、テストでは該当関数をモックして応答を制御できます（ドキュメント内にモック方法のコメントあり）。

---

README は以上です。実行や設定で不明点があれば、使いたい機能（監視 / 実行 / AI / レポート）を指定していただければ、起動コマンドや設定例を具体的に提示します。