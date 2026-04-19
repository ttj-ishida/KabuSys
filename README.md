# KabuSys

日本株の自動売買システムのリポジトリ（軽量なオンプレ／ローカル実行向け）。  
本リポジトリは取引実行（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・リサーチ（DuckDB を利用）・AI を使ったニュースセンチメント評価などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような責務を持つモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）: ブローカークライアント経由で発注を行う（本番/ペーパートレード対応）。
- 監視（Monitoring）: システム状態・注文状況・リスク（ドローダウン・ポジション上限）を定期チェックし、必要に応じて Kill Switch を発動。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制限など。
- リサーチ: DuckDB 上でファクター計算・特徴量探索・Forward Returns / IC 計算。
- AI モジュール: OpenAI を用いたニュースのセンチメント評価（ai.news_nlp）と市場レジーム判定（ai.regime_detector）。
- ユーティリティ: ログ設定、プロセス優先度/CPU affinity 設定、.env 読み込みウィザード / 構成検証 CLI、ツール類（検証レポート生成）。

設計上のポイント:
- 本番環境／ペーパートレード用 DB を分離（ペーパートレードは data/paper_trading.db を使用）。
- .env ファイルを優先して読み込み、Settings クラスで環境変数をラップ。
- OpenAI 呼び出しはリトライやバリデーションを備えた安全な実装。
- 監視は SQLite（monitoring.db）にログを残し、DuckDB は解析／リサーチ用に利用。

---

## 主な機能一覧

- 実行
  - ExecutionEngine（本番は kabuステーション、paper_trading は MockBrokerClient）
  - RiskManager（ポジション／利用率／ドローダウン等の制約）
  - OrderManager / Reconciler

- 監視
  - SystemMonitor（CPU/Memory/Disk、データ鮮度、プロセス PID チェック）
  - TradeMonitor（滞留注文・約定異常チェック）
  - RiskMonitor（ドローダウン・ポジション上限検知）
  - KillSwitch（条件を満たしたら data/kill.flag を作成して停止シグナル）
  - MonitoringEngine（各 Monitor を束ねてポーリング、AlertManager 経由で通知）

- ポートフォリオ構築（純関数群）
  - 候補選定、等配分／スコア配分、リスクベースサイズ算出、セクターキャップ、レジーム乗数

- リサーチ（DuckDB）
  - モメンタム・ボラティリティ・バリュー計算、将来リターン、IC 計算、統計サマリ

- AI（OpenAI）
  - ニュース NLP（銘柄別センチメントを ai_scores に保存）
  - レジーム検出（ETF 1321 の MA200 とマクロニュースを合成）

- ツール
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）

---

## 動作環境／前提

- Python 3.10 以上（typing 演算子 `|` を使用）
- 推奨パッケージ（抜粋）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証用、なくても動作）
- SQLite3（Python 標準ライブラリに含まれる）
- ネットワークアクセス（kabuステーション（本番）、OpenAI API は任意の機能で必要）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb psutil openai PyYAML
   ```
   実行に不要なパッケージ（例えば OpenAI）は AI 機能を使う場合のみ必須です。

4. 環境変数設定（.env を作成）
   - 対話式ウィザードで生成:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは `.env` を手動作成。主な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（instant/partial/never/reject、デフォルト: instant）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, KILL_FLAG_CLEAR_ON_START など

5. 設定検証（起動前に実行推奨）
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data logs
   ```

---

## 使い方（主要コマンド）

- 実行エンジンを起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV で切替
  - ペーパートレード時は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録
  ```bash
  python -m kabusys.run_execution
  ```

  挙動:
  - 起動時にプロセス優先度を high に設定（可能な場合）
  - ペーパートレード時は専用 SQLite を使用（実運用 DB と分離）
  - data/stop_requested.flag が存在すると起動しない、起動中に存在すると停止要求を検出して停止

- 監視ループを起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を変更可（デフォルト 60）。
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使う設計（環境にかかわらず）。
  - 監視は SystemMonitor.check_once() などを定期実行し、SQLite にログを残します。

- Paper Trading 検証レポートを生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- .env ウィザード（初期設定）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- AI 機能（プログラムから呼び出す）
  - ニューススコア登録:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（OPENAI_API_KEY）を要求します。

---

## 停止と Kill Switch

- 強制停止シグナル:
  - data/stop_requested.flag: run_execution / run_monitoring が参照する停止フラグ（スクリプト側で検出して終了）。
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine 停止を促す（実行中エンジンは起動時に clear する設定あり）。
- 実運用では KILL_FLAG_CLEAR_ON_START を慎重に扱ってください（本番では 0 を推奨）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env の読み込みと Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前のコンフィグ検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト

  - utils/
    - logging_setup.py — ログ設定ユーティリティ（console + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（テーブル作成・CRUD）
    - system_monitor.py — CPU/Memory/Disk・データ鮮度・PID チェック
    - trade_monitor.py — （注文ログ・滞留注文等のチェック）※実装ファイルあり
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - kill_switch.py — フラグファイルを書いて停止シグナル送信
    - monitoring_engine.py — 各 Monitor を束ねる

  - execution/ （発注周り: broker_factory, execution_engine, order_manager, order_repository, risk_manager など）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — DuckDB を使ったファクター・解析
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + MA200）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート
  - data/（デフォルトのデータ・ログ格納場所）
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード用デフォルト）
  - logs/（ログ出力先、デフォルト）

（上は主要ファイルの抜粋です。実際のツリーはリポジトリを参照してください。）

---

## 主な設定項目（要点）

- KABUSYS_ENV
  - development（開発、発注なし）
  - paper_trading（ペーパートレード、MockBrokerClient、専用 DB）
  - live（本番）

- DB 関連
  - DUCKDB_PATH: DuckDB（解析）ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

- AI / OpenAI
  - OPENAI_API_KEY が必要（ai.news_nlp / ai.regime_detector を使う場合）

- 監視
  - MONITOR_POLL_INTERVAL（秒、デフォルト 60）

- PAPER_FILL_MODE
  - ペーパートレード時の約定挙動（instant / partial / never / reject）

---

## 運用上の注意

- .env は絶対にリポジトリにコミットしないこと（シークレット情報を含む）。
- 本番（KABUSYS_ENV=live）では kill flag の自動クリアを有効にしない（KILL_FLAG_CLEAR_ON_START=0 を推奨）。
- OpenAI の呼び出しではレート制限や失敗を想定したリトライ／フェイルセーフ実装がありますが、APIキーの取り扱い・費用に注意してください。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります（setup_logging の挙動）。

---

## 開発メモ / 拡張ポイント

- position sizing の lot_size は今後銘柄別対応に拡張可能（stocks マスタの導入）。
- news_nlp / regime_detector は OpenAI SDK の変更に伴う互換性注意（返却形式・例外挙動）。
- DuckDB のバージョン依存の制約（executemany の空配列等）に注意している実装が各所にあります。

---

この README はコードベースから抽出できる主要情報に基づいて作成しています。実際の運用前に `python -m kabusys.validate_config` による検証と、.env の適切な設定を必ず行ってください。質問や追加のドキュメント（API 呼び出し例、システムアーキテクチャ図など）が必要であれば教えてください。