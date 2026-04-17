# KabuSys

日本株自動売買システムのコードベース README。  
この README ではプロジェクト概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買（Execution）および稼働監視（Monitoring）、研究用ファクター計算や AI を用いたニュースセンチメント評価を含む小規模な取引システムです。  
主な設計方針はフェイルセーフ性（API失敗時のフォールバック）、ルックアヘッドバイアス回避（日時参照の扱いの注意）、および本番/ペーパートレーディングの分離です。

主要コンポーネント:
- ExecutionEngine: ブローカー連携による注文発行・状態管理・リスク管理
- MonitoringEngine: システム稼働状況、注文滞留、リスク（ドローダウン等）監視とアラート送信
- Research: DuckDB を用いたファクター計算・特徴量探索
- AI: OpenAI を使ったニュースのセンチメントスコアリングと市場レジーム判定
- Tools: ペーパートレーディングの検証レポート生成、Streamlit ベースの監視ダッシュボード

---

## 機能一覧

- プロセス優先度・CPU affinity の設定（クロスプラットフォーム、psutil ベース）
- 監視機能
  - CPU / メモリ / ディスク使用率のログ
  - Execution プロセスの生存確認（PIDファイル）
  - データ鮮度チェック（DuckDB の prices_daily）
  - 注文滞留・約定異常価格の検知
  - ドローダウン監視・ポジション上限監視（kill flag 発動対応）
  - LINE への一方向プッシュ通知（AlertManager）
  - Streamlit ダッシュボード（read-only 接続）
- 実行機能
  - ブローカー抽象化（本番/Mock 切替）
  - 注文の状態管理、再起動時のリコンシリエーション
  - リスク管理（ポジション上限、最大利用率、レート制限等）
  - Paper trading 用 DB と本番 DB の分離（KABUSYS_ENV=paper_trading）
- 研究機能（DuckDB）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、ファクター統計
- AI 機能（OpenAI）
  - ニュース記事を銘柄別に集約して LLM でセンチメント評価 → ai_scores に格納
  - マクロニュース＋ETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）
- ユーティリティ
  - ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
  - Paper Trading 検証レポート生成ツール

---

## セットアップ手順

以下はローカル開発環境向けの一例です。

前提：Python 3.9+ を推奨（コードは型ヒントにより現代的な機能を使用）。  
実際の Python バージョンはプロジェクト要件に合わせてください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   requirements.txt は同梱されていない想定なので、主要依存を手動でインストール：
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   - DuckDB: データ解析用
   - psutil: プロセス優先度 / CPU 情報
   - requests: LINE API 呼び出し
   - openai: LLM 呼び出し
   - streamlit: ダッシュボード

4. データディレクトリ作成
   ```
   mkdir -p data
   ```

5. 環境変数設定  
   プロジェクトは .env / .env.local 自動読み込み機能を持ちます（デフォルトで自動ロード）。`.env.example` を参考に `.env` を作成してください。主な環境変数:

   - 必須（実行時に必要な場合）
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
   - OpenAI 関連
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - 実行環境指定
     - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
   - DB / ファイルパス
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH — execution.pid のパス（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
   - モード・閾値など
     - PAPER_FILL_MODE — instant | partial | never | reject（paper trading の注文約定挙動）
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
   - 自動ロード無効化（テスト向け）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要スクリプト）

パッケージ内モジュールとして実行できます（リポジトリ直下で行う想定）。

1. Monitoring を起動
   - 監視ポーリングを開始します（永続的プロセス）
   ```
   python -m kabusys.run_monitoring
   ```
   - 環境変数でポーリング間隔を変更:
   ```
   MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   ```
   - 停止は `Ctrl+C` またはプロジェクトの data/stop_requested.flag を作成するとループが検知して終了します。

2. Execution（エンジン）を起動
   - 本番 or ペーパーの切替は KABUSYS_ENV で制御
   ```
   # 本番環境（例）
   KABUSYS_ENV=live python -m kabusys.run_execution

   # ペーパートレード（Mock broker を使用、専用 DB を利用）
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   ```
   - 実行中に data/stop_requested.flag を作成するとエンジンが停止します。実行中は data/execution.pid に PID が書き込まれます。

3. Paper Trading 検証レポート生成ツール
   ```
   python -m kabusys.tools.paper_verification_report
   ```
   - 期間指定:
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   - DB パスを指定:
   ```
   python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   ```

4. Streamlit ダッシュボード（監視）
   - 起動方法（プロジェクト直下から）:
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   - もしくはパッケージ化された環境でモジュール経由にすることも可能です（環境に応じてパスを調整）。

5. AI 機能（ニューススコアリング / レジーム判定）
   - OpenAI API キーが必要です（OPENAI_API_KEY）。
   - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を渡して呼び出します（スクリプト化はしていませんが、ツール化可能）。

停止・強制停止の概念:
- data/stop_requested.flag: run_monitoring / run_execution のループ停止判定に使用
- data/kill.flag: KillSwitch により書き込まれる（Execution に対する停止シグナル）
- kill.flag を手動で削除するには:
  ```
  rm data/kill.flag
  ```

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイル・ディレクトリと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite ベースの監視 DB 層（初期化・読み書き）
    - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / PID チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）
  - execution/
    - order_manager.py — 注文作成・キャンセル等の外向け API（OrderManager）
    - reconciler.py — 起動時の注文・ポジション照合
    - （その他ブローカー抽象等はここに存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・投下資金スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースの LLM による銘柄別センチメント付与
    - regime_detector.py — 市場レジーム判定（ETF MA + LLM）
  - data/ （実行時に作成される）
    - monitoring.db（SQLite 監視 DB）
    - paper_trading.db（ペーパートレード用 DB、KABUSYS_ENV=paper_trading 時に別扱い）
    - execution.pid / kill.flag / stop_requested.flag など

---

## 注意点 / 運用メモ

- .env ファイルは機密情報（API キー等）を含むため、リポジトリにコミットしないでください。`.gitignore` に追加してください。
- Settings はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に .env/.env.local を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用）。
- Paper trading は専用の SQLite を使用し、本番 DB と完全分離されています（安全のため）。
- OpenAI や外部 API 呼び出しはフェイルオープン／フェイルセーフを基本とし、API 失敗時はスコアをゼロにする等の処理が入っていますが、運用では API の利用制限やコストに注意してください。
- 実行時に PID ファイルや stop/kill フラグの取り扱いに注意してください。自動停止や手動停止のワークフローを運用ルールとして明確にしておくことを推奨します。

---

## 連絡先 / 貢献

この README はコードベースに含まれるドキュメントコメントを基に作成しています。実装の変更に伴い README の更新を行ってください。バグや改善提案は Issue を作成してください。

--- 

必要であれば以下を追加で作成できます:
- requirements.txt の推奨パッケージ一覧
- .env.example のテンプレート
- 簡易運用ガイド（起動/停止シナリオ、ログローテーション、バックアップ手順）
希望があれば教えてください。