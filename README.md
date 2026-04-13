# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群と運用ツール群です。  
本リポジトリは注文管理・実行エンジン、監視（Monitoring）機能、ポートフォリオ構築ロジック、リサーチ用ファクター計算、LLM を使ったニュースセンチメント評価などを含みます。

主な目的は「実運用を想定した堅牢な自動売買基盤」を提供することです（本番 / paper_trading の分離、DB マイグレーション、フェイルセーフ設計、ログ／監視、再起動後のリコンシリエーション等を考慮）。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動例・ツール）
- 主要環境変数（重要）
- ディレクトリ構成（主なファイル説明）
- 補足（運用に関する注意点）

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的とした Python パッケージ群です。主なコンポーネントは以下です。

- Execution（発注・注文状態管理・ブローカ連携・リコンシリエーション）
- Monitoring（システム状態、注文滞留、リスク監視、アラート送信）
- Portfolio（銘柄候補選定、重み付け、ポジションサイズ計算、セクター制約）
- Research（DuckDB を用いたファクター計算・特徴量探索）
- AI（OpenAI を利用したニュースセンチメント評価、レジーム判定）
- Tools（Paper Trading 検証レポート生成、Streamlit ダッシュボード等）

設計では以下の点を重視しています：
- 本番と paper_trading の分離（DB、ブローカー、fill モードなど）
- ルックアヘッドバイアス回避（date.today()/datetime.today() を直接参照しない設計）
- フェイルセーフ（API失敗時のフォールバック、部分書込で既存データを保護する設計）
- テストしやすさ（外部呼出しを差し替え可能な設計）

---

## 機能一覧

- Execution
  - 注文作成 / 送信 / 状態同期（OrderManager）
  - 再起動時の自動リコンシリエーション（Reconciler）
  - RiskManager による発注前リスクチェック（レート制限・最大ポジション等）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検知
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード集計更新
  - KillSwitch: フラグファイルによる ExecutionEngine 停止シグナル
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- Portfolio
  - 候補選定（スコア降順、上位 N 件）
  - 等金額・スコア加重配分
  - セクター上限チェック（apply_sector_cap）
  - ポジションサイズ計算（単元丸め、aggregate cap、リスクベース配分）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB + prices_daily/raw_financials）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI
  - ニュースをまとめて OpenAI へ送信し銘柄別センチメント（ai_scores）を保存
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（market_regime）
- Tools
  - Paper Trading 検証レポート（paper_verification_report）
  - Streamlit ダッシュボード（streamlit_dashboard.py）

---

## セットアップ手順

前提
- Python 3.10 以上（| 型表記や match-less の記法、typing の新機能を使用）
- Git リポジトリのルートに .env/.env.local を配置する想定（設定は Settings モジュールで読み込みます）

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）
4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動でロードされます。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. 必須環境変数（代表）
   - JQUANTS_REFRESH_TOKEN（J-Quants API）
   - KABU_API_PASSWORD（kabu API）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - KABUSYS_ENV（development / paper_trading / live）
   - 任意で DB パスなど（下記参照）

重要: Settings クラスで環境変数の妥当性チェックやデフォルトパスが定義されています（例: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db, PAPER_TRADING_SQLITE_PATH=data/paper_trading.db）。

---

## 使い方

主要スクリプトはパッケージモジュールとして起動します（モジュール名は import パスに対応）。

1. Monitoring（監視ループ）を起動
   - モジュール: kabusys.run_monitoring
   - 起動例:
     - python -m kabusys.run_monitoring
   - 設定:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します（監視は運用 DB を想定）
     - PID 優先度設定: 起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）

2. ExecutionEngine（発注エンジン）を起動
   - モジュール: kabusys.run_execution
   - 起動例:
     - python -m kabusys.run_execution
   - 設定:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 SQLite（デフォルト: data/paper_trading.db）へ記録し、本番 DB と分離します。
     - PAPER_FILL_MODE 環境変数で MockBroker の約定モードを制御できます（instant / partial / never / reject）

3. Streamlit ダッシュボード（監視 UI）
   - 起動コマンド（スクリプト内の案内に従う）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only モードで SQLite を開き、ダッシュボード表示を行います。

4. Paper Trading 検証レポート
   - 実行モジュール: kabusys.tools.paper_verification_report
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - 出力: システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などをコンソールに表示し PASS/FAIL を判定します。

5. AI 機能（ニューススコア・レジーム判定）
   - ニュースセンチメントの収集とスコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, target_date, api_key=...)
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(conn, target_date, api_key=...)
   - 注意: OPENAI_API_KEY が必要。API 呼び出しはリトライ・フォールバックを備えていますが、API キー未設定時は ValueError が発生します。

その他:
- プロセス優先度・CPU affinity: kabusys.utils.process_priority.set_process_priority / set_cpu_affinity を用いてプラットフォーム差分を吸収して設定します。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト: 60
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイルパス（デフォルト: data/kill.flag）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API の認証情報（必須設定項目）

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）に .env と .env.local を置くと自動的に読み込みます。
- 読み込み優先順: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます（テスト用途等）。

---

## ディレクトリ構成（主要部分）

src/kabusys/
- __init__.py
  - パッケージ定義、バージョン情報
- config.py
  - Settings クラス（.env 読み込み・環境変数管理・妥当性チェック）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード分離）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py — SQLite ベースの監視ログ永続化・CRUD
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセスチェック
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン/ポジション上限監視
  - kill_switch.py — フラグファイルによる停止シグナル管理
  - alert_manager.py — LINE プッシュ通知（クールダウン付き）
  - monitoring_engine.py — 各モニタを束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit によるダッシュボード
- execution/
  - order_manager.py, order_repository.py, reconciler.py, etc.（発注/DB/同期ロジック）
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 発注株数計算（単元丸め・aggregate cap）
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value の計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py — ニュースを LLM で銘柄ごとにスコア化して ai_scores へ書き込む
  - regime_detector.py — マクロニュース + ETF MA200 を合成して市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

各ファイル内に詳細な docstring と設計注記があり、関数・クラス単位での使い方やフォールバック挙動が明記されています。

---

## 補足（運用時の注意点）

- DB マイグレーション: monitoring_db.init_monitoring_db() は必要なテーブルと一部カラム追加（マイグレーション）を行います。複雑なスキーマ変更は別途対応してください。
- Paper Trading の分離: paper_trading モードでは paper_sqlite_path を使用し、本番監視 DB とは分離されます。実運用時は設定の確認を徹底してください。
- Kill Flag / PID: ExecutionEngine は data/execution.pid を用いてプロセス生存を管理します。KillSwitch が data/kill.flag を書き込むと Execution 停止シグナルになります。KILL_FLAG_CLEAR_ON_START を設定して起動時にフラグをクリアする挙動を制御できます。
- LLM（OpenAI）利用: API 呼び出しにはレート制限や失敗が起きるため、リトライ・フォールバックロジックが組み込まれていますが、API キーとクォータの管理は運用者の責任です。
- ロギング: 各モジュールは標準 logging を使用。必要に応じてログ設定（ファイル出力やローテーション）を追加してください。
- セキュリティ: .env に API キーやパスワードを置く場合、リポジトリに含めないよう注意してください。

---

必要に応じて README を拡張し、設定例（.env.example）、運用 runbook、Dockerfile や systemd サービス定義のテンプレートなどを追加できます。README の補足や具体的な運用手順の追加を希望する場合は用途（本番デプロイ / ローカル検証 / CI）を教えてください。