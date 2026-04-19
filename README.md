# KabuSys

日本株自動売買システムの軽量コアライブラリ。シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI（ニュースセンチメント／レジーム判定）・各種ユーティリティを含むモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の要件を満たすよう設計されたモジュール群です。

- データ解析（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み付け、株数算出）
- ExecutionEngine による発注処理（paper_trading と live を分離）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- OpenAI を用いたニュースセンチメント／市場レジーム判定（AI モジュール）
- .env 対話式設定ウィザード・起動前設定検証ツール
- ペーパートレード検証レポート等のツール

設計上のポイント:
- DuckDB と SQLite を用途別に使い分け（分析用 / 監視・発注ログ）
- 環境変数・.env による柔軟な設定
- フェイルセーフ（API失敗時のフォールバック、部分書き込みで既存データ保護）
- ルックアヘッドバイアス回避（日時の直接参照や未来データの使用禁止）

---

## 機能一覧

- 環境設定
  - アンチパターンを避ける .env 自動読み込み / 対話式ウィザード（kabusys.config_setup）
  - 起動前設定検証（kabusys.validate_config）
- 実行エンジン / 発注
  - ExecutionEngine 起動スクリプト（run_execution）
  - Paper trading 用 MockBroker と専用 DB（data/paper_trading.db）
  - 発注ログ・ポジションの永続化（SQLite）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
  - run_monitoring ポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可）
- ポートフォリオ構築
  - 候補選定、等重／スコア重み、リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数計算
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン・IC 計算・統計サマリー
- AI
  - ニュースセンチメント集計（OpenAI 使用: gpt-4o-mini を想定）
  - 市場レジーム判定（MA200 とマクロニュースの LLM 評価を混成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - ログ設定（TimedRotatingFileHandler + stdout）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必要条件 / 推奨環境

- Python 3.9+（typing の構文に合わせてください）
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML を検証する場合に必要）
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI / 外部 API を使う場合）

（プロジェクトに requirements.txt があればそちらを使用してください）

インストール例:
```
python -m pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードはデフォルト値を提示します。必須項目:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要な環境変数（抜粋）
   - KABUSYS_ENV: development / paper_trading / live
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
   - LOG_LEVEL (INFO 等)
   - OPENAI_API_KEY（AI 機能を使う場合）

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱い
   ```

---

## 使い方

基本的なコマンド例:

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に本番用の sqlite_path を使用（環境にかかわらず）
  - 停止: プロセスに KeyboardInterrupt（Ctrl-C）を送る、あるいはプロジェクトルートの data/stop_requested.flag を作成するとループが終了します。

- ExecutionEngine を起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、記録は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ行われ、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動をせずに終了します。
  - 実行中に data/stop_requested.flag を作成するとエンジンを停止します。
  - エンジンの PID は data/execution.pid に書き込まれます。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。--db で上書き可能。

- AI モジュール（プログラムから呼び出し）
  - ニューススコア: kabusys.ai.score_news (DuckDB 接続と target_date を渡す)
  - レジーム判定: kabusys.ai.regime_detector.score_regime

Kill Switch とフラグについて:
- kill.flag: リスクトリガにより自動で書き込まれる（Settings.kill_flag_path、デフォルト data/kill.flag）。ExecutionEngine 起動時に Kill Flag をクリアする設定（KILL_FLAG_CLEAR_ON_START）がありますが、本番では 0 を推奨します。
- stop_requested.flag: run_monitoring / run_execution が監視する外部停止要求ファイル。任意に作成してプロセスを止められます（プロセス自身も削除する実装がある場合あり）。

ログ:
- ログは stdout と logs/<app_name>.log に日次ローテートで出力されます（logs ディレクトリが作成されます）。setup_logging を全スクリプトで使用しています。

---

## よく使う設定項目（抜粋）

- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。run_monitoring 用。
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite パス
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート /src/kabusys を基準に抜粋）

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI 使用）
    - regime_detector.py    — 市場レジーム判定（MA200 + LLM）
  - monitoring/
    - monitoring_db.py      — SQLite 監視テーブル初期化・永続化層
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - system_monitor.py     — システム・データ鮮度監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — Kill Switch（flag 書き込み）
    - (trade_monitor 等 他ファイル)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity
  - data/                  — 実行時に使用するファイル（デフォルトパス）
    - monitoring.db (SQLITE)
    - paper_trading.db (paper trading 用)
    - kabusys.duckdb
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/                  — ログ出力先（ランタイムで作成）

（上記は主要モジュールの抜粋です。詳細はソースコメントを参照してください）

---

## 開発者向けメモ / 注意点

- .env は決してリポジトリへコミットしないこと（config_setup のヘッダにも注意書きあり）。
- validate_config で PyYAML がインストールされていない場合、YAML の内容検証がスキップされます（警告）。
- OpenAI 呼び出しはリトライ・スコア検証を行う実装になっていますが、API キー未設定時は例外を投げます。テスト時は該当関数をモックしてください。
- run_monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを残します（設計上の意図）。
- ExecutionEngine は paper_trading モードで DB を分離します。paper_trading のデータは paper_trading.db に保存され、本番 DB を汚染しません。

---

## トラブルシューティング

- ログディレクトリが作成できない場合: ログのファイルハンドラはスキップされ、stdout のみでログ出力されます。必要に応じて LOG_DIR 環境変数で出力先を変更してください。
- psutil でプロセス優先度変更に失敗する場合: 権限不足でエラーログが出ますが処理は継続します。
- DuckDB / SQLite の接続例外は、該当処理で適切にハンドリングされる設計ですが、DB パスや権限を確認してください。

---

この README はソースコード内のドキュメント文字列に基づいて作成しています。各モジュールの詳細な挙動や追加設定は該当ソース（src/kabusys 以下）を参照してください。必要であれば各コンポーネント（ExecutionEngine、MonitoringEngine、AI モジュール等）の使い方サンプルや API ドキュメントを別途作成します。