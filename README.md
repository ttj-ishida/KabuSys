# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ＆実行スクリプト群）です。本 README はコードベースから自動生成的に作成した概要・セットアップ・使い方ドキュメントです。

---

目次
- プロジェクト概要
- 機能一覧
- 必須 / 推奨依存パッケージ
- セットアップ手順
- 使い方（主要スクリプト・CLI）
- 環境変数（主要項目）
- 停止・Kill Switch の仕組み
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（取引エンジン、監視、ポートフォリオ構築、研究ツール、AI を使ったニュース評価など）を含むコードベースです。  
主要設計方針として次を掲げています：

- 本番とペーパートレードを明確に分離（KABUSYS_ENV による切替）
- DuckDB を使ったリサーチ（prices_daily / raw_financials 等）
- SQLite を用いた監視ログ・トレードログ保存（monitoring.db / paper_trading.db）
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP / レジーム判定（オプション）
- フェイルセーフ（API エラー時のバックオフ、部分失敗での DB 保護 等）

---

## 機能一覧

- ExecutionEngine（発注エンジン）: Broker クライアント経由で発注、Order 管理、リスク管理、整合性チェック
  - `run_execution.py` で起動
  - `paper_trading` モードでは MockBrokerClient を使用し、専用 DB (`data/paper_trading.db`) に記録
- Monitoring（監視）: システム状態、注文滞留、リスク（ドローダウン・ポジション上限）監視、Kill Switch 発動
  - `run_monitoring.py` で簡易ポーリング実行 / `MonitoringEngine` で統合
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
  - 関数群: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- Research: ファクター計算（モメンタム・バリュー・ボラティリティ）、将来リターン計算、IC 計算、統計サマリ
  - DuckDB データを用いて純粋計算を行う
- AI モジュール（オプション）:
  - ニュース NLP（news_nlp.score_news）: raw_news を集約して OpenAI に投げ、銘柄毎の ai_score を ai_scores テーブルに書き込む
  - レジーム判定（regime_detector.score_regime）: ETF の MA とマクロニュースの LLM スコアを合成して daily regime を生成
- ツール:
  - Paper Trading 検証レポート生成 (`kabusys.tools.paper_verification_report`)
- 設定支援:
  - 対話式 .env 作成ウィザード (`config_setup.py`)
  - 設定検証 CLI (`validate_config.py`)

---

## 必須 / 推奨依存パッケージ

（プロジェクトに登場するライブラリを列挙しています。実際の requirements.txt がある場合はそれを使用してください）

- Python: 3.10 以上（型記法 / 機能より）
- 必須（実行に必要）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 推奨 / 開発時:
  - PyYAML（config/*.yaml の検証に使用、未インストールでも動作は継続）
  - その他テスト用ライブラリ等

インストール例:
```bash
python -m pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動します。
2. Python 仮想環境を作成・有効化（推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール:
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
4. `.env` の作成:
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくはリポジトリにある `.env.example` を参考に `.env` を作成してください。
   - 自動ロード: 起動時に `.env` と `.env.local` がプロジェクトルートから自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
5. 設定検証（必ず実行しておくことを推奨）:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリ作成（必要に応じて）:
   - デフォルトで `data/` 配下に SQLite / DuckDB 等を置きます。実行時に自動作成される箇所もありますが、権限等に注意してください。

---

## 使い方（主要スクリプト・CLI）

- ExecutionEngine（発注エンジン）起動:
  - 本番 / 開発 / ペーパー切替は KABUSYS_ENV 環境変数で行います。
  - ペーパートレード時は MOCK ブローカーを使い DB を `PAPER_TRADING_SQLITE_PATH` に記録します。
  ```bash
  # そのまま起動
  python -m kabusys.run_execution

  # 環境変数上書き例（Linux/macOS）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - run_execution は起動時に `data/execution.pid` へ PID を書く設計（設定で変更可）。停止は stop フラグ / kill flag により制御されます（下記参照）。

- Monitoring（監視ループ）起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書きできます（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず「本番の sqlite_path」を参照する設計（監視 DB は本番 DB を想定）。

- 設定ウィザード / 検証:
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- ライブラリ的な呼び出し（AI スコア等）:
  - DuckDB 接続を作り、関数を呼び出します（例: news_nlp.score_news / regime_detector.score_regime）。
  - これらは OpenAI API キー（OPENAI_API_KEY）が必要です（引数で渡すことも可能）。

---

## 環境変数（主要項目）

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能使用時に必須)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート通知用）
- システム / 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- データパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db) — 監視 DB（monitoring は本番 sqlite_path を使用）
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — ペーパートレード専用 DB
- その他
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の MockBrokerClient の fill 動作）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - MONITOR_POLL_INTERVAL（監視のポーリング間隔、秒）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を読み込みます。
- 読み込みルール: OS 環境変数 > .env.local > .env。環境変数の上書きを禁止する「protected」挙動があります。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化できます。

---

## 停止・Kill Switch の仕組み

- stop_requested.flag（data/stop_requested.flag）
  - run_execution.py / run_monitoring.py 共にプロジェクトの data/stop_requested.flag を監視し、存在するとメインループを終了します（外部からの停止指示用）。
- Kill Switch（kill.flag）
  - 監視モジュール（KillSwitch）が重大リスク（ドローダウン・ポジション上限超過等）を検出した場合、`data/kill.flag` に理由を書き込みます。
  - ExecutionEngine 側は `Settings.kill_flag_path` を参照して動作（clear / is_flagged 等）します。
  - 注意: `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なため 0 を推奨します。

---

## ディレクトリ構成（主要ファイルの説明）

以下は `src/kabusys` 配下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py
    - パッケージ定義、バージョン
  - config.py
    - 環境変数の取得・ラッパー（Settings クラス）
    - .env 自動読み込みロジック
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - .env と config/*.yaml の起動前検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（ペーパートレードは専用 DB を使用）
  - run_monitoring.py
    - SystemMonitor 単体のポーリング起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
  - utils/
    - process_priority.py
      - プラットフォーム差を吸収したプロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/ (発注関連)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
    - （コードベース内で参照されています）
  - monitoring/
    - monitoring_db.py
      - SQLite 用永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
      - システム状態 / データ鮮度チェック
    - trade_monitor.py
      - 注文滞留・約定異常検出
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - Kill Switch 実装
    - monitoring_engine.py
      - 各 Monitor を束ねたポーリングエンジン
    - alert_manager.py
      - 通知管理（LINE 等への通知は設定次第）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - ポートフォリオ構築・リスク制御・サイズ計算の純粋関数群
  - research/
    - factor_research.py
      - momentum/volatility/value 等のファクター計算（DuckDB を利用）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリ
  - ai/
    - news_nlp.py
      - raw_news を LLM に投げて銘柄別スコアを生成・ai_scores に書き込み
    - regime_detector.py
      - ETF MA とマクロニュース LLM を合成して日次レジーム判定
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成スクリプト
  - monitoring/monitoring_db.py
    - MonitoringDB クラス（読み書きユーティリティ）
  - data/（ランタイム）
    - 各種 DB（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
    - flag / pid ファイル（data/execution.pid, data/kill.flag, data/stop_requested.flag）

---

## 注意事項 / 運用上のヒント

- `KABUSYS_ENV=live` を使う前に必ず `validate_config.py` で設定を確認してください。LINE 通知の設定不足や kill flag の設定は本番で致命的になります。
- OpenAI を利用する機能は API キーと課金が必要です。API レスポンス失敗時のフォールバックロジックは実装されていますが、実運用ではレート制限やコストを考慮してください。
- monitoring は監視 DB を用いるため、バックアップや永続ストレージの運用を検討してください。
- 単体テストや CI を導入する際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定するとテスト環境が安定します。

---

この README はコードから読み取れる仕様をまとめたものです。各モジュールの詳細設計（StrategyModel.md、PortfolioConstruction.md 等）はプロジェクト内のドキュメントを参照してください。追加で README の改善点や具体的な使い方（Engine の設定オプション、Broker の設定など）を反映したい場合は、どの部分を充実させるかを教えてください。