# KabuSys

日本株向け自動売買システムのリポジトリ（README はコードベースより自動生成）。  
以下は開発者/運用者向けの簡易ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なフレームワークです。  
主な要素は以下のとおりです。

- ExecutionEngine：発注ロジック・注文管理・リスク管理を含む実行エンジン（本番／ペーパートレード対応）
- Monitoring：システム稼働性・注文状況・リスクをポーリングしてログ・アラート発行・Kill Switch を管理
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI モジュール：OpenAI を用いたニュースセンチメント評価・市場レジーム判定
- Tools：ペーパートレード検証レポート等のユーティリティスクリプト
- 環境・設定関連：対話型の .env 生成ウィザード、設定検証ツール

設計方針として、ルックアヘッド（未来参照）を避ける、安全なフォールバック（API失敗時は無害な値で継続）、本番とペーパーの DB 分離などが考慮されています。

---

## 機能一覧

- 発注と注文管理（ExecutionEngine / OrderManager / OrderRepository）
- リスク管理（RiskManager, RiskMonitor）
- 監視（SystemMonitor, TradeMonitor、MonitoringEngine）
  - プロセス生存確認（PIDファイル）
  - CPU / メモリ / ディスク使用率
  - 株価データ鮮度チェック
  - 滞留注文・約定異常の検出
- Kill Switch：条件に基づき `data/kill.flag` を書き込んで ExecutionEngine を停止
- ペーパートレード対応（KABUSYS_ENV=paper_trading で MockBrokerClient と専用 SQLite を使用）
- ファクター計算（momentum, volatility, value など）および特徴量解析（IC 計算等）
- ニュースの LLM センチメント評価と市場レジーム判定（OpenAI API を利用）
- Paper Trading 検証レポート出力ツール
- .env 対話式セットアップ、設定検証 CLI

---

## 前提・依存

- Python 3.9+（型注釈や新しい標準ライブラリ使用を想定）
- 推奨パッケージ（概略）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証オプションで必要）
- その他、SQLite は標準ライブラリで利用

インストール例:
```bash
python -m pip install duckdb psutil openai PyYAML
# または要件ファイルがあれば:
# python -m pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. 必要パッケージをインストール（上記参照）
3. .env の作成（推奨: 対話式ウィザード）
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成された .env は絶対にコミットしないこと
4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じてデータディレクトリ作成:
   - デフォルトの DB 等は `data/` 配下に置かれる（例: `data/monitoring.db`, `data/paper_trading.db`, `data/kabusys.duckdb`）
6. OpenAI を使う機能を利用する場合は `OPENAI_API_KEY` を .env に設定

重要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使い DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパー専用 SQLite、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）

自動 .env ロード:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を基準）を探索し `.env` / `.env.local` を自動読み込みします。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 使い方（主要 CLI / モジュール）

以下は主要な実行方法例です。各モジュールはパッケージモジュールとして実行可能です。

- ExecutionEngine（発注実行）
  ```bash
  # 本番/開発/ペーパーは KABUSYS_ENV の値で分岐
  python -m kabusys.run_execution
  ```
  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは `PAPER_TRADING_SQLITE_PATH` に記録（本番 DB と分離）
  - 起動時に `data/execution.pid`（デフォルト）等 PID ファイルを扱います
  - 停止は `data/stop_requested.flag` の作成や Kill Switch による `data/kill.flag` によって制御

- Monitoring（監視ループ）
  ```bash
  # ポーリングループを起動
  python -m kabusys.run_monitoring
  # ポーリング間隔を変更する（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  挙動:
  - デフォルトは 60 秒ごとに SystemMonitor.check_once() を呼ぶ
  - 監視は常に（環境にかかわらず）本番 sqlite_path (`SQLITE_PATH`) を参照してログを保存
  - 停止フラグは `data/stop_requested.flag`（ファイルの存在を確認してループを終了）

- .env ウィザード（対話式）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```bash
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラム API）
  - ニュースセンチメントを付与して AI スコアを ai_scores テーブルへ書き込む:
    - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - 市場レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - これらは DuckDB 接続（kabusys.data 用の DB）を受け取り、必要に応じて OpenAI API をコールします。

- ライブラリ関数（研究・ポートフォリオ構築）
  - ファクター計算: `kabusys.research.calc_momentum`, `calc_volatility`, `calc_value`
  - ポートフォリオ構築: `kabusys.portfolio.select_candidates`, `calc_equal_weights`, `calc_score_weights`, `calc_position_sizes`
  - リスク調整: `kabusys.portfolio.apply_sector_cap`, `calc_regime_multiplier`

---

## 停止・Kill Switch・フラグファイル

- 停止要求（監視・実行の安全停止）:
  - 監視ループ / 実行ループはリポジトリの `data/stop_requested.flag` を確認して終了するようになっています。
  - Kill Switch は `data/kill.flag` を生成して ExecutionEngine に停止を促す仕組みです（KillSwitch クラス）。
  - Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると起動時に kill.flag を自動削除しますが、本番では 0 を推奨します。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
  - config_setup.py           — .env 対話式ウィザード（CLI）
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュースを OpenAI で評価して ai_scores に書き込む
    - regime_detector.py      — マクロ + MA200 でレジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite ベースの監視ログ永続化層
    - monitoring_engine.py    — 各 Monitor をまとめるエンジン
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - kill_switch.py          — Kill Switch（flag ファイル管理）
    - alert_manager.py        — （アラート送信管理：未掲示の詳細あり）
  - execution/
    - order_manager.py
    - order_repository.py
    - order_record.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py              — DuckDB / データ取得ユーティリティ等（参照箇所あり）
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

その他: `data/`（DB・PID・flag 等のデフォルト置き場）、`config/`（YAML 設定テンプレート群）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定ミスやプレースホルダのままの値が重大なリスクとなります。`validate_config.py` で事前チェックを必ず行ってください。
- OpenAI 等外部 API を使う機能は API キーの管理（.env に設定）に注意してください。呼び出しは失敗耐性（リトライやフォールバック）を備えていますが、コストやレート制限に留意してください。
- DB スキーマのマイグレーションは monitoring_db.init_monitoring_db 内で最小限の互換処理を行います。バックアップを取った上で運用してください。
- ペーパートレードでは本番 DB とデータを完全に分離するよう設計されています（ペーパー用 sqlite を使用）。

---

もし README の内容をさらに詳しく（設定項目一覧を全て展開、各クラスの API ドキュメント、運用手順のチェックリストなど）にしたい場合は、どの部分を優先して深掘りするか教えてください。