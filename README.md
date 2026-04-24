# KabuSys

日本株向け自動売買システムの軽量実装リポジトリです。  
本リポジトリは実行エンジン（ExecutionEngine）／監視サブシステム（Monitoring）／ポートフォリオ構築・ポジションサイズ計算・リスク管理・リサーチ・AI ニュース NLP 等の機能群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群から構成されます。

- 発注/実行エンジン（ExecutionEngine） — ブローカークライアントを通じた発注管理、リスク管理、再調整（reconciler）等
- 監視サブシステム（Monitoring） — システム状態・注文ログ・リスクイベントの監視、Kill Switch によるエンジン停止
- ポートフォリオ構築ライブラリ — 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチモジュール — ファクター計算・将来リターン・IC 計算等（DuckDBを利用）
- AI ツール — ニュースセンチメント集計（OpenAI 経由）、市場レジーム判定
- ユーティリティ — ログ設定、プロセス優先度設定、設定管理ウィザード / 検証ツール 等

設計方針の一部:
- DB や外部 API 呼び出し箇所は明示的に分離（Paper Trading 用 DB など）
- 実運用を想定したフェイルセーフ（API リトライ、部分書き込みで既存データ保護等）
- テストや解析に使える純粋関数群（ポートフォリオ構築、リサーチ等）

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード（KABUSYS_ENV により切替）
  - RiskManager による発注前チェック（上限ポジション比率、利用率など）
  - OrderManager / OrderRepository による発注履歴の永続化
- Monitoring
  - CPU / メモリ / ディスク監視、Execution プロセス生存確認
  - 注文滞留検知、約定異常検知、ドローダウン検知、ポジション上限監視
  - Kill Switch による安全停止（data/kill.flag）
  - アラート通知フック（LINE など）
- Portfolio
  - 候補選定、スコア加重/等配分、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - ファクター（momentum / volatility / value）計算（DuckDB）
  - 将来リターン / IC / 統計サマリー
- AI
  - ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に書き込み
  - マクロニュース + ETF MA を合成して市場レジーム判定
- ツール
  - .env 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順

前提: Python 3.10+ を推奨します。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （requirements.txt がある想定がなければ、主要依存のみ例示）
   ```
   pip install duckdb psutil openai
   # オプション: YAML 検証を行う場合
   pip install pyyaml
   ```
   主要な依存ライブラリ:
   - duckdb : リサーチ・AI 等でのデータ処理
   - psutil : システム情報取得 / プロセス優先度制御
   - openai : ニュース NLP / レジーム判定（使用する場合）
   - PyYAML（任意）: validate_config の YAML パース検証に利用

4. 環境変数設定 (.env)
   - 対話式ウィザードで初期 .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成。主要な環境変数（抜粋）:

     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (default: development) — 値: development | paper_trading | live
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - LOG_LEVEL (default: INFO)
     - LINE_CHANNEL_ACCESS_TOKEN (任意)
     - LINE_USER_ID (任意)
     - OPENAI_API_KEY (AI 機能を使う場合に必須)

   自動ロード: リポジトリルートに `.env` があれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. 設定検証（起動前推奨）
   ```
   python -m kabusys.validate_config
   # 警告を厳格に失敗扱いする場合
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

以下は主要な実行エントリポイントです。各スクリプトはパッケージモジュールとして実行できます。

- ExecutionEngine を起動
  ```
  python -m kabusys.run_execution
  ```
  特記事項:
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority）。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と完全に分離されます。
  - 実行中、PID ファイル（data/execution.pid）を使用します。
  - 停止させたい場合はルートプロジェクトの data/stop_requested.flag を作成すると安全に停止します（または Monitoring の Kill Switch により data/kill.flag が作られると停止をトリガーします）。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  特記事項:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
    - デフォルト: 60 秒
  - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用します（監視は本番DB参照が想定されるため）。
  - 停止は data/stop_requested.flag を作成することで行います（run_monitoring ループが検知して終了します）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定

- .env ウィザード（再掲）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（再掲）
  ```
  python -m kabusys.validate_config
  ```

- AI 周り（ライブラリ関数として利用）
  - ニュース NLP（ai.score_news）やレジーム判定（ai.regime_detector.score_regime）は DuckDB 接続を渡して呼び出します。OpenAI API を利用するため OPENAI_API_KEY の設定が必要です。
  - 直接スクリプト化された CLI はありませんが、運用スケジュールで呼び出すことが想定されます。

ログ出力:
- デフォルトのログディレクトリ: logs/
- 各アプリ名ごとに日次ローテートされるログファイルが作られます（例: logs/execution.log, logs/monitoring.log）。ログ設定は kabusys.utils.logging_setup.setup_logging を利用。

停止・Kill Switch:
- 手動停止フラグ: data/stop_requested.flag — run_* スクリプトはこのファイルの存在を見てループを終了します。
- Kill Switch（自動停止判定）: data/kill.flag — Monitoring がリスク閾値を超えた場合に書き込まれ、ExecutionEngine 起動中であれば停止トリガーとなります。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると Kill Flag を自動でクリアします（本番では推奨されません）。

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — (必須) J-Quants API のトークン
- KABU_API_PASSWORD — (必須) kabuステーション API パスワード
- KABUSYS_ENV — 実行モード（development / paper_trading / live） — default: development
- DUCKDB_PATH — DuckDB ファイルパス — default: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（SQLite） — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite — default: data/paper_trading.db
- LOG_LEVEL — ログレベル（DEBUG/INFO/...） — default: INFO
- OPENAI_API_KEY — OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒） — default: 60
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアする（開発時のみ 1 を推奨） — default: 0

---

## ディレクトリ構成（抜粋）

以下は主要なファイル・モジュールのツリー（src/kabusys 以下）。実際のリポジトリに合わせて調整してください。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / Settings 管理
    - config_setup.py              — .env 対話式ウィザード
    - validate_config.py           — 設定検証 CLI
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - run_monitoring.py            — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

- data/                — 実行時に使う DB / フラグファイル 保存先（既定）
- logs/                — ログファイル（デフォルトはここに出力）

---

## 注意点・運用上のヒント

- Monitoring は常に settings.sqlite_path（監視用DB）を参照します。実運用では監視 DB と発注 DB の分離ポリシーに注意してください。
- KABUSYS_ENV=paper_trading の場合、発注系はペーパートレード DB に完全分離して記録されます（本番 DB に影響なし）。
- OpenAI を使う処理（news_nlp / regime_detector）は API 呼び出しの失敗時に安全側（スコア 0.0 や処理スキップ）で継続する設計です。ただし API キーは必須なので、AI 機能を使わない場合は設定しなくても動作可能です。
- validate_config で設定を事前チェックしてから本番環境（KABUSYS_ENV=live）で起動することを強く推奨します。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合はコンソール出力のみで継続するため、運用時は logs/ の書き込み権限を確認してください。

---

この README はコードベースの主要部分をカバーしています。個別モジュール（ExecutionEngine の詳細な挙動、OrderRepository API、BrokerClient の実装など）については該当ソースの docstring / コメントを参照してください。必要であれば各コンポーネントごとの利用例や設計ドキュメント（API サンプル、シーケンス図 等）を追記できます。