# KabuSys

日本株向け自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、シグナル生成→ポジション構築→発注実行→監視・アラートまでを含む日本株自動売買の基盤コードです。設計はフェイルセーフを重視し、ペーパートレード機能・監視エンジン・AI を使ったニュース評価・研究用ファクター計算などを備えています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数 / 設定項目
- 停止・Kill スイッチについて
- ディレクトリ構成（主要ファイル一覧）
- 注意事項

---

プロジェクト概要
- 株式自動売買システムのコアライブラリと、運用用の起動スクリプト群を収めた Python パッケージ `kabusys`。
- データ永続化に SQLite（監視用 / ペーパートレード用）と DuckDB（研究・分析用）を使用。
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）を環境変数で切り替え可能。
- OpenAI を利用したニュース NLP（センチメント）や、レジーム判定機能を備える（API キー必須）。

主な機能
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、本番 DB と分離して `data/paper_trading.db` に記録。
  - プロセス優先度の設定、PID ファイル作成、停止フラグ対応。
- Monitoring ポーリング（run_monitoring.py）
  - システム状態・注文状況・リスクを定期監視し、監視ログを SQLite に永続化。
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）。
- MonitoringDB（monitoring/monitoring_db.py）
  - system_status、trade_logs、positions、risk_logs、dashboard 等のテーブル定義と読み書きユーティリティ。
- Kill Switch（monitoring/kill_switch.py）
  - ドローダウンやポジション上限を検知して `data/kill.flag` を書き込み、ExecutionEngine に停止指示を出す。
- RiskMonitor / TradeMonitor / SystemMonitor（monitoring/*.py）
  - ドローダウン監視、滞留注文・約定異常検出、データ鮮度監視などのロジック。
- Portfolio（portfolio/*）
  - 候補選定、重み計算、セクター制約適用、ポジションサイズ計算（lot 単位丸めなど）。
- Research（research/*）
  - DuckDB を使ったファクター計算（Momentum, Volatility, Value）や将来リターン、IC 計算など。
- AI モジュール（ai/*）
  - news_nlp: OpenAI でニュース記事を銘柄別にセンチメント評価して ai_scores に格納。
  - regime_detector: ETF（1321）などの MA 指標とマクロセンチメントを合成して市場レジーム判定。
- ユーティリティ
  - ロギング設定（utils/logging_setup.py）：stdout と日次ローテートファイル出力（logs/<app>.log）。
  - プロセス優先度・CPU affinity 設定（utils/process_priority.py）。
- CLI ツール
  - 環境設定ウィザード（config_setup.py）: .env の対話的生成・更新。
  - 設定検証（validate_config.py）: 必須環境変数・config/*.yaml・パス等をチェック。
  - Paper Trading 検証レポート（tools/paper_verification_report.py）: ペーパートレード DB から各種指標を集計して評価。

---

セットアップ手順（開発者向け）
1. Python バージョン
   - Python 3.10+ を推奨（typing の一部機能を使用）。

2. 必要なパッケージ（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config ファイル検証を行う場合）
   - その他（requirements.txt があればそれを使用）

   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

3. プロジェクトルート
   - リポジトリをクローンして、プロジェクトルートに移動します（.git または pyproject.toml を基準に自動で .env を読み込みます）。

4. .env の作成
   - 対話的に作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参照して手動作成。

5. 設定検証
   - 自動ロード後、設定を検証:
     ```
     python -m kabusys.validate_config
     ```
   - 警告を厳密に扱う場合は `--strict` を付ける。

6. データディレクトリ
   - デフォルトの DB / フラグ / PID ファイルは `data/` に配置されます。必要に応じて .env で上書きしてください。
   - ログは `logs/` に出力されます（LOG_DIR で変更可）。

---

使い方（代表的なコマンド）
- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - アプリケーションは KABUSYS_ENV を参照します。`paper_trading` では MockBrokerClient を使用し、データは paper_trading 用 DB に分離します。
  - PID ファイル: デフォルト `data/execution.pid`（Settings.pid_file_path / .env で変更可）。
  - 停止フラグ: `data/stop_requested.flag` / `data/kill.flag` をチェックします。

- 監視ループ起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を秒で上書き（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを書きます。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は `PAPER_TRADING_SQLITE_PATH` 環境変数、もしくは `--db` オプションで指定可能。

- AI 機能（ニューススコアリング / レジーム判定）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定してください。
  - 例: news scoring を呼び出すライブラリ関数を利用して、DuckDB 接続と target_date を渡します。
  - CLI ラッパーは実装されていないため、スクリプトやジョブから関数を呼び出して利用してください。

---

主要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API リフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（Settings 経由で参照）

補足:
- 自動 .env ロードはデフォルトで有効。無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- .env.local は .env より優先して上書きされます（OS 環境変数は常に最優先で保護）。

---

停止方法 / Kill スイッチ
- 実行中の ExecutionEngine や監視ループは、プロジェクトの `data/` 配下にあるフラグファイルで制御します:
  - data/stop_requested.flag: run_execution / run_monitoring のループ停止検出用（外部で作成すると安全に停止）
  - data/kill.flag: KillSwitch が書き込む（リスク閾値超過時）。ExecutionEngine 起動時にクリアする設定があるため注意。
- KillSwitch は監視モジュール（RiskMonitor 等）の評価結果に基づき `data/kill.flag` を作成します。存在すると ExecutionEngine は停止されます（起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定していると自動クリアされるので本番では `0` 推奨）。

---

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロード、Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 / DB ラッパー
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - system_monitor.py      — CPU/メモリ/ディスク・データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書込ユーティリティ
    - trade_monitor.py       — （注文状態監視など）※実装あり
    - alert_manager.py       — 通知（LINE など）※実装あり
  - execution/
    - execution_engine.py    — 発注エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算 / 上限・スケール調整
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等の計算
    - feature_exploration.py — 将来リターン・IC・統計解析
  - ai/
    - news_nlp.py            — ニュースの LLM センチメント評価
    - regime_detector.py     — マクロ + MA ベースのレジーム判定

（上記は主要なファイルのみ。詳細はソースを参照してください）

---

注意事項 / 運用上のポイント
- 本番環境（KABUSYS_ENV=live）では設定やトークン管理に十分注意してください。validate_config の警告をよく確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- OpenAI API を利用する機能はネットワーク遅延や API レート制限に依存します。失敗時はフェイルセーフ（スコア 0.0 等）で処理する設計ですが、API キーの漏洩やコストに注意してください。
- DuckDB / SQLite ファイルはデフォルトで `data/` に保存されます。バックアップやアクセス制御を検討してください。
- run_execution と run_monitoring はそれぞれ PID / stop flag を使って停止・管理されるため、運用時は外部監視（systemd / supervisor / cron 等）でプロセス監視を行うことを推奨します。

---

サポート
- この README はソースコードのコメントと関数ドキュメントに基づいて作成しています。詳細な実装・拡張は各モジュールの docstring を参照してください。質問があればソースの具体的な箇所を指定して問い合わせてください。