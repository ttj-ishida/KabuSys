# KabuSys

日本株自動売買システムのコアライブラリ。バックテスト/リサーチ・ポートフォリオ構築・発注エンジン・監視・AI 支援（ニュース NLP / レジーム判定）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

このリポジトリは KabuSys 本体の Python 実装です。主な目的は以下：

- 銘柄選定・配分・株数決定などのポートフォリオ構築ロジック
- 発注・リスク管理を行う ExecutionEngine（実運用 / ペーパートレード分離）
- システム稼働・注文状態・リスク指標の監視（Monitoring）
- ニュースを LLM でスコア化する AI モジュール（OpenAI）
- 研究用ファクター計算・特徴量解析（DuckDB を利用）
- .env の対話式セットアップ / 設定検証 / 各種ユーティリティ

設計方針として「本番 DB・発注 API に対する意図しないアクセスを防ぐ」「ルックアヘッドバイアスを排除する」「フェイルセーフ（API 失敗時に例外伝播させず継続）」が組み込まれています。

---

## 主な機能

- ExecutionEngine（発注/注文管理/リスク管理/再整合）
  - KABUSYS_ENV=`paper_trading` 時は MockBrokerClient を用い、paper DB に記録
  - プロセス優先度設定、PID 管理、停止フラグ対応
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
  - system_status / trade_logs / risk_logs / dashboard テーブルを持つ SQLite ベースの監視
  - Kill Switch（条件満たせば data/kill.flag に書き込み）
- ポートフォリオ構築（候補選定・重み付け・サイズ決定・セクター制限）
- 研究モジュール（ファクター計算・将来リターン・IC 計算・統計サマリー）
- AI モジュール
  - ニュースの銘柄別センチメント付与（OpenAI）
  - マクロ記事 + ETF MA200 を使った市場レジーム判定（OpenAI）
- ユーティリティ
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - ログ設定ユーティリティ（統一的な Stream + ローテートファイル）
  - process priority / cpu affinity ユーティリティ
- ツール
  - ペートレ検証レポート生成（kabusys.tools.paper_verification_report）

---

## 動作要件（目安）

- Python 3.9+
- 推奨依存（requirements.txt がある場合はそちらを使用してください）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合に必要）
- SQLite（組み込み）、ログ用に書き込み可能なディレクトリ

（実際のプロダクション運用では OS に依存する設定や broker client の準備が必要です）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は少なくとも duckdb, psutil, openai をインストールしてください
     - pip install duckdb psutil openai
   - PyYAML は設定ファイル検証で必要：pip install PyYAML
4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワード、KABUSYS_ENV 等を入力
5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗にできます
6. 必要なディレクトリ（data, logs 等）は自動作成される場合がありますが、権限に注意してください

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 動作モード
  - KABUSYS_ENV — development | paper_trading | live
    - paper_trading: 発注は MockBrokerClient、paper DB に記録
    - live: 実際に発注される可能性あり
- DB / ログ
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…）
  - LOG_DIR — ログファイル格納ディレクトリ（デフォルト logs/）
- AI
  - OPENAI_API_KEY — OpenAI 呼び出しに必要（AI 機能を使う場合）
- Monitoring / Kill Switch
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動消去するか（"1" で有効。production では "0" 推奨）
- 監視間隔
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

.env は絶対にリポジトリにコミットしないでください（機密情報含む）。

---

## 使い方（コマンドの例）

- .env 作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動（本番/ペーパートレードに応じて .env の KABUSYS_ENV を切替）
  - python -m kabusys.run_execution
  - 実行時に data/stop_requested.flag があれば起動しません。起動中に stop_requested.flag が置かれると停止処理されます。
- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用します（監視データは本番 DB に記録）
- Paper trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
- AI スコアリング（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — api_key None の場合は OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意点:
- run_execution は起動直後にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を扱います。
- 停止制御は stop_requested.flag（run_* の停止） / kill.flag（ExecutionEngine に対する停止要求）で行います。
- Monitoring は監視専用 DB の初期化（init_monitoring_db）を行います。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数のロード・Settings クラス（.env 自動ロード機能含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity
  - execution/  — 発注周り（BrokerFactory / Engine / OrderManager / RiskManager 等）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・永続化 API
    - system_monitor.py — システム・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション監視
    - trade_monitor.py — 注文滞留・約定異常監視（実装ファイルあり）
    - monitoring_engine.py — 各 Monitor の統合ループ
    - kill_switch.py — Kill Switch（kill.flag 書き込み）
    - alert_manager.py — 通知（LINE 等）管理（実装ファイルあり）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・投下資金スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等の計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI で銘柄別スコア）
    - regime_detector.py — マクロ + ETF MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力

（上記は主要ファイルを抜粋した構成です。細かい実装は各ディレクトリ以下を参照してください）

---

## 開発者向けメモ / 運用注意

- DB の分離
  - monitoring（監視情報）は settings.sqlite_path（デフォルト data/monitoring.db）に記録
  - ペーパートレードは settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離
- ロギング
  - setup_logging() で stdout と logs/<app>.log に日次ローテートで出力
  - LOG_DIR の作成に失敗した場合はコンソール出力のみ行います
- Kill Switch と停止
  - KillSwitch は RiskMonitor の結果に基づき kill.flag を書き込みます
  - ExecutionEngine は起動時に kill.flag を自動クリアするかは KILL_FLAG_CLEAR_ON_START に依存
- AI（OpenAI）モジュール
  - OPENAI_API_KEY が未設定だと例外を投げる箇所があります（呼び出し側で処理してください）
  - API 呼び出しはリトライ・バックオフ・レスポンスのバリデーションが組み込まれています
- ユニットテスト
  - 公開関数は外部 API を直接呼ばない設計になっていることが多く、モックしやすい構成です
- セキュリティ
  - .env に機密情報を置くため、必ず .gitignore に追加して Git にコミットしないこと

---

## トラブルシューティング

- 起動時に "ログディレクトリの作成に失敗しました" と出る
  - 権限を確認するか LOG_DIR を書き込み可能な場所に設定してください
- run_monitoring/run_execution がすぐ終了する
  - data/stop_requested.flag の存在を確認（停止フラグ）。削除または不要ならファイルを削除してください
- 設定検証でエラーが出る
  - python -m kabusys.validate_config を実行して出力される ERROR / WARNING を確認
- OpenAI 関連が動作しない
  - OPENAI_API_KEY 環境変数（または関数引数）を確認、ネットワーク接続と API 使用量・レート制限に注意

---

README はこのリポジトリの主要な導入ガイドです。詳細な API ドキュメントや設計資料（PortfolioConstruction.md 等）が付随している場合は併せて参照してください。必要であればサンプルの .env.example やデプロイ手順の追記も作成できます。