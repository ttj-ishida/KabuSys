# KabuSys — 日本株自動売買システム (README)

本ドキュメントはリポジトリ内の Python モジュール群（src/kabusys）に対する簡易 README です。システム全体像、主要機能、セットアップ、実行方法、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコアライブラリ群です。  
主な責務は以下の通りです。

- 市場データ（DuckDB）を用いたファクター / 特徴量計算（research）
- ポートフォリオ構築・重み計算・ポジションサイズ決定（portfolio）
- 発注処理（ExecutionEngine）と発注管理・リスク管理（execution）
- システム監視・アラート・Kill Switch（monitoring）
- ニュースを利用した LLM ベースのセンチメント解析（ai）
- ペーパートレード検証レポート等のツール（tools）

設計上の方針:
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV による動作切替）
- DuckDB を集計・リサーチ用 DB として使用
- SQLite を監視・発注ログの永続化に使用
- OpenAI API は外部 LLM 呼び出し用（ニュース NLP / レジーム判定）

---

## 機能一覧

- 環境設定ウィザード（.env 生成 / 更新）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml の検証）: `kabusys.validate_config`
- 実取引 / ペーパートレード用 ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用、専用 SQLite（data/paper_trading.db）へ記録
- 監視モード起動スクリプト（SystemMonitor のポーリング）: `kabusys.run_monitoring`
  - 環境に依らず本番の sqlite_path を監視用 DB として使用
- 監視エンジン: SystemMonitor / TradeMonitor / RiskMonitor をまとめて実行（アラート・Kill Switch）
- ニュース NLP（OpenAI を用いた銘柄別センチメント付与）: `kabusys.ai.news_nlp`
- 市場レジーム判定（MA とマクロニュースの LLM 評価の合成）: `kabusys.ai.regime_detector`
- 研究用ファクター計算（momentum / volatility / value）: `kabusys.research`
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・サイズ算出）: `kabusys.portfolio`
- ペーパートレード検証レポート生成ツール: `kabusys.tools.paper_verification_report`

---

## 必要要件（概略）

- Python 3.10 以上を想定（typing の構文などが使用されています）
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - (任意) PyYAML — validate_config の YAML 検証で使用
- その他: SQLite は標準搭載

実際の環境では requirements.txt を用意して pip でインストールしてください（本リポジトリに requirements.txt がない場合は上のパッケージをインストール）。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意して依存をインストールする（上記参照）。

2. .env の初期作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env（プロジェクトルート）を作成／更新します。`.env` は絶対に Git にコミットしないでください。

3. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションで警告も失敗扱いにできます:
   ```
   python -m kabusys.validate_config --strict
   ```

4. DB 初期化
   - Monitoring 用の SQLite（デフォルト: data/monitoring.db）は各起動スクリプト内で自動的に初期化（テーブル作成）されます。
   - DuckDB（デフォルト: data/kabusys.duckdb）は研究処理などで使用します。必要に応じてデータをロードしてください。

---

## 主な環境変数（主要なもの）

- 必須（実行前に設定が必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード

- 動作モード
  - KABUSYS_ENV (default: development)
    - development, paper_trading, live

- データベース / パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用, default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)

- ログ・監視
  - LOG_LEVEL (DEBUG/INFO/...)
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

- ペーパートレード動作
  - PAPER_FILL_MODE (instant|partial|never|reject; default: instant)

- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector が使用（未設定時は呼び出し側で例外）

- 開発用
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

詳細は `src/kabusys/config.py` の docstring/コメントを参照してください。

---

## 使い方（代表コマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動（デフォルトは現在の KABUSYS_ENV に従う）
  ```
  python -m kabusys.run_execution
  ```
  挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - 実行中は PID を data/execution.pid に書き込み
  - 外部から停止するには data/stop_requested.flag（run_execution と run_monitoring はこのファイルを監視）や data/kill.flag を利用

- Monitoring（SystemMonitor の簡易ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60）。

- Paper Trading 検証レポート出力
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または環境変数 `PAPER_TRADING_SQLITE_PATH` で DB を指定できます。

- LLM ベース処理（プログラムから呼び出す例）
  - ニュース NLP:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="sk-...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")

注: LLM API 呼び出しは OPENAI_API_KEY を使用するか、api_key 引数で渡してください。呼び出し時のエラーはフェイルセーフ設計（例: API 失敗時は中立値で続行）されていますが、キーが未設定の場合は ValueError を送出します。

---

## Kill Switch / 停止フラグについて

- data/kill.flag: KillSwitch が書き込むフラグファイル。ExecutionEngine 停止のシグナルとして使用。
- data/stop_requested.flag: run_execution / run_monitoring などが監視する「外部からの停止要求」フラグ。存在するとループを抜けて終了します。
- 実行時に起動フラグ類が既に存在する場合の挙動について:
  - run_execution は起動前に stop flag の存在を確認し、存在すれば起動しません。
  - Settings.kill_flag_clear_on_start が "1" の場合、起動時に kill.flag を自動でクリアする設定があります（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定の読み込みと検証ロジック
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
    - __init__.py
  - research/
    - factor_research.py — momentum / volatility / value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
    - __init__.py
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（複数方式）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py
  - execution/ (発注関連: ExecutionEngine, OrderRepository, BrokerFactory, 等)
    - (各モジュールファイル。今回のコード抜粋では参照されるが詳細は省略)
  - monitoring/
    - monitoring_db.py — SQLite への永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch の判定と flag 書き込み
    - monitoring_engine.py — 各 Monitor をまとめてポーリング
    - alert_manager.py — （アラート送信ロジック、抜粋中は未表示）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity セットユーティリティ
    - __init__.py

その他: config/*.yaml（各種設定テンプレート）、data/（デフォルトの DB ファイル・PID/flag ファイルを置く想定）

---

## 注意事項・ベストプラクティス

- .env は絶対にリポジトリにコミットしないでください（APIキー・パスワードを含みます）。
- KABUSYS_ENV を `live` にした場合は、本番発注が行われます。十分に設定を確認したうえで実行してください。
- ペーパートレードは紙上の動作検証用途です。本番口座とは DB が分離されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI API 呼び出しを行う処理はレート制限やネットワーク障害に対してリトライやフェイルセーフが実装されていますが、APIキー漏洩に注意してください。
- process priority / cpu affinity の設定は psutil の権限によって失敗する場合があります（警告でスキップされます）。

---

もし README に追加してほしいセクション（例: API の詳細、設定ファイルテンプレート、ユニットテストの実行方法、具体的な運用手順など）があれば教えてください。必要に応じて追記します。