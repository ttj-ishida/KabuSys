# KabuSys

日本株向け自動売買システムのコードベース（ドキュメント版 README）。  
この README ではプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・モニタリングを目的とした Python ベースのシステムです。  
主な設計方針は以下の通りです。

- 実運用（live）とペーパートレード（paper_trading）を明確に分離する（ペーパートレードは専用 SQLite DB を使用）。
- DuckDB をデータ分析（price / financials / news 等）に使用。
- SQLite を運用ログ（監視・注文履歴・ダッシュボード）に使用。
- ロギング、プロセス優先度設定、Kill Switch 等の運用機能を備える。
- LLM（OpenAI）を使ったニュース NLP や市場レジーム判定機能を提供（オプション）。

パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

---

## 主な機能一覧

- Execution（発注系）
  - 実際のブローカークライアントまたは MockBrokerClient を切り替えて発注を行う（KABUSYS_ENV に依存）。
  - RiskManager / OrderManager / Reconciler / ExecutionEngine により発注・管理を行う。

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェックとログ保存（SQLite）。
  - Kill Switch（条件による停止フラグ作成）と AlertManager への通知連携。
  - モニタリングループ起動スクリプト（`run_monitoring.py`）。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。

- Portfolio construction（銘柄選定・配分）
  - 候補選定（スコア順）と重み計算（等金額／スコア加重）。
  - セクターキャップ適用、レジーム乗数（bull/neutral/bear）適用。
  - ポジションサイズ計算（単元株丸め、aggregate cap、コストバッファ対応）。

- Research（研究・分析）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等） — DuckDB での SQL / Python 処理。
  - 特徴量探索・IC 計算・将来リターン計算等。

- AI（OpenAI 統合）
  - ニュース文章を LLM で解析し、銘柄別センチメント（ai_scores）を DuckDB に保存（`ai.news_nlp`）。
  - マクロニュース＋ETF MA200 乖離を組み合わせた市場レジーム判定（`ai.regime_detector`）。
  - OpenAI API の失敗時はフォールバックしフェイルセーフ動作を保つ。

- ユーティリティ
  - `.env` を対話式に作成するウィザード（`config_setup.py`）。
  - 設定検証 CLI（`validate_config.py`）。
  - Paper Trading 検証レポート生成スクリプト（`tools/paper_verification_report.py`）。
  - ログ設定ユーティリティ（stdout + 日次ローテートファイル）。
  - プロセス優先度 / CPU affinity 設定（psutil ベース）。

---

## セットアップ手順

想定: Python 3.10+（型注釈や Union 型の記法等に依存）を使用。必要に応じて仮想環境の作成を推奨します。

1. リポジトリをクローン / ソースを取得
   - 例: git clone ...

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - 最低限（実行環境により追加が必要）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（`validate_config` で YAML 検証をしたい場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. データ/ログディレクトリを作成（任意）
   - デフォルトのパス:
     - data/: SQLite 等の DB 場所（例: data/monitoring.db, data/paper_trading.db）
     - logs/: ログファイル保存先
   - 例:
     - mkdir -p data logs

5. 環境変数の設定（.env 推奨）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは `.env` を手動で作成（`.env.example` を参照）。
   - 重要な環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live） — デフォルト: development
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能使用時）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番でアラート通知を行う場合）

   - 自動読み込みについて:
     - パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動でロードします。
     - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱いたい場合:
     - python -m kabusys.validate_config --strict

---

## 使い方（主要スクリプト）

以下はプロセス起動の代表的なコマンド例です。環境変数や .env を先に準備してください。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - （--strict で警告を FAIL 扱いにできます）

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db`（または PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と分離）。
    - プロセス優先度を起動時に「high」に設定します。
    - 停止は `data/stop_requested.flag` を作成することで行えます（または Kill Switch により `data/kill.flag` が作られる場合もあります）。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で変更できます（例: MONITOR_POLL_INTERVAL=30）。
    - Monitoring は環境にかかわらず本番用の sqlite_path（Settings.sqlite_path）を参照します（運用ログは単一 DB に保存）。

- Paper Trading レポート生成（検証ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

- AI によるニューススコア / レジーム判定
  - ニューススコア: kabusys.ai.news_nlp.score_news（ライブラリ関数）
  - レジーム判定: kabusys.ai.regime_detector.score_regime（ライブラリ関数）
  - いずれも `OPENAI_API_KEY` が必要（引数で API キーを渡すことも可能）。

停止フラグ / Kill Switch（運用）
- 実行用プロセスの停止フラグ:
  - data/stop_requested.flag — 実行スクリプトがこれを検知して終了する
- Kill Switch:
  - 条件（ドローダウンやポジション上限）発生時に monitoring が data/kill.flag を作成し、ExecutionEngine の起動を阻止または停止できます。
  - Settings.kill_flag_clear_on_start が `1` の場合、起動時に kill.flag を自動でクリアします（本番では `0` 推奨）。

ログ
- ログは stdout（StreamHandler）とファイル（logs/<app_name>.log）に出力されます。ログディレクトリは環境変数 `LOG_DIR` またはデフォルト `logs/`。
- ログローテーション: 日次、30日保持。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API 用）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — AI 機能（news_nlp / regime_detector）で必要
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1、デフォルト 0）

（完全な一覧は `kabusys/config.py` と `config_setup.py` を参照してください）

---

## ディレクトリ構成（主要ファイル）

以下はプロジェクトの主なファイル・パッケージ構造（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (参照されるがここに無い場合あり)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (参照されるがここに無い場合あり)
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - portfolio/, execution/, data/, research/ ...（その他サブモジュール）
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  - （これらは生成スクリプトやサンプルが提供される想定）
- data/
  - monitoring.db (SQLite、デフォルト)
  - paper_trading.db (ペーパートレード用 DB、デフォルト)
  - stop_requested.flag / kill.flag / execution.pid などの運用フラグ・PID ファイル
- logs/
  - execution.log
  - monitoring.log
  - ...（日次ローテーションで管理）

※ 上記はソースからの抜粋であり、実際のコードベースで追加ファイルがある可能性があります。

---

## 運用上の注意点

- .env は機密情報（API トークン等）を含むため、決して Git 等にコミットしないでください。
- 本番（KABUSYS_ENV=live）では設定を慎重に確認してください（validate_config の live 用ガードが警告を出します）。
- OpenAI の呼び出しはコストとレイテンシが発生します。AI 機能はオプションであり、API キーの管理に注意してください。
- Monitoring は設定により本番 DB に書き込みます。Monitoring は常に Settings.sqlite_path を参照するため、本番 DB を使いたくない場合はパスの切り替え設定を行ってください。
- プロセス優先度設定（High）や CPU affinity の変更は OS 権限に依存し、失敗する場合は警告ログにとどまり継続します。

---

## 参考コマンドまとめ

- 仮想環境 & 依存インストール（例）
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt
  - （requirements.txt が無ければ: pip install duckdb psutil openai pyyaml）

- .env 作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動（フォアグラウンド）
  - python -m kabusys.run_execution

- Monitoring 起動（フォアグラウンド）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

もし README の追加項目（例えば CI / デプロイ手順、詳細な設定項目一覧、API ドキュメント、開発ガイド）を追記したい場合は、必要な情報やフォーマット（例: Markdown セクション分け）を教えてください。