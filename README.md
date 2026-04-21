# KabuSys

日本株自動売買システムのコアライブラリ群（軽量実装）。  
この README はパッケージ内部の主要スクリプト / モジュールの使い方、セットアップ手順、ディレクトリ構成を日本語でまとめたものです。

注意: このリポジトリは実際の発注・運用に用いる前に必ず設定・検証を行ってください。特に `KABUSYS_ENV=live` は本番運用となり実際に発注されます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムを構成するモジュール群を含みます。主な機能は以下の通りです。

- Execution エンジン（発注・注文管理・リスク管理）
- Monitoring（システム状態、注文状況、リスクの監視と Kill Switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ機能（ファクター計算、特徴量探索、IC 計算）
- AI 補助モジュール（ニュースセンチメント評価、レジーム判定） — OpenAI を利用
- 補助ツール（ペーパートレード検証レポート生成など）
- 設定管理 / ウィザード / 検証 CLI

設計上の特徴:
- 設定は環境変数・`.env` によって管理（`.env.local` を上書き）
- Paper Trading と Live（本番）を明確に分離（paper_trading は専用 SQLite DB を使用）
- DuckDB を分析用途に使用、SQLite を監視・注文ログに使用
- OpenAI 呼び出しは失敗耐性やリトライを備え、フェイルセーフで動作

---

## 主な機能一覧

- run_execution: ExecutionEngine を起動（発注を行うエンジン）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録
  - プロセス優先度を高に設定、PID 管理、停止フラグ検出
- run_monitoring: SystemMonitor をポーリングして監視を行う
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可（デフォルト 60 秒）
  - 監視用 DB は環境にかかわらず本番 sqlite_path を使用
- monitoring サブモジュール
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス生存監視
  - TradeMonitor: 発注ログの滞留・価格異常検出（コード参照）
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch: `data/kill.flag` の書き込みによる ExecutionEngine 停止
  - MonitoringDB: SQLite に対する永続化レイヤ（テーブル作成 / マイグレーション含む）
- portfolio サブモジュール
  - 候補選定、等金額/スコア配分、リスク調整（セクター上限）、株数算定（単元丸め）
- research サブモジュール
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン/IC/統計サマリ機能
- ai サブモジュール
  - news_nlp.score_news: OpenAI を用いたニュースセンチメントスコアの算出・保存
  - regime_detector.score_regime: ETF の MA200 とマクロニュースを組み合わせたレジーム判定
- tools
  - paper_verification_report: ペーパートレードの稼働率・成功率・レイテンシ等を集計してレポート出力
- 設定管理
  - config_setup.py: 対話式ウィザードで `.env` を作成・更新
  - validate_config.py: 起動前に設定・ファイルを検証

---

## 必要な依存パッケージ（例）

主な依存項目（実行する機能により異なる）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config YAML を検証したい場合）
- その他: 標準ライブラリ

インストール例（仮に pipenv / venv を使用する場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

必要なパッケージは機能や実行環境によって変わるため、使用するモジュールに応じて追加してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. 仮想環境を作成して依存をインストール（上記参照）
3. 初期設定ファイル `.env` を作成
   - 対話式ウィザードを推奨:
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザードは `.env`（デフォルト）に必要項目を書き込みます。重要なキー:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH, SQLITE_PATH（データファイルパス）
     - OPENAI_API_KEY（AI 機能を使う場合）
4. 起動前の設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じて `data/` ディレクトリやログディレクトリ（デフォルト `logs/`）の権限を確認

---

## 使い方（実行例）

- ExecutionEngine（発注エンジン）を起動:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB が使用され発注はモックになります。
  - 終了は `data/stop_requested.flag` を作成するか Ctrl+C。

- Monitoring を起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視ルーチンはログ・監視 DB へ書き込み、Kill Switch の評価を行います。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（プログラムから直接呼び出し）
  - ニューススコア算出:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```

- ログ
  - デフォルトでは `logs/<app_name>.log` に日次ローテートでログが出力されます（`logs/` ディレクトリ）。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒。デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH（ファイルパスの上書き）

Kill / stop の制御:
- data/kill.flag: Kill Switch により ExecutionEngine に停止シグナルを送る（存在するとエンジンは停止します）
- data/stop_requested.flag: run_monitoring / run_execution の外部停止検出に使用（存在するとループを抜ける）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - config.py — 環境変数 / Settings 管理、.env 自動ロード機能
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py — SQLite テーブル/マイグレーション / 永続化 API
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文ログ監視（滞留・異常検出）
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信のラッパー、実装参照）
  - utils/
    - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFileHandler）
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 運用上の注意点

- 本番環境（KABUSYS_ENV=live）では Kill Switch / LINE 通知設定などを十分に確認してください。validate_config はライブ設定時に注意喚起を出します。
- Paper trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。必ず別ファイルを使用してください。
- OpenAI を利用する AI モジュールは API キーおよび料金に注意し、テスト時にはモック化して実行することを推奨します（モジュール内で API 呼び出し箇所を差し替え可能）。
- psutil によるプロセス優先度設定は権限が必要な場合があります（Linux の nice 値変更や Windows の優先度設定でアクセス拒否されることがあるため警告を出してスキップする実装になっています）。
- `.env` は絶対にリポジトリにコミットしないでください（secret 値が含まれます）。

---

## 追加情報 / トラブルシューティング

- DuckDB / SQLite のファイルパスは Settings（環境変数）で変更できます。デフォルトは `data/` 配下です。
- ログディレクトリ作成に失敗するとファイル出力が無効化され、コンソール出力のみになります（`setup_logging` が警告します）。
- validate_config は PyYAML が無ければ YAML 内容チェックをスキップします（警告）。
- AI 周りの API エラーはリトライやフォールバック（スコア 0.0）でフェイルセーフ化されていますが、運用では API レートや費用を管理してください。

---

README は以上です。必要であれば、運用手順（デーモン化、systemd ユニットファイル例、ログローテーションやバックアップ方針）や各モジュールのより詳細な API ドキュメント（関数引数の例、戻り値例、エラーケース）も作成します。どの部分を拡張しますか？