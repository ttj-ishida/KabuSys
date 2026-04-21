# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ + 起動スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコア部分を切り出したコードベースです。  
主な役割は以下の通りです。

- 資産配分・ポジションサイズ計算（ポートフォリオ構築）
- 取引実行エンジン（ExecutionEngine）および発注管理
- 監視（System / Trade / Risk モニタリング）と Kill Switch
- 研究用モジュール（ファクター計算・特徴量探索）
- AI 補助（ニュース NLP によるセンチメント / レジーム判定）
- 各種 CLI ツール（.env ウィザード・設定検証・ペーパートレード検証レポート 等）

設計方針としては、DB（DuckDB / SQLite）を活用する分析／履歴管理、LLM（OpenAI）を利用した補助機能、そして本番／ペーパートレードを分離する運用が考慮されています。

---

## 主な機能一覧

- 環境設定ウィザード（config_setup）による .env 生成
- 設定検証 CLI（validate_config）
- ExecutionEngine の起動スクリプト（run_execution.py）
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、ペーパートレード用 DB に記録
- Monitoring（run_monitoring.py）
  - システム指標・データ鮮度・取引ログ・リスク（ドローダウン・ポジション数）をポーリング
  - Kill Switch（条件により data/kill.flag を作成して ExecutionEngine に停止シグナル）
- ポートフォリオ構築ユーティリティ
  - 候補選定、重みづけ（等金額 / スコア加重）、ポジションサイズ計算、セクター上限・レジーム補正
- 研究モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC 計算
- AI モジュール
  - ニュース記事の LLM によるセンチメント集計（ai.news_nlp）
  - マクロ + ETF MA を用いた市場レジーム判定（ai.regime_detector）
- ツール
  - ペーパートレードの検証レポート生成（tools/paper_verification_report.py）
- ユーティリティ
  - 統一的なログ設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）

---

## 動作要件（推奨）

- Python 3.10+
- 必須（主に利用するライブラリ）
  - duckdb
  - psutil
  - openai
- 任意（設定検証で YAML を検証する場合）
  - PyYAML

（プロジェクトに requirements.txt がない場合は上記を pip で個別にインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動します。

2. 仮想環境を作成して依存ライブラリをインストールします（上記参照）。

3. .env を作成（推奨: ウィザードを使用）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは対話形式で .env を生成します（デフォルトはプロジェクトルートの .env）。

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   問題がある場合はメッセージに従って .env や config/*.yaml を修正してください。`--strict` をつけると警告も失敗扱いになります。

5. 必要ディレクトリの確認（ログ・データ）
   - デフォルト:
     - data/（SQLite / PID / flag 等）
     - logs/（ログファイル）
   これらは起動時に自動作成されますが、権限等に注意してください。

6. OpenAI を使用する場合
   - 環境変数 `OPENAI_API_KEY` を .env に設定してください（AI モジュールを使うときのみ必須）。

7. 必須環境変数
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

---

## 使い方（主要スクリプト）

- ExecutionEngine（取引エンジン）起動
  ```
  # 本番/開発/ペーパーは KABUSYS_ENV で制御（.env で設定）
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、データは data/paper_trading.db（デフォルト）に記録され、本番 DB と分離されます。
  - 停止フラグ: data/stop_requested.flag が存在すると起動を抑止／実行中は停止します。
  - 実行中は PID ファイル（data/execution.pid や .env の PID_FILE_PATH）を作成します。

- Monitoring（監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒単位に上書き可能（デフォルト 60 秒）。
  - 監視は環境に関わらず本番 sqlite_path（.env の SQLITE_PATH）を使用してログを残します。
  - 停止フラグ: run_monitoring は data/stop_requested.flag を監視してループを終了します。

- Kill Switch
  - Kill Switch は監視の結果に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - Kill Flag のパスは Settings.kill_flag_path（.env の KILL_FLAG_PATH）で制御可能。
  - `.env` の `KILL_FLAG_CLEAR_ON_START=1` にすると ExecutionEngine 起動時に kill.flag を自動クリアします（本番では推奨しません）。

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  - 簡易的な PASS/FAIL 判定と指標（稼働率、成功率、送信率、P95 レイテンシ等）を出力します。
  - DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または引数 `--db` で指定できます。

- AI モジュール（プログラム的に使用）
  - ニュース NLP（スコア書き込み）
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=None)
  - レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=None)
  - いずれも `OPENAI_API_KEY` を環境変数、または関数引数 `api_key` にて指定します。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- LOG_LEVEL / LOG_DIR: ログ出力設定

---

## 注意事項 / 運用メモ

- run_monitoring は監視用 DB に対して本番 sqlite_path を使用します。監視ログは本番と同一 DB に残る点に注意してください。
- run_execution は `KABUSYS_ENV=paper_trading` の場合に限り paper_sqlite_path を使って本番 DB と切り離します。
- Kill Switch による停止はファイルフラグ方式（data/kill.flag）です。ファイル存在チェックと削除は環境に応じて扱ってください。
- ログはデフォルトで logs/ に出力され、日次ローテーション（30日分）で保持されます。ログディレクトリが作成できない場合、ファイル出力は無効化されコンソール出力のみになります。
- OpenAI API 呼び出しは外部ネットワーク依存です。レート制限や一時的なエラー発生時のリトライ実装がありますが、運用時は鍵や利用上限に注意してください。

---

## ディレクトリ構成（抜粋）

（ルートは src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数読み込み・自動 .env ロード）
  - config_setup.py
    - .env を対話式で作成するウィザード
  - validate_config.py
    - .env / config/*.yaml の静的チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — ログの統一設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py     — システム健全性・データ鮮度チェック
    - trade_monitor.py      — 取引ログの監視（滞留注文・約定異常 等）※実装ファイルは存在
    - risk_monitor.py       — ドローダウン・ポジション数監視
    - kill_switch.py        — Kill Switch（flag の書き込み）
    - monitoring_engine.py  — 各 Monitor を束ねる実行ループ
    - alert_manager.py      — アラート送信（LINE 等のラッパー）※実装ファイルは存在
  - execution/
    - execution_engine.py   — ExecutionEngine（注文発行ループ等）※実装ファイルは存在
    - broker_factory.py     — ブローカークライアントの生成（Mock 含む）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み計算
    - position_sizing.py    — 発注株数計算・スケールダウンロジック
    - risk_adjustment.py    — セクター上限・レジーム乗数
  - research/
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py           — ニュース記事の LLM ベースセンチメント
    - regime_detector.py    — 市場レジーム判定（ETF MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

---

## 開発・拡張に関する備考

- DuckDB は分析向けの永続化層として使用します。research / ai モジュールは DuckDB 接続を受け取り SQL を実行する設計です。
- モジュールは外部 API（kabuステーション / J-Quants / OpenAI）へのアクセス部分をファクトリやクライアントで分離しているため、テスト時はモックで差し替えやすく設計されています。
- 設計コメントや TODO がコード中に含まれているため、機能追加や挙動変更の設計方針をコードから追いやすくなっています。

---

もし README に追記してほしい具体的な内容（例: 実際の .env サンプル、使える CLI 引数一覧、実行時のログ例、ユニットテスト実行方法など）があれば教えてください。必要に応じて追加します。