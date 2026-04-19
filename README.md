# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
リサーチ、ポートフォリオ構築、注文実行、監視、AI によるニュース評価などの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成される自動売買基盤です。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- ExecutionEngine による発注ロジック（本番 / ペーパートレード切替）
- 監視システム（リソース・データ鮮度・注文明細の監視）と Kill Switch
- OpenAI を用いたニュース NLP（センチメント）とレジーム判定
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、ルックアヘッドバイアスを避ける、フェイルセーフ（外部 API 失敗時のフォールバック）、DB 分離（本番 / ペーパートレード）などが採用されています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成 / 更新）: python -m kabusys.config_setup
- 設定検証ツール（.env / config/*.yaml のチェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）: python -m kabusys.run_execution
- Monitoring 起動スクリプト（定期ポーリング）: python -m kabusys.run_monitoring
- ペーパートレード検証レポート出力: python -m kabusys.tools.paper_verification_report
- AI モジュール
  - ニュースセンチメント評価（ai.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
- ポートフォリオ構築ユーティリティ
  - 候補選定 / 等重・スコア重み / ポジションサイズ計算 / セクターキャップ / レジーム乗数
- 監視
  - system_monitor, trade_monitor, risk_monitor と MonitoringEngine 統合
  - kill.flag による ExecutionEngine 停止信号
- ログ設定ユーティリティ（共通ログ構成: stdout + 日次ローテーション）

---

## 依存関係（代表例）

主な外部ライブラリ:

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能利用時）
- PyYAML（config/*.yaml のパース検証用、任意）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# requirements.txt がない場合:
pip install duckdb psutil openai PyYAML
```

注意: 実際のプロジェクトでは requirements.txt を用意してください。

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動

2. 仮想環境の作成と依存インストール（上記参照）

3. .env を作成（ウィザード推奨）

```bash
python -m kabusys.config_setup
```

対話ウィザードで J-Quants トークンや kabu API パスワードなどを入力して .env を生成します。

4. 設定検証

```bash
python -m kabusys.validate_config
# 警告を FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

5. データ / ログ ディレクトリの確認・作成  
   デフォルトの DB / ログ パスは .env の値または Settings のデフォルトを使用します。必要に応じてディレクトリを作成してください（自動作成される場合もありますが権限に注意）。

---

## 主要環境変数（一部、代表）

（ウィザードで設定される項目。デフォルト値は Settings クラスを参照）

- JQUANTS_REFRESH_TOKEN — J-Quants API
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 用）
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/...
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)
- OPENAI_API_KEY — OpenAI を使う機能で必要
- PAPER_FILL_MODE — ペーパートレードの約定モード: "instant" | "partial" | "never" | "reject"
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）

注意: Monitoring は「環境にかかわらず」本番の sqlite_path を利用する仕様（監視ログは本番 DB を想定）。Execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用し、DB を分離します。

---

## 使い方

以下は一般的な起動・実行方法です。プロダクション運用では systemd / supervisord / cron 等で管理してください。

- 環境準備（仮想環境有効化、.env 作成、依存インストール）

- 設定検証

```bash
python -m kabusys.validate_config
```

- ExecutionEngine 起動

本番/ペーパートレードは KABUSYS_ENV に依存します（.env で設定）。

```bash
# 実行（バックグラウンド管理はプロセス監視ツールで行うことを推奨）
python -m kabusys.run_execution
```

実行時の挙動のポイント:

- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と完全分離）。
- エンジンは data/execution.pid に PID を書きます（Settings.pid_file_path に依存）。
- data/stop_requested.flag が存在すると起動を行わず、実行中はこのファイル検知で停止を行います。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合は kill.flag を自動クリアするオプションがあります（本番では 0 推奨）。

- Monitoring 起動

```bash
# ポーリングループを起動
python -m kabusys.run_monitoring

# ポーリング間隔を環境変数で上書き（秒）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

Monitoring の挙動のポイント:

- Monitoring は環境にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
- 監視ループは data/stop_requested.flag の存在で停止します。
- MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（1 秒未満や 0 は無効でデフォルトにフォールバック）。

- ペーパートレード検証レポート

```bash
# デフォルト DB パス (環境変数 or デフォルト)
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# --db オプションで明示的に DB を指定可能
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI / ニュース NLP（プログラムから呼び出す）

OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または関数引数で指定）。

例（ライブラリ関数を呼ぶ）:

```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
# target_date に対する前日 15:00 JST ～ 当日 08:30 JST のニュースを収集してスコアを生成
count = score_news(conn, target_date=date(2026, 4, 10), api_key=None)  # env の OPENAI_API_KEY を利用
```

---

## 運用上の注意点 / トラブルシューティング

- ログ: デフォルトは logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- 権限: data/ や logs/ に書き込み権限が必要です。初回起動時にディレクトリを作成してください。
- Kill Switch: RiskMonitor → KillSwitch の評価により data/kill.flag を生成し、ExecutionEngine 側で停止させる仕組みがあります。KILL_FLAG_CLEAR_ON_START の設定に注意してください（本番では 0 推奨）。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等にテーブルと列を作成 / 追加する処理を含みます。既存 DB に対して欠けているカラムを追加します。
- OpenAI: API エラーはリトライやフォールバックを備えていますが、API キーや料金に注意してください。

---

## ディレクトリ構成

リポジトリの主要なファイル・ディレクトリ（src/kabusys 以下）:

- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリングループ起動スクリプト
- config.py — 環境変数 / 設定の集中管理（Settings クラス）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前設定検証 CLI

サブパッケージ（主要モジュール）:

- kabusys/ai/
  - news_nlp.py — ニュースの LLM センチメント評価
  - regime_detector.py — 市場レジーム判定
- kabusys/monitoring/
  - monitoring_db.py — SQLite 永続化層（監視ログ）
  - system_monitor.py — リソース・データ鮮度監視
  - trade_monitor.py — （注文明細監視） ※本リストではコード断片あり
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — フラグファイル生成による停止シグナル
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — （アラート送信）※実装参照
- kabusys/execution/
  - execution_engine.py — 発注エンジン本体
  - broker_factory.py — ブローカークライアント生成（本番/モック）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行関連ロジック
- kabusys/portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数決定・制限
  - risk_adjustment.py — セクターキャップ / レジーム乗数
- kabusys/research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算
  - feature_exploration.py — IC/相関/統計サマリー等
- kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- kabusys/utils/
  - logging_setup.py — 共通ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- その他
  - __init__.py, __version__ 等

（上記は主要ファイルの概観です。詳しい実装は各ファイルを参照してください。）

---

## よく使うコマンド一覧

- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper trade レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ライセンス / 貢献

（ここにライセンス情報や貢献ガイドラインを記載してください。リポジトリに LICENSE ファイルがあればそちらを参照する旨を追記してください。）

---

README は以上です。必要であれば以下を追加できます:

- 詳しい .env のサンプル（.env.example）
- systemd / supervisor のサービス定義例
- 開発用テストの実行方法（ユニットテスト等）
- 各モジュールの API 使用例（コードスニペット）