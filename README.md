# KabuSys

日本株自動売買フレームワーク（軽量プロトタイプ）

このリポジトリは「KabuSys」と呼ばれる日本株自動売買システムの主要コンポーネント群を含みます。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視機構、そしてニュースのLLM評価を組み合わせた設計になっています。本 README は開発者向けにプロジェクト概要、機能、セットアップ、主要な使い方、ディレクトリ構成をまとめたものです。

注意: 本リポジトリは実装の一部（データパイプラインやブローカー実装の詳細など）を前提としており、本番運用にはさらに安全設計・テストが必要です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数一覧（主要）
- ツール / 補助コマンド
- ディレクトリ構成（主要ファイル）
- 補足（注意事項）

---

## プロジェクト概要

KabuSys は日本株自動売買システムのコンポーネント群です。主な設計思想は以下のとおりです。

- モジュールを分離（研究 / ポートフォリオ / 実行 / 監視 / AI）
- DuckDB を使った時系列データ処理（prices_daily, raw_financials 等を想定）
- SQLite を使った監視ログ・注文ログの永続化
- Paper trading モードを標準で分離（本番 DB と分離）
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント評価（任意）
- 単純で再現性のあるポートフォリオ構築・サイズ計算の純粋関数群

---

## 機能一覧

- 研究（research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ポートフォリオ（portfolio）
  - 候補選定（スコア順・signal_rank タイブレーク）
  - 重み計算（等分配 / スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（リスクベース / 等分配 等）
- 実行（execution）
  - ExecutionEngine、OrderManager、Reconciler（再起動時の同期）
  - Paper trading モード（KABUSYS_ENV=paper_trading）で本番 DB と分離
- 監視（monitoring）
  - SystemMonitor（プロセス生存・CPU/メモリ/ディスク/データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常）
  - RiskMonitor（ドローダウン・ポジション数監視、ダッシュボード永続化）
  - KillSwitch（フラグファイル書き込みにより ExecutionEngine 停止）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- AI（ai）
  - ニュースのセンチメント評価（OpenAI を使用）
  - 市場レジーム判定（MA200 と LLM マクロセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）

---

## セットアップ手順（開発環境）

想定 Python バージョン: 3.10+

1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate （Windows は .venv\Scripts\activate）

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - ※ requirements.txt はこのリポジトリに含まれていないため、実行に必要なライブラリを適宜インストールしてください。

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数（.env）を用意する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（既存の OS 環境変数は保護されます）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DB 初期化
   - monitoring 用の SQLite は起動スクリプト（実行時）で自動的に init されます（init_monitoring_db を呼びます）。
   - DuckDB テーブル（prices_daily など）は別途データパイプラインで準備する必要があります。

---

## 使い方（主要スクリプト）

各スクリプトはパッケージとして実行できます。

1. 監視ループ（SystemMonitor を単独で実行）
   - python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。0 以下や不正値はデフォルトにフォールバック。
   - 備考:
     - run_monitoring は Monitoring 用 SQLite（settings.sqlite_path）を環境にかかわらず使用します（監視データは本番 DB を使う設計）。
     - 起動直後にプロセス優先度を "high" に設定しようとします（psutil によりプラットフォーム差分を吸収）。

2. 実行エンジン（ExecutionEngine）
   - python -m kabusys.run_execution
   - 挙動:
     - 環境変数 KABUSYS_ENV を `paper_trading` にすると paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離します。
     - Paper trading の振る舞いは環境変数 `PAPER_FILL_MODE`（instant, partial, never, reject）で制御できます。
     - 実行前に kill flag のクリア等の設定は Settings で制御できます（KILL_FLAG_CLEAR_ON_START）。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --from / --to: レポート期間（YYYY-MM-DD）
     - --db: SQLite ファイルパス（指定がなければ環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
   - 出力: 稼働率、注文成功率、送信率、レイテンシ統計、PASS/FAIL 判定（所定閾値を参照）

4. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only で監視用 SQLite を開きます（DB が存在しない場合はエラー表示）。

5. AI 関連
   - news_nlp.score_news / regime_detector.score_regime を使うと OpenAI API を呼びます。
   - 必要: 環境変数 OPENAI_API_KEY（または関数引数で API キーを渡す）
   - AI 呼び出しはレート制限・エラーを考慮したリトライ・フェイルセーフ実装を含みます。API キー未設定時は例外が発生します。

---

## 環境変数（主要）

以下は Settings クラス・コードで参照される主要な環境変数（抜粋）です。詳細は src/kabusys/config.py を参照してください。

- KABUSYS_ENV: 起動環境 (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring 用のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用トークン・ユーザ ID

---

## ツール / 補助コマンド

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 検証基準値はスクリプト内定数で定義（稼働率 99% 等）。テストや監査に利用できます。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- DB 初期化
  - run_execution / run_monitoring 起動時に monitoring テーブルは自動作成（init_monitoring_db）されます。
  - 既存 DB に対する簡易マイグレーション（例: dashboard に peak_value カラム、trade_logs に latency_ms カラムの追加）も含まれます。

---

## ディレクトリ構成（抜粋）

以下は repo の主要なファイル・ディレクトリ（src/kabusys 以下）の一覧です。実際のリポジトリではさらにファイルがある場合がありますが、ここでは提供コードに基づく主要部を列挙します。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定読み込みロジック
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py               — ニュースを LLM でスコアリング
    - regime_detector.py        — 市場レジーム判定
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン計算・IC・統計ユーティリティ
  - portfolio/
    - __init__.py
    - portfolio_builder.py     — 候補選定・重み計算
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
    - position_sizing.py       — 発注株数計算・キャップ処理
  - monitoring/
    - __init__.py
    - monitoring_db.py         — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py        — システム状態・データ鮮度チェック
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag を書いて Execution 停止を促す
    - alert_manager.py         — LINE Push 通知
    - monitoring_engine.py     — 複数モニタの束ね・ポーリング
    - streamlit_dashboard.py   — Streamlit ベースの監視ダッシュボード（起動例あり）
  - execution/
    - order_manager.py        — Order 管理（作成→送信→同期）
    - reconciler.py           — 再起動時の同期（Order / Position の突合）
    - （その他 execution モジュールは省略/別ファイル）
  - utils/
    - __init__.py
    - process_priority.py     — プロセス優先度 / CPU affinity のユーティリティ

---

## 補足（運用上の注意）

- 本番運用前に十分なテストを行ってください。特にブローカー API 呼び出し・注文状態遷移・リスク制御は重大な影響を与えます。
- OpenAI の利用はコストが発生します。AI 機能は必要に応じて無効化してください（OPENAI_API_KEY を設定しない等）。
- run_monitoring は監視データを本番 monitoring DB へ書き込みます。paper_trading モードでも監視 DB は本番パスを使用する設計になっています（意図的）。
- kill.flag による停止は簡易な仕組みです。誤動作防止のため kill_flag_clear_on_start 等の設定や手順をマニュアルに明記してください。
- .env の自動ロード処理はプロジェクトルート（.git または pyproject.toml）を探索して行われます。CI / テスト環境で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要であれば、README に以下の追加情報を追記できます:
- 依存ライブラリの推奨バージョン（requirements.txt の生成）
- 実行時の systemd / Docker 化手順（サービス化）
- DuckDB のテーブルスキーマ & サンプルデータ作成手順
- テストの実行方法（ユニット・統合テスト）

ご希望があれば、上記のうちどれを優先して詳細化するか教えてください。