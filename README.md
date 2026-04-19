# KabuSys

日本株自動売買システムの実装コア（ライブラリ＋起動スクリプト群）。

このリポジトリは、戦略・ポートフォリオ構築、発注実行、監視、研究・調査、AI（ニュースセンチメント）などを含むモジュール群を収録しています。小規模プロダクション運用を想定した設計で、環境変数／`.env` による設定、SQLite / DuckDB を使った永続化、OpenAI を利用した NLP モジュールなどを備えます。

---

目次
- プロジェクト概要
- 主な機能
- 要件（依存）
- セットアップ手順
- 環境変数（主要）
- 使い方（コマンド例）
- アーキテクチャと動作メモ
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。主な責務は以下です。

- 市場データ・財務データを使ったファクター計算（research）
- 銘柄選定、配分、ポジションサイズ計算（portfolio）
- 発注周りの実行エンジン（execution） — paper_trading と live を分離
- 実行状況・システム状態の監視（monitoring）と Kill Switch（自動停止）
- OpenAI を用いたニュース NLP（AI）と市場レジーム判定
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として「外部サーバに直接不正アクセスしない」「ルックアヘッドバイアスを避ける」「フェイルセーフ（API失敗時はスキップ）」などを採用しています。

---

## 主な機能一覧

- 設定関連
  - 対話式 `.env` ウィザード（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）
- 実行・監視
  - ExecutionEngine 起動スクリプト（run_execution）
  - SystemMonitor（CPU/メモリ/ディスク/データ鮮度監視）
  - TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
  - run_monitoring による常駐ポーリング
- 発注（Execution）
  - Paper trading モード分離（DB と挙動を本番と切り分け）
  - RiskManager / OrderManager / Reconciler 等の組み合わせ
- ポートフォリオ構築
  - 候補選定、等金額／スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究（Research）
  - Momentum / Volatility / Value 等ファクター計算（DuckDB を利用）
  - 将来リターン、IC（情報係数）、統計サマリ
- AI（ニュース）
  - OpenAI を使ったニュースセンチメント評価（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 要件（依存）

推奨 Python バージョン: 3.10+

主な外部パッケージ:
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合に任意）

インストール例:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements ファイルがあればそちらを使ってください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成し依存をインストール（上記参照）
3. 環境変数設定
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートに `.env` を作成／更新できます。
   - あるいは `.env` を手動で作成（`.env.example` を参照）
4. 設定検証（起動前チェック）:
   ```
   python -m kabusys.validate_config
   # 厳格モード（警告も失敗扱い）
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じてデータディレクトリを作成
   - デフォルトの DB / ログ格納場所は `data/` と `logs/`（設定で変更可）
   - `.env` 内のパスを確認してください

---

## 環境変数（主要）

主な環境変数とデフォルト値 / 必須情報:

- 必須
  - JQUANTS_REFRESH_TOKEN — J‑Quants API（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）

- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）

- データベース
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

- ログ / 実行制御
  - LOG_LEVEL — ログレベル（デフォルト: INFO）
  - LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
  - PID_FILE_PATH — ExecutionEngine の pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1, デフォルト 0）

- モニタリング
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒, デフォルト: 60）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値（%）

- Paper trading / Mock
  - PAPER_FILL_MODE — instant / partial / never / reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY — AI モジュール（news_nlp / regime_detector）で使用

その他の補助変数はソース（kabusys.config.Settings）を参照してください。

---

## 使い方（主要コマンド例）

- 環境ウィザード（.env生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine（発注エンジン）起動
  - 通常起動（環境依存で paper_trading/live を切替）
  ```
  python -m kabusys.run_execution
  ```
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に書き込みます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - Execution は data/execution.pid に PID を書きます。

- Monitoring（常駐監視）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` で間隔（秒）を指定可能（デフォルト: 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を利用します（監視の永続化先は production DB を想定）
  - 停止はプロジェクトルートの `data/stop_requested.flag` を作成することで検知して終了します

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを別指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラム API）
  - ニューススコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は DuckDB 接続 (duckdb.connect(...))
    score_news(duckdb_conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```

---

## 動作メモ / 運用上の注意

- Kill Switch / 停止制御
  - リスク閾値を超えると `KILL_FLAG_PATH`（デフォルト data/kill.flag）に理由を書き込んで ExecutionEngine に停止シグナルを送ります。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START が 1 の場合、kill.flag を自動クリアする設定があります（本番では 0 推奨）。
  - 手動で停止（運用側）する場合は `data/stop_requested.flag` を作成すると run_monitoring / run_execution のループが終了します。

- ログ
  - ログは stdout と日次ローテートされたファイル（logs/<app>.log）に出力されます（kabusys.utils.logging_setup）。
  - ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソールのみ出力されます。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等で必要なテーブルと列を作成します。既存 DB に新カラムがない場合は ADD COLUMN による簡易マイグレーションを行います。

- Paper trading と本番 DB 分離
  - run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使って完全に分離された DB に書き込みます。テスト／検証時は必ず設定を確認してください。

- ルックアヘッドバイアス回避
  - AI / research のモジュールは内部で system 時刻や DB クエリにおいてルックアヘッドしない設計になっています（target_date を明示する API）。

---

## ディレクトリ構成（主要ファイル抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings クラス（自動 .env ロード含む）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン／ポジション数監視
    - trade_monitor.py — （発注状況監視）※実装参照
    - kill_switch.py — Kill Switch 実装（flag ファイル制御）
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — （通知管理）※実装参照
  - execution/ — 発注エンジン関連（Engine, OrderManager, BrokerFactory, RiskManager 等）
  - portfolio/ — 銘柄選定・重み計算・ポジションサイズ（portfolio_builder, position_sizing, risk_adjustment）
  - research/ — ファクター計算 / feature_exploration
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリング
    - regime_detector.py — マクロ + ma200 を使った市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

（上記は主要ファイルのみ。詳細はソースコードコメントや docstring を参照してください）

---

## よくある質問 / トラブルシュート

- Q: モニタが本番 DB を参照しているか？
  - A: run_monitoring は KABUSYS_ENV に関係なく Settings.sqlite_path（本番監視 DB）を使用します。運用時は監視 DB のパスに注意してください。

- Q: ペーパートレードのデータをどこに書く？
  - A: KABUSYS_ENV=paper_trading の場合は Settings.paper_sqlite_path（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。

- Q: OpenAI の呼び出しでエラーが出る（API キーなど）
  - A: 環境変数 OPENAI_API_KEY を設定するか、API キーを関数引数に渡してください。API 呼び出しはリトライとフォールバック（失敗時は 0.0 などを使う）が実装されていますが、API キー未設定だと例外になります。

---

この README はソース内ドキュメント（docstring）を元に作成しています。各モジュールに詳細な docstring があるため、実装や挙動の詳細は該当ファイルを参照してください。運用時は必ず `python -m kabusys.validate_config` で設定検証を行い、本番環境（KABUSYS_ENV=live）では kill flag 等の設定を慎重に扱ってください。