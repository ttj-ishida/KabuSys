# KabuSys

日本株向け自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、取引実行エンジン、監視/アラート、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント）などを包含する自動売買基盤のコードベースです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール化された自動売買フレームワークです。

- 戦略に基づく銘柄選定およびポジションサイズ計算（portfolio モジュール）
- DuckDB を用いたリサーチ・ファクター計算（research モジュール）
- OpenAI を利用したニュースのセンチメント評価・レジーム判定（ai モジュール）
- 発注の実行エンジン（execution）とモック（paper trading）
- 実行状況・リスク監視と Kill Switch（monitoring）
- 環境設定ツール、設定検証ツール、検証レポート等のユーティリティ（tools / utils）

設計方針の一部:
- DB・ファイルパスは環境変数または .env から設定
- 本番（live）とペーパー（paper_trading）を分離（paper は専用 SQLite）
- ルックアヘッドバイアス対策として日付参照に注意（各モジュールで説明あり）

---

## 機能一覧

主な機能（抜粋）

- execution
  - ExecutionEngine（実際の発注／セッション管理）
  - BrokerClientFactory（実ブローカ／Mock の切替）
  - OrderManager / RiskManager / Reconciler 等の運用コンポーネント
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス存在、データ鮮度チェック
  - TradeMonitor: 注文滞留、約定異常などの検出（実装ファイル参照）
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch: 条件で kill.flag を作成し Engine 停止指示
  - MonitoringEngine: 各モニタを束ねて定期実行
  - monitoring_db: SQLite テーブル定義と永続化 API
- ai
  - news_nlp.score_news: raw_news を LLM（OpenAI）に送信し銘柄ごとのスコアを ai_scores に保存
  - regime_detector.score_regime: ETF + マクロニュースを組み合わせた市場レジーム判定
- research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上でファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量評価ツール
- portfolio
  - 銘柄選定（select_candidates）、等配分／スコア加重、リスク調整、ポジションサイズ計算
- tools
  - paper_verification_report: ペーパートレード結果の検証レポート生成
- utils
  - logging_setup: 統一的なログ設定（stdout + 日次ローテーション）
  - process_priority: プロセス優先度 / CPU affinity 設定
- 設定関連
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前の設定検証 CLI

---

## 前提・依存関係

推奨 Python バージョン: 3.10 以上（union 型記法や | を使用しているため）

必須（代表例）
- duckdb
- psutil
- openai
- その他: sqlite3 は標準ライブラリ

開発 / 任意
- PyYAML（validate_config が config/*.yaml の構文検査を行う場合に必要）

例: pip でのインストール例
```
pip install duckdb psutil openai
# オプション: PyYAML
pip install pyyaml
```

（requirements.txt が付属していない場合は上のパッケージを適宜追加してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境の作成（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai
   pip install pyyaml  # validate_config で YAML チェックしたい場合
   ```

4. 環境変数設定 (.env)
   - 初回は対話式ウィザードで .env を作成するのが簡単です。
     ```
     python -m kabusys.config_setup
     ```
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY（score_news / score_regime を利用する際に必要）
   - DB のデフォルトパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

5. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする:
   python -m kabusys.validate_config --strict
   ```

6. データ・ログディレクトリ
   - 実行時に必要なディレクトリ（data/, logs/）は多くのスクリプトで自動作成されますが、手動で作成してパーミッションを確認しておくと確実です。

---

## 使い方（主要な実行スクリプト）

- 監視ループ起動（SystemMonitor をポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
  - 監視は常に本番用 sqlite_path を使用（環境に依らず）

  停止方法:
  - data/stop_requested.flag を作成するとループ検知で終了します
  - KeyboardInterrupt（Ctrl+C）

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離します
  - プロセス優先度を high に設定して起動します
  - 起動時に data/stop_requested.flag が既に存在すると起動をスキップします
  - 停止指示は data/stop_requested.flag 又は monitoring 側の kill.flag（KillSwitch により作成）などで行います

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）

- AI / リサーチ系はライブラリ API として利用
  例: ニューススコアを呼ぶ（Python REPL やスクリプト内で）
  ```python
  from kabusys.ai import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  from datetime import date
  # OPENAI_API_KEY を環境変数に設定済みであること
  score_news(conn, target_date=date(2026, 4, 10))
  ```

- ログ設定
  - 各起動スクリプトは utils.logging_setup.setup_logging を呼び出します
  - stdout と logs/<app_name>.log（デイリーローテート）に出力

---

## 代表的な環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV = development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- MONITOR_POLL_INTERVAL (run_monitoring 用ポーリング秒数)
- KILL_FLAG_CLEAR_ON_START (0/1) — ExecutionEngine 起動時の kill.flag 自動クリア（本番では 0 推奨）

詳細は kabusys.config.Settings のプロパティ実装を参照してください。

---

## ディレクトリ構成（src 内の主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数と .env 自動読み込みロジック、Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

src/kabusys/utils/
- logging_setup.py — 標準ログ設定ユーティリティ
- process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- __init__.py

src/kabusys/monitoring/
- monitoring_db.py — SQLite テーブル作成 + 永続化 API（MonitoringDB）
- system_monitor.py — システム状態・データ鮮度チェック
- risk_monitor.py — ドローダウン／ポジション上限監視
- trade_monitor.py — （注文監視ロジック）※ファイルあり
- kill_switch.py — kill.flag の作成 / 管理
- monitoring_engine.py — 各 Monitor を束ねる
- alert_manager.py — 通知管理（LINE 等、実装を確認）

src/kabusys/execution/
- execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, ...（発注周り）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・重み計算
- position_sizing.py — 株数計算・資金上限制御
- risk_adjustment.py — セクターキャップ、レジーム乗数
- __init__.py

src/kabusys/research/
- factor_research.py — momentum/volatility/value 等の計算（DuckDB）
- feature_exploration.py — forward return / IC / 統計サマリ等
- __init__.py

src/kabusys/ai/
- news_nlp.py — ニュースセンチメント収集・OpenAI 呼び出しラッパ
- regime_detector.py — ETF + マクロニュースでのレジーム判定
- __init__.py

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成
- __init__.py

その他:
- data/ — デフォルトの SQLite / pid / flag 等が置かれる（実行時に作成）
- logs/ — ログファイル（setup_logging が作成）
- config/*.yaml — 各種設定テンプレート（validate_config が参照）

---

## 運用上の注意・トラブルシューティング

- .env は決して Git にコミットしないでください（config_setup.py にも注記あり）。
- KABUSYS_ENV=live の場合は特に LINE 通知設定や Kill Switch 設定を慎重に確認してください（validate_config の警告参照）。
- OpenAI の呼び出しは外部 API に依存するため、API エラーは適切にハンドリングされていますが、API キーとレート制限には注意してください。
- monitoring / execution の停止は stop_requested.flag（run_* スクリプトで使用）や kill.flag（KillSwitch）で行えます。flag ファイルは data/ 以下に作られます。
- DuckDB / SQLite のパスが異なる場合は環境変数で上書きしてください。

---

## 開発者向けメモ

- 各モジュールは可能な限り副作用を抑え、テストしやすい純粋関数群と副作用を伴うラッパー（DB 書き込み等）に分離しています（例: portfolio/*.py や research/*.py）。
- OpenAI 呼び出し部分にはテスト用に差し替え可能な関数（_call_openai_api 等）が用意されています。ユニットテスト時はパッチして外部依存を切り離してください。
- validate_config や config_setup は CI / デプロイ前チェックとして有用です。

---

必要に応じて README に加筆できます（例: CI 設定、Dockerfile、requirements.txt の追加、具体的な broker 実装の説明など）。追加してほしい項目があれば教えてください。