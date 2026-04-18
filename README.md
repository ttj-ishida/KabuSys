# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ部分）。  
この README はコードベースから自動作成された概要ドキュメントです。実際の運用前には必ず `python -m kabusys.validate_config` による設定検証を行ってください。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・実行コマンド）
- 主要環境変数（抜粋）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究用モジュール群をまとめたプロジェクトです。  
主な目的は以下です。

- 売買シグナルの生成・ポートフォリオ構築・ポジションサイズ計算（純粋関数群）
- ExecutionEngine による発注管理（本番 / ペーパートレードの分離）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- DuckDB / SQLite を使った履歴・分析データ管理
- OpenAI を利用したニュース NLP（センチメント）と市場レジーム判定（オプション）
- ペーパートレード検証レポート生成ツール

設計方針として、ビジネスロジックと永続化・IOを分離し、テストしやすい純粋関数群を多用しています。

---

## 主な機能一覧

- 実行・監視用スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 or ペーパートレード）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 環境設定支援
  - config_setup.py: 対話式で .env を生成・更新するウィザード
  - validate_config.py: .env および config/*.yaml の事前検証 CLI（--strict オプションあり）
- 監視・安全機構
  - monitoring/*: system, trade, risk 各種モニタ、kill switch、alert 管理、監視 DB 初期化
  - monitoring_db: SQLite ベースの永続化（冪等なテーブル作成 / マイグレーション含む）
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み計算、セクター制約・レジーム乗数、ポジションサイズ計算
- 研究・ファクター計算
  - research/*: モメンタム、ボラティリティ、バリュー等のファクター、将来リターン、IC 計算
- AI（OpenAI）連携
  - ai/news_nlp.py: ニュース記事を LLM でスコアリングして ai_scores に保存
  - ai/regime_detector.py: ETF の MA とマクロニュースを LLM 結果と組合せた市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポート出力

---

## セットアップ手順

以下はローカルで動かすための一般的な手順です。プロジェクトに requirements.txt があればそれを使用してください。

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 必要パッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (validate_config の YAML 検証を行う場合)
   ```
   pip install duckdb psutil openai PyYAML
   ```
   ※ 実運用では requirements.txt を用意して `pip install -r requirements.txt` を推奨します。

4. 必要ディレクトリを作成
   ```
   mkdir -p data logs
   ```

5. .env の準備
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成（.env.example を参考にしてください）。
   - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（validate_config が検出します）

6. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

以下は代表的な実行コマンド例です。プロジェクトルートから実行してください。

- 実行エンジン（ExecutionEngine）起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で制御します。
  ```
  python -m kabusys.run_execution
  ```
  - ペーパートレード時は設定により MockBrokerClient が使用され、データは `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 監視プロセスは常に本番用の sqlite_path を使って監視 DB を記録します（`Settings.sqlite_path`）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコア生成（プログラムから呼び出す）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定するか、関数呼び出し時に api_key を渡してください。
  - 例: `kabusys.ai.score_news(conn, target_date, api_key=...)`、`kabusys.ai.score_regime(conn, target_date, api_key=...)`

停止方法（安全停止 / フラグ操作）
- ExecutionEngine / Monitoring の停止には次のファイルを使用します:
  - data/stop_requested.flag: run_* スクリプトの外部停止フラグ（存在するとループを抜けます）
  - data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine の停止シグナルとして利用されます
- `KILL_FLAG_CLEAR_ON_START` が 1 の場合、起動時に kill.flag を自動クリアする設定（本番では 0 推奨）

ログ
- ログは `kabusys.utils.logging_setup.setup_logging` により統一的に設定されます。
- デフォルトは stdout と `logs/<app_name>.log`（日次ローテーション、30 日保持）。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合の API キー（AI モジュールで必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: monitoring ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）

※ 必須項目や詳細は `kabusys.config.Settings` を参照してください。`config_setup.py` ウィザードが入力支援を行います。

---

## ディレクトリ構成

（抜粋）プロジェクトルートを基準にした主要ファイル / ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み/Settings 定義 (.env 自動読み込み機能含む)
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（OpenAI 連携）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・API）
    - system_monitor.py
    - trade_monitor.py       — （コードベースに存在するがここでは省略）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信機能）
  - execution/               — ExecutionEngine, order_manager, broker factory 等（起動に必要）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                    — （運用時に data/*.db, flags を配置）
  - logs/                    — （ログ出力先、setup_logging により日次ローテーション）
  - utils/
    - logging_setup.py
    - process_priority.py
    - その他ユーティリティ

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （validate_config はこれらの存在・パースをチェックします。PyYAML 未導入時はパースチェックをスキップ）

- data/
  - monitoring.db (デフォルト SQLite)
  - paper_trading.db (ペーパートレード用)
  - kill.flag
  - stop_requested.flag
  - execution.pid

---

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨します。
- run_monitoring は監視 DB として常に Settings.sqlite_path（本番 DB）を使用します。監視は本番 DB を参照する設計です。
- OpenAI を利用する機能は API 呼び出しエラーやレート制限に対してリトライやフェイルセーフを備えていますが、API キーを適切に管理してください（.env を Git にコミットしないでください）。
- Logging は標準出力とファイルの両方に出ます。cron / systemd などの運用時には stdout/stderr の取り扱いに注意してください。
- DB のマイグレーション（monitoring_db.init_monitoring_db）は冪等実装になっており、既存 DB にカラムがない場合は自動で追加するケースがあります。

---

この README はコード内のドキュメンテーション（docstring / コメント）を基に作成されています。より詳細な挙動や設計文書（PortfolioConstruction.md や StrategyModel.md など）がプロジェクトに同梱されている場合はそちらも参照してください。質問や具体的な起動・設定例が必要であれば教えてください。