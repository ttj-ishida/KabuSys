# KabuSys

日本株向け自動売買 / 研究フレームワーク（軽量オーケストレーション + 分析コンポーネント）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを想定したコードベースです。  
主な責務は以下のとおりです。

- ExecutionEngine（発注エンジン）とその補助コンポーネント（オーダー管理、リスク管理、再突合等）
- Monitoring（システム稼働・注文・リスク監視）と Kill Switch
- ポートフォリオ構築 / ポジション決定用の純粋関数群（候補選定・重み計算・サイズ計算・リスク調整）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI 補助（ニュースの NLP スコアリング・市場レジーム判定。OpenAI を利用）
- 開発者向けツール（対話式 .env 作成 / 設定検証 / Paper Trading 検証レポート生成）
- ロギング・プロセス優先度設定などのユーティリティ

設計方針として、実運用におけるフェイルセーフ、ルックアヘッドバイアス回避（現在時刻参照の抑制）、および DB の分離（ペーパートレード用 DB と本番 DB）を意識しています。

---

## 主な機能一覧

- Execution
  - ブローカークライアント抽象化（本番 / モック切替）
  - OrderRepository / OrderManager / RiskManager / Reconciler 統合
  - デーモン的に実行し PID ファイルを管理
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / 実行プロセス生存監視
  - TradeMonitor：注文や約定ログの監視（滞留注文・異常約定など）
  - RiskMonitor：ドローダウン・ポジション上限の監視、ダッシュボード更新
  - KillSwitch：条件を満たした場合に data/kill.flag を書き込み ExecutionEngine に停止シグナルを送信
  - AlertManager（抽象化）経由で通知（LINE 等を想定）
- Portfolio（純粋関数）
  - 候補選定（スコア順）／等金額・スコア重み配分
  - セクター制限の適用
  - ポジションサイズ算出（リスクベース、等配分、スコア配分）
- Research
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
  - DuckDB を用いた高速分析
- AI（OpenAI）
  - ニュースを LLM でスコア化して ai_scores に保存
  - マクロニュース + ma200 を組み合わせた市場レジーム判定
  - API 呼び出しは堅牢な retry/バックオフ とレスポンス検証を実装
- 開発者ツール
  - config_setup: 対話式で .env を生成
  - validate_config: 起動前の設定チェック（--strict モードあり）
  - paper_verification_report: ペーパートレード DB の指標を集計してレポート出力

---

## 必要条件（概略）

- Python 3.10 以上（typing に `|` を使用）
- 推奨パッケージ（主要なもの）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の内容検証用）
- SQLite は標準ライブラリで利用
- ネットワーク接続（OpenAI / ブローカ API 等を利用する場合）

インストール例（venv 推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai
# optional: pip install pyyaml
```

（requirements.txt は本リポジトリに含まれていないため、必要に応じて上記パッケージをインストールしてください）

---

## 環境変数（主なもの）

`.env` を用いて設定することを想定しています。対話式で作成するには `python -m kabusys.config_setup` を使用してください。

主な環境変数（キー / 説明 / デフォルト）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading: Execution は MockBrokerClient を使い、paper DB に記録
  - live: 実運用（注意深く設定を確認）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト: INFO
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（1 で有効。live では危険）

その他: PAPER_FILL_MODE（instant/partial/never/reject）、MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）、KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env 読み込みを無効化）など。

Settings クラスに多くのデフォルト値・検証ロジックがありますので参照してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. 対話式で .env を作成
   ```bash
   python -m kabusys.config_setup
   ```
   もしくは `.env` を手動で用意（`.env.example` があれば参照）
5. 設定検証を実行
   ```bash
   python -m kabusys.validate_config
   # 警告も fail にしたい場合:
   python -m kabusys.validate_config --strict
   ```
6. DB の初期化・データ用ディレクトリを作成（必要に応じて）
   - monitoring/engine は内部で SQLite / DuckDB のファイルを必要に応じて作成します
   - `data/` ディレクトリが必要（stop/kill/ pid ファイルなど）

---

## 実行方法（主要エントリポイント）

すべてモジュールとして実行可能です（推奨）。

- 実行エンジン（ExecutionEngine）起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 起動時にプロセス優先度を `high` に設定します。
  - 停止は `data/stop_requested.flag` によるフラグ検知または Kill Switch による `data/kill.flag` によって制御されます。

- 監視（Monitoring）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は実行環境に関係なく本番 sqlite_path を使用して監視テーブルを初期化します。

- 対話式 .env ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-10
  ```
  - デフォルト DB は data/paper_trading.db、期間指定は任意

---

## 使い方（ワークフロー例）

1. .env を用意（config_setup を推奨）
2. validate_config で設定をチェック
3. (任意) 事前に DuckDB に株価データ / raw_financials / raw_news 等をロード
4. 実行エンジンを起動
   - paper_trading モードで動作を確認することを強く推奨
5. 別プロセスで monitoring を起動して監視（kill flag やアラート発動を確認）
6. AI 機能を使う場合は OPENAI_API_KEY を設定してから score_news / score_regime を呼び出す
7. ペーパートレードの結果確認は paper_verification_report を実行

停止（強制）:
- ExecutionEngine を停止させたい場合は monitoring の KillSwitch または手動で `data/kill.flag` を作成することで停止シグナルを送れます。  
  起動スクリプトは `data/stop_requested.flag` を検知すると自ら終了します。

---

## ディレクトリ構成（抜粋）

以下は主要なパッケージ構成です（ファイル名はコードベースから抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - execution/                   — 発注関連コンポーネント（Engine, OrderManager 等）
    - (OrderManager, ExecutionEngine, broker_factory, order_repository, risk_manager, reconciler など)
  - monitoring/
    - monitoring_db.py           — SQLite 永続層（テーブル作成・CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (抽象化)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

その他、data/（DB・フラグ・PID・ログ出力先）、logs/（ログファイル）を想定。

---

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では kill_flag や通知設定（LINE_TOKEN / LINE_USER_ID）を確実に整えてください。validate_config は live 用の注意点を警告します。
- AI 機能（news_nlp / regime_detector）は OpenAI API を使用します。API_KEY を適切に管理し、コスト・レートリミットに注意してください。ネットワーク障害時はフェイルセーフでスコアをフォールバックしますが、運用方針を決めてください。
- ペーパートレード（KABUSYS_ENV=paper_trading）では紙上での検証が可能です。本番 DB と完全分離するため必ずデフォルトの paper DB を確認してください。
- ログは logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリ作成に失敗するとコンソールのみになります。
- プロセス優先度・CPU affinity の設定は OS に依存します。権限不足で失敗する場合は警告で続行します。

---

## 開発 / 貢献

- コードはモジュール単位に分かれており、純粋関数（portfolio/*）と副作用を含むコンポーネント（execution/、monitoring/）が区別されています。ユニットテストは純粋関数に対して容易に書けます。
- 外部サービス（OpenAI、ブローカ API）呼び出し箇所はラップされており、テスト時にモック差し替えしやすい設計です（内部の `_call_openai_api` などはテスト用に patch 可能）。

---

README は以上です。追加で「利用可能なコマンド一覧を詳しく」「各環境変数のサンプル .env」を作成するなどが必要であれば、要求に応じて追記します。