# KabuSys

日本株自動売買システムのコアライブラリ群および起動用スクリプト群。  
このリポジトリは戦略の研究・ファクター計算、ポートフォリオ構築、発注実行（本番／ペーパートレード）、監視・アラート、AI を使ったニューススコアリングなどを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントをモジュール化した Python パッケージです。主な機能は以下の通りです。

- 戦略研究（ファクター計算、特徴量解析、IC 計算）
- ポートフォリオ選定・配分計算（等金額、スコア加重、リスクベース）
- ポジションサイズ計算（単元株丸め、コストバッファ、上限管理）
- ExecutionEngine（発注実行） — 本番 / ペーパートレード対応（分離された DB を使用）
- Monitoring（システム状態、注文ログ、リスク監視、Kill Switch）
- AI モジュール（ニュースの NLP によるセンチメント、マーケットレジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、環境読み込みウィザード / 検証 CLI）
- ツール（ペーパートレード検証レポート生成 等）

設計方針として「本番口座に無関係な部分は DuckDB / SQLite のみを参照し、外部 API への不要な呼び出しをしない」「起動時の環境設定の安全性（KABUSYS_ENV による振る舞い差分）」「フェイルセーフ（API 失敗時に例外を投げず安全に継続）」などが採られています。

---

## 主な機能一覧

- config 管理
  - .env の自動読み込み / 対話式作成（config_setup）
  - 起動前の設定検証 CLI（validate_config）
- 実行 / 監視
  - run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV に応じてペーパートレード分離）
  - run_monitoring.py: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定）
  - Kill Switch（data/kill.flag）を使った安全停止
- 監視関連
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブル管理
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager（アラート送信は LINE 等を想定）
- ポートフォリオ構築
  - 銘柄選定、等重・スコア重み付け、セクター上限適用、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap）
- 研究（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC 計算、統計サマリ
- AI（openai）
  - news_nlp: raw_news をまとめて LLM に投げ、銘柄ごとのセンチメント（ai_scores）を作成
  - regime_detector: ETF（1321）とマクロニュースを組み合わせて market_regime を判定
- ツール
  - paper_verification_report: ペーパートレード DB を解析して Pass/Fail レポートを出力

---

## セットアップ手順

1. Python 環境
   - Python 3.10+ を推奨

2. 必要なパッケージ（主な依存）
   - duckdb
   - psutil
   - openai
   - PyYAML（config/*.yaml の検証を行いたい場合）
   - 上記は pip でインストールしてください。例:
     - pip install duckdb psutil openai pyyaml

   （本リポジトリに requirements.txt があれば `pip install -r requirements.txt` を使用）

3. リポジトリルートに移動して .env を作成
   - 対話式ウィザード（推奨）:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（例は .env.example を参照）

4. 環境変数（主なもの）
   - 必須
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意 / 推奨
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
       - paper_trading: ExecutionEngine は MockBrokerClient を使用し、paper_trading 専用 SQLite を使用
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）を使う場合に必須
     - PAPER_FILL_MODE: ペーパートレードの Fill モード（instant / partial / never / reject、デフォルト: instant）
     - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
   - Kill スイッチ関連
     - KILL_FLAG_PATH（デフォルト: data/kill.flag）
     - KILL_FLAG_CLEAR_ON_START（0/1、デフォルト: 0）

5. データディレクトリ・ログディレクトリ作成
   - デフォルトでは `data/`、`logs/` が利用されます。起動時に自動作成されますが権限等に注意してください。

---

## 使い方

基本的にはモジュールとして起動します。以下は代表的なコマンド例です。

- .env の対話式作成
  - python -m kabusys.config_setup

- 設定の検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳格モード（警告も FAIL とする）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine の起動
  - 本番/開発モードを環境変数で切替:
    - KABUSYS_ENV=development python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
      - paper_trading の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録します。
  - 起動時にプロセス優先度を high にセットします。
  - 実行中に `data/stop_requested.flag`（プロジェクトルート配下）を作成すると安全に停止します。
  - Execution 用の PID ファイルは `data/execution.pid`（デフォルト）に書き出されます。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番の `SQLITE_PATH` を使用します（監視 DB は常に監視対象の本番 DB を参照する設計）。
  - `data/stop_requested.flag` を置くとループを終了します。

- Kill Switch（外部から Engine を止める）
  - `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch を経由して評価・書き込みされます）。
  - KillSwitch は一度書かれた flag を上書きしない（冪等）ため、手動で削除するか、設定 KILL_FLAG_CLEAR_ON_START=1 を設定して起動時に自動クリアすることができます（本番では危険なので注意）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` オプションで DB パスを直接指定可能（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）の設定が必要です。
  - ニューススコアリングを呼ぶ API はパッケージ関数を通じて利用できます（例: kabusys.ai.score_news）。
  - レスポンスは ai_scores / market_regime テーブルへ冪等的に書き込まれます。

---

## 知っておくべき挙動・デフォルト値

- run_monitoring は監視用 SQLite（Settings.sqlite_path）を環境にかかわらず使用します（監視は常に本番 DB にアクセス）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と完全に分離します。
- MONITOR_POLL_INTERVAL は整数秒の指定を期待します。不正な値（0以下や非整数）はデフォルト値 60 秒にフォールバックします。
- プロセス優先度は起動直後に `high` に設定されます（set_process_priority）。
- ログは stdout と日次ローテーションファイル（logs/<app_name>.log）に出力されます。ログ保存に失敗した場合はコンソール出力のみになります。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、.env 自動読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
  - research/
    - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  — 将来リターン, IC, 統計サマリ
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 株数・配分計算（lot 丸め、aggregate cap）
    - risk_adjustment.py      — セクター上限 / レジーム乗数
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ初期化・永続化 API
    - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
    - system_monitor.py       — システム状態／データ鮮度監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch（flag ファイルによる停止）
    - trade_monitor.py        — （注文ログ監視等、実装ファイル）
  - utils/
    - logging_setup.py       — 統一ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  - （これら YAML を用いる設計。generate_config.py 等でテンプレート生成を想定）

- data/
  - monitoring.db           — デフォルト監視 SQLite（生成・使用される）
  - paper_trading.db        — ペーパートレード用 DB（KABUSYS_ENV=paper_trading）
  - kill.flag, stop_requested.flag, execution.pid — 制御用フラグ / PID

- logs/
  - execution.log, monitoring.log, ... — 日次ローテートログ

---

## 開発・運用上の注意

- 本番環境（KABUSYS_ENV=live）では特に次を確認してください:
  - LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）が適切に設定されているか
  - KILL_FLAG_CLEAR_ON_START は通常 0（自動クリア禁止）を推奨
  - validate_config を実行して、欠落や危険な設定がないことを確認すること

- OpenAI を使う機能は API コストやレート制限を考慮してください。retry/backoff は実装されていますが、適切なキー管理と制限設定が必要です。

- データ鮮度チェックやポジション上限は監視コンポーネントで行いますが、最終的な安全性は運用ルール（Kill Switch、運用者の監視）で担保してください。

---

この README はコードベースのソースを元にした概要ドキュメントです。さらに詳しい実装説明や運用手順（デプロイ手順、コンテナ化、CI/CD、バックアップ方針など）は別途運用ドキュメントを整備してください。もし README に加えたい詳細（例: よくあるトラブルシュート、環境変数の具体的例、サンプル .env）や英語版が必要であれば教えてください。