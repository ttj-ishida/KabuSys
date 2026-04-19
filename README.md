# KabuSys

日本株向け自動売買システムのサンプル実装（モジュール群と起動スクリプト群）。  
この README はコードベース（src/kabusys 以下）の主要コンポーネント、セットアップ、実行方法、ディレクトリ構成をまとめたものです。

注意：本プロジェクトは実際に発注を行う機能を含みます。KABUSYS_ENV に `live` を設定すると実発注が行われます。運用時は設定と権限を十分に確認してください。

---

## プロジェクト概要

KabuSys は以下の主要機能を持ちます。

- 注文実行エンジン（ExecutionEngine） — ブローカークライアントを通じて注文を作成・管理
- 監視コンポーネント（Monitoring） — システム状況、注文ログ、リスク指標を定期的に収集・評価しアラートや Kill Switch をトリガー
- ポートフォリオ構築（portfolio） — 候補選定、重み付け、ポジションサイズ計算、セクター制限等の純粋関数群
- リサーチ（research） — ファクター計算、将来リターン・IC計算、特徴量サマリ等（DuckDB 経由で価格データを参照）
- AI モジュール（ai） — ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- ユーティリティ（utils） — ロギング設定、プロセス優先度設定、設定読み込み等
- CLI ツール — 設定ウィザード、設定検証、ペーパートレード検証レポートなど

---

## 主な機能一覧

- run_execution.py：ExecutionEngine を起動（KABUSYS_ENV に応じて実取引 / ペーパートレードを切替え）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録して本番 DB と分離
  - 停止は data/stop_requested.flag の作成で行う（Kill Switch は data/kill.flag）
- run_monitoring.py：SystemMonitor のポーリングループを起動（環境にかかわらず本番 sqlite_path を監視 DB に使用）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可（デフォルト 60 秒）
- monitoring モジュール：system/trade/risk のチェック、KillSwitch、アラート統合
- portfolio：候補選定、等重/スコア重み、リスク制限、ポジションサイズ算出
- research：momentum / volatility / value ファクター、将来リターン、IC、統計サマリ
- ai：
  - news_nlp：ニュースを OpenAI でセンチメント評価して ai_scores テーブルへ書き込む
  - regime_detector：MA とマクロニュースを組み合わせて市場レジームを判定・保存
- tools：
  - paper_verification_report：ペーパートレード DB を解析して Pass/Fail 判定を行うレポート生成

---

## 前提・要件

- Python 3.10 以上（型注釈の union 型（|）を使用）
- SQLite（Python 標準ライブラリ）
- 主要依存パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証時に任意）
- ネットワーク接続（OpenAI / ブローカー API を使う場合）

インストール例（仮の requirements）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ 実プロジェクトでは requirements.txt / Poetry などで依存管理してください。

---

## セットアップ手順

1. リポジトリをクローンしソースに移動
2. 仮想環境を作成して有効化
3. 必要なパッケージをインストール（上記参照）
4. 環境変数を準備（.env を作成するか環境変数で設定）
   - 推奨: `python -m kabusys.config_setup` を実行して対話的に .env を作成
5. 設定検証（任意だが推奨）
   - `python -m kabusys.validate_config`  
     -- `--strict` を付けると警告も失敗扱いになり exit(1)
6. データディレクトリ・ログディレクトリの確認
   - デフォルト SQLite / DuckDB は `data/`、ログは `logs/`（環境変数で上書き可）

重要な環境変数（必須 / 主要）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live）（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL, LOG_DIR（ロギング設定）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
- KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）

.env 自動読込について：
- プロジェクトルートの `.env` と `.env.local` が自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

注意: `.env` は絶対に Git にコミットしないでください（config_setup のヘッダに注意書きあり）。

---

## 使い方

基本的な実行例を示します。

1) 設定ウィザード（.env を作成）
```
python -m kabusys.config_setup
```

2) 設定検証
```
python -m kabusys.validate_config
# strict モード:
python -m kabusys.validate_config --strict
```

3) 実行エンジンを起動（本番/ペーパーは KABUSYS_ENV で切替）
```
python -m kabusys.run_execution
```
- 起動時に `data/stop_requested.flag` が存在すると起動を行わず終了します。
- 停止は `data/stop_requested.flag` を作成することで行えます（run_execution はこのフラグを監視して安全に停止します）。
- ExecutionEngine は PID を `data/execution.pid` に書きます。

4) 監視ループを起動
```
python -m kabusys.run_monitoring
# ポーリング間隔を変更したい場合（秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- 監視は環境に関係なく本番 sqlite_path（Settings.sqlite_path）を使用。
- 監視ループは `data/stop_requested.flag` を検出すると終了します。

5) ペーパートレード検証レポート生成（ツール）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

6) AI / Research 機能の呼び出し（Python スクリプト内で利用）
例: ニューススコアリング
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# target_date は scoring 日（date オブジェクト）
score_count = score_news(conn, date(2026, 4, 1), api_key="sk-...")
```

例: ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, date(2026, 4, 1))
```

注意: AI 機能は OpenAI API キー（OPENAI_API_KEY）または関数引数でキーを渡す必要があります。API 呼び出し失敗時はフェイルセーフ（スコア0やスキップ）で継続する設計です。

---

## 運用上の注意

- KABUSYS_ENV が `live` の場合は実際に発注します。十分に検証された設定と適切な監視体制の下で実行してください。
- Kill Switch（data/kill.flag）は手動で作成されると ExecutionEngine に停止指示を与えます。設定 `KILL_FLAG_CLEAR_ON_START` が `1` の場合、起動時に自動クリアされますが、本番では `0` を推奨します。
- run_monitoring/run_execution は data/stop_requested.flag を使ってプロセス間でシャットダウン要求をやり取りします。
- プロセス優先度や CPU affinity の設定は OS により制約があり、権限不足で設定に失敗する可能性があります（ログに警告が出ます）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数/.env の読み込みと Settings
- config_setup.py — 対話式 .env 作成ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

モジュール群:
- execution/  — 注文実行関連（BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等）※ソースベースに存在
- monitoring/
  - monitoring_db.py — SQLite による永続化層（system_status/trade_logs/positions/risk_logs/dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py など
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数決定・集計キャップ処理
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value 計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + マクロニュース + OpenAI）
- utils/
  - logging_setup.py — 標準化されたロギング設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

プロジェクトルート上の重要ファイル / ディレクトリ（ランタイム）
- data/ — SQLite / pid / flag ファイル等（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）
- logs/ — ログファイル（app_name による日次ローテート）
- config/ — 各種設定 yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, ...） — validate_config で検証する

---

## よく使うファイル・フローのまとめ

- .env / 環境変数 → kabusys.config.Settings で読み込まれアプリ全体が参照
- run_execution.py
  - Settings で DB パス等を読み込み
  - BrokerClientFactory でブローカークライアントを作成（paper_trading なら Mock）
  - ExecutionEngine をスレッドで起動、data/stop_requested.flag を監視して停止
- run_monitoring.py
  - SystemMonitor を初期化、周期的に check_once() を実行して monitoring_db に記録
  - KillSwitch/Alerter を通じて Execution 停止要求や通知を送る
- ai.news_nlp.score_news / ai.regime_detector.score_regime は DuckDB に対してデータ読込／書込みを行い、OpenAI を呼び出して結果を ai_scores / market_regime 等に永続化

---

## 参考・トラブルシュート

- `.env` がロードされない：
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` が設定されていないか確認
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行われる（見つからない場合は自動ロードをスキップ）
- ログファイルが作れない：
  - 権限やパスの存在を確認。LOG_DIR 環境変数で別ディレクトリを指定可能。ファイル出力に失敗するとコンソールのみで動作します。
- Process priority / CPU affinity の設定失敗：
  - 権限が不足している可能性があります（特に nice 値の低減は root 権限が必要）。失敗時は警告ログが出て継続します。

---

必要に応じて README を拡張します（依存管理の例、ユニットテストの実行方法、CI 設定、各コンポーネントの詳細設計書へのリンクなど）。追加で欲しいセクションがあれば教えてください。