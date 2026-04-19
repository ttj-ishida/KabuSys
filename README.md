# KabuSys

日本株向けの自動売買 / 研究プラットフォーム (KabuSys)。  
シグナル生成・ポートフォリオ構築・発注エンジン・監視・リスク管理・研究用ツール群を含むモジュール構成のプロジェクトです。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- 株価データを用いたファクター計算・特徴量探索（research）
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制約など）
- 発注・実行エンジン（ExecutionEngine）と注文管理（paper/live 両対応）
- 実行状況やシステム状態の監視（Monitoring）と Kill Switch による自動停止
- Paper Trading の検証レポート生成ツール
- ニュースを使った LLM ベースのセンチメント（AI モジュール）
- ユーティリティ（ログ設定・プロセス優先度設定・設定ウィザード等）

設計方針として、DB（DuckDB / SQLite）を用いたデータ保管、OpenAI を利用した NLP、psutil によるシステム情報取得などを組み合わせ、開発／ペーパートレード／本番（live）を環境変数で切り替え可能です。

---

## 主な機能一覧

- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等重 / スコア重み / リスクベース配分
  - セクター上限フィルタ
  - レジームに応じた乗数調整
  - 株数の単元丸め・集約キャップ処理

- 研究（research）
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily, raw_financials を参照）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー

- AI（ニュース NLP / レジーム判定）
  - raw_news から銘柄ごとに LLM（gpt-4o-mini）でセンチメントを算出して ai_scores に保存
  - ETF（1321）MA200乖離 + マクロニュースセンチメントを組み合わせて market_regime を算出・保存
  - OpenAI の API 呼び出しはリトライや応答検証を行い堅牢化

- 実行・注文管理（execution）
  - Paper Trading（モックブローカー、専用 SQLite）と Live（実ブローカー）を分離
  - RiskManager / OrderManager / Reconciler 等の構成要素

- 監視（monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・プロセス生存確認
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン、ポジション上限を監視
  - KillSwitch: 指定条件で data/kill.flag を作成して ExecutionEngine を停止
  - MonitoringEngine: 監視コンポーネントを束ねて定期実行

- 運用ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - 統一されたログ設定ユーティリティ（utils/logging_setup.py）

---

## セットアップ手順

前提: Python 3.9+ を想定（プロジェクト固有の要件は環境に応じて調整してください）。

1. リポジトリをクローン / 展開
   - この README はパッケージソースが `src/` 以下に置かれている構成を想定しています。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 主要な依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（任意: validate_config の YAML 検証等）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを使用してください）

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 生成後、`python -m kabusys.validate_config` で検証を行ってください。

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは `data/` に SQLite / DuckDB が作られます:
     - data/kabusys.duckdb
     - data/monitoring.db
     - data/paper_trading.db（paper_trading 環境で使用）

6. ログディレクトリ
   - デフォルトは `logs/`。`LOG_DIR` 環境変数で変更可能。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（INFO 等）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- PAPER_FILL_MODE: PaperTrading の約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

注意: パッケージは起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 使い方（主なコマンド）

- 環境作成ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジンを起動（ExecutionEngine）:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper用DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中に data/stop_requested.flag を作成するとエンジンに停止シグナルを送ります。

- 監視ループを起動（Monitoring）:
  - python -m kabusys.run_monitoring
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らない）。
    - 停止制御用フラグファイル: src から見てプロジェクトルート/data/stop_requested.flag を監視。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB を使う:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラムから呼び出す関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と対象日を渡し、ニュースセンチメントを計算して ai_scores テーブルへ書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルにレジーム情報を書き込む

- ログ設定
  - 起動スクリプトは共通の setup_logging(app_name="...") を呼んでログをセットアップします（logs/<app_name>.log、日次ローテーション）。

---

## 運用フラグ / ファイル

- data/stop_requested.flag
  - run_execution / run_monitoring の起動ループがチェックする「停止依頼」フラグ（存在すればループを抜ける）。

- data/kill.flag
  - KillSwitch が条件を満たしたときに作成されるファイル。ExecutionEngine の起動中にこれが存在すると停止対象となる。

- data/execution.pid
  - ExecutionEngine が PID を書き込むために使用するファイル（pid_file）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                  — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring ポーリング起動スクリプト

subpackages:
- ai/
  - __init__.py
  - news_nlp.py              — LLM を使ったニュースセンチメント処理
  - regime_detector.py       — マーケットレジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py         — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py        — CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - trade_monitor.py         — （滞留注文・約定異常監視: 実装ファイルあり）
  - risk_monitor.py          — ドローダウン・ポジション上限監視
  - kill_switch.py           — Kill Switch 実装
  - monitoring_engine.py     — 複数モニタの統合実行
  - alert_manager.py         — （アラート送信を管理するコンポーネント）
- execution/
  - execution_engine.py      — ExecutionEngine（発注実行ループ）
  - order_manager.py         — 注文管理
  - order_repository.py      — 注文の永続化（SQLite）
  - reconciler.py            — ブローカーとレポの差分を整合
  - broker_factory.py        — ブローカークライアントの生成（Mock/Live 切替）
  - risk_manager.py          — リスク制御ロジック
- portfolio/
  - portfolio_builder.py     — 候補選定 / 重み計算
  - position_sizing.py       — 株数決定（単元丸め・aggregate cap）
  - risk_adjustment.py       — セクター制約・レジーム乗数
- research/
  - factor_research.py       — Momentum/Value/Volatility ファクター計算
  - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - __init__.py
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - logging_setup.py         — 共通ログ設定ユーティリティ
  - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - __init__.py

（その他、data/、config/、logs/ といった運用ディレクトリを想定）

---

## 開発メモ / 注意事項

- DB 周り
  - DuckDB は分析用（prices_daily, raw_financials, raw_news など）。
  - 監視ログ / 発注ログ等は SQLite（monitoring.db / paper_trading.db）を使用。
  - Paper Trading は本番 DB と分離される（settings.is_paper の分岐）。

- LLM（OpenAI）利用
  - OPENAI_API_KEY の設定が必須（AI 機能を使う場合）。
  - API 呼び出しは JSON mode を用い、レスポンス検証・リトライロジックが入っています。
  - レート制限や 5xx などの一時エラーは指数バックオフで再試行される設計。

- ログ
  - すべての起動スクリプトは utils.logging_setup.setup_logging を呼び、標準出力と日次ローテートファイルに統一して出力します。

- 安全機構
  - Kill Switch / risk_monitor により、ドローダウンやポジション上限超過時に自動で停止できる仕組みがあります。
  - 本番環境（KABUSYS_ENV=live）では特に .env 設定の確認を強く推奨します。

---

## よく使うコマンド例

- ウィザードで .env を作る
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config

- 監視を起動（デフォルト 60 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（paper_trading 環境の例）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README はここまで。追加で以下の情報があれば README をさらに充実させられます。

- requirements.txt / poetry / pyproject.toml の依存情報
- 実行例（ログ抜粋、DB スキーマのサンプル）
- CI / デプロイ手順、コンテナ化（Dockerfile）
- テスト実行方法（pytest 等）

必要であれば、上記のうち任意の項目を追加して README を拡張します。