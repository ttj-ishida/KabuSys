# KabuSys

日本株自動売買システムの参照実装（ライブラリ + 起動スクリプト群）。

このリポジトリは、戦略研究（ファクター計算・特徴量探索）、ポートフォリオ構築、発注実行エンジン、監視・アラート、AI（ニュースセンチメント）連携などを含むモジュール群で構成されています。

## 概要
- 目的: 日本株向けの自動売買システムを構成する共通機能を提供する（研究、ポートフォリオ構築、実行、監視、AI スコアリングなど）。
- 設計方針:
  - モジュールは可能な限り純粋関数（副作用を限定）で実装。
  - DB は SQLite（監視/発注履歴など）と DuckDB（分析・研究用）を併用。
  - 本番/ペーパー（ペーパートレード）で DB を分離する仕組みを備える。
  - OpenAI（gpt-4o-mini）を利用したニュース NLP / レジーム検出をサポート（APIキー必須、失敗時はフェイルセーフ動作）。

## 主な機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（実注文 or MockBroker によるペーパー発注）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動（システム状態・プロセス・データ鮮度監視）。
- 設定管理
  - config.py: 環境変数と .env 自動読み込み / Settings クラス。
  - config_setup.py: 対話式 .env 作成ウィザード。
  - validate_config.py: 起動前設定検証ツール（必須環境変数や config/*.yaml の存在チェック）。
- 研究・分析
  - research.factor_research: モメンタム／ボラティリティ／バリュー系ファクター計算（DuckDB ベース）。
  - research.feature_exploration: 将来リターン・IC 等の統計解析ユーティリティ。
- ポートフォリオ構築
  - portfolio.portfolio_builder: シグナル選抜・重み計算（等配分 / スコア加重）。
  - portfolio.position_sizing: 株数算出（リスクベース・上限・単元丸め・スケーリング）。
  - portfolio.risk_adjustment: セクター制限・レジーム乗数。
- 監視
  - monitoring.monitoring_db: 監視用 SQLite テーブル定義と読み書きユーティリティ。
  - monitoring.system_monitor / trade_monitor / risk_monitor / monitoring_engine: 各種チェックとアラート連携。
  - monitoring.kill_switch: ドローダウン等で ExecutionEngine 停止用の kill.flag 管理。
- AI 関連
  - ai.news_nlp: raw_news を集約して OpenAI に問い合わせ、銘柄ごとのセンチメント（ai_scores）を更新。
  - ai.regime_detector: マクロ記事 + ETF MA を使った市場レジーム判定。
- ユーティリティ
  - utils.logging_setup: 統一的なログ設定（stdout + 日次ローテーション）。
  - utils.process_priority: プロセス優先度 / CPU affinity の設定ユーティリティ。
- ツール
  - tools.paper_verification_report: ペーパートレード DB を解析して検証レポート（PASS/FAIL）を出力。

## 動作環境（推奨）
- Python >= 3.10（typing の `X | Y` を利用）
- 必要な外部パッケージ（最低限）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config の YAML 検証を有効にする場合）
- SQLite は標準ライブラリに含まれます。

インストール例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がある場合はそれを使用してください）

## セットアップ手順（初回）
1. リポジトリをクローンして作業ディレクトリに入る。
2. Python 仮想環境を作成・有効化し、必要パッケージをインストール。
3. 対話式で .env を作る（推奨）
   - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - ペーパー運用や本番運用は KABUSYS_ENV により振る舞いが変わります（development / paper_trading / live）。
4. 設定チェック（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱う。
5. データディレクトリ初期化
   - デフォルトでは data/ 以下に DB やフラグファイルを置きます。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を調整してください。

## 使い方（主なコマンド例）
- 実行エンジン（ExecutionEngine）起動
  - 本番（KABUSYS_ENV=live）やペーパー（KABUSYS_ENV=paper_trading）に応じて .env を設定してください。
  - 起動:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - プロセス PID ファイルは data/execution.pid（Settings.pid_file_path）に書き込まれます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV にかかわらず同じ monitoring DB を見る実装）。
  - 停止: data/stop_requested.flag を作成するとループが止まります。

- 設定ウィザード / 検証
  - 対話式 .env 作成: python -m kabusys.config_setup
  - 設定チェック: python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能。デフォルト: data/paper_trading.db

- AI モジュール（ライブラリ呼び出し）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  ※ AI 機能を使う場合は OPENAI_API_KEY を .env に設定するか、関数呼び出し時に api_key 引数を渡してください。

## 主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）、デフォルト development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）

## 停止・フラグ類
- data/stop_requested.flag: run_execution / run_monitoring の外部停止フラグ（存在すると起動抑止またはループ終了）
- data/kill.flag: KillSwitch により ExecutionEngine を強制停止するために書かれるフラグ（monitoring が書き込む）
- PID ファイル: data/execution.pid（ExecutionEngine が起動時に作成）

## ディレクトリ構成（主なファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境設定 / Settings
    - config_setup.py               — .env 対話ウィザード
    - validate_config.py            — 設定検証 CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py — ペーパー検証レポート
    - portfolio/
      - portfolio_builder.py        — 候補選定・重み付け
      - position_sizing.py          — 株数決定・スケール調整
      - risk_adjustment.py          — セクター上限 / レジーム乗数
      - __init__.py
    - research/
      - factor_research.py          — Momentum/Volatility/Value 等の計算
      - feature_exploration.py      — 将来リターン / IC / 統計要約
      - __init__.py
    - ai/
      - news_nlp.py                 — ニュース NLP（OpenAI 連携）
      - regime_detector.py          — 市場レジーム判定（MA + マクロ NLP）
      - __init__.py
    - monitoring/
      - monitoring_db.py            — SQLite テーブル定義と CRUD ユーティリティ
      - system_monitor.py           — システム・データ鮮度監視
      - trade_monitor.py            — 発注ログ監視（stale/anomaly 検出）※（ファイル存在）
      - risk_monitor.py             — ドローダウン / ポジション上限監視
      - kill_switch.py              — Kill Switch 制御
      - monitoring_engine.py        — 各 Monitor を束ねる
    - utils/
      - logging_setup.py            — ログ初期化ユーティリティ
      - process_priority.py         — プロセス優先度 / affinity 設定
      - __init__.py
    - data/ (実行時に利用するデータ/ログ/DB を置くのが想定)
- config/
  - system_config.yaml, data_config.yaml, ...（テンプレート/生成スクリプトを利用）

（上記は主要ファイル抜粋です。詳細は各モジュールの docstring を参照してください。）

## 開発上の注意点 / 運用メモ
- DB 分離:
  - paper_trading モードでは発注系の SQLite は paper_trading 専用 DB に書き込まれ、本番データとは分離されます。
  - 監視用 DB は run_monitoring から常に本番 sqlite_path を使用する実装になっています（意図的）。
- ロギング:
  - utils.logging_setup.setup_logging を各起動スクリプトの最初に呼ぶことで stdout と日次ローテーションファイル（logs/）に統一的にログ出力されます。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼んでいます。環境によって権限不足で警告が出ますが実行は継続します。
- AI 呼び出し:
  - OpenAI API が失敗した場合は個別にフェイルセーフ（0 フォールバックやスキップ）する設計です。ただし API キー漏洩やコストに注意してください。
- テスト:
  - AI 呼び出しや外部 API を含む箇所はテスト用にモック可能な実装になっています（_call_openai_api を patch など）。

## よくあるコマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパー検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に書かれていない詳細な実装や追加の CLI オプションについては各モジュールの docstring を参照してください。必要であれば README の補足（例: systemd ユニット例、Docker 化手順、CI 設定）も作成します。どの情報を追加希望か教えてください。