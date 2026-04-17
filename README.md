# KabuSys — README (日本語)

このリポジトリは日本株自動売買フレームワーク「KabuSys」の一部実装です。戦略のポートフォリオ構築、発注エンジン、監視、研究（ファクター計算）、AI を用いたニューススコアリングなどのコンポーネントを含みます。本 README はコードベース（src/kabusys 以下）をもとに使い方・セットアップ方法をまとめたものです。

※ 開発中のコードスナップショットに基づくドキュメントです。実運用前に十分なテストを行ってください。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 実行／使い方
- 重要な環境変数
- ファイル・ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買システム向けのライブラリ/ツール群です。
- 主な機能は「シグナル → 銘柄選定・配分 → 発注 → 監視・リスク管理 → ログ・レポート」です。
- DuckDB / SQLite を使って市場データ・ログ・監視情報を保存します。
- OpenAI（gpt-4o-mini 等）を使ったニュース NLP による銘柄センチメント評価や、市場レジーム判定モジュールを含みます。
- Paper Trading モードをサポートし、本番 DB とは分離して検証できます。

主な機能一覧
- portfolio:
  - 候補選定 (select_candidates)
  - 等重・スコア重み計算 (calc_equal_weights, calc_score_weights)
  - ポジションサイズ算出 (calc_position_sizes)
  - セクター上限適用・レジーム乗数 (apply_sector_cap, calc_regime_multiplier)
- execution:
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / Reconciler（クラッシュ復旧・突合）
  - ブローカー抽象層（実ブローカー／MockBroker 切替）
- monitoring:
  - SystemMonitor / TradeMonitor / RiskMonitor、MonitoringEngine のポーリング
  - 監視ログ永続化（SQLite via MonitoringDB）
  - KillSwitch（リスクトリガで停止フラグを出す）
  - AlertManager（LINE プッシュ通知）
  - Streamlit ダッシュボード（監視 UI）
- research:
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC（情報係数）・特徴量サマリ
- ai:
  - news_nlp: raw_news を LLM に送り銘柄ごとの ai_score を生成して ai_scores テーブルに書き込む
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して市場レジームを判定
- tools:
  - paper_verification_report: Paper Trading DB（デフォルト data/paper_trading.db）から検証レポートを生成

セットアップ手順（ローカル）
1. リポジトリをクローン / ダウンロードし、プロジェクトルートに移動する。
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（最低限）
   - pip install duckdb psutil requests streamlit openai
   - （requirements.txt があれば pip install -r requirements.txt）
4. データディレクトリを作成
   - mkdir -p data
5. 環境変数を設定
   - プロジェクトルートに .env または .env.local を配置して必要な変数を設定できます。
   - 自動読み込みはデフォルトで有効（.env / .env.local をロード）。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
6. 必要な初期 DB は実行時に自動で作成・マイグレーションされます（monitoring 用テーブルなど）。

重要な環境変数（代表）
- 必須（機能を使う場合）
  - JQUANTS_REFRESH_TOKEN — J-Quants API（データ取得）を使う場合
  - KABU_API_PASSWORD — kabuステーション API を使う場合（発注等）
- OpenAI 関連
  - OPENAI_API_KEY — AI 機能（news_nlp / regime_detector）を使う場合に必要
- 動作モード・パス等
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
    - paper_trading: MockBroker を使用し、Paper Trading 専用 SQLite を使う
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — KillSwitch が書くフラグ（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject、デフォルト "instant"）
  - LOG_LEVEL — ロギングレベル（DEBUG/INFO/...）
- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。

使い方（代表的なコマンド）
- 実行環境の前提: プロジェクトルートから実行するか、PYTHONPATH に src を追加してください。
  - 推奨: export PYTHONPATH=src  (Windows: set PYTHONPATH=src)

1) ExecutionEngine を起動（発注エンジン）
- 実行ファイルを直接:
  - python src/kabusys/run_execution.py
- モジュールとして（PYTHONPATH=src を設定した上で）:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV が paper_trading の場合は MockBroker を使用し、paper_sqlite_path にログを記録して本番 DB と分離します。
  - 起動時に data/stop_requested.flag が既にあると起動せず終了します。
  - 停止は data/stop_requested.flag を作成することで検出され、エンジンを停止します。

2) Monitoring を起動（System / Trade / Risk のポーリング）
- 実行:
  - python src/kabusys/run_monitoring.py
  - または python -m kabusys.run_monitoring （PYTHONPATH=src 前提）
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
- 停止:
  - run_monitoring はプロジェクトルートから data/stop_requested.flag の存在を検知するとループを抜けて終了します。

3) Streamlit ダッシュボード（監視 UI）
- 実行例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開くので、MonitoringEngine を並行して動かしているときの可視化に便利です。

4) Paper Trading 検証レポート生成（コマンドライン）
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD  レポート開始日
    - --to YYYY-MM-DD    レポート終了日
    - --db PATH          SQLite DB パス（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）
- 出力:
  - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を標準出力に表示し PASS/FAIL を判定します。

5) AI モジュール（ライブラリ呼び出し）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（duckdb.connect(...) で得た接続）を渡して呼び出します。
  - OPENAI_API_KEY または api_key 引数で API キーを指定してください。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジームを計算して market_regime テーブルに書き込みます。
- 注意:
  - これらは CLI ではなく関数呼び出し（スクリプト等からインポートして利用）する想定です。
  - API キーが未設定の場合は ValueError を送出します。

プロセス制御 / 停止フラグ
- stop_requested.flag
  - run_execution.py / run_monitoring.py は data/stop_requested.flag の存在を見てループを終了します（手動停止用）。
- kill.flag
  - KillSwitch（監視）モジュールは条件を満たした場合、Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を記述して書き込みます。これにより運用側が検知して手動対応できます。
- execution.pid
  - ExecutionEngine は PID ファイル（設定に基づく）を作成します。SystemMonitor はこの PID を参照してプロセスの生存をチェックします。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py          — パッケージ定義（バージョン等）
  - config.py            — 環境変数 / 設定読み込みロジック（.env 自動ロード・Settings）
  - run_monitoring.py    — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py     — ExecutionEngine 起動スクリプト（paper_trading 分離対応）
  - ai/
    - news_nlp.py        — ニュース NLP（OpenAI）による銘柄スコア化
    - regime_detector.py — 市場レジーム判定モジュール
  - monitoring/
    - monitoring_db.py   — SQLite 監視 DB レイヤ（テーブル作成・読み書き）
    - system_monitor.py  — システム状態・データ鮮度監視
    - trade_monitor.py   — 注文滞留・約定異常監視
    - risk_monitor.py    — ドローダウン・ポジション上限監視
    - kill_switch.py     — フラグ書込みによる停止シグナル
    - alert_manager.py   — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねてポーリング
    - streamlit_dashboard.py — Streamlit ベース監視ダッシュボード（UI）
  - execution/
    - order_manager.py   — 発注管理（OrderManager）
    - reconciler.py      — 起動時自動復旧 / 突合（Reconciler）
    - ...（ブローカー抽象等 他ファイル）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数算出（丸め・制限）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

設計上の注意点・補足
- Settings クラスは KABUSYS_ENV に応じた動作切替や、.env / .env.local の自動読み込みを行います。
- Monitoring の DB 初期化（テーブル生成・簡易マイグレーション）は init_monitoring_db() によって実行時に行われます。
- Paper Trading モードは本番 DB と分離されるよう設計されています。安全のため paper_trading 時は PAPER_TRADING_SQLITE_PATH を正しく設定してください。
- AI を使う機能は外部 API（OpenAI）に依存します。API エラーはリトライやフェイルセーフ（score=0 等）で扱う実装になっていますが、API 利用料・レイテンシの考慮が必要です。
- Streamlit UI は監視 DB を読み取り専用で開きます（可視化用途）。並行して MonitoringEngine を動かしながら確認する想定です。

トラブルシューティング（よくある問合せ）
- 「.env が読み込まれない」: KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認、またはプロジェクトルート検出が .git / pyproject.toml に依存します。必要であれば手動で環境変数を export してください。
- 「Monitoring が DB を開けない」: ファイルパスとアクセス権を確認。streamlit は read-only モードで URI を組み立てて開きます。
- 「Execution が起動しない」: data/stop_requested.flag が存在すると起動せず終了します。不要なら削除してください。

ライセンス・貢献
- 本リポジトリのライセンス情報が別途ある場合はそちらをご確認ください。パッチや改善提案は Pull Request を通じて歓迎します。

---

この README はコードベースの現状（src/kabusys 以下の実装）に基づいています。実際の運用に際しては環境変数やブローカー API の仕様、データベースのバックアップ・権限などを十分に確認してください。必要であれば README を更新しますので、補足したい部分や質問があれば教えてください。