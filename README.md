# KabuSys

日本株自動売買システムのサブセット実装。ポートフォリオ構築、注文発行（ExecutionEngine）、監視（Monitoring）、リサーチ／ファクター計算、AI ベースのニュース解析などの機能を持つモジュール群で構成されています。

以下はこのリポジトリの README.md（日本語）です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主な目的は以下です。

- 売買シグナルに基づくポートフォリオ構築と発注（ExecutionEngine）
- 実行系の監視・アラート・Kill Switch（Monitoring）
- DuckDB を用いたファクター計算・リサーチ（research）
- OpenAI を使ったニュースの NLP スコアリングと市場レジーム判定（ai）
- ペーパートレード用の分離された DB を使った検証
- 運用に便利な CLI ツール（設定ウィザード、設定検証、検証レポート等）

コア設計方針の例:
- 本番データとペーパートレード DB を分離
- ルックアヘッドバイアスを避ける（date.today() など直接参照しない実装）
- API 呼び出し失敗はフェイルセーフで扱い、システム全体を落とさない

---

## 主な機能一覧

- 設定管理
  - .env の読み込みと対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行系（Execution）
  - ExecutionEngine（発注/注文管理/リスク管理/注文リコンシリエーション）
  - Broker クライアント工場（本番/Mock の分離。KABUSYS_ENV=paper_trading をサポート）
- 監視（Monitoring）
  - SystemMonitor（CPU/メモリ/ディスク/データ鮮度/プロセス生存確認）
  - TradeMonitor（滞留注文 / 約定異常の検出）
  - RiskMonitor（ドローダウン / ポジション上限の監視）
  - KillSwitch（条件に応じて data/kill.flag を書き込み ExecutionEngine を停止）
  - MonitoringEngine（各モニタの統合と定期実行）
- ポートフォリオ構築
  - 候補選定、重み付け（等金額 / スコア加重）、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）
  - ニュース記事のセンチメントスコアリング（ai.news_nlp.score_news）
  - マクロニュース＋ETF MA による市場レジーム判定（ai.regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提:
- Python 3.9+（ソース上は型注釈に 3.10 的な記法を含みますが、一般的に 3.9+ を想定）
- SQLite（組み込み）、DuckDB、psutil、openai などの Python パッケージ

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージのインストール（代表例）
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - PyYAML は設定ファイル検証（validate_config）で任意に使われます。なくても動作しますが検証機能が制限されます。

3. data ディレクトリ作成（デフォルト DB パス用）
   ```
   mkdir -p data
   ```

4. 環境変数設定
   - 対話式ウィザードで `.env` を生成できます（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - または `.env` を手動作成してください。.env の自動読み込みはプロジェクトルート検出（.git / pyproject.toml）に基づき行われます。自動ロードを無効にするには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告もエラー扱いにする
   ```

---

## 主要な環境変数（重要項目・デフォルト）

必須（少なくとも設定が必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用関連（デフォルト値を示す）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）. デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite（monitoring）DB。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite。デフォルト: data/paper_trading.db
- PAPER_FILL_MODE — ペーパートレード時の約定モード。デフォルト: "instant"（instant|partial|never|reject）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / score_regime 用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）。デフォルト: 60
- PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch が書き込むフラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" 有効）。本番では 0 推奨。

.env のロード順序:
- OS 環境変数 > .env.local > .env（但し OS 環境変数は保護され上書きされない）

---

## 使い方（よく使うコマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine（自動売買エンジン）起動
  - 通常:
    ```
    python -m kabusys.run_execution
    ```
  - 注意点:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
    - 実行中は data/execution.pid に PID を書きます。run_execution は stop_requested.flag の検知または Kill Switch /手動で停止できます。

- Monitoring（監視）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（秒、デフォルト 60）。
  - 監視は環境にかかわらず本番の sqlite_path を使用します（監視ログは共有 DB に保存される想定）。
  - 停止には data/stop_requested.flag を作成するか、Ctrl+C。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。`--db` で別パス指定可。

- AI モジュールをプログラムから利用
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を使用

---

## 停止・Kill Switch の仕組み

- stop_requested.flag
  - run_execution および run_monitoring のトップレベルスクリプトは `data/stop_requested.flag` の存在を定期的にチェックし、検知したら安全に終了します。
  - 運用上の「人為的な停止要求」を行うにはこのファイルを作成します。

- kill.flag（Kill Switch）
  - KillSwitch（監視コンポーネント）は条件（例: ドローダウン超過、ポジション上限超過）を満たすと `data/kill.flag` に理由を記述して書き込みます。
  - ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` の設定に応じてこのフラグをクリアできますが、本番では自動クリアを無効にすることを推奨します。
  - kill.flag が書かれると ExecutionEngine は停止するよう設計されています（監視ループ経由で検出して停止）。

---

## ディレクトリ構成（主なファイルと概要）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数／Settings 管理（.env 自動ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート CLI
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py — 市場レジーム判定（ETF MA + LLM）
  - monitoring/
    - monitoring_db.py — SQLite 監視ログラッパー（永続化層）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — Kill Switch 制御
    - monitoring_engine.py — モニタ群の統合・ループ
    - alert_manager.py — （アラート送信ロジック: 未表示 ／ 実装参照）
  - execution/ (発注・注文管理関連、主要クラス)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py など
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・投下キャップ/丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計機能
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他:
- data/ — デフォルトで DB やフラグファイルを置く場所（実運用ではバックアップ/マウント等を検討）
  - data/monitoring.db（デフォルト）
  - data/paper_trading.db（ペーパートレード）
  - data/kabusys.duckdb（DuckDB）
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

※ 実際のリポジトリでは `config/` ディレクトリ（各種 YAML 設定）なども存在します。

---

## 運用上の注意

- KABUSYS_ENV を `live` に設定すると本番モードになります。LINE 通知設定や kill flag の設定など本番固有の注意（validate_config の警告参照）を必ず確認してください。
- OpenAI を利用する機能は API 呼び出し（課金）が発生します。API キーと利用ポリシーを確認してください。
- ペーパートレードは本番 DB と完全分離していますが、設定ミスによる本番資金操作を避けるため `.env` の管理には十分注意してください。
- プロセス優先度や CPU affinity の設定は OS によって動作が異なり、権限不足で失敗する場合があります（警告ログが出ます）。
- DuckDB / SQLite ファイルは運用環境でのサイズ・I/O を監視し、バックアップや VACUUM 等を検討してください。

---

## 開発／拡張メモ

- テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env 自動ロードを無効にできます。
- AI 呼び出し（OpenAI）は内部でリトライ処理・レスポンス検証を行いますが、ユニットテスト時には `_call_openai_api` をモック化することを想定しています。
- DuckDB によるリサーチ系関数は副作用を持たない純粋関数群（データ参照のみ、挿入無し）として設計されています。

---

README の補足や特定機能（例: ExecutionEngine の詳細な起動オプション、AlertManager の設定方法、broker の実装など）について追記を希望される場合は、どの項目を詳しくしたいか教えてください。