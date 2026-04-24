# KabuSys

日本株向けの自動売買システム（プロトタイプ）

このリポジトリは、シグナル生成→ポートフォリオ構築→発注（ExecutionEngine）→監視（Monitoring）→分析（DuckDB を使ったリサーチ）までのワークフローを含む自動売買システムの主要コンポーネントを提供します。AI を用いたニュースセンチメント（OpenAI）やレジーム判定機能も含まれます。

注意: 本リポジトリは学習/社内利用を想定した実装例です。実際の運用・本番発注を行う場合は十分な検証とガード（テスト、監査、運用ルール）を行ってください。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動・ツール）
- 環境変数（主要なもの）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株（kabuステーション API / J-Quants データ等）を対象とした自動売買フレームワークです。  
主な役割は以下です。

- ExecutionEngine: 発注ロジック、注文管理、リスク制御
- Monitoring: システム稼働監視、オーダーログ監視、Kill Switch（異常時に Execution を停止）
- Portfolio モジュール: 候補選定、重み計算、ポジションサイズ決定、セクター制約・レジーム調整
- Research: DuckDB を利用したファクター計算・特徴量分析
- AI モジュール: ニュースの NLP スコアリング、マクロを組み合わせたレジーム判定
- ツール: .env ウィザード、設定検証、ペーパートレード検証レポート生成

---

## 主な機能（機能一覧）

- 環境設定ウィザード: `kabusys.config_setup` により .env を対話的に生成
- 設定検証: `kabusys.validate_config` で必須環境変数や設定ファイルの初期チェック
- 実行エンジン起動スクリプト: `kabusys.run_execution`
  - KABUSYS_ENV により paper_trading 用の MockBroker を使用
  - paper_trading 時は専用 DB (`data/paper_trading.db`) に出力し本番 DB と分離
- 監視ループ起動スクリプト: `kabusys.run_monitoring`
  - システム状態・注文状態・リスクをポーリングしログに保存
  - 環境変数でポーリング間隔の上書き可能（MONITOR_POLL_INTERVAL）
- Kill Switch（フラグファイル）: drawdown やポジション上限などで `data/kill.flag` を書き込み Execution を停止
- Portfolio コンポーネント（純粋関数）:
  - 候補選定、等重／スコア重み、サイズ計算（ロット丸め・コストバッファ・aggregate cap）
  - セクター上限除外、レジーム乗数
- Research（DuckDB）:
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン、IC 計算、統計サマリー
- AI（OpenAI）:
  - ニュースをまとめてセンチメント評価（gpt-4o-mini を想定）
  - マクロニュース + ETF MA200 乖離で市場レジーム判定
- ツール:
  - `kabusys.tools.paper_verification_report`：ペーパートレードの検証レポート生成

---

## セットアップ手順

前提:
- Python 3.10 以上（コード内で | 型注釈を使用しているため）
- 仮想環境の利用を推奨

1. リポジトリをクローンして移動
   - git clone ... && cd <repo>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主要パッケージ（最低限）:
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML （config YAML の検証を行う場合／任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※requirements.txt がある場合はそれを使ってください（本コードベースでは同梱されていません）。

4. .env ファイルを作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - あるいは .env.example（存在する場合）を参考に手動作成してください。
   - 重要: .env は絶対にバージョン管理にコミットしないでください。

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトでは `data/`、`logs/` を使用します。自動作成されることが多いですが、権限等で失敗する場合は手動で作成してください。

---

## 使い方

主要な実行モードとツールの使い方を示します。

1. ExecutionEngine を起動（発注エンジン）
   - 開発 / ペーパートレード / 本番は KABUSYS_ENV によって切り替え
   - 起動:
     - python -m kabusys.run_execution
   - 動作:
     - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し DB は data/paper_trading.db に記録します（本番 DB と分離）。

2. Monitoring を起動（監視ループ）
   - python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で上書き:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使って監視テーブルに記録します（環境に関わらず）。

3. ペーパートレード検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスはオプション --db または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

4. .env の作成・更新（対話式）
   - python -m kabusys.config_setup

5. 設定検証
   - python -m kabusys.validate_config [--strict]

6. AI 機能（プログラムから呼び出す例）
   - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を DuckDB 接続と target_date、OpenAI API キーで呼び出します。
   - OpenAI API キーは環境変数 OPENAI_API_KEY で設定するか、関数引数で渡します。

停止・Kill Switch:
- ExecutionEngine / Monitoring はプロジェクトルート下の data/stop_requested.flag や data/kill.flag（KillSwitch 用）等のフラグファイルを監視・操作します。運用時の停止 / 強制停止に利用できます。

ログ:
- ログは `logs/<app_name>.log` に日次ローテーションで出力されます（デフォルト 30 日保持）。
- setup_logging を各スクリプトで最初に呼んで統一されたログ出力が行われます。

---

## 主要な環境変数（抜粋 / デフォルト）

以下はコードで参照される主要な環境変数の一覧（デフォルト値があるものは併記）。

- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用）
- KABU_API_PASSWORD: 必須（kabuステーション API 用）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject） デフォルト: instant
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） デフォルト: INFO
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必要）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等は Settings により参照可能

詳しくは `kabusys.config.Settings` と `kabusys.config_setup` を参照してください。

---

## ディレクトリ構成（主要ファイルの説明）

以下は `src/kabusys` 配下の主要モジュールと簡単な説明です。

- __init__.py
  - パッケージ初期化。バージョン情報を含む。

- config.py
  - 環境変数読み込み・設定クラス（Settings）。.env 自動ロード機能あり。

- config_setup.py
  - 対話式 .env 作成ウィザード。

- validate_config.py
  - 起動前の設定検証 CLI。

- run_execution.py
  - ExecutionEngine を起動するエントリポイント。paper_trading モードでは MockBroker を使用。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動するエントリポイント。

- monitoring/
  - monitoring_db.py: SQLite へのテーブル作成 & 永続化 API（MonitoringDB クラス）
  - system_monitor.py: システム状態・データ鮮度監視
  - trade_monitor.py: （注文ログ監視）※ファイルの詳細実装あり
  - risk_monitor.py: ドローダウン・ポジション数監視
  - kill_switch.py: フラグファイルによる停止シグナル生成
  - monitoring_engine.py: 各モニタを束ねる

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
  - BrokerClientFactory を用いて実際の/Mock ブローカークライアントを生成

- portfolio/
  - portfolio_builder.py: 候補選定、等重／スコア重み
  - position_sizing.py: 株数計算（ロット丸め・aggregate cap）
  - risk_adjustment.py: セクター上限、レジーム乗数

- research/
  - factor_research.py: momentum / volatility / value 等ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリー

- ai/
  - news_nlp.py: ニュース記事の LLM によるセンチメント評価（ai_scores へ書き込み）
  - regime_detector.py: ETF MA200 とマクロセンチメントからレジーム判定

- utils/
  - logging_setup.py: ログ設定ユーティリティ（コンソール + 日次ローテーションファイル）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- tools/
  - paper_verification_report.py: ペーパートレード結果の検証レポート生成ツール

---

## 運用上の注意点 / トラブルシューティング

- .env の扱い:
  - .env は機密情報（APIキー・パスワード）を含むため git 等の VCS にコミットしないでください。

- 本番環境の設定:
  - KABUSYS_ENV=live に設定すると本番動作になります。LINE 通知の設定や Kill Switch の挙動など、本番は十分に確認してください。
  - validate_config の追加チェックを活用してください（--strict オプション推奨）。

- AI 機能:
  - OpenAI SDK の挙動や rate limit に依存します。API キーの管理、コスト、呼出し頻度には注意してください。
  - OpenAI 関連処理ではリトライやフェイルセーフが組み込まれていますが、API に依存する処理は運用設計が重要です。

- 依存パッケージが足りない場合:
  - PyYAML が無い場合、validate_config の YAML 検証はスキップされます（警告メッセージが出ます）。
  - openai がないと AI 機能は使えません（ImportError / 呼び出しエラー）。

- 権限:
  - ログディレクトリや data ディレクトリの作成権限が無いとログファイル・DB の作成が失敗することがあります。最初に適切な権限でディレクトリを作ってください。

---

README は以上です。詳細な API や追加の実装（order_manager、execution_engine、trade_monitor 等）の使い方は各モジュールの docstring を参照してください。必要であれば起動スクリプトや主要コンポーネントのより詳しい運用ドキュメントを別途作成します。