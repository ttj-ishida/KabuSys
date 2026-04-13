KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買および関連研究／監視ツール群です。本リポジトリは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）: ブローカーに対する注文発行・状態管理・リスクガード
- 監視（Monitoring）: システム状態・注文滞留・リスク監視、監視ログの永続化、Kill Switch
- ポートフォリオ構築ユーティリティ: 候補選定、重み付け、ポジションサイズ計算、セクター制限
- リサーチ（Research）: ファクター計算、将来リターン、IC（情報係数）・統計サマリー
- AI 支援モジュール: ニュースのセンチメント評価（OpenAI）と市場レジーム判定
- 運用補助ツール: Paper Trading 検証レポート、Streamlit ダッシュボード など

主な特徴
--------
- 環境切替: KABUSYS_ENV により development / paper_trading / live を切替可能
- Paper Trading 分離: paper_trading 時は本番 DB と分離して data/paper_trading.db に記録
- 監視データ永続化: SQLite（data/monitoring.db デフォルト）で監視ログを蓄積
- DuckDB を利用した高速な履歴データ集計（prices_daily, raw_financials 等想定）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントとレジーム判定（API キー必須）
- フェイルセーフ設計: API失敗や DB エラー時でも安全にフォールバック・継続する実装

セットアップ
------------
前提: Python 3.10+ を想定します（typing 構文等のため）。プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（必要な主要パッケージ例）
   - pip install duckdb psutil requests openai streamlit

   ※ 実際の requirements.txt が無い場合はプロジェクトに合わせて追加してください。

3. 環境変数 / .env
   - プロジェクトルートの .env, .env.local を自動で読み込みます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 代表的な環境変数:
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な機能がある場合）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（ExecutionEngine 用）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の実行モード（instant|partial|never|reject）
     - PID_FILE_PATH / KILL_FLAG_PATH などの監視関連設定
   - .env のパースはシェル形式に近い簡易実装に対応しています（コメント・クォート処理あり）。

使い方（主要コマンド）
--------------------

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関係なく sqlite_path（本番 DB）を使用します（監視データは共通に蓄積）。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合:
    - Broker は MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます（本番 DB と完全分離）。
  - 実行前に必要な環境変数（KABU_API_PASSWORD など）を確認してください。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 DB を読み取り専用モードで開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを明示可能。デフォルトは data/paper_trading.db。
  - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計して PASS/FAIL を判定します。

- AI 関連
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出すことで
    - raw_news から銘柄別センチメントを ai_scores テーブルへ書き込み
    - マクロニュースと ETF（1321）MA200乖離から市場レジームを判定して market_regime テーブルへ書き込み
  - いずれも OPENAI_API_KEY の設定が必要です。API呼出しは冗長性（リトライ）やパース検証を備えています。

設定・注意事項
--------------
- KABUSYS_ENV:
  - development / paper_trading / live のいずれか。Settings クラスで検証しています。
  - paper_trading: 実ブローカーに発注せず、専用 DB に記録して検証可能。

- 監視（run_monitoring）:
  - 監視は常に Settings.sqlite_path（本番側）を使用する設計です。実稼働監視は常に本番データで行われます。

- プロセス優先度:
  - 起動時に set_process_priority("high") を呼びます。Linux での nice 値変更は権限が必要な場合があります（sudo 等）。
  - CPU affinity の設定もユーティリティにより可能ですが、アクセス権限の制限により失敗することがあります（ログに警告）。

- OpenAI:
  - API のレート制限やネットワークエラーは内部でリトライし、致命的な場合は安全にフォールバック（スコア0やスキップ）するよう実装されています。
  - 出力のバリデーションを行い、無効レスポンスは無視します。

- DB マイグレーション:
  - init_monitoring_db() は冪等でテーブル作成・簡易マイグレーション（列追加）を行います。

ディレクトリ構成（概要）
----------------------
以下は主要なファイル／ディレクトリです（src/kabusys 以下）。

- src/kabusys/
  - __init__.py                 — パッケージ定義、バージョン
  - config.py                   — Settings クラス（環境変数 / .env 読込ロジック）
  - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト（paper_trading 対応）
  - utils/
    - process_priority.py       — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py          — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py         — CPU/メモリ/ディスク/データ鮮度/実行プロセス監視
    - trade_monitor.py          — 注文滞留・約定価格異常監視
    - risk_monitor.py           — ドローダウン / ポジション上限監視
    - kill_switch.py            — kill.flag を書き込み Execution 停止を指示
    - alert_manager.py          — LINE Messaging API での通知
    - monitoring_engine.py      — 各 Monitor を束ねるオーケストレータ
    - streamlit_dashboard.py    — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py          — OrderManager（注文フローの外向き API）
    - reconciler.py             — 起動時の注文・ポジション再照合（リコンシリエーション）
    - ...                      — （その他 Execution 関連モジュールが存在）
  - portfolio/
    - portfolio_builder.py      — 候補選定、等重/スコア重み計算
    - position_sizing.py        — 株数決定・単元丸め・aggregate cap 調整
    - risk_adjustment.py        — セクター上限・レジーム乗数
  - research/
    - factor_research.py        — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py    — 将来リターン計算、IC、統計サマリー
  - ai/
    - news_nlp.py               — raw_news を LLM でスコアリングして ai_scores に書込
    - regime_detector.py        — マクロ + ETF MA で市場レジーム判定、market_regime 書込
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力ツール
    - __init__.py

開発・拡張のヒント
------------------
- DuckDB 接続を渡す設計になっているため、リサーチ／AI モジュールは本番口座への影響を与えずにローカルで計算できます。
- AI モジュールのテストでは _call_openai_api をモックすることが想定されています（unittest.mock.patch）。
- position_sizing / risk_adjustment 等は純粋関数として実装されているためユニットテストが容易です。
- .env の自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してテスト側で制御してください。

ライセンス・その他
------------------
- 本 README はコードベースの説明用です。実運用する際はブローカー API の仕様、手数料・税金、実行環境の可用性・安全性を十分に検討してください。

必要があれば、README に入れる具体的な .env.example（推奨環境変数のテンプレート）や、サンプル起動スクリプト（systemd ユニットや Dockerfile）の例も作成します。どの情報を追加したいか教えてください。