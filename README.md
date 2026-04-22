# KabuSys

日本株向け自動売買システム（軽量プロトタイプ / ライブラリ群）

このリポジトリは、戦略ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
およびニュースNLP / レジーム判定のユーティリティ群を含むモジュール群です。

---

## 主要機能（概要）

- 環境設定管理
  - .env の対話式ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）
- 実行エンジン（Execution）
  - ExecutionEngine の起動スクリプト（run_execution）
  - Paper Trading モード時は MockBroker を利用し、paper_trading DB に分離保存
- 監視（Monitoring）
  - System / Trade / Risk の監視コンポーネント
  - 監視ループ起動スクリプト（run_monitoring）
  - Kill Switch による発注エンジン停止トリガ
- ポートフォリオ関連（純関数群）
  - 候補選定、重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究用モジュール（Research）
  - Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - 将来リターン、IC、統計サマリ、ランク関数
- AI 関連
  - ニュースのセンチメントを OpenAI でスコアリングして ai_scores に書き込む（news_nlp）
  - ETF + マクロニュースを用いた市場レジーム判定（regime_detector）
- ユーティリティ
  - 統一的なロギング設定（stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法（X | Y）を使用）
- SQLite は標準で提供されます
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に必要）

推奨インストール例:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

（requirements.txt がある場合は `pip install -r requirements.txt` を使用）

初期設定（.env 作成）
1. 対話式ウィザードで .env を作成:
   ```
   python -m kabusys.config_setup
   ```
   - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - KABUSYS_ENV（development / paper_trading / live）
   - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH などを設定

2. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告もエラー扱いになり終了コード 1 を返します

ファイル/ディレクトリ自動作成:
- デフォルトでは data/ や logs/ は必要に応じて自動生成されますが、権限等で失敗する場合は手動で作成してください。

環境変数の補足（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログレベル / ログ格納ディレクトリ
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）

---

## 使い方（主なコマンド）

設定作成・検証
- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

起動スクリプト
- ExecutionEngine 起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。

- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（デフォルト 60 秒）。
  - 監視は Settings に従い本番の sqlite_path を使用します（環境に依らず本番DBを参照する仕様）。
  - 動作中にプロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します。

ツール
- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

AI 関連関数（ライブラリ呼び出し例）
- news_nlp.score_news / ai.regime_detector.score_regime は DuckDB 接続と target_date、OpenAI API キーを受け取ります。
  - 例（スクリプト内から呼ぶ）:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 1), api_key="sk-...")
    ```

停止・Kill Switch
- ExecutionEngine の停止トリガ:
  - 監視コンポーネントが条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止信号を与えます（KillSwitch）。
  - run_execution は起動時に kill flag をクリアするオプション（環境変数 KILL_FLAG_CLEAR_ON_START=1）を持ちますが、本番では通常 0 を推奨します。
- ループ停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution の監視ループが検知して順次終了します。

ログ
- ログは stdout に出力され、かつデフォルト logs/<app_name>.log に日次ローテートで出力されます。
- LOG_DIR 環境変数でログ格納先を変更できます。

---

## 重要な挙動メモ

- Paper Trading は本番 DB と完全に分離:
  - KABUSYS_ENV=paper_trading のとき、ExecutionEngine は paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用します。
- Monitoring は常に本番 sqlite_path を参照:
  - 監視は実稼働 DB を対象にする設計です（Settings.sqlite_path を使用）。
- DB マイグレーション（軽微）:
  - init_monitoring_db() は必要なテーブルを作成し、既存 DB に対してカラム追加（例: latency_ms, peak_value）を試みます（冪等）。
- OpenAI 呼び出しはリトライとパースの堅牢化が組み込まれていますが、API キー未設定時は ValueError を投げます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - __version__ (0.1.0)
  - config.py                     — 環境変数 / 設定読み込みロジック
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py                 — ニュースセンチメント（OpenAI 利用）
    - regime_detector.py          — 市場レジーム判定（ETF + マクロ）
  - monitoring/
    - monitoring_db.py            — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py           — システム状態・データ鮮度監視
    - trade_monitor.py            — （注文監視：参考ファイルあり）
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 書き込みロジック
    - monitoring_engine.py        — 各 Monitor を束ねるループ
  - execution/                    — 発注関連（OrderManager, ExecutionEngine 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py          — Momentum/Value/Volatility 等
    - feature_exploration.py      — 将来リターン / IC / 統計
    - __init__.py
  - utils/
    - logging_setup.py            — ルートロガー設定（stdout + 日次ファイル）
    - process_priority.py         — プロセス優先度 / CPU affinity 設定

（注）実際の全ファイルは src/kabusys 以下に多数あります。上は主要なコンポーネントの抜粋です。

---

## 開発者向けメモ

- 型ヒント・純関数設計を多用しており、研究 / バックテスト用途で関数を直接呼び出せます（DuckDB 接続を渡す設計）。
- DuckDB を使ったファクター計算は SQL と Python の組み合わせで高速に集計できます。
- ロギングとプロセス優先度設定は各起動スクリプトで最初に呼び出す共通ユーティリティが用意されています（setup_logging, set_process_priority）。
- テスト実行や CI で自動的に .env を読ませたくない場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## よくある運用フロー

1. リポジトリをチェックアウトして依存ライブラリをインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定を確認
4. 本番/ペーパーに応じて Execution を起動:
   - Paper: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - Live: KABUSYS_ENV=live python -m kabusys.run_execution
5. 監視プロセスを別プロセスで起動:
   - python -m kabusys.run_monitoring
6. ログ / data ディレクトリを監視し、必要に応じて kill.flag / stop_requested.flag を操作

---

問題や追加のドキュメントが必要であれば、どの部分を深掘りしたいか教えてください（例: ExecutionEngine の起動オプション、BrokerClient の実装、DuckDB テーブルスキーマなど）。