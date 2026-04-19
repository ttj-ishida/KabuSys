# KabuSys — 日本株自動売買システム

小規模な自動売買フレームワーク。市場データ解析、ポートフォリオ構築、発注（実運用/ペーパートレード）、監視・アラート、LLM を使ったニュース解析などの機能を備えています。

> バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（よく使うコマンド）
- 環境変数 / 設定
- 停止・Kill スイッチについて
- ディレクトリ構成（主要ファイル説明）
- 依存パッケージ（概要）
- 補足・運用上の注意

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けライブラリ兼実行スクリプト群です。設計は以下を重視しています。

- 明確な開発 / ペーパートレード / 本番切替（KABUSYS_ENV）
- DuckDB / SQLite を使った分析・監視データ永続化
- ポートフォリオ構築・ポジションサイジングの純粋関数群（テスト容易）
- モニタリングコンポーネントで稼働監視・リスク検知・Kill Switch を実装
- OpenAI を用いたニュースセンチメント / レジーム判定モジュール（オプション）
- 実行エンジンはペーパートレード時にモックブローカーを使用（本番 DB と分離）

---

## 主な機能一覧

- 実行（ExecutionEngine）:
  - 本番 / ペーパートレード切替
  - ブローカークライアント生成（Mock 等）
  - 注文管理、リスク管理、調整（reconciler）
- 監視 (Monitoring):
  - SystemMonitor（CPU/メモリ/ディスク、データ鮮度、プロセス生存確認）
  - TradeMonitor（滞留注文・約定異常などの検出）
  - RiskMonitor（ドローダウン、ポジション上限検出）
  - KillSwitch（条件に応じて停止フラグを書き込み）
  - MonitoringEngine：各 Monitor を組み合わせた運用ループ
- ポートフォリオ構築:
  - 候補選定、等ウェイト/スコアウェイト、リスクベースのポジション決定
  - セクター集中制限、レジーム乗数
- リサーチ / ファクター計算:
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン、IC 計算、特徴量サマリ
- AI:
  - ニュースの NLP スコアリング（OpenAI）
  - マクロニュース + ETF MA での市場レジーム判定
- ツール:
  - Paper Trading 検証レポート生成スクリプト
  - 対話式 .env 設定ウィザード、設定検証 CLI
- ユーティリティ:
  - 統一的なロギング設定（console + 日次ローテーション）
  - プロセス優先度 / CPU affinity 設定

---

## セットアップ手順（手早い開始手順）

1. リポジトリをクローンしてソースルートに移動（python パッケージ状態を想定）:
   git clone ... && cd <repo>

2. 仮想環境を作って依存パッケージを入れる（プロジェクトに requirements.txt がある想定）:
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   （主要依存: duckdb, psutil, openai, sqlite3 は標準で利用可能。PyYAML は optional。）

3. .env を作成（対話式ウィザード）:
   python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 選択肢に沿って設定してください。

   もしくは .env を手で作成。デフォルトのパス等は README 下部の「環境変数 / 設定」を参照。

4. 設定検証（起動前に実行推奨）:
   python -m kabusys.validate_config
   エラーがある場合は修正、--strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

5. 必要なディレクトリの作成（logs / data 等は自動作成されますが、手動でも）:
   mkdir -p data logs

---

## 使い方（コマンド例）

- 実行エンジン起動（通常はサーバ上でデーモンとして実行）:
  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、ペーパートレード用 DB（デフォルト data/paper_trading.db）に分離して記録されます。
  - 実行はスレッドで行われ、data/stop_requested.flag により外部から停止できます。

- モニタリング起動（ポーリングループ）:
  python -m kabusys.run_monitoring

  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path（monitoring DB）を利用します（KABUSYS_ENV に依存せず本番パスを利用する実装になっています）。
  - run_monitoring は data/stop_requested.flag の存在でループを終了します。

- 対話式 .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで SQLite ファイルパスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- AI モジュールの利用:
  - ニュース NLP / レジーム判定は OPENAI_API_KEY が必要です（引数から渡すことも可能）。
  - これら関数は DuckDB 接続と target_date を受け取り、結果をテーブルに書き込みます（実行スクリプトには組み込み済みのはずです）。

---

## 環境変数 / 設定（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 主要（デフォルト値あり / 説明）
  - KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト: development
  - DUCKDB_PATH: DuckDB DB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） — デフォルト: INFO
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring のみ、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: ExecutionEngine / Kill Switch 関連

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` を自動読み込みします。
  - .env.local は上書き読み込みされ、OS 環境変数は保護されます。
  - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 停止・Kill スイッチについて

運用上の停止方法は複数あります。実装上の挙動は次の通りです。

- stop_requested.flag（data/stop_requested.flag）
  - run_execution と run_monitoring のトップレベルループはこのファイルの存在を監視し、存在すれば安全に終了します。
  - 外部から即時に停止したい場合はこのファイルを作成してください。

- Kill Switch（data/kill.flag 等）
  - 監視コンポーネント（KillSwitch）が、ドローダウンやポジション上限などの条件を満たすと `kill.flag` を書き込みます。
  - KillSwitch は冪等に動作し、理由文字列をファイルに書きます。
  - ExecutionEngine 側では設定された kill flag を参照して動作を止める設計になっています（Settings.kill_flag_path を使用）。
  - 本番運用では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動でクリアしない）。

- PID ファイル
  - ExecutionEngine は起動時に PID ファイル（data/execution.pid 等）を扱います。強制終了／復旧の管理に使えます。

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・丸め・資金制約処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコア化し ai_scores へ書き込み
    - regime_detector.py — ETF MA + マクロニュースの LLM で市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite を使った永続化層（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py — (コードベースにあり) 発注／約定の監視ロジック
    - risk_monitor.py — ドローダウン/ポジション上限チェック
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 各モニタを束ねるループ
  - utils/
    - logging_setup.py — 共通ロギング設定（console + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定

（上記は主要なファイルのみを抜粋しています。詳細は src/kabusys 以下を参照してください）

---

## 依存パッケージ（概要）

最低限想定されるパッケージ:

- Python 標準ライブラリ: sqlite3, logging, threading, argparse, json, datetime, pathlib, os, time など
- duckdb — 分析用 DB 接続
- psutil — システムリソース計測・プロセス操作
- openai（OpenAI Python SDK）— AI モジュールを使う場合
- PyYAML（任意）— validate_config で config/*.yaml を検証する場合

requirements.txt があればそれを参照してください。

---

## 運用上の注意・ベストプラクティス

- KABUSYS_ENV を適切に設定してください（特に本番では `live`）。本番時は LINE の通知設定などを必ず確認してください。
- .env は絶対に Git にコミットしないでください（config_setup も README に警告ヘッダを出力します）。
- モニタリングは run_monitoring.py をデーモン化して常時稼働させることを推奨します。MONITOR_POLL_INTERVAL で間隔を調整可能です。
- AI モジュールは外部 API を呼ぶため、API レート制限やコストに注意してください。OPENAI_API_KEY の保護を徹底してください。
- ペーパートレードは paper_sqlite_path に完全に分離されます。意図しない本番 DB 上書きを避けるため、環境変数 `PAPER_TRADING_SQLITE_PATH` を確認してください。
- ログは logs/<app_name>.log に日次ローテートで保存されます。ログディレクトリの権限や容量管理を行ってください。
- Kill スイッチや stop flag の動作を運用手順に落とし込んでください（自動復帰設定は危険です）。

---

この README はコード中の実装（config, run_*.py, monitoring, portfolio, research, ai 等）をベースにした運用・導入メモです。より詳細な設計・アルゴリズム仕様（PortfolioConstruction.md や StrategyModel.md 等）がプロジェクト内にある場合は、そちらも参照してください。必要があれば、特定モジュールの使い方や API 例（関数シグネチャ、戻り値）を追記します。