# KabuSys

日本株向け自動売買システムのコアライブラリ／ツール群です。  
このリポジトリには、発注エンジン（ExecutionEngine）・監視（Monitoring）・研究用ファクター計算・ポートフォリオ構築ロジック・AI を使ったニュース解析などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような責務を持つモジュール群から構成されています。

- 発注系（execution）: ブローカークライアントを経由して注文を管理・実行するエンジン
- 監視系（monitoring）: システム状態・注文状況・リスク指標を定期的に監視し、Kill Switch を発動可能
- 研究系（research）: DuckDB 上の時系列データからファクターや将来リターン・IC 等を計算
- ポートフォリオ構築（portfolio）: 候補選定、配分・ポジションサイズ計算、セクター制限など
- AI（ai）: ニュースのセンチメント解析（OpenAI）や市場レジーム判定
- ユーティリティ（utils）: ロギング設定、プロセス優先度設定、設定読み込み等
- CLI ツール群: .env ウィザード、設定検証、ペーパートレード検証レポート 等

設計方針としては、ルックアヘッドの排除（date.today() 等を直接参照しない等）、フェイルセーフ（API エラー時のデフォールト処理）、DB 操作の冪等性等が考慮されています。

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB を分離
  - プロセス優先度を高く設定（set_process_priority）
  - 停止フラグ（data/stop_requested.flag）による安全停止
- Monitoring ポーリング（run_monitoring.py / MonitoringEngine）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文異常、リスク（ドローダウン・ポジション上限）監視
  - KillSwitch により条件達成時に data/kill.flag を書き込み ExecutionEngine に停止シグナルを送出
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
- モニタリング永続化（monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理・マイグレーション対応
- ポートフォリオ構築
  - 候補選定（score / rank ベース）、等金額/スコア加重、リスクベースの株数算出、単元（lot）丸め、セクターキャップ、レジーム乗数
- 研究（research）
  - モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB 利用）
  - 将来リターン、IC（スピアマン）、統計サマリー等
- AI（news_nlp, regime_detector）
  - OpenAI を使ったニュースセンチメントスコア計算（ai_scores に保存）
  - マクロニュースと ETF MA200 を組み合わせたレジーム判定（market_regime に保存）
  - OpenAI API のキーは環境変数 `OPENAI_API_KEY` または関数引数で指定
- ツール
  - .env 生成ウィザード（config_setup）
  - 起動前設定検証（validate_config） — --strict オプションあり
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）

---

## 要件（推奨）

- Python 3.10+
- 依存パッケージ（主要）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の内容検証に使用）
- SQLite / DuckDB 用のディスク領域
- OpenAI を使う場合は API キー（OPENAI_API_KEY）

requirements.txt が別途ある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリに移動
   ```
   git clone <repo url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   requirements.txt が無い場合は最低限以下を入れてください:
   ```
   pip install duckdb psutil openai
   ```
   （PyYAML は任意: config ファイルの検証を行う場合に必要）

4. 環境変数ファイル (.env) の生成
   - 対話式で .env を作る:
     ```
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートに `.env` が生成されます。機密情報（トークン・パスワード）はマスクされます。

5. 設定検証（必須項目が揃っているか確認）
   ```
   python -m kabusys.validate_config
   ```
   - 警告も FAIL 扱いにする場合:
     ```
     python -m kabusys.validate_config --strict
     ```

6. データディレクトリ（logs, data など）は必要に応じて作成されます（logging_setup が自動作成を試みます）。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV=development|paper_trading|live（デフォルト: development）

- ログ / DB
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）

- OpenAI
  - OPENAI_API_KEY（ai モジュールを使う場合に必須）

- 監視・Kill Switch
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START（"0" または "1"。本番では "0" 推奨）

- モニタリング
  - MONITOR_POLL_INTERVAL（秒、run_monitoring でポーリング間隔を上書き。デフォルト 60）

- Paper Trading の挙動
  - PAPER_FILL_MODE（instant|partial|never|reject。デフォルト: instant）

（完全な一覧は `kabusys.config.Settings` を参照してください）

---

## 使い方（実行例）

- ExecutionEngine を起動（フォアグラウンドで実行）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 起動時に data/stop_requested.flag が存在する場合はエンジンは起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。

- Monitoring を起動（ポーリング）
  ```
  # デフォルト 60 秒間隔
  python -m kabusys.run_monitoring

  # ポーリング間隔を 30 秒に変更
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - Monitoring は KABUSYS_ENV にかかわらず本番（settings.sqlite_path）を監視 DB として使用します。
  - data/stop_requested.flag を作成すると監視ループが終了します。

- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（プログラム内 API）
  - ニュースのスコアリング:
    ```
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="...")  # api_key を指定するか OPENAI_API_KEY を環境変数に
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```

---

## ログ・停止フラグ・PID

- ログ: `kabusys.utils.logging_setup.setup_logging` により stdout と `logs/<app_name>.log`（日次ローテート）へ出力
- 停止フラグ:
  - data/stop_requested.flag: run_execution/run_monitoring の起動ループで監視される外部停止指示ファイル（存在したら停止）
  - data/kill.flag: KillSwitch が発動した際に書き込まれるファイル（ExecutionEngine 側で検出して停止）
- PID ファイル:
  - ExecutionEngine は `data/execution.pid`（デフォルト）へ PID を書きます（Settings.pid_file_path で変更可）

---

## ライブラリ的利用（研究・ポートフォリオ）

- 研究機能（DuckDB 接続を渡して利用）
  - ファクター計算: `kabusys.research.calc_momentum/ calc_volatility/ calc_value`
  - 将来リターン・IC 等: `kabusys.research.calc_forward_returns`, `kabusys.research.calc_ic`, `kabusys.research.factor_summary`
- ポートフォリオ構築（純関数）
  - 候補選定: `kabusys.portfolio.select_candidates`
  - 重み計算: `kabusys.portfolio.calc_equal_weights`, `calc_score_weights`
  - ポジションサイズ: `kabusys.portfolio.calc_position_sizes`
  - セクター制限等: `kabusys.portfolio.apply_sector_cap`, `calc_regime_multiplier`

これらは DuckDB や外部 API への副作用が少ない設計になっており、単体テストしやすくなっています。

---

## ディレクトリ構成（抜粋）

```
src/
  kabusys/
    __init__.py
    config.py                 # 環境変数・Settings
    config_setup.py           # .env 作成ウィザード
    validate_config.py        # 設定検証 CLI
    run_execution.py          # ExecutionEngine 起動スクリプト
    run_monitoring.py         # Monitoring 起動スクリプト

    execution/                # 発注エンジン関連（broker_factory, execution_engine, order_manager, risk_manager ...）
      ...
    monitoring/
      monitoring_db.py        # SQLite テーブル定義・永続化
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      alert_manager.py
      kill_switch.py
      ...
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py
      regime_detector.py
    tools/
      paper_verification_report.py
    utils/
      logging_setup.py
      process_priority.py
    data/                     # （運用時に生成される）データ・フラグ・DB・PID 等
    logs/                     # ログファイル（デフォルト）
```

---

## 注意事項 / 運用メモ

- 本番環境（KABUSYS_ENV=live）時は `.env` の内容や `KILL_FLAG_CLEAR_ON_START` の値に特に注意してください（validate_config は live 時の追加チェックを行います）。
- OpenAI を使用する機能は API コストやレート制限が発生します。score_news / score_regime は再試行やバックオフのロジックを持ちますが、運用時のコスト管理とリトライポリシーの確認を推奨します。
- Monitoring は監視 DB（SQLite）へ定期的に記録します。監視間隔は `MONITOR_POLL_INTERVAL` で調整可能です（デフォルト 60 秒）。
- Paper Trading（模擬発注）は本番 DB と明確に分離されます（PAPER_TRADING_SQLITE_PATH）。本番データに影響しないよう設計されています。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します（logging_setup のフォールバック動作）。

---

## トラブルシューティング

- .env を作成しても環境変数が読み込まれない場合:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` が設定されていないか確認。自動ロードを無効化していると `.env` は読み込まれません。
  - プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行います。パッケージ配布後は環境変数を直接セットしてください。
- OpenAI 呼び出しで頻繁に失敗する場合:
  - `OPENAI_API_KEY` の有無、ネットワーク、レート制限を確認してください。ログにリトライ情報が出ます。
- Monitoring / Execution が起動しない（すぐ終了する）:
  - `data/stop_requested.flag` が存在しないか確認してください。存在すると起動を抑止します。

---

必要であれば、README に含める具体的な起動例（systemd ユニット例・Dockerfile・compose 等）や、各モジュールの API ドキュメント（関数引数や戻り値の説明）を追加で作成します。どの部分を詳述したいか教えてください。