# KabuSys

日本株自動売買システムのミニマル実装（ライブラリ / 起動スクリプト群）

この README は提供されたコードベースの使い方・セットアップ・構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存ライブラリ
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数（主なもの）
- ファイル・ディレクトリ構成
- 注意事項・トラブルシューティング

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。  
このコードベースは以下のような役割を持つモジュールで構成されています。

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
- 監視（Monitoring）用ポーリングループ（run_monitoring, MonitoringEngine）
- 環境設定ウィザード / 設定検証ツール（config_setup, validate_config）
- Paper Trading 検証レポート生成ツール
- ポートフォリオ構築（選定・重み付け・株数決定）
- リサーチ（ファクター計算、特徴量探索）
- AI 関連：ニュース NLP（OpenAI を用いたセンチメント）やレジーム判定
- SQLite（監視用） / DuckDB（時系列・分析用）を用いた永続化

設計上の注意点（ソース内コメントより）
- .env を利用した環境変数管理（config.py）
- Paper Trading は本番 DB と分離（別 SQLite を使用）
- OpenAI 呼び出しは失敗時にフォールバックしてフェイルセーフにする実装
- ログは stdout と日次ローテーションファイルへ出力（utils.logging_setup）

---

## 主な機能一覧

- ExecutionEngine 起動 / 停止管理（run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使い paper_trading DB に記録
  - プロセス優先度の設定（high）
  - stop フラグファイルによる安全停止

- 監視（run_monitoring / MonitoringEngine）
  - システムリソース（CPU/メモリ/ディスク）監視
  - Execution の稼働検出、データ鮮度チェック
  - トレード・リスク監視（リスクイベント・ドローダウン）
  - Kill Switch（kill.flag）による自動停止シグナル
  - ポーリング間隔は環境変数で調整可能（MONITOR_POLL_INTERVAL）

- 環境設定支援
  - 対話式ウィザードで .env を作成・更新（config_setup.py）
  - validate_config で .env / config/*.yaml の事前検証

- 解析・研究
  - ファクター計算（momentum / volatility / value） — DuckDB を利用
  - 将来リターン・IC 計算、統計サマリー

- AI（OpenAI）連携
  - ニュース記事を LLM でスコアリングして ai_scores に格納
  - マクロニュースを LLM で評価して市場レジーム（bull/neutral/bear）を判定

- ユーティリティ
  - ログ設定（stdout + 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 前提・依存ライブラリ

推奨 Python バージョン：3.10+

主な Python パッケージ（代表例）
- duckdb
- psutil
- openai
- PyYAML（config 検証で利用されるが必須ではない）
- （必要に応じて）その他ライブラリ

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

プロジェクトに requirements.txt が無い場合は上記を参考に追加してください。

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成し依存ライブラリをインストール（上記参照）
3. .env の初期作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートに .env が作成されます（パスは引数で変更可能）。
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   ```
   必須 env が設定されているか、デフォルトパスの親ディレクトリ存在などをチェックします。
   --strict オプションで警告も失敗として扱います。
5. データディレクトリ作成（必要に応じて）
   - デフォルトで使用されるファイル例:
     - data/monitoring.db（SQLite, 監視用）
     - data/paper_trading.db（Paper Trading 用、KABUSYS_ENV=paper_trading 時）
     - data/kabusys.duckdb（DuckDB）
   - ログディレクトリ: logs/（デフォルト）

---

## 使い方

主要スクリプトはモジュールとして起動することを想定しています。

1. 監視（Monitoring）起動
   ```bash
   python -m kabusys.run_monitoring
   ```
   - デフォルトポーリング間隔: 60 秒
   - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（例: 30）
   - 停止制御:
     - プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

2. 実行エンジン（Execution）起動
   ```bash
   python -m kabusys.run_execution
   ```
   - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading DB に記録します（本番 DB と分離）。
   - 起動時に data/stop_requested.flag が既に存在する場合は起動しません。
   - 実行中は data/execution.pid ファイルが使用されます。

3. 設定検証
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

4. Paper Trading 検証レポート生成
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可）

5. AI 関連（例）
   - news_nlp.score_news / regime_detector.score_regime はコード内 API を呼び出して ai_scores / market_regime に書き込みます。OpenAI API キーは環境変数 OPENAI_API_KEY で指定。

ログ設定は utils.logging_setup.setup_logging により統一されます。デフォルトで stdout と logs/<app_name>.log（日次ローテーション）へ出力します。

---

## 環境変数（主なもの）

必須（少なくとも設定必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要な任意・設定
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合は paper_trading 用 DB に記録（分離）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject、デフォルト instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番で Kill Flag 自動クリアを有効にするか（0/1、デフォルト 0）

kill / stop フラグ
- デフォルト kill.flag: data/kill.flag — KillSwitch により ExecutionEngine に停止シグナルを送るファイル
- stop フラグ（停止要求）: data/stop_requested.flag — run_* スクリプトが監視している停止フラグ

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下にある主要なファイル・モジュール構成の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env 自動読み込みロジック
  - config_setup.py            — .env 対話ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / affinity
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 層（スキーマ生成・API）
    - system_monitor.py
    - trade_monitor.py         — （トレード監視: ソースは一部省略）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py         — （アラート送信ロジック: 実装に依存）
  - execution/
    - execution_engine.py      — 実行エンジン（エントリは run_execution）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py               — ニュース NLP（OpenAI を使用）
    - regime_detector.py       — レジーム判定（MA200 + macro sentiment）
    - __init__.py
  - tools/
    - paper_verification_report.py

（上記はコードベースの抜粋であり、実際のリポジトリ内にさらにファイルが存在する場合があります）

---

## 注意事項 / トラブルシューティング

- Python バージョン
  - ソースに使われている型注釈（X | Y）などから Python 3.10 以降を想定しています。

- .env の自動読み込み
  - config.py はプロジェクトルートを .git または pyproject.toml を基準に自動判定し、.env / .env.local をロードします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- validate_config
  - PyYAML がインストールされていない場合、config/*.yaml の内容チェックはスキップされます（警告が出ます）。

- OpenAI API
  - OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。API レート制限や 5xx エラーはリトライロジックがありますが、キーが無いと実行時に ValueError が発生します。

- 権限
  - process_priority の設定は OS と権限に依存します。アクセス権が無いと警告が出ますが処理は継続します。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等（既存テーブル確認）です。既存 DB にカラムが無い場合は ALTER TABLE による簡易マイグレーションを行います。

- 停止フラグ
  - 停止や Kill Switch 関連のファイル（data/stop_requested.flag, data/kill.flag）は運用上重要です。運用時にはこれらの取り扱いに注意してください（本番で KILL_FLAG_CLEAR_ON_START を 1 にするのは危険）。

---

README は以上です。実運用や拡張を行う際は、各モジュールの docstring / ソース内コメントを参照してください。必要であれば、この README をベースにインストール用の requirements.txt や systemd 起動ユニット、Dockerfile などの運用ドキュメントも作成できます。