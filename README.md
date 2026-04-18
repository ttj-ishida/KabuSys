# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI サービス等）をまとめたものです。  
以下はこのコードベースを使い始めるための README（日本語）です。

---

## 概要

KabuSys は複数の責務を分離したモジュール型アプリケーションです。主な機能は以下の通りです。

- ExecutionEngine（売買実行）: 実際の/ペーパートレード発注、注文管理、リスク管理、リコンサイル
- Monitoring（監視）: システム稼働状況、データ鮮度、注文ログ、リスク指標の定期ポーリングと記録
- Portfolio（ポートフォリオ構築）: 候補選定・配分・ポジションサイジング・セクター制限
- Research（リサーチ）: ファクター計算（モメンタム/バリュー/ボラティリティ等）、特徴量解析、IC 計算
- AI（ニュース / レジーム判定）: LLM を用いたニュースのセンチメント集計、マクロセンチメントとETF MAに基づくレジーム判定
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定、レポートツール 等

設計上の特徴：
- 設定は .env（または環境変数）で管理。KABUSYS_ENV により `development` / `paper_trading` / `live` を切替え。
- DB: 監視・注文履歴は SQLite（デフォルト：data/monitoring.db）、分析は DuckDB（デフォルト：data/kabusys.duckdb）。ペーパートレードは分離された SQLite（data/paper_trading.db）。
- LLM 呼び出し（OpenAI）は堅牢なリトライとレスポンス検証を実装。

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading のときは MockBroker を使用し DB を分離）
- run_monitoring.py: SystemMonitor ポーリングループを起動（MONITOR_POLL_INTERVAL で間隔を変更可能）
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: .env と config/*.yaml の静的チェック CLI
- tools/paper_verification_report.py: ペーパートレードの検証レポート生成
- portfolio/*: 候補選定、重み付け、リスク調整、ポジションサイズ計算
- research/*: ファクター計算、特徴量解析、IC 計算
- ai/*: news_nlp（ニューススコアリング）・regime_detector（市場レジーム判定）
- monitoring/*: DB 永続化層・各種モニタ（system/trade/risk）・KillSwitch・Alert 管理
- utils/*: ログ設定・プロセス優先度等のユーティリティ

---

## セットアップ手順

前提:
- Python 3.10+ を想定
- OS により追加で psutil のビルド依存パッケージが必要な場合があります（例: Linux の場合 build-essential 等）

1. リポジトリをクローン / コピー
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt  
   （本コードでは外部パッケージとして例: duckdb, psutil, openai, PyYAML が使われます）
   例:
   - pip install duckdb psutil openai PyYAML
4. .env を作成
   - 対話式: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit(1)）
6. ディレクトリ／ファイル(自動作成)
   - デフォルトで使用する data/ や logs/ は必要に応じて自動作成されますが、権限によっては手動で作成してください。

環境変数（主要なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution モード（development / paper_trading / live）、デフォルト development
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL / LOG_DIR: ログ設定

注意:
- 本番環境（KABUSYS_ENV=live）では設定ミスが致命的なので validate_config を必ず確認してください。
- .env は機密情報を含むため Git にコミットしないでください。

---

## 使い方（起動例）

ログ設定を統一的に行うため、各モジュールは内部で setup_logging を呼び出します。

1. 環境ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict

3. ExecutionEngine 起動（本番 / ペーパートレード共通）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH に書き込む
     - 起動時に data/stop_requested.flag があるとエンジンを起動せず終了
     - 実行中に data/stop_requested.flag が作成されるとエンジンが停止する

4. Monitoring 起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
   - 監視ループは data/stop_requested.flag の存在で終了します

5. Kill Switch（外部から ExecutionEngine を止めたい場合）
   - data/kill.flag を作成すると（KillSwitch が検出すれば）ExecutionEngine に停止シグナルを送ります
   - KillSwitch は Settings.kill_flag_clear_on_start が 1 に設定されていれば起動時に自動クリアする挙動を持つ（本番では 0 推奨）
   - Kill flag を手動で消す: rm data/kill.flag

6. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

7. AI モジュール（ニューススコア / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要
   - 直接スクリプトで呼ぶ例: Python REPL などで kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ
   - これらは DuckDB 接続を受け取り、ai_scores / market_regime テーブルへ書き込みます

ログ:
- デフォルトログディレクトリ: logs/
- ログは stdout と日次ローテートされたファイル（logs/<app_name>.log）に出力されます
- ログレベルは LOG_LEVEL または setup_logging の引数で決定

プロセス優先度:
- 起動スクリプトは set_process_priority("high") を呼びますが、権限不足や OS によっては失敗して警告が出ます（挙動は安全側フォールバック）

停止 / 停止フラグ:
- 管理用のフラグファイル:
  - data/stop_requested.flag: run_* スクリプトが外部から終了させるために監視するファイル
  - data/kill.flag: KillSwitch が書き込む ExecutionEngine 停止フラグ

---

## ディレクトリ構成（抜粋）

（ルートがプロジェクトルート、ソースは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数/.env の読み込み・検証ロジック
  - config_setup.py
    - 対話式 .env ウィザード
  - validate_config.py
    - 起動前の設定チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading は分離 DB / mock broker）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ (stdout + 日次ファイル)
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成 / MonitoringDB ラッパ
    - system_monitor.py — CPU/Mem/Disk / データ鮮度 / プロセス生存監視
    - trade_monitor.py — (注文ログ監視: ファイル参照) *実装詳細があるファイル群*
    - risk_monitor.py — ドローダウン監視 / ポジション数監視
    - kill_switch.py — kill.flag の管理・評価
    - monitoring_engine.py — 監視モジュールの統合ポーリングエンジン
    - alert_manager.py — (通知管理: LINE など) *実装想定*
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
      - 実際の注文フロー / リスク管理 / リポジトリ実装
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・資金配分ロジック
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — マクロ + ETF MA によるレジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（上記に加えて config/*.yaml, data/ ディレクトリ等がプロジェクトルートに存在します）

---

## 注意点 / トラブルシューティング

- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）未設定だと validate_config でエラーになります。
- OpenAI を利用する機能は OPENAI_API_KEY が必要。無ければ例外またはフェイルセーフ（score_news 等は未取得なら 0 件）扱いになる部分があります。
- psutil を利用してプロセス優先度や CPU 情報を取得します。権限不足で AccessDenied が出る場合はログにワーニングが出て処理は継続します。
- DuckDB / SQLite ファイルへの書き込み権限が必要です。データディレクトリに対するパーミッションを確認してください。
- ローカルでテストするときは KABUSYS_ENV=development か paper_trading を使うと実注文を防げます。
- .env は機密情報を含むため絶対にコミットしないでください（config_setup でその旨の注意文が出ます）。

---

この README はコードベースの主要ファイル（起動スクリプト、設定、監視、ポートフォリオ、AI、リサーチ等）に基づいて作成しています。個々のモジュールの詳細（関数引数や追加の設定項目）は各ソースファイル内の docstring / コメントを参照してください。質問や追加で README に欲しい項目があれば教えてください。