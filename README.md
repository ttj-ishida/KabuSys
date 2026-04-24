# KabuSys

日本株向け自動売買システムのコアライブラリ群（リサーチ、ポートフォリオ構築、実行、監視、AI 補助機能など）。

このリポジトリはモジュール群（pure function なポートフォリオ計算、DuckDB ベースのファクター計算、OpenAI を利用したニュース NLP / レジーム判定、ExecutionEngine 起動スクリプト、監視エンジンなど）を提供します。

## 主な機能

- ポートフォリオ構築
  - 候補選定（スコア順）、等配分 / スコア加重配分
  - ポジションサイズ計算（risk-based / equal / score）
  - セクター上限適用、レジーム乗数算出
- リサーチ / ファクター計算（DuckDB）
  - Momentum / Volatility / Value ファクター算出
  - 将来リターン計算、IC 計算、統計サマリー
- AI 補助（OpenAI）
  - ニュース記事のセンチメント付与（ai_scores への書込み）
  - マクロニュース + ETF MA による市場レジーム判定（market_regime への書込み）
  - API 呼び出しはリトライ・検証を行い、フェイルセーフを考慮
- 実行（ExecutionEngine）起動スクリプト
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Paper Trading は本番 DB と分離して data/paper_trading.db に記録
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による ExecutionEngine 停止（Kill Switch）
  - 監視ログは SQLite（monitoring.db）へ永続化
- CLI 補助ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）
- ユーティリティ
  - 統一的なログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

## 要件

- Python 3.10 以上（PEP 604 の union 型表記を使用）
- 主要外部パッケージ（機能によって必要）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML をパースする場合に必要）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実際の依存関係はプロジェクトの配布形態（requirements.txt / pyproject.toml）に合わせてください。

## セットアップ手順（簡易）

1. 仮想環境を作成・有効化
2. 必要パッケージをインストール（上記参照）
3. .env を作成
   - 対話式で作成する: `python -m kabusys.config_setup`
   - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
4. 設定検証: `python -m kabusys.validate_config`
   - `--strict` を付けると警告も失敗扱いになります
5. データディレクトリなどを確認（デフォルトは project_root/data）

デフォルトの DB / ファイルパス:
- DuckDB: data/kabusys.duckdb
- SQLite (monitoring): data/monitoring.db
- SQLite (paper trading): data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill flag: data/kill.flag
- Stop flag（プロセス停止用）: data/stop_requested.flag

## 主な環境変数（抜粋・デフォルト）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: monitoring SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（default: INFO）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必要）
- PAPER_FILL_MODE: paper_trading の注文模擬モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default: 60）

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（本番 / ペーパーは KABUSYS_ENV で切替）
  ```
  # 本番・ローカル共通
  python -m kabusys.run_execution

  # ペーパートレードで起動する例
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - ペーパートレード時は MockBrokerClient が使われ、記録先は data/paper_trading.db（本番 DB と分離）

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで検知して終了

- Paper Trading 検証レポート（標準出力へ）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（プログラム内で呼び出す例）
  - ニュース NLP（score_news）
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 15), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定（score_regime）
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 4, 15), api_key="YOUR_OPENAI_KEY")
    ```

## 監視・安全機構について（概要）

- MonitoringEngine が SystemMonitor / TradeMonitor / RiskMonitor を定期実行し、異常を検出したら AlertManager に通知（LINE 等、設定に応じて実装）。
- KillSwitch はドローダウンやポジション上限超過が検出された場合に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る仕組み（ExecutionEngine は起動時に kill flag を確認・起動中は定期的にチェック）。
- MonitoringDB（SQLite）には system_status / trade_logs / positions / risk_logs / dashboard テーブルを持ち、初回接続時にスキーマを作成・マイグレーションを行います。

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / Settings 管理（.env 自動ロード機能あり）
- config_setup.py — .env 対話式ウィザード CLI
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（PID / stop flag 管理）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（リスク制御）
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書込む
  - regime_detector.py — マクロ記事 + ETF MA によるレジーム判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ定義・読み書きヘルパー
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - system_monitor.py — CPU / メモリ / ディスク / データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - (trade_monitor.py, alert_manager.py 等が存在する想定)
- utils/
  - logging_setup.py — 共通ログ設定（stdout + ローテートファイル）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- execution/, data/, ...（ExecutionEngine / ブローカー関連、データパイプライン等のモジュール群）

（注）この README はコードベースの主要部分に基づく要約です。各サブモジュールはさらに詳細なドキュメント（モジュール内 docstring）を参照してください。

## 開発上の注意点 / 推奨事項

- KABUSYS_ENV を `live` にする前に必ず validate_config を実行して設定を確認してください。`live` では一部のチェックが厳しくなります。
- .env は絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも記載）。
- OpenAI API を利用する機能は API キーの管理と呼び出しコストに注意してください。API 呼び出しはリトライ・レスポンス検証を行いますが、キーやレート制限上の例外ハンドリングを確認してください。
- Paper Trading 用 DB は本番 DB と分離されます（設定: KABUSYS_ENV=paper_trading）。テストや検証はペーパートレードモードで行うことを推奨します。

---

問題報告や改善提案がある場合はリポジトリの Issue に記載してください。