# KabuSys

日本株向け自動売買システムのコードベース（ドキュメント版）。  
本 README はリポジトリ内の主要スクリプト／モジュール群に基づき、概要・機能・セットアップ・起動方法・ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド・よく使うスクリプト）
- 環境変数（代表的なもの）
- ディレクトリ構成（主要ファイル説明）
- 運用上の注意

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買／リサーチ基盤です。  
主な要素は以下の通りです。

- 実行エンジン（ExecutionEngine）：ブローカー接続・注文管理・リスク管理を行う。
- 監視システム（Monitoring）：プロセス・リスク・注文状態・データ鮮度を定期的にチェックし、ログ・アラート・Kill Switch を管理する。
- ポートフォリオ構築モジュール：銘柄選定、重み計算、サイズ算出、セクター制約などの純粋関数群。
- リサーチ（Research）：DuckDB を使ったファクター計算や特徴量解析。
- AI モジュール：OpenAI（GPT 系）を用いたニュースセンチメント評価や市場レジーム判定（オプション）。
- ツール群：ペーパートレード検証レポート等のユーティリティ。

設計方針として、実際の発注系（kabuステーション）は本番／ペーパートレードで分離し、DBやログの分離・フェイルセーフ／冪等性を重視しています。

---

## 主な機能一覧

- Execution
  - 本番・ペーパートレード（MockBroker）を切り替えて起動
  - 注文管理、リスク制御（利用率・最大ポジション・ドローダウン等）
  - PID / kill flag を使った外部制御

- Monitoring
  - CPU/メモリ/ディスク、実行プロセスの生存、データ鮮度を定期チェック
  - trade_logs / risk_logs / dashboard などの永続化（SQLite）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、ExecutionEngine を停止）
  - AlertManager 経由の通知（LINE 等の設定を想定）

- Portfolio
  - 候補選定（スコア順）
  - 等金額／スコア加重の重み計算
  - ポジションサイズ計算（リスクベース、単元株丸め、aggregate cap）

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ

- AI（任意）
  - ニュース文章を LLM（OpenAI）でセンチメント化して ai_scores に書き込み
  - マクロニュース＋ETF MA を用いた市場レジーム判定（bull/neutral/bear）
  - API 呼び出しはリトライ・バックオフ・レスポンス検証を実装

- ツール
  - .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows PowerShell
   ```

3. 必要パッケージをインストール  
   （プロジェクトに requirements.txt があればそれを使う。なければ主要依存を手動インストール）
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - 実行エンジンや AI 機能を使う場合は openai が必要です。
   - DuckDB はリサーチ・AI 前処理に使用します。

4. .env の準備  
   - 対話式ウィザードで .env を生成できます:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他は README 下段「環境変数」を参照してください。

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。

6. データディレクトリの初期化  
   - デフォルトでは `data/` 配下に DB 等が配置されます（自動作成されますが権限に注意）。
   - ログは `logs/` に日次ローテートで出力されます。

---

## 使い方（起動コマンド）

- ExecutionEngine を起動（デフォルト: KABUSYS_ENV により本番/ペーパー切替）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB（data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が既にある場合は起動せず終了します。

- Monitoring をデーモン的に起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依らず）。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も使用可。

- AI 関連（プログラム内呼び出し）
  - ニュースセンチメント:
    from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime

---

## 代表的な環境変数（デフォルト含む）

- 基本
  - KABUSYS_ENV: execution 環境（development / paper_trading / live） — デフォルト: development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...） — デフォルト: INFO

- API / 認証
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
  - OPENAI_API_KEY — AI 機能利用時に必要
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート用（任意）

- データベース / ファイルパス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視 DB のパス（data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（data/paper_trading.db）
  - PID_FILE_PATH — 実行エンジン PID ファイル（data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（data/kill.flag）

- 実行 / 動作調整
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading の約定動作（instant|partial|never|reject、デフォルト instant）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" で有効、デフォルト "0"）

注意: config_setup.py のウィザードや .env.example を参考に .env を作成してください。

---

## ディレクトリ構成（主要ファイルの説明）

リポジトリの主要部分（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数のロード／Settings クラス。自動で .env / .env.local を読み込む（無効化可能）。
  - config_setup.py
    - .env を対話的に生成・更新するウィザード。
  - validate_config.py
    - 起動前チェック用 CLI（必須環境変数や config/*.yaml の存在などを検査）。
  - run_execution.py
    - ExecutionEngine の起動スクリプト。ペーパー／本番 DB の切替、プロセス優先度設定、スレッド起動、停止フラグ監視。
  - run_monitoring.py
    - SystemMonitor をポーリングする監視ループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）。
  - utils/
    - logging_setup.py — ログ設定（stdout + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度・プロセス監視
    - trade_monitor.py — （存在）注文滞留・約定異常などの監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込み（Execution 停止シグナル）
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - alert_manager.py — アラート送信ロジック（LINE 等を想定）
  - execution/
    - broker_factory.py — ブローカークライアント生成（本番／Mock 切替）
    - execution_engine.py — ExecutionEngine 本体（セッション管理・注文実行）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（リスク基準等）
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — Momentum/Value/Volatility 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM で評価して ai_scores に書き込む
    - regime_detector.py — ETF MA と LLM を組み合わせたレジーム判定
  - tools/
    - paper_verification_report.py — paper_trading DB を使った検証レポート生成
  - data/
    - （デフォルトの DB /フラグファイル出力場所: data/*.db, data/*.flag, data/*.pid）
  - logs/
    - （ログ出力先、logging_setup で生成）

---

## 運用上の注意 / ヒント

- ペーパートレードモード（KABUSYS_ENV=paper_trading）では、MockBroker を使って data/paper_trading.db に記録し、本番データと完全分離されます。実行前に環境変数を確認してください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知等の設定を必ず確認し、KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動クリアは危険）。
- Monitoring は常に「本番 sqlite_path」を参照する仕様です。監視ログの DB を適切にバックアップしてください。
- OpenAI を利用する AI 機能は APIキーの管理に注意。呼び出しはレート制限や料金が発生します。
- logs ディレクトリの権限／ディスク空き容量に注意してください。TimedRotatingFileHandler が失敗するとコンソールのみの出力になります。
- process_priority の設定は OS 権限（root や管理者）に依存します。権限不足時は警告が出ますが、致命的ではありません。
- 設定検証（validate_config）はデプロイ前に必ず実行することを推奨します。

---

README はここまでです。必要であれば以下の追加情報も作成できます：
- requirements.txt の候補（推奨パッケージ一覧）
- デプロイ手順（systemd ユニットファイル例）
- 詳細な設定例（.env.example）
- 各モジュールの API 使用例（サンプルコード）

どれを追加しますか？