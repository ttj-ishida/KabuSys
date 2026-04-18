# KabuSys

日本株自動売買システムのモジュール群（ライブラリ兼実行スクリプト群）。

このリポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、発注実行（本番／ペーパートレード）、監視・アラート、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

---

## 概要

- Python パッケージ `kabusys` を中心に設計されており、コマンドラインからの起動スクリプト（例: ExecutionEngine、Monitoring）や対話式の `.env` 作成ウィザード、設定検証ツール、レポート生成ツールを提供します。
- 永続化は主に SQLite（監視／ペーパートレード DB）と DuckDB（データ分析用）を使用します。
- 環境変数・`.env` による設定管理を行い、`Settings` クラス経由で安全に参照できます。
- OpenAI（GPT 系）を用いたニュースセンチメント・レジーム判定機能を備えています（API キー必須）。

---

## 主な機能一覧

- 実行系
  - run_execution.py: ExecutionEngine の起動スクリプト（本番 / paper_trading 切替）。
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に記録。
    - 停止はフラグファイル（data/stop_requested.flag）で検知。
- 監視系
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視ログは SQLite（`SQLITE_PATH`）に永続化。Monitoring は常に本番 sqlite_path を使用する設計。
- 設定管理／検証
  - config_setup.py: 対話式ウィザードで `.env` を作成／更新。
  - validate_config.py: `.env` と `config/*.yaml` の基本的な妥当性チェック（`--strict` オプションあり）。
- 研究・分析
  - research パッケージ: ファクター計算（momentum / volatility / value）や特徴量探索（IC 等）。
  - data → DuckDB を利用したデータパイプライン（prices_daily / raw_financials など）想定。
- ポートフォリオ構築
  - portfolio パッケージ: 候補選定、重み計算、ポジションサイズ計算、セクター上限適用等。
- AI
  - ai.news_nlp: ニュース記事を LLM でセンチメント評価して ai_scores に書き込む処理。
  - ai.regime_detector: ma200 とマクロニュースセンチメントから市場レジームを判定。
- ユーティリティ
  - utils: ロギング設定、プロセス優先度 / CPU affinity 設定など。
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポートを生成（稼働率・成立率・レイテンシなど）。

---

## セットアップ手順（開発向け）

1. リポジトリをクローンし、Python 仮想環境を作成／有効化します。

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストールします（requirements ファイルがない場合は主な依存を手動で入れてください）。

   推奨パッケージ（少なくとも）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   - そのほか必要に応じて

   例:

   ```bash
   pip install duckdb psutil openai PyYAML
   ```

3. 初期ディレクトリを作成（デフォルトで使用するディレクトリ）:

   ```bash
   mkdir -p data logs config
   ```

4. 環境変数の準備:
   - 対話式で `.env` を作る場合:

     ```bash
     python -m kabusys.config_setup
     ```

   - または、`.env`（プロジェクトルート）に必要なキーを記載してください。
     自動ロードはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

5. 設定検証:

   ```bash
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

---

## 主な環境変数（代表例とデフォルト）

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- API / トークン
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能利用時)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- ログ
  - LOG_DIR (デフォルト: logs/)
  - LOG_LEVEL (デフォルト: INFO)
- 監視 / 停止制御
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリア（1 で有効、デフォルト 0）
- その他
  - PID / フラグファイル:
    - pid ファイル: data/execution.pid（Settings.pid_file_path で参照）
    - stop フラグ: data/stop_requested.flag（run_monitoring/run_execution が監視）
    - kill フラグ: data/kill.flag（KillSwitch が書き込む）

---

## 使い方（主なコマンド）

- 実行エンジン（ExecutionEngine）を起動

  - 通常起動（KABUSYS_ENV に応じて挙動が切り替わる）:

    ```bash
    python -m kabusys.run_execution
    ```

  - ペーパートレードで起動するには .env で `KABUSYS_ENV=paper_trading` を設定するか、環境変数で指定してください。
    ペーパートレード時は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）が使用され、本番 DB と分離されます。

  - 停止:
    - 実行中のプロセスは `data/stop_requested.flag` の存在を検出すると安全に停止します（同様に監視プロセスも検出して停止処理）。

- 監視プロセスを起動

  ```bash
  # デフォルト 60 秒間隔
  python -m kabusys.run_monitoring

  # ポーリング間隔を環境変数で変更
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  監視は system_status / trade_logs / risk_logs / dashboard 等のテーブルに記録します。監視は本番 sqlite_path を常に参照します（環境に依らず）。

- 設定ウィザード（.env 生成）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ペーパートレード検証レポート

  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定例
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定例
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- プログラム内 API（ライブラリとして利用）

  - 設定参照:

    ```python
    from kabusys.config import settings
    print(settings.sqlite_path)
    ```

  - AI スコアリングを呼ぶ（DuckDB 接続を渡す）:

    ```python
    import duckdb
    from kabusys.ai import score_news  # score_news は ai/__init__.py で公開

    conn = duckdb.connect("data/kabusys.duckdb")
    from datetime import date
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

  - レジーム判定:

    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

---

## 停止・安全関連ファイル

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py はこのファイルの存在をチェックしてループを終了します（外部プロセスからの停止指示に使用）。
- data/kill.flag
  - KillSwitch（監視ロジック）が書き込み、ExecutionEngine に致命的なリスクが発生した際に停止を促します。
  - `KILL_FLAG_CLEAR_ON_START` による自動クリアが設定可能（本番では `0` 推奨）。
- data/execution.pid
  - ExecutionEngine の PID ファイル（デフォルト path）。起動時に PID を記録します。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py (存在を前提)
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (存在を前提)
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - data/ (実行時に利用するローカルディレクトリ: DB / flags 等)
    - config/ (YAML テンプレートや設定ファイルを配置)
- logs/ (デフォルトのログ出力ディレクトリ)

注: 上記はコードベースから抽出した代表的なファイルとモジュールです。実際には他の補助モジュール（execution/*.py、data/*.py 等）が含まれる想定です。

---

## 注意事項 / 運用メモ

- .env は機密情報（API トークン等）を含むため Git にコミットしないでください（config_setup.py でも同旨の注意が出ます）。
- `KABUSYS_ENV=live` を設定すると本番動作になります。設定値（API トークン、LINE 通知設定、KILL_FLAG 確認等）を十分に確認してください。validate_config.py は `live` 時に追加の警告を出します。
- Monitoring は本番の monitoring DB（SQLITE_PATH）を参照して記録します。`KABUSYS_ENV` に関わらず監視ログは同一の sqlite_path に記録される設計です。
- Paper trading（ペーパートレード）は本番 DB と分離されるよう設計されています。ただし、運用時は DB パス設定を必ず確認してください。
- OpenAI を用いる機能は API キーの課金・レート制限があるため、運用では注意してください。失敗時のフォールバック（スコア 0.0）やリトライ処理は実装されていますが、API 呼び出しはコストが発生します。

---

README は以上です。実際の運用や導入に際しては config/*.yaml（存在する場合）の内容確認、`config_setup` → `validate_config` → 実行スクリプト の順で安全に進めてください。必要であれば、より詳細な運用手順やデプロイ手順（systemd ユニット、コンテナ化、監視ダッシュボード連携など）用のドキュメントも作成できます。