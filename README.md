# KabuSys

日本株向け自動売買システムのリポジトリ（軽量版）。  
このリポジトリは、戦略・ポートフォリオ構築、発注実行、監視、研究（DuckDB ベース）、およびニュース NLP / レジーム判定等の補助ツール群を含みます。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のコンポーネントを備えた自動売買プラットフォームのコードベースです。

- ExecutionEngine: ブローカークライアント経由で注文を管理・実行（paper_trading モードあり）
- Monitoring: システム・注文・リスク監視、Kill Switch（フラグファイルによる強制停止）
- Portfolio モジュール: 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- Research / Data: DuckDB を用いたファクター計算・将来リターン / IC 計算
- AI コンポーネント: OpenAI を用いたニュースセンチメント（news_nlp）、レジーム判定（regime_detector）
- CLI ツール: .env ウィザード（config_setup）、設定検証（validate_config）、Paper Trading 検証レポート生成ツール

設計方針の一部:
- 本番 DB（監視用 SQLite）と paper_trading 用 DB を分離して安全性を確保
- DuckDB を解析用途に採用
- OpenAI を使う機能は API キーの有無で有効/無効化
- 自動化されたログ設定とプロセス優先度設定を提供

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV による動作切替（development / paper_trading / live）
  - paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db を使用
- 監視ループ起動スクリプト（python -m kabusys.run_monitoring）
  - SystemMonitor を定期ポーリングし監視ログを永続化
  - MONITOR_POLL_INTERVAL 環境変数で間隔変更可能（デフォルト 60 秒）
- Monitoring サブモジュール:
  - SystemMonitor / TradeMonitor / RiskMonitor の統合（MonitoringEngine）
  - Kill Switch（data/kill.flag を書き込むことで ExecutionEngine を停止）
  - 監視ログ永続化（SQLite）
- Portfolio ユーティリティ:
  - 候補選定、等重・スコア重み計算、位置サイズ算出、セクターキャップ適用、レジーム乗数
- Research ユーティリティ:
  - モメンタム・バリュー・ボラティリティ指標計算、forward returns、IC 計算、統計サマリー
- AI / NLP:
  - ニュース集約→OpenAI によるセンチメント付与（ai_scores テーブルへ保存）
  - レジーム判定（ETF ma200 とマクロニュースを組み合わせて判定）
- ツール:
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## 必要条件（推奨）

- Python 3.10+
- 必須ライブラリ（pip インストール）:
  - duckdb
  - psutil
  - openai
- 任意 / 機能限定で必要:
  - PyYAML（config/*.yaml のパース検証に使用）
- SQLite（標準ライブラリに同梱）

例: requirements.txt がない場合のインストール例
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリを取得し、作業ディレクトリに移動:
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 環境を準備（仮想環境推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb psutil openai PyYAML
   ```

3. 初期 .env を作成:
   - 対話式ウィザード（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成します（.env は絶対にリポジトリにコミットしないでください）。

   - 手動で作る場合の例（.env.example を参考にしてください）:
     ```
     JQUANTS_REFRESH_TOKEN=your_token
     KABU_API_PASSWORD=your_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=sk-...
     ```

4. 設定検証（必須環境変数やファイルパスをチェック）:
   ```
   python -m kabusys.validate_config
   # 警告もエラーにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）:
   ```
   mkdir -p data logs
   ```

---

## 使い方（起動・運用）

- ExecutionEngine（発注エンジン）を起動:
  - 通常起動:
    ```
    python -m kabusys.run_execution
    ```
  - 動作モードは KABUSYS_ENV 環境変数で制御:
    - development: 発注なし（開発用）
    - paper_trading: MockBroker 使用、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
    - live: 本番ブローカー使用（設定に注意）

  - 起動時のプロセス優先度は high に設定されます（可能な場合）。

  - 停止方法:
    - ExecutionEngine は data/stop_requested.flag を監視しており、フラグが置かれると停止します。
    - Kill Switch（監視側）が条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止させます。

- 監視ループの起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒指定（例: 30）。
  - 監視は settings.sqlite_path（デフォルト data/monitoring.db）にログを記録します。

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（ニュース NLP / レジーム判定）
  - 実行には OpenAI API キーが必要:
    - 環境変数 OPENAI_API_KEY または関数引数で渡す
  - ニューススコア付与: kabusys.ai.score_news を利用
  - レジーム判定: kabusys.ai.regime_detector.score_regime を利用

- ロギング
  - setup_logging() により logs/<app_name>.log に日次ローテーションで出力（デフォルト logs ディレクトリ）
  - ログレベルは LOG_LEVEL 環境変数か起動時引数で制御

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・kill スイッチ関連

---

## 停止 / Kill Switch の仕組み

- KillSwitch クラスが RiskMonitor 等の結果を評価して条件に合致すると `data/kill.flag` を作成します。
- ExecutionEngine は起動時および実行中に `data/stop_requested.flag` の存在を監視し、存在すれば安全に停止します。
- ExecutionEngine の PID 管理は data/execution.pid（デフォルト）を使用します。

※ 本番運用時は KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨（自動クリアは危険）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル / ディレクトリ構成（src/kabusys 以下を抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定管理
    - config_setup.py                 — .env ウィザード CLI
    - validate_config.py              — 設定検証 CLI
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py  — Paper Trading 検証レポート
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (実装あり)
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (実装あり)
    - execution/                       — 発注関連（OrderManager 等）
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/ (実行時に使用されるディレクトリ)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - kill.flag
      - stop_requested.flag
      - execution.pid
    - logs/ (デフォルトログディレクトリ)

※ 実際のファイルはリポジトリの内容に依存します。上は主要モジュールの一覧です。

---

## 開発者向け補足

- DB マイグレーションは簡易的に init_monitoring_db() 内で行われます（既存テーブルの列追加など）。
- DuckDB 接続は分析用途に使われ、AI / Research モジュールは基本的に DuckDB のテーブル（prices_daily, raw_financials, raw_news など）を参照します。
- OpenAI への呼び出しはリトライやレスポンスの厳密なバリデーションを行い、失敗時はフェイルセーフ（スコア 0 やスキップ）で継続します。
- ローカル開発では KABUSYS_ENV=development を使用し、ExecutionEngine は実際の発注を行いません。

---

## トラブルシューティング

- PyYAML が見つからない場合、validate_config は YAML の内容検証をスキップして警告を出します。
- ログディレクトリの作成に失敗するとコンソール出力のみで継続します（警告が出ます）。
- OpenAI 呼び出しはネットワークエラーや 429 を考慮したリトライ処理を組み込んでいますが、APIキー未設定の場合は明示的なエラーを投げます。

---

## ライセンス / 注意

- この README に示した設定ファイル（.env）や API キーは機密情報です。リポジトリにコミットしないでください。
- 本コードは例示的な自動売買システムのコンポーネント群です。実際のマネーを扱う前に十分な検証と安全対策（監視、アラート、Kill Switch、運用手順）を行ってください。

---

必要であれば、README に入れるコマンド例や .env のサンプル（敏感情報はマスク）を追記します。どの部分をより詳しく書きたいか教えてください。