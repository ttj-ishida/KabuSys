KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／研究／監視ツール群を収めた軽量なフレームワークです。
主要コンポーネントとして、ExecutionEngine（発注エンジン）、Monitoring（監視・アラート）、Research（ファクター計算）、
AI モジュール（ニュース NLP / レジーム判定）、Portfolio Construction ユーティリティ等を提供します。

要点
- 実行／監視はローカルの SQLite / DuckDB を使って状態を永続化します。
- Paper Trading 環境と本番環境は DB を分離して運用できます。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／レジーム判定機能を含みます（APIキー必須）。
- LINE Messaging API 経由でアラート送信が可能です（アクセストークン・ユーザーID 必須）。

主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカークライアント抽象（BrokerClientFactory）により本番 / モックを切り替え可能
  - リコンシリエーション（再起動時の同期）機能（Reconciler）
  - 注文管理（OrderManager / OrderRepository）
- Monitoring
  - SystemMonitor: プロセス生存・CPU/メモリ/ディスク・データ鮮度検査
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件満たしたら停止フラグを書き込み ExecutionEngine を停止
  - AlertManager: LINE へプッシュ送信（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Research / Portfolio
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量探索（IC 計算、将来リターン計算、統計サマリ）
  - ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算）  
- AI
  - ニュース NLP による銘柄単位センチメントスコアリング（src/kabusys/ai/news_nlp.py）
  - マクロ＋ETF を使った市場レジーム判定（src/kabusys/ai/regime_detector.py）
- ツール
  - Paper Trading 検証レポート出力スクリプト（src/kabusys/tools/paper_verification_report.py）

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - 以下のパッケージが利用されます（requirements.txt は本リポジトリに含まれていない想定）
     - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit
4. 環境変数設定
   - ルートに .env ファイルを置くと自動で読み込まれます（.env.local を上書きして読み込み可能）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN — （J-Quants API 用）
     - KABU_API_PASSWORD — （kabuステーション API 用）
   - 推奨 / 主要な環境変数（デフォルト値は括弧内）:
     - KABUSYS_ENV: development | paper_trading | live  (default: development)
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - DUCKDB_PATH: data/kabusys.duckdb
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
     - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE アラート用
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL: DEBUG|INFO|...（default: INFO）
   - 例 .env（テンプレート）
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_kabu_password
     - OPENAI_API_KEY=sk-...
     - KABUSYS_ENV=paper_trading
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=
     - LINE_USER_ID=
5. データディレクトリ
   - data ディレクトリを作成してください（DB ファイルやフラグファイルを格納）
   - 例: mkdir -p data

使い方（実行例）
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
    - 監視モジュールは環境にかかわらず本番用 SQLite（Settings.sqlite_path）を参照して監視ログを書きます
    - 停止するにはルートプロジェクトの data/stop_requested.flag を作成するか、Ctrl+C
- Execution エンジン起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます。本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動しません。
    - 実行中に停止させるには data/stop_requested.flag を作成してください（エンジンが検知して停止します）。
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を開き、ダッシュボードを表示します。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db /path/to/paper_trading.db  （環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- AI 機能
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - APIキーは引数または環境変数 OPENAI_API_KEY を使用
    - OpenAI API 呼び出しに失敗した場合はフェイルセーフで継続（必要に応じ警告ログ）
  - kabusys.ai.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 とマクロニュースを組み合わせて 'bull'/'neutral'/'bear' を判定

重要な挙動メモ
- Settings（src/kabusys/config.py）
  - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env/.env.local を読み込みます。
  - KABUSYS_ENV に許される値は development / paper_trading / live です（それ以外はエラー）。
  - PAPER_FILL_MODE の有効値: instant | partial | never | reject
  - kill flag のパス等は Settings 経由で取得できます。
- 監視と停止
  - run_monitoring / MonitoringEngine は定期的に System/Trade/Risk の各モニタを実行し、KillSwitch 条件を評価して必要なら data/kill.flag を書き込みます。
  - ExecutionEngine は kill.flag（または stop_requested.flag）を検出すると安全に停止する設計です。
- DB マイグレーション
  - monitoring_db.init_monitoring_db はテーブル作成と簡易マイグレーション（カラム追加）を行います。冪等に実行できます。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py — パッケージ宣言、バージョン情報
  - config.py — 環境変数 / 設定管理（Settings）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュースのセンチメントスコアリング（OpenAI 経由）
    - regime_detector.py — 市場レジーム判定（ETF + マクロ）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグファイル書き込みによる停止シグナル
    - alert_manager.py — LINE Push 通知（クールダウン）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ... — 発注／同期関連
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・資金制限
    - risk_adjustment.py — セクター上限 / レジーム乗数
  - research/
    - factor_research.py — ファクター計算
    - feature_exploration.py — 将来リターン・IC・サマリー等
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

開発・運用上の注意
- OpenAI / LINE / ブローカーの実際の API キーは機密情報です。絶対に公開リポジトリにコミットしないでください。
- Paper Trading モードでは本番口座とは DB を分離して動作することを想定しています。KABUSYS_ENV を適切に設定してください。
- プロセス優先度や CPU affinity はプラットフォーム依存性（権限）により失敗することがあるため、ログに警告が出ますが処理自体は続行します。
- 監視モジュールは定期的に system_status / risk_logs 等を更新します。運用時は data/*.db のバックアップを検討してください。

サポート / 拡張
- ブローカー実装（実ブローカー / モック）の追加は BrokerClientFactory を拡張してください。
- 単元株（lot size）の銘柄別対応や手数料モデルの導入は position_sizing の拡張点です。
- AI モデルやプロンプトの調整でセンチメント品質を改善できます（news_nlp._SYSTEM_PROMPT などを参照）。

ライセンス
- 本リポジトリのライセンス情報が別途ある場合はそちらに従ってください（README に明示されていない場合はリポジトリルートを参照）。

以上がこのコードベースの概要と基本的な使い方です。必要なら、特定モジュール（例: ExecutionEngine の詳細構成、OrderRepository の DB スキーマ、AI 呼び出しのテスト方法等）についての追加ドキュメントを作成します。どの部分を詳しく解説しますか？