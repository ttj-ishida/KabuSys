# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 起動スクリプト群）。  
このリポジトリは取引実行、監視、ポートフォリオ構築、ファクター研究、AI ベースのニュース解析などを含むコンポーネントで構成されています。

## 概要
- 実行エンジン（ExecutionEngine）：発注／注文管理／リスク管理を担う。  
- 監視（Monitoring）：システム状態・注文状態・リスクを定期的にチェックし、アラートや Kill Switch を発動。  
- 研究（Research）：DuckDB 上の時系列データからファクター（モメンタム、ボラティリティ、バリュー）・IC 等を算出。  
- AI（News NLP / Regime Detector）：OpenAI を用いたニュースのセンチメント集約や市場レジーム判定。  
- ペーパートレード用ツール（Paper Verification Report）など運用・検証補助スクリプト。

ライブラリ部は純粋関数・DB読み書き層に分かれており、テストや研究用に再利用しやすく設計されています。

---

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）。
  - Paper Trading 時は MockBrokerClient を使用し、別 DB（data/paper_trading.db）へ記録。
  - プロセス優先度設定・PID ファイル管理・停止フラグ検出。
- 監視ループ起動スクリプト（run_monitoring.py）
  - システムリソース、データ鮮度、プロセス生存、注文状況、リスクをポーリング。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視ログは SQLite（monitoring.db）に永続化。
- 監視サブコンポーネント
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager（ログ/LINE 等へ通知する想定）。
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重配分、ポジションサイズ計算、セクターキャップ適用、レジーム乗数。
- 研究用モジュール
  - ファクター計算（mom/volatility/value）、将来リターン計算、IC、統計サマリー。
- AI モジュール
  - news_nlp: raw_news を集約して OpenAI に送り、銘柄別センチメント（ai_scores）を書き込む。
  - regime_detector: ETF の MA 差とマクロニュースから市場レジームを判定して格納。
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度設定、CPU affinity（utils/process_priority.py）
- 運用ツール
  - tools/paper_verification_report.py：ペーパートレードの稼働率・成立率・レイテンシ等を集計しレポート出力。

---

## 必要要件（推奨）
- Python 3.9+
- ライブラリ（抜粋）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- SQLite（標準ライブラリに同梱）

（実際の requirements.txt がある場合はそれを使用してください。）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# または: pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成して依存をインストールする。

2. .env の準備（推奨）
   - 対話式ウィザードを使って .env を作成／更新できます：
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成された .env は Git 管理対象にしないでください（README や .gitignore を参照）。

3. 設定検証（起動前チェック）
   - .env と config/*.yaml の状態を検証します：
     ```bash
     python -m kabusys.validate_config
     # 警告もエラー扱いにする場合:
     python -m kabusys.validate_config --strict
     ```

4. DB パスなどの初期ディレクトリを作成
   - デフォルトでは以下ファイルパスを使います（必要に応じて .env で上書き）:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - ログ・data ディレクトリは自動作成されますが、権限等で失敗する場合は手動で作成してください。

5. OpenAI を使う機能を使う場合
   - 環境変数 OPENAI_API_KEY を設定してください（news_nlp/regime_detector の API 呼び出しで使用）。
   - AI 機能はネットワークアクセスとコストが発生する点に注意してください。

---

## 使い方（実行例）

- 監視ループ起動
  - デフォルト（ポーリング間隔 60 秒）:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を変更（秒）:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は内部で data/stop_requested.flag を監視しています。ファイルが存在するとループを終了します。

- 実行エンジン起動（ExecutionEngine）
  - 本番 / 開発は KABUSYS_ENV で切替:
    ```bash
    # 開発（デフォルト）
    python -m kabusys.run_execution

    # ペーパートレード（MockBroker を使用、DB は data/paper_trading.db）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

    # 本番
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - 実行エンジンは data/stop_requested.flag を検知すると停止します。ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を作成します。

- .env ウィザード / 設定検証
  - .env 作成:
    ```bash
    python -m kabusys.config_setup
    ```
  - 設定検証:
    ```bash
    python -m kabusys.validate_config
    ```

- ペーパートレード検証レポート
  - デフォルト DB を使う:
    ```bash
    python -m kabusys.tools.paper_verification_report
    ```
  - 期間指定 / DB 指定:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
    ```

- ライブラリ的な利用（例: 研究・スクリプト内で）
  - DuckDB 接続を渡してファクター計算等を呼ぶ:
    ```python
    import duckdb
    from datetime import date
    from kabusys.research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, date(2026, 4, 11))
    ```
  - AI スコアリング（OpenAI API キー要）
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_count = score_news(conn, date(2026, 4, 11), api_key="sk-...")
    ```

---

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート用、任意）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（本番実行時の Kill Flag 自動クリア挙動）

詳しい項目は kabusys.config.Settings のドキュメント（プロパティ docstring）を参照してください。

---

## 運用上の注意
- Paper Trading は本番 DB と完全に分離されています（設定により切替）。本番環境で設定ミスをしないよう .env を慎重に管理してください。
- Kill Switch（data/kill.flag）や stop flag（data/stop_requested.flag）は運用上重要です。特に本番で KILL_FLAG_CLEAR_ON_START=1 は危険です（validate_config.py でも警告）。
- OpenAI を使う部分は外部 API 呼び出しと料金が発生します。API リクエスト制御・リトライ・フォールバックが実装されていますが、キー管理・コスト監視を行ってください。
- ログは logs/<app_name>.log に日次ローテーション（30日保持）で出力されます。ログディレクトリのパーミッションに注意してください。

---

## ディレクトリ構成（抜粋）
src/kabusys 以下の主要ファイル／モジュール:

- __init__.py
- config.py                  — 環境変数/設定読み込み
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_monitoring.py          — 監視ループ起動スクリプト
- run_execution.py           — 実行エンジン起動スクリプト

- ai/
  - news_nlp.py              — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py       — 市場レジーム判定
- monitoring/
  - monitoring_db.py         — SQLite 永続化層
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
- execution/                  — ExecutionEngine 周り（BrokerFactory, OrderManager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py         — ログ設定ユーティリティ
  - process_priority.py      — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py

プロジェクトルート:
- .env, .env.local (環境依存)
- data/                      — デフォルト DB・フラグ類（data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag 等）
- logs/                      — ログ出力先
- config/                    — YAML 設定テンプレート群（system_config.yaml 等）

---

## 開発者向けメモ
- DuckDB を利用する研究関数は接続（DuckDBPyConnection）を受け取り SQL を実行します。データテーブル名（prices_daily, raw_financials 等）を想定しています。
- 監視系は SQLite（monitoring_db）に対するマイグレーション処理を持ち、冪等でテーブルを作成します。
- AI 呼び出し部分はリトライ・レスポンス検証を備えており、部分失敗時に既存スコアを不必要に消さない工夫（コード絞り込みの DELETE → INSERT）があります。
- テスト時は外部 API 呼び出しをモックできるように内部呼び出し関数を patch 可能に設計されています（例: _call_openai_api の差し替え等）。

---

README にない個別の使い方や API ドキュメントが必要でしたら、目的に応じて具体的なコマンド例やモジュール呼び出し例を追記します。どの部分を補足しましょうか？