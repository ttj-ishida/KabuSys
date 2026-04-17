# KabuSys — README

このリポジトリは日本株自動売買システムのコアライブラリ群です。戦略のポートフォリオ構築、発注実行（ExecutionEngine）、監視（Monitoring）、リサーチ用のファクター計算、AI を用いたニュース解析など、多数のモジュールで構成されています。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、ディレクトリ構成の説明です。

## プロジェクト概要
KabuSys は日本株自動売買システムの基盤的なコンポーネント群を提供します。主な目的は以下です。

- 戦略からのシグナルを受けて発注を管理・実行する ExecutionEngine（ブローカー抽象化を経由）
- システム稼働状況・注文・リスク指標を収集・永続化する Monitoring（SQLite）
- ポートフォリオ構築ロジック（候補選定、重み付け、ポジションサイジング、セクター制限）
- リサーチ用のファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- AI（OpenAI）を用いたニュースのセンチメント解析・市場レジーム判定
- 運用補助ツール（Paper Trading 検証レポートの出力、Streamlit ダッシュボード）

設計方針として、DB は sqlite / DuckDB を利用し、外部 API 呼び出し（ブローカー・OpenAI 等）は抽象化・フェイルセーフを重視しています。

## 主な機能一覧
- Execution
  - ExecutionEngine 周りの起動スクリプト（run_execution）
  - ブローカー抽象化（本番・Mock 対応、paper_trading の分離）
  - リコンシリエーション（再起動時の状態同期）
  - OrderManager / OrderRepository による注文ライフサイクル管理
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk、プロセス/データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格異常検出
  - RiskMonitor: ドローダウンやポジション上限監視、ダッシュボード更新
  - KillSwitch: しきい値超過で ExecutionEngine 停止フラグ（data/kill.flag）を書き込む
  - AlertManager: LINE プッシュ通知（クールダウン付き）
  - Streamlit で参照可能な監視ダッシュボード
- Portfolio
  - 候補選定（スコア、上位 N）
  - 重み付け（等金額・スコア加重）
  - セクター集中制限適用
  - ポジションサイズ計算（リスクベース・等分配など）、単元株丸め、aggregate cap
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）などの統計ユーティリティ
- AI
  - ニュース NLP（OpenAI）による銘柄別センチメント取得と ai_scores への格納
  - 市場レジーム判定（ma200 短期乖離 + マクロニュースセンチメント合成）
- Tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）

## セットアップ手順（ローカル）
※ 以下は最小限のセットアップ例です。環境や配布パッケージに応じて適宜調整してください。

1. Python（推奨: 3.10+）を用意。
2. 仮想環境を作成・有効化:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```
3. 依存ライブラリをインストール（代表的なパッケージ）:
   ```bash
   pip install duckdb openai psutil requests streamlit
   ```
   - sqlite3 は標準ライブラリ（Python に同梱）。
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を使って依存管理することを推奨します。
4. データディレクトリの作成:
   ```bash
   mkdir -p data
   ```
5. 環境変数の設定:
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル, デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知設定）
     - PAPER_FILL_MODE（paper_trading の約定モード, instant|partial|never|reject、デフォルト instant）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）
   - 簡易例（`.env`）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     ```

注意: AI 機能（news_nlp / regime_detector）は OPENAI_API_KEY 未設定時にエラーを投げます（呼び出し箇所で ValueError）。Paper Trading 実行は paper_trading DB を使って本番 DB と分離します。

## 使い方（主要な実行方法）

- ExecutionEngine（発注エンジン）を起動
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動しません。
    - 実行中の停止は data/stop_requested.flag を作成することで行います（Monitoring などが検知して停止可能）。
    - プロセス PID は data/execution.pid に書き込まれます。

- Monitoring（監視ループ）を起動
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視テーブルを管理します（監視用 DB は共通）。
  - Monitoring はシステム状態を監視し、KillSwitch を経由して ExecutionEngine 停止フラグ（data/kill.flag）を作成することがあります。
  - 実行開始時にプロセス優先度が "high" に設定されます（set_process_priority）。設定できない場合は警告でスキップします。

- Paper Trading 検証レポート (ツール)
  - 実行:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先して DB を指定）
  - 出力: 標準出力にレポートを出力します（稼働率、注文成功率、送信率、P95 レイテンシなど）。

- Streamlit ダッシュボード（監視）
  - 実行:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを提供します。

- AI モジュールの呼び出し（プログラム内）
  - ニューススコアリング:
    ```py
    from kabusys.ai import score_news
    score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn=duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - いずれも api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定します。

## 重要なランタイム挙動・フラグファイル
- data/stop_requested.flag
  - run_execution/run_monitoring が監視している停止フラグ。存在するとループを終了します。
- data/kill.flag
  - KillSwitch が書き込む停止指示フラグ。ExecutionEngine の起動中にこのファイルが検出されるとエンジン停止処理が行われます。
- data/execution.pid
  - 実行中の ExecutionEngine の PID を格納。SystemMonitor はこの PID をチェックしてプロセスの健全性を判定します。

## トラブルシュート（よくある注意点）
- OpenAI 関連:
  - OPENAI_API_KEY が未設定の場合、score_news / score_regime は ValueError を投げます。環境変数か引数で設定してください。
- psutil 系の操作:
  - プロセス優先度や CPU affinity の設定は権限不足で失敗することがあります（警告でスキップされます）。
- DuckDB / SQLite:
  - paper_trading モードは本番 monitoring.db と分離して PAPER_TRADING_SQLITE_PATH を使います。検証レポート実行時は該当 DB が存在するか確認してください。
- .env 自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を見つけると .env / .env.local を自動読み込みします。テストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## ディレクトリ構成
主要ファイル・モジュールのツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ
  - portfolio/
    - __init__.py
    - portfolio_builder.py        — 候補選定・重み付け
    - position_sizing.py          — 発注株数計算
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py          — モメンタム/バリュー/ボラティリティ計算（DuckDB）
    - feature_exploration.py      — 将来リターン / IC / 統計サマリー
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースを OpenAI でセンチメント化して ai_scores に書込む
    - regime_detector.py          — マクロ + ma200 で市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py            — SQLite スキーマ + 永続化層
    - system_monitor.py           — システム状態監視
    - trade_monitor.py            — 注文滞留・約定異常監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 管理
    - alert_manager.py            — LINE Push 通知
    - monitoring_engine.py        — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py      — Streamlit ダッシュボード（監視）
  - execution/
    - order_manager.py            — OrderManager（発注 API との橋渡し）
    - reconciler.py               — 起動時の自動復旧・突合せ
    - ...（ブローカー関連 / order_repository / order_record 等の実装を含む想定）
  - monitoring/monitoring_db.py   — 監視用 DB の初期化・クラス（前述）
  - その他: data/ (実行時に使うフラグ/DBファイルなど)

（実際のリポジトリには execution 以下に broker_factory、order_repository、order_record 等の実装ファイルが存在します）

## 開発上のメモ
- 型注釈（Python 3.10 の union 型など）を使用しているため、Python 3.10 以上を推奨します。
- DuckDB を利用するモジュールは prices_daily / raw_financials / raw_news 等を想定しており、事前にデータをロードしておく必要があります（研究用途）。
- モジュールは外部 API 呼び出し時にフェイルセーフ（リトライ・ログ・部分失敗時の保護）を考慮した実装になっています。運用時はログを確認して問題の原因を特定してください。

---

必要であれば README に次の情報を追加できます:
- 具体的な requirements.txt / pyproject.toml の内容
- CI やデプロイ手順（systemd / Docker / k8s 起動例）
- 各モジュールの API（関数シグネチャ）一覧と例
- 実例の .env.example ファイル

追加で欲しい内容があれば教えてください。