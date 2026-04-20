# KabuSys

日本株自動売買システムのコアライブラリ（プロトタイプ）。  
本リポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI 補助機能（ニュース NLP / レジーム判定）などを含むモジュール群を提供します。

注意: 本 README はソースコード（src/kabusys 以下）を基に作成しています。実運用時は config/*.yaml や .env の値を十分に確認してください。

## 概要
KabuSys は以下の主要コンポーネントで構成されています。

- ExecutionEngine（発注エンジン）: ブローカークライアントを通じて注文管理・発注を行う。
- Monitoring（監視）: システム稼働状況・注文ログ・リスク監視を定期的に収集・アラート判定する。
- Portfolio（ポートフォリオ構築）: 候補選定、重み計算、ポジションサイズ計算、セクター制限など純粋関数群。
- Research（リサーチ）: ファクター計算、特徴量探索、IC 計算など分析用ユーティリティ（DuckDB を使用）。
- AI（OpenAI 連携）: ニュース NLP による銘柄センチメント、マクロニュースを使った市場レジーム判定。
- Tools: ペーパートレード検証レポート生成などのユーティリティスクリプト。
- Utils: ロギング設定、プロセス優先度設定などの共通ユーティリティ。

## 主な機能
- 実行環境を切り替える `KABUSYS_ENV`（development / paper_trading / live）
- Paper Trading 時は本番データベースと分離して `data/paper_trading.db` を使用
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）による定期チェックと Kill Switch（フラグファイルで ExecutionEngine を停止）
- DuckDB を用いた時系列データ処理（ファクター計算・リサーチ）
- OpenAI（gpt-4o-mini 等）を用いたニューススコアリング / レジーム判定（API 呼び出しはフェイルセーフ設計）
- ログはコンソール + 日次ローテートファイル（logs/<app_name>.log）
- 設定ウィザード、設定検証ツール、紙上検証レポート生成 CLI

## 必要条件（推奨）
- Python 3.10+
- pip, 仮想環境（venv / poetry / pipenv 等）
- 以下の主要 Python パッケージ（プロジェクトに requirements.txt がある場合はそれを使用してください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証に必要だが任意）
- SQLite（標準ライブラリで利用可）

例（最低限のインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存をインストール（上記参照）。

3. .env を作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは .env（デフォルト: プロジェクトルート/.env）を対話で生成します。機密情報（API トークン等）は表示されません。生成後は必ず `python -m kabusys.validate_config` で検証してください。

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告もエラーにしたい場合
   python -m kabusys.validate_config --strict
   ```

5. DB ファイル準備
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - Monitoring (SQLite): data/monitoring.db
     - Paper trading (SQLite): data/paper_trading.db
   - 必要に応じて環境変数でパスを上書き（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）

## 使い方（主なコマンド）

- ExecutionEngine を起動（発注エンジン）
  ```bash
  python -m kabusys.run_execution
  ```
  挙動:
  - 環境変数 `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して `data/paper_trading.db` に記録（本番 DB と完全分離）。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）
  - 停止は data/stop_requested.flag を作成すると検知して停止します。Kill Switch により data/kill.flag が書き込まれた場合は ExecutionEngine 停止。

- Monitoring（監視）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  挙動:
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書き可能（1 以上の整数）。
  - Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番 sqlite_path）を使用して監視テーブルを更新します。
  - 停止フラグ file: data/stop_requested.flag

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート生成（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- ライブラリ関数呼び出し（例）
  - AI スコアリング: `from kabusys.ai.news_nlp import score_news`
  - レジーム判定: `from kabusys.ai.regime_detector import score_regime`
  - リサーチ: `from kabusys.research import calc_momentum, calc_volatility, calc_value`

  これらは DuckDB 接続 (`duckdb.connect(...)`) と target_date を引数に取り、DB を参照して処理します。

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
- LOG_LEVEL（例: INFO）
- LOG_DIR（ログ出力ディレクトリ、デフォルト: logs/）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- MONITOR_POLL_INTERVAL（監視のポーリング秒数、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。1 = 自動クリア）

自動 .env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意: .env は機密情報を含むため、絶対に Git にコミットしないでください。

## 停止 / Kill Switch / フラグファイル
- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルの存在を監視し、検知時に正常終了します（運用上の停止フラグ）。
- data/kill.flag
  - KillSwitch が発動した際に書き込まれるファイル。ExecutionEngine はこのファイルにより停止指示を受けます。
- PID ファイル
  - 実行時に ExecutionEngine は pid ファイル（デフォルト data/execution.pid）を利用します。

KillSwitch の評価は RiskMonitor の結果に基づき行われます（ドローダウン・ポジション上限等）。

## ログ
- logging_setup モジュールにより、ルートロガーを統一的に設定します。
- 出力先:
  - コンソール（stdout）
  - 日次ローテーションファイル logs/<app_name>.log（デフォルト 30 日保持）
- ログレベルは引数 / 環境変数 `LOG_LEVEL` で設定可能。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主なファイル・ディレクトリと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py — .env 作成ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（CLI）
  - run_monitoring.py — Monitoring 起動スクリプト（CLI）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・単元丸め・投下キャップ
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Value / Volatility ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC /統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マクロ + MA を用いたレジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（監視テーブル）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文ログ監視）※実装詳細ファイルに依存
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch ロジック（フラグファイル作成）
    - monitoring_engine.py — モニター束ねてポーリングするエンジン
  - execution/
    - execution_engine.py — 実行エンジン本体（EngineConfig, run_session 等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注関連コンポーネント
  - data/（データ / DB ファイルはプロジェクトルート直下の data/ に置かれる想定）

（注）上記は主要ファイルの抜粋です。実際のリポジトリ内にはさらに補助モジュールが存在します。

## 開発上の注意点 / トラブルシューティング
- .env に未設定の必須値があると validate_config でエラーになります。J-Quants / kabu API のトークンは必須です。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必要。キーがない場合は例外を投げるか、モジュール側でフェイルセーフ（0.0 でフォールバック）を行う箇所があります。
- DuckDB の接続先ファイルを誤るとリサーチ機能が正常に動作しません。
- psutil を使ったプロセス優先度設定は OS に依存します（権限不足で設定に失敗することがありますが警告が出てスキップされます）。
- 監視（monitoring）はデフォルトで本番 sqlite を参照するので、paper_trading 環境で監視だけ行う場合は注意してください。

## 付記
- 本 README はコードコメント・関数ドキュメントを元に自動的にまとめたものであり、実運用の安全チェック（設定、ネットワーク、セキュリティ、資金管理）は必ず別途行ってください。
- さらなる詳細（API 実装、戦略ドキュメント、マイグレーション方針など）はプロジェクト内のドキュメント（PortfolioConstruction.md 等）を参照してください。

---

質問や追加で README に含めたい内容（例: docker イメージ化手順、CI 設定例、具体的な設定例ファイルなど）があれば教えてください。必要に応じて追記します。