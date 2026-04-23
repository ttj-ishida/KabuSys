# KabuSys

日本株向け自動売買システムの主要コンポーネント群をまとめたリポジトリ。取引実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ/ファクター計算、AI（ニュース NLP / レジーム判定）などのモジュールが含まれます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 日次・リアルタイムでのシグナルに基づく売買実行（ExecutionEngine）
- システム稼働状況・注文の監視と Kill Switch（Monitoring）
- ポートフォリオ構築、ポジションサイズ決定、リスク調整（Portfolio）
- DuckDB を使ったファクター計算やリサーチツール（Research）
- OpenAI を用いたニュースセンチメント評価・市場レジーム判定（AI）
- コマンドラインでの設定ウィザード / 設定検証 / 検証レポート生成ツール

設計方針として、実行系（発注）と分析系（DuckDB）は明確に分離され、Paper Trading（模擬発注）モードを用意して本番 DB と切り離して運用できるようになっています。

---

## 主な機能一覧

- Execution
  - 実際のブローカー or モックブローカー（KABUSYS_ENV=paper_trading）による発注
  - リスク管理（position 上限、drawdown 等）
  - PID / stop フラグ連携で安全に停止
- Monitoring
  - システムリソース (CPU/メモリ/ディスク) とプロセス生存チェック
  - 注文滞留・約定異常の検出、ダッシュボード更新
  - Kill Switch（リスク閾値を超えた場合に停止フラグを書き込む）
- Portfolio
  - 候補選定、等分配 / スコア加重、リスクベースの株数算出
  - セクターキャップ、レジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）などの統計処理
- AI
  - ニュース記事を LLM（OpenAI）でスコアリングして ai_scores テーブルへ保存
  - ETF 指標とマクロニュースの LLM 評価を組み合わせた市場レジーム判定
- ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

---

## セットアップ手順

前提
- Python 3.9+（実装上 typing の一部に 3.9 機能を利用）
- SQLite（標準ライブラリ）
- 開発環境では仮想環境を推奨

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（代表的な依存）
   ```
   pip install duckdb psutil openai
   ```
   - optional: PyYAML を入れると `validate_config` が config/*.yaml のパース検証を行えます:
     ```
     pip install pyyaml
     ```

   （実プロジェクトでは requirements.txt / pyproject.toml が用意されている想定です。あればそちらを使用してください。）

4. .env を作成
   - 対話式ウィザードで作成できます:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（例は次節参照）。

5. 設定検証（オプション）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い
   ```

---

## 環境変数 / .env の例

以下は最低限必要な主要環境変数の例（.env に保存）。実際にはウィザードや .env.example を参照してください。

```
# 実行環境: development | paper_trading | live
KABUSYS_ENV=development

# J-Quants API
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# データベース
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  # paper_trading 用 DB

# ログ
LOG_LEVEL=INFO
LOG_DIR=logs

# Kill Switch 動作
KILL_FLAG_CLEAR_ON_START=0
```

注意:
- OpenAI を使う機能を利用する場合は環境変数 `OPENAI_API_KEY` を設定してください（ai モジュールで参照）。
- Paper Trading では `KABUSYS_ENV=paper_trading` に設定するとモックブローカーを使用し paper_sqlite_path（デフォルト data/paper_trading.db）に書き込みます。実 DB と完全分離されます。

---

## 使い方（主要スクリプト）

起動スクリプトは直接モジュールとして実行するのが推奨です。

- ExecutionEngine（取引実行）
  ```
  python -m kabusys.run_execution
  ```
  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB に記録します。
  - 実行中に `data/stop_requested.flag` が作られると安全に停止します。
  - PID ファイルは `data/execution.pid` に作成されます。

- Monitoring（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  挙動:
  - 監視ループのポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
  - Monitoring は環境に関わらず本番の `sqlite_path` を使用して監視テーブルに書き込みます。
  - 停止フラグ `data/stop_requested.flag` を検知するとループを終了します。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

備考:
- ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで出力されます。`LOG_DIR` で変更可。
- MONITOR のポーリング間隔やログレベルは環境変数で調整可能です。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys をルートにした主要構成）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（アプリ設定をプロパティで提供）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py  — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（テーブル作成・CRUD）
    - system_monitor.py — システムリソース・データ鮮度チェック
    - trade_monitor.py — （注文監視、コードベースに含まれる他部分）
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag 管理（Execution の停止トリガ）
    - monitoring_engine.py — 各 Monitor を束ねる実行ループ
    - alert_manager.py — アラート送信（LINE 等の実装想定）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py ...
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - data/
    - pipeline.py, stats.py など（DuckDB 用データ処理）
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py — OpenAI を使ったニューススコアリング
    - regime_detector.py — レジーム判定
  - tools/
    - paper_verification_report.py

その他:
- data/ 以下に DB ファイル（data/monitoring.db, data/paper_trading.db）、flag/pid ファイルが作成されます。
- logs/ 以下にログファイルが出力されます（`kabusys.utils.logging_setup.setup_logging` が作成）。

---

## 運用メモ / 注意点

- KABUSYS_ENV が `live` の場合は本番運用なので `.env` の内容（API キー、通知先など）を厳重に確認してください。validate_config でも注意喚起を行います。
- Kill Switch は `KillSwitch` によって `data/kill.flag` を作成して ExecutionEngine に停止シグナルを送る設計です。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされますが、本番では危険なため推奨されません。
- OpenAI API を利用するモジュール（ai.news_nlp / ai.regime_detector）は API キー（OPENAI_API_KEY）とネットワークが必要です。API 欠落・失敗時はフェイルセーフで継続する実装が多数ありますが、期待したスコアが得られない可能性があります。
- 実行中の停止は `data/stop_requested.flag` を作成すると各 run_* スクリプトが検知して安全に終了します。運用環境では監視プロセスや systemd 等で監督するのが望ましいです。

---

## 追加情報 / 開発時のヒント

- DuckDB と prices_daily / raw_financials / raw_news 等のテーブル構造が必要です。初期データの投入は data pipeline モジュールを使って行う想定です。
- unit テストでは外部 API 呼び出し（OpenAI 等）をモックするため、モジュール内部の _call_openai_api 等を patch してください（コード内にコメント例あり）。
- ログや DB のパスは Settings を通じて一元管理されているため、環境変数で簡単に切り替え可能です。

---

README はここまでです。必要であれば次の内容を追加します:
- 具体的な requirements.txt / pyproject.toml の推奨依存一覧
- 各モジュールの詳細な API/関数リファレンス
- systemd / supervisor 用の起動ユニット例
- テスト実行手順

どれを追加しますか？