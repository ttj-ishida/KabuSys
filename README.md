# KabuSys

日本株向けの自動売買 / 研究用ライブラリ兼実行エンジン群。  
このリポジトリには環境設定ウィザード、設定検証、監視・リスク管理、ポートフォリオ構築、リサーチ機能、AI ベースのニュース・レジーム判定、ペーパートレードの検証レポート等のユーティリティと起動スクリプトが含まれます。

主にローカル開発・ペーパートレード・本番（live）を想定した実行フローを提供します。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存ライブラリ
- セットアップ手順
- 環境変数（主要）
- 使い方（コマンド / API）
- 停止・フラグ・PID の取り扱い
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株の自動売買システムと研究ツールを併せ持つコードベースです。  
設計方針として以下を重視しています。

- 本番・ペーパートレードの分離（DB を分けて運用）
- ルックアヘッドバイアスを避ける（日時参照の設計）
- フェイルセーフ（外部 API 失敗時は安全側にフォールバック）
- モジュール化された監視・アラート・Kill Switch 機構

---

## 機能一覧

- 環境設定ウィザード（.env 自動生成）
- 設定検証 CLI（.env / config/*.yaml 検証）
- ExecutionEngine 起動スクリプト（実際の発注ロジック起動）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、専用の paper_trading DB を使用
- Monitoring（System / Trade / Risk）および MonitoringEngine（ポーリング）
  - system 状態、データ鮮度、滞留注文、約定異常、ドローダウン監視
  - Kill Switch による ExecutionEngine 停止シグナル発行
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、ポジションサイズ計算）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール
  - ニュース NLP（OpenAI を使ったニュースセンチメント → ai_scores へ書き込み）
  - レジーム検出（ETF MA とマクロニュースを統合して market_regime を算出）
- ペーパートレード検証レポート生成スクリプト（稼働率・成功率・レイテンシ等）

---

## 前提条件 / 依存ライブラリ

主な依存（実行に必要／推奨）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能使用時)
- PyYAML（設定 YAML 検証を行う場合に推奨）

pip での例:
```bash
pip install duckdb psutil openai pyyaml
```

※ テストや開発時は追加の dev 依存がある場合があります。

---

## セットアップ手順

1. リポジトリをクローンして Python 環境を用意する
2. 依存ライブラリをインストールする（上記参照）
3. .env を作成する（対話式ウィザード推奨）

.env の生成（対話式）:
```bash
python -m kabusys.config_setup
```
ウィザードは .env を作成または更新します。生成後、設定検証を実行してください。

設定検証:
```bash
python -m kabusys.validate_config
# 警告もFAIL扱いにする場合
python -m kabusys.validate_config --strict
```

---

## 主要な環境変数（サンプル・説明）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API のパスワード

主なオプション（デフォルト値含む）:
- KABUSYS_ENV (development | paper_trading | live) — 実行環境（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（INFO 等）
- PID_FILE_PATH — ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch の flag 保存先（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効化（テスト用）

デフォルトの多くは .env ウィザードや README の .env.example を参照してください。

---

## 使い方（コマンド）

主要なエントリポイント・スクリプト

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（発注エンジン）
  - 本番 / 開発 / ペーパートレードの挙動は KABUSYS_ENV に依存します。
  - ペーパートレード時は paper_trading 用 DB を使用し MockBroker を使用します。
  ```bash
  python -m kabusys.run_execution
  ```
  実行中に停止させたい場合は data/stop_requested.flag を作るか kill.flag を作成してください（設定により挙動が変わります）。

- Monitoring 起動（SystemMonitor の単体起動スクリプト）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
  ```bash
  python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- ライブラリとしての利用例（コードから呼ぶ）
  - AI ニューススコア生成:
    ```python
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date, api_key="sk-...")
    ```
  - レジームスコア算出:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```
  - 研究モジュール例:
    ```python
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    result = calc_momentum(conn, date.today())
    ```
  - ポートフォリオ計算:
    ```python
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
    ```

---

## 停止・フラグ・PID の取り扱い

- stop_requested.flag（data/stop_requested.flag）
  - 起動スクリプト（run_execution/run_monitoring）がこのファイルを検知するとループを終了します。
  - ファイルはプロジェクトルートの data ディレクトリ下に置かれます。

- kill.flag（デフォルト: data/kill.flag）
  - KillSwitch が有効条件を検出したとき（ドローダウン超過など）に作成されます。ExecutionEngine はこれを検知して停止します。
  - KillSwitch は既存の flag がある場合は上書きしません（冪等）。

- PID ファイル（例: data/execution.pid）
  - ExecutionEngine 起動時に PID を書き込みます。SystemMonitor は PID ファイルの有無・残存確認によりプロセスの健全性を監視します。

- 注意:
  - 設定によっては ExecutionEngine の起動時に kill.flag を自動クリアする挙動を許す設定（KILL_FLAG_CLEAR_ON_START）があります。本番ではクリアしないことを推奨します。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- __init__.py
  - パッケージのメタ情報（バージョンなど）

- config.py
  - 環境変数 / .env の自動読み込み、Settings クラス（アプリ設定の中央管理）

- config_setup.py
  - .env を対話式で作成するウィザード

- validate_config.py
  - 設定ファイル／環境の検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番/ペーパー切替対応）

- run_monitoring.py
  - SystemMonitor 単体のポーリング起動スクリプト（MONITOR_POLL_INTERVAL 使用可）

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores テーブルへ書き込む
  - regime_detector.py — 市場レジーム判定（MA + マクロニュース）

- monitoring/
  - monitoring_db.py — SQLite のスキーマと永続化用ラッパー（MonitoringDB）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 滞留注文・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — 条件に応じて kill.flag を書き込む
  - monitoring_engine.py — 上記 Monitor を束ねた運用用エンジン
  - alert_manager.py — アラート送信管理（LINE 等の通知はここに実装）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・資金配分ロジック
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
  - __init__.py — 便利関数のエクスポート（zscore 等）

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 運用上の注意

- DB の分離:
  - 監視用の SQLite（monitoring.db）とペーパートレード用 DB（paper_trading.db）は分離されています。KABUSYS_ENV=paper_trading のとき run_execution は paper_trading DB を使用します。
- AI 機能（OpenAI）:
  - OPENAI_API_KEY が必須。リクエスト失敗時はフェイルセーフで継続しますが、スコア取得は行えません。
- .env は絶対にバージョン管理（Git）にコミットしないでください。
- 本番（KABUSYS_ENV=live）では設定（LINE 通知、KILL フラグ設定等）を慎重に確認してください。validate_config にて live ガードが入ります。

---

README は以上です。必要であれば以下の追加情報を作成できます:
- 詳しい .env.example（全キー一覧と説明）
- systemd / Supervisor 用のユニットファイル（起動とログ管理）
- サンプル DB スキーマ / ダミーデータ作成スクリプト
- 各モジュールの API 使用例（ノートブック形式）