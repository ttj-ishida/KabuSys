# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」の一部実装です。本ドキュメントはコードベース（src/kabusys 配下）を基に、導入・実行方法、主要機能やディレクトリ構成を日本語でまとめた README です。

注意: 実運用前に各種設定（APIキー・パス等）を必ず確認してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・リサーチ・監視機能群を備えたシステムです。本コードベースには以下の主要領域が含まれます。

- Execution（発注エンジン、OrderManager、Reconciler 等）
- Monitoring（システム監視、トレード監視、リスク監視、アラート）
- Portfolio（候補選定・配分計算・ポジションサイズ計算）
- Research（ファクター計算、特徴量解析）
- AI（ニュース NLP によるセンチメント、レジーム判定）
- Tools（Paper Trading 検証レポート生成等）
- Utils（プロセス優先度など共通ユーティリティ）
- 設定管理（環境変数ベースの Settings）

設計方針の一例:
- DuckDB はリサーチ（価格・財務テーブル）用、SQLite は監視ログや注文リポジトリ用に用いる。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離され、モックブローカーを使用する。
- OpenAI を用いた NLP 機能は API キーを環境変数で受け取る（失敗時はフェイルセーフで継続する実装が多い）。

---

## 主な機能一覧

- 実行 / 発注
  - ExecutionEngine を起動して注文作成・管理（OrderManager、OrderRepository、RiskManager、Reconciler を含む）
  - 再起動後の自動リコンシリエーション（Reconciler）
  - Paper Trading モード：MockBrokerClient + data/paper_trading.db（本番 DB と分離）

- 監視（Monitoring）
  - SystemMonitor: CPU・メモリ・ディスク・データ鮮度・プロセス生存チェック
  - TradeMonitor: 滞留注文・約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件に応じてデータ/kill.flag を書き込み Execution を停止させる
  - AlertManager: LINE Messaging API による通知（オプション）
  - Streamlit ベースの監視ダッシュボード（read-only 接続）

- ポートフォリオ構築（純粋関数）
  - 銘柄選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース配分等）

- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI 経由）
  - ニュースのセンチメントを銘柄単位でスコア化して ai_scores テーブルに保存
  - マクロニュースと ETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）

- ツール
  - paper_verification_report: Paper Trading DB から稼働率、注文成功率、レイテンシ等の検証レポートを出力

---

## セットアップ手順（ローカル開発向け）

1. Python 環境
   - Python 3.9+ を想定（実装上の互換性を確認してください）

2. 必要パッケージ（代表例）
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit
   - （必要に応じて）その他のライブラリ

   例:
   pip install duckdb psutil openai requests streamlit

   ※ requirements.txt が提供されていない場合はプロジェクトに合わせて依存を整備してください。

3. プロジェクトルートに .env を用意（任意）
   - Settings モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動探索して .env を読み込みます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）
   - KABUSYS_ENV: 起動環境 ("development" | "paper_trading" | "live")（デフォルト: development）
   - PAPER_FILL_MODE: paper_trading の約定動作 ("instant" | "partial" | "never" | "reject")（デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - LOG_LEVEL: ログレベル（"DEBUG","INFO",...）

   サンプル .env:
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   PAPER_FILL_MODE=instant

5. データディレクトリ
   - デフォルトで data/ に DB やフラグファイルが置かれます（data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid 等）
   - 必要に応じてディレクトリを作成してください。

---

## 使い方（主要スクリプト / コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - デフォルト（production として SQLite は Settings.sqlite_path を使用）
  - KABUSYS_ENV=paper_trading にすると paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用
  実行例:
  python -m kabusys.run_execution

  動作:
  - data/stop_requested.flag が存在する場合は起動を中止
  - data/execution.pid に PID を書き込む（設定により）
  - 停止は data/stop_requested.flag を作成することで行う（外部から停止させる用途）

- 監視ループ（SystemMonitor）を起動
  実行例:
  python -m kabusys.run_monitoring

  オプション / 環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - 監視は Settings.sqlite_path（本番 DB）を常に使用する設計です

- Streamlit 監視ダッシュボード（読み取り専用）
  実行例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  実行例:
  python -m kabusys.tools.paper_verification_report
  または
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
  --db PATH で DB を指定（優先）

- AI 関連（ニュース NLP / レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行には OPENAI_API_KEY（または引数で api_key）必須

- フラグ制御
  - data/stop_requested.flag: run_execution/run_monitoring が監視している停止フラグ（存在すると起動停止/ループ停止する）
  - data/kill.flag: KillSwitch が書き込む停止要求（ExecutionEngine 停止のために使用）
  - PID ファイル: data/execution.pid（pid の存在を SystemMonitor が確認）

---

## 設計・運用上のポイント / 注意事項

- 環境依存設定
  - Settings クラスは .env と OS 環境変数を組み合わせて初期化します。自動ロードが行われるため .env の扱いに注意してください。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると .env の自動読込を抑制できます（テスト用）。

- Paper Trading の分離
  - KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient を用い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込まれます。本番 SQLite（SQLITE_PATH）とは完全に分離されます。

- フェイルセーフ
  - 多くの AI / 外部 API 呼び出しは失敗時にフォールバック（0.0 等）するか、例外を外へ投げずにログに落とすよう実装されています（運用での冗長性を重視）。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でスキーマを作成し、簡単なマイグレーション（カラム追加等）も行います。

- 権限
  - set_process_priority 等は権限により失敗することがあります（警告ログを出してスキップ）。root 権限なしでも動作するよう設計されていますが、期待する優先度を得るには権限が必要です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なファイルと役割の概観です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数読み込み、バリデーション）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading の挙動分離含む）
  - tools/
    - paper_verification_report.py
      - Paper Trading DB 検証レポート生成 CLI
  - utils/
    - process_priority.py
      - プロセス優先度 / CPU affinity ユーティリティ
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - （その他、broker_factory 等の実装を持つ想定）
  - data/（runtime）
    - monitoring.db（デフォルト SQLITE_PATH）
    - kabusys.duckdb（デフォルト DUCKDB_PATH）
    - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
    - stop_requested.flag / kill.flag / execution.pid

---

## 追加情報・トラブルシューティング

- DB が見つからない / 読取専用で開く必要がある場合
  - streamlit_dashboard は SQLite を read-only モードで開く（URI + ?mode=ro）。DB が存在しない場合はエラーメッセージが表示されます。

- OpenAI API の呼び出し失敗
  - レート制限やネットワークエラーにはリトライ処理が実装されていますが、APIキー未設定は即時例外になります。テスト時は API 呼び出し関数をモックすることを推奨します。

- ログレベル
  - 環境変数 LOG_LEVEL で制御可能。実行スクリプトは basicConfig(level=logging.INFO) を呼んでいますが、詳細なデバッグが必要な場合は LOG_LEVEL=DEBUG を設定してください。

---

## 開発上のメモ

- 多くのモジュールは外部接続（DuckDB / SQLite / Broker / OpenAI）を引数として受け取り、テストしやすい設計になっています。ユニットテストでは接続や API 呼び出しを差し替えて利用してください。
- Portfolio / Research モジュールは「純粋関数群」として DB 参照を限定している箇所があり、再利用性が高くなっています。

---

README は以上です。実行や導入で不明点があれば、具体的なエラーや使いたい機能（例: Paper Trading レポートの実行方法、AI スコア収集の実行）を教えてください。必要に応じてコマンド例や .env のテンプレートを補足します。