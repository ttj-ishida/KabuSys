README.md

KabuSys — 日本株自動売買システム（簡易ドキュメント）
================================

概要
---
KabuSys は日本株向けの自動売買・リサーチ基盤のミニマム実装です。  
主な機能は、データ分析（DuckDB）、シグナル生成・ポートフォリオ構築、発注エンジン（本番／ペーパートレード対応）、監視・アラート、LLM を使ったニュースセンチメント解析などを含みます。  
設計方針としてはフェイルセーフ性（API失敗時のフォールバック）、環境分離（ペーパートレード用 DB の分離）、ルックアヘッドバイアス回避等を重視しています。

主な機能
---
- Execution エンジン（ExecutionEngine）  
  - 本番・ペーパートレード切替（KABUSYS_ENV に依存）。ペーパートレードは専用 SQLite（デフォルト data/paper_trading.db）に記録します。
  - Broker クライアントの抽象化（BrokerClientFactory）。
  - 注文管理、リスク管理、リコンシリエーション機能を備えます。

- 監視（Monitoring）  
  - SystemMonitor: CPU・メモリ・ディスク・プロセス死活・データ鮮度を監視し monitoring DB に記録。
  - TradeMonitor: 注文滞留や約定異常価格の検出。
  - RiskMonitor: ドローダウン・ポジション上限のチェックとアラート記録。
  - KillSwitch: 閾値トリガー時に data/kill.flag を作成して ExecutionEngine を停止させる仕組み。
  - AlertManager: LINE Messaging API による通知（トークン・ユーザーIDが設定されている場合）。

- ポートフォリオ構築（Portfolio）  
  - 候補選定、等分配 / スコア加重配分、リスク調整（セクター制限・レジーム乗数）、株数決定（単元丸め・資金配分）等の純粋関数群。

- リサーチ（Research）  
  - DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー）および将来リターン・IC 計算、統計要約など。

- AI（OpenAI）連携  
  - news_nlp: ニュース記事を LLM（gpt-4o-mini 想定）でセンチメント評価し ai_scores に格納。
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースの LLM 判定を合成して市場レジーム（bull/neutral/bear）を判定・永続化。
  - 失敗時は安全にフォールバックする設計（API失敗時に中立値等で継続）。

- ユーティリティ
  - 環境設定ウィザード（config_setup）: .env を対話式で作成／更新。
  - 設定検証ツール（validate_config）: .env と config/*.yaml の基本チェック。
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report）。

セットアップ手順
---
1. Python 環境作成（推奨: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - PyYAML（config の詳細検証に必要だが必須ではない）
   - インストール例:
     - pip install duckdb psutil requests openai PyYAML

   ※ 実プロジェクトでは requirements.txt を用意してください（本リポジトリには含まれていません）。

3. ディレクトリと初期 DB（data ディレクトリ）
   - data/ ディレクトリは自動生成されますが、手動で作る場合:
     - mkdir -p data
   - DuckDB / SQLite のデフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite (ペーパートレード時): data/paper_trading.db

4. 環境変数設定（.env）
   - 手早く設定するにはウィザードを使う:
     - python -m kabusys.config_setup
   - 主要な環境変数（最小）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（必要に応じて）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート送信を有効化する場合）
     - PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject）
     - KILL_FLAG_CLEAR_ON_START（本番での自動クリアを避けるなら 0）

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があればメッセージに従って修正してください。
   - --strict オプションで警告をエラー扱いにできます。

使い方（主なエントリポイント）
---
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）の起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録されます（本番 DB と分離）。
    - 実行中は data/execution.pid に PID が書かれます。
    - 停止は data/stop_requested.flag を作成するか（run_execution は stop フラグを監視）、KillSwitch が data/kill.flag を作成すると停止されます。

- Monitoring（監視ループ）の起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
  - 監視は常に本番用の sqlite_path を使用します（環境に依らず本番 DB に書き込む仕様）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI / リサーチ API（プログラムから利用）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)
  - ファクター計算等:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

運用上の注意
---
- .env は機密情報（API トークン等）を含むため Git にコミットしないでください。
- 本番環境 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。
- OpenAI を使用する機能は API キーが必要で、呼び出しコスト・レート制限に注意してください。
- run_monitoring は監視 DB に常時書き込みを行います。監視 DB のパスは Settings.sqlite_path で決まります。

データ／フラグファイル
---
- data/execution.pid — ExecutionEngine の PID（存在しない場合はプロセス未起動）
- data/stop_requested.flag — 管理者が作成することで監視または実行ループを終了させるためのフラグ
- data/kill.flag — KillSwitch が書き込む停止要求（ExecutionEngine に停止シグナル）
- data/kabusys.duckdb — DuckDB（分析用）
- data/monitoring.db — 監視ログ SQLite（system_status, trade_logs, positions, risk_logs, dashboard 等）
- data/paper_trading.db — ペーパートレード専用 SQLite（KABUSYS_ENV=paper_trading 時に使用）

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py — パッケージ情報
- config.py — 環境変数 / Settings 管理、自動 .env ロード機能
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト（エントリポイント）
- run_monitoring.py — SystemMonitor 起動スクリプト（エントリポイント）

src/kabusys/execution/
- execution_engine.py — 発注エンジン本体（EngineConfig 等）
- order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py など — 発注関連ロジック

src/kabusys/monitoring/
- monitoring_db.py — SQLite への永続化層（テーブル作成・読み書き）
- system_monitor.py — システム・データ鮮度監視
- trade_monitor.py — 注文滞留・約定異常監視
- risk_monitor.py — ドローダウン・ポジション上限チェック
- kill_switch.py — Kill Switch（flag ファイル管理）
- monitoring_engine.py — 各 Monitor を束ねるエンジン
- alert_manager.py — LINE 連携アラート

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・配分スコア
- position_sizing.py — 株数決定・資金配分ロジック
- risk_adjustment.py — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py — ファクター計算（momentum/volatility/value）
- feature_exploration.py — 将来リターン・IC・統計サマリ

src/kabusys/ai/
- news_nlp.py — ニュース NLP スコアリング（OpenAI 連携）
- regime_detector.py — レジーム判定（MA200 + マクロニュース）

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート生成

src/kabusys/utils/
- process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

拡張・開発のヒント
---
- DuckDB を使ってローカルで大量の時系列データを保存・分析できます。prices_daily / raw_financials / raw_news 等のテーブル設計に合わせてデータ投入してください。
- AI 統合は OpenAI の SDK（openai パッケージ）を利用しています。コールの単体テストでは _call_openai_api をモック化することを推奨します。
- 実運用ではログ管理（ファイル・外部サービス）やプロセスマネージャ（systemd / supervisor 等）でプロセスを管理するとよいです。

ライセンス / 注意事項
---
この README はリポジトリ内のコードから抽出した情報に基づく概要・運用ガイドです。実運用時は更なる安全対策（テスト、監査、アクセス制御）を必ず行ってください。

問題点や追加資料が必要であれば、どの点について深掘りしたいか教えてください。