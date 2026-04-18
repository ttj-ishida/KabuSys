# KabuSys

日本株向け自動売買システムのコアコンポーネント群（ライブラリ & 起動スクリプト群）。

このリポジトリは、戦略作成・ポートフォリオ構築・発注エンジン・監視・AI を組み合わせた自動売買フレームワークの一部を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュールで構成されています。

- 発注実行エンジン（ExecutionEngine） — ブローカークライアント経由で注文を管理・実行
- 監視コンポーネント（Monitoring） — システム状態・注文ステータス・リスクを定期チェックしログ/アラート/Kill Switch を生成
- ポートフォリオ構築（Portfolio） — 候補選定・重み計算・銘柄ごとの株数算出（単体関数群）
- リサーチ（Research） — DuckDB を使ったファクター計算・特徴量探索
- AI（news_nlp / regime_detector） — ニュースのセンチメント解析・市場レジーム判定（OpenAI を利用）
- ユーティリティ — ロギング設定、プロセス優先度管理、設定ロード等
- CLI ツール — .env ウィザード、設定検証、Paper Trading レポート生成 等

設計方針の一部：
- 本番・ペーパートレードを分離（paper_trading 環境時は専用 SQLite を使用）
- Look-ahead バイアス防止（計算で日付参照の扱いに注意）
- フェイルセーフ：API失敗などで例外を投げる代わりにフォールバックして継続する箇所がある

---

## 機能一覧

主な機能・モジュール（ファイル名は実装ファイルの概要）

- 起動スクリプト
  - `run_execution.py` — ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
  - `run_monitoring.py` — SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔上書き可能）

- 設定・ユーティリティ
  - `config.py` — 環境変数 / .env 自動ロード、Settings クラス
  - `config_setup.py` — 対話式 .env ウィザード
  - `validate_config.py` — 設定検証 CLI
  - `utils/logging_setup.py` — 統一ログ設定
  - `utils/process_priority.py` — プロセス優先度・CPU affinity 設定

- 監視
  - `monitoring/monitoring_db.py` — SQLite による監視ログ永続化（テーブル初期化含む）
  - `monitoring/system_monitor.py` — CPU/メモリ/ディスク/プロセスの監視、データ鮮度チェック
  - `monitoring/trade_monitor.py`（実装参照） — 注文滞留・約定異常監視
  - `monitoring/risk_monitor.py` — ドローダウン・ポジション上限監視
  - `monitoring/kill_switch.py` — kill.flag による ExecutionEngine 停止機構
  - `monitoring/monitoring_engine.py` — 各モニタを束ねるエンジン
  - `monitoring/alert_manager.py`（実装参照） — LINE 等への通知管理

- 発注 / 実行
  - `execution/*` — ブローカーファクトリ、ExecutionEngine、OrderManager、RiskManager、Reconciler など

- ポートフォリオ構築（純粋関数群）
  - `portfolio/portfolio_builder.py` — 候補選定、重み計算
  - `portfolio/position_sizing.py` — 株数算出、アグリゲートキャップ処理
  - `portfolio/risk_adjustment.py` — セクター上限、レジーム乗数

- リサーチ
  - `research/factor_research.py` — モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB）
  - `research/feature_exploration.py` — 将来リターン計算、IC、統計サマリ

- AI
  - `ai/news_nlp.py` — raw_news を集約して OpenAI に投げ、銘柄ごとのスコアを ai_scores に書き込む
  - `ai/regime_detector.py` — ETF の MA とマクロ記事の LLM 評価を合成してレジーム判定

- ツール
  - `tools/paper_verification_report.py` — ペーパートレード DB を元に検証レポートを生成

---

## 前提・依存関係

- Python 3.10+（注: 型注釈に `X | None` を使用）
- 推奨ライブラリ（実行する機能により必要）
  - duckdb
  - psutil
  - openai（AI 機能）
  - PyYAML（設定検証で config/*.yaml を読みたい場合）
- SQLite（標準）
- 必要に応じて仮想環境を用意してください。

pip のインストール例（requirements ファイルがないため機能に応じて個別導入）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンする
2. Python 仮想環境を作成・有効化
3. 依存ライブラリをインストール（上記参照）
4. .env を作成する（推奨: 対話式ウィザードを利用）

対話式で .env を生成:
```
python -m kabusys.config_setup
```

設定を検証:
```
python -m kabusys.validate_config
# 警告も失敗扱いにしたい場合:
python -m kabusys.validate_config --strict
```

ログディレクトリ・DB のデフォルトパスは `.env` に設定がない場合は以下:
- DuckDB: data/kabusys.duckdb
- SQLite (monitoring): data/monitoring.db
- Paper trading SQLite: data/paper_trading.db

初回実行時、これらの親ディレクトリは自動作成される場合があります（ログ設定等でハンドリング）。

---

## 主要な環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（instant|partial|never|reject）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知用（任意）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）

---

## 使い方（起動例）

- ExecutionEngine を起動（通常: デーモンや systemd / supervisor などで管理）
```
python -m kabusys.run_execution
```
- Monitoring を起動（監視のポーリングループ）
```
python -m kabusys.run_monitoring
# ポーリング間隔を上書きする例（30秒間隔）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

停止方法:
- 実行中のスクリプトは Ctrl+C で停止可能
- 運用上はフラグファイルを使って外部から停止指示を出します:
  - `data/stop_requested.flag` を作成すると run_monitoring/run_execution のループが検知して安全に終了します
  - `Settings.kill_flag_path`（デフォルト: data/kill.flag）により ExecutionEngine に対して「Kill Switch」を書き込めます（監視が判定した場合や手動で書き込むことが可能）

Paper Trading（ペーパートレード）:
- `.env` の `KABUSYS_ENV=paper_trading` を設定すると、ExecutionEngine は本番 DB と完全分離して `PAPER_TRADING_SQLITE_PATH` を使用します。

設定検証:
```
python -m kabusys.validate_config
```

Paper Trading 検証レポート生成:
```
# デフォルト DB を使う場合
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パスを直接指定
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

AI 機能（ニュース NLP / レジーム検出）:
- OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または各関数に api_key 引数を渡す）
- news_nlp と regime_detector は DuckDB 接続を受け取り、ai_scores / market_regime テーブルへ書き込みます

例（Python REPL から呼ぶ）:
```py
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
score_news(conn, target_date=date(2026,4,11), api_key="YOUR_KEY")
```

---

## 運用ノート / 注意点

- Monitoring は設定にかかわらず `Settings.sqlite_path`（本番 monitoring DB）を使用します。ペーパートレード用の監視 DB とは別設計です。
- Run スクリプトはプロセス優先度を上げる処理を行います（`psutil` を利用）。権限不足等で設定できない場合はログに警告が出ます。
- `config_setup.py` により生成された .env はセキュリティ上 Git にコミットしないでください（README ヘッダにも明記）。
- OpenAI を利用する部分は API コスト・レート制限に注意してください。実装にはリトライやバックオフ戦略が組み込まれていますが、運用時は十分なレート管理を行ってください。

---

## ディレクトリ構成（抜粋）

プロジェクトルート直下に `src/kabusys` 以下が存在します。主要ファイルをツリー形式で示します。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/  (発注エンジン関連: BrokerClientFactory 等)
    - ...
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/      (データ・DB・flag 用のディレクトリ — 起動時に作成されることが多い)
  - logs/      (ログ出力先、デフォルト)

※ 実際のファイルの詳細はリポジトリ内の該当ファイルを参照してください。

---

## よくある操作例まとめ

- .env を対話式作成:
  - `python -m kabusys.config_setup`

- 設定をチェック:
  - `python -m kabusys.validate_config`
  - `python -m kabusys.validate_config --strict`

- 起動:
  - Execution（本番/ペーパートレードは .env による）:
    - `python -m kabusys.run_execution`
  - Monitoring:
    - `python -m kabusys.run_monitoring`

- 停止 / 強制停止:
  - プロセスへ SIGINT（Ctrl+C） または `data/stop_requested.flag` を作成
  - 監視による自動停止は `data/kill.flag` を書き込むことで ExecutionEngine 停止を促す（KillSwitch）

- レポート:
  - `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`

---

詳細な実装や拡張方法は、各モジュールの docstring / コメントを参照してください。必要であれば README の英語版や運用ガイド、systemd ユニット例、Docker 化手順なども追記できます。