# KabuSys — README

本リポジトリは日本株向けの自動売買・研究・監視ツール群「KabuSys」のコードベースです。以下はコードベースの概要・機能・セットアップ・使い方・ディレクトリ構成の簡潔な説明です。

---

プロジェクト概要
- KabuSys は自動売買エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター研究、AI（ニュース NLP / レジーム判定）などを含む総合的な日本株自動売買フレームワークです。
- SQLite（監視ログ等）と DuckDB（時系列・財務データ解析）をデータ永続化・分析に利用します。
- 本番（live）・ペーパートレーディング（paper_trading）・開発（development）の複数実行環境を想定しています（KABUSYS_ENV）。

主な機能一覧
- Execution（実行）
  - ブローカー経由での発注管理・注文状態同期・リコンシリエーション（再起動後の自動復旧）。
  - ペーパートレーディングモード時は MockBroker を使い、本番 DB と分離して `data/paper_trading.db` に記録。
  - リスク管理（ポジション上限・ドローダウン等）。
- Monitoring（監視）
  - システムリソース・Execution プロセスの生存確認・データ鮮度チェック。
  - 注文滞留／約定異常の検出、リスクイベントのログ化、LINE 通知（AlertManager）。
  - KillSwitch によるフラグファイルでの ExecutionEngine 強制停止。
  - Streamlit ダッシュボード（監視情報表示）。
- Portfolio（配分設計）
  - 候補選定、等金額／スコア加重配分、セクター上限適用、ポジションサイズ計算（単元株丸め、aggregate cap）。
- Research（研究）
  - ファクター計算（モメンタム／バリュー／ボラティリティ等）、将来リターン、IC 計算、統計サマリ。
  - DuckDB を使った SQL＋Python 実装でローカル解析可能。
- AI（LLM）
  - ニュース記事を OpenAI（gpt-4o-mini 等）でセンチメント評価し ai_scores に記録。
  - マクロニュース＋ETF MA200 を組み合わせた市場レジーム（bull/neutral/bear）判定。
- ツール
  - Paper Trading 用の検証レポート生成スクリプト（レイテンシ、成功率、稼働率などを出力）。

セットアップ手順（概要）
1. Python と依存パッケージ
   - 推奨: Python 3.10+（コードは typing の新構文を利用しています）
   - 主要依存（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit（ダッシュボード使用時）
   - インストール例:
     ```
     pip install duckdb psutil requests openai streamlit
     ```
   - （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

2. プロジェクトルートの特定と .env
   - Settings モジュールはプロジェクトルート（.git または pyproject.toml がある場所）を自動検出し、`.env` / `.env.local` を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - まず `.env.example` を参考に `.env` を作成し、以下の必須環境変数を設定してください（用途に応じて追加で設定可）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定（AI 機能を使う場合）

3. データディレクトリ
   - デフォルトの DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
     - Monitoring SQLite: data/monitoring.db（Settings.sqlite_path）
     - Paper Trading SQLite: data/paper_trading.db（Settings.paper_sqlite_path）
     - PID / kill flag: data/execution.pid / data/kill.flag
   - 必要に応じてディレクトリを作成してください（多くの処理で親ディレクトリを自動作成しますが、パーミッション等に注意）。

4. （任意）環境モード切替
   - KABUSYS_ENV=development|paper_trading|live
   - paper_trading の場合、実行コンポーネントは MockBroker を使用し、paper_sqlite_path に書き込みます。

使い方（主要エントリポイント）
- 監視ループの起動（Monitoring）
  - デフォルトは本番 sqlite_path を使って監視（KABUSYS_ENV に関係なく本番監視 DB を使用する旨に注意）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）でオーバーライド可能（デフォルト 60 秒）
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - 停止:
    - プロセスに Ctrl+C
    - またはプロジェクトルートの data/stop_requested.flag を作成するとループは検知して終了します。

- 実行エンジンの起動（ExecutionEngine）
  - paper_trading の場合は MockBroker を使用（DB は paper_sqlite_path）
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 停止:
    - data/stop_requested.flag を作成すると Engine に停止命令が送られます。
    - Execution は data/execution.pid に PID を書きます（pid ファイルの存在/整合を SystemMonitor がチェックします）。

- Streamlit ダッシュボード（監視可視化）
  - 実行例:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 読み取り専用で DB を開きます（起動前に MonitoringEngine が DB に書き込んでいる必要があります）。

- Paper Trading 検証レポート
  - 実行例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB は data/paper_trading.db。`--db` オプションで変更可。

- AI モジュールの利用例（プログラム内呼び出し）
  - OpenAI API キーを環境変数または関数引数で渡して使用します。
  - 例（ニューススコア付与）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 4, 1), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 4, 1), api_key="sk-...")
    ```

重要な設定（Settings）
- 自動 .env 読み込みの挙動:
  - 優先順: OS 環境 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化
- KABUSYS_ENV: development / paper_trading / live（不正値は例外）
- PAPER_FILL_MODE: paper_trading のモック約定挙動（instant | partial | never | reject）
- その他監視・閾値等は Settings から取得可能（CPU/MEM/DISK の閾値や PID / FLAG パス等）

運用に関する補足
- Monitoring は常に本番 sqlite_path（data/monitoring.db 相当）を使用します。実行時に KABUSYS_ENV が何であっても監視 DB は同じです。
- Execution の paper_trading モードは本番 DB と完全分離するため安全に検証可能です。
- KillSwitch は条件を満たした場合に data/kill.flag を書き込み、Execution の強制停止トリガーとして機能します。
- Process priority / CPU affinity を設定するユーティリティを内部で使用しています（管理者権限が必要な操作は失敗しても警告を出してスキップします）。

ディレクトリ構成（主要ファイルと役割）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョンなど）
  - config.py — 環境変数 / Settings 管理（.env 自動ロード、必須キーチェック）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替対応）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 初期化・読み書き層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — LINE push 通知ラッパ
    - monitoring_engine.py — 複数モニタをまとめるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注管理（Order State Machine の外向き API）
    - reconciler.py — 起動時リコンシリエーション
    - （その他ブローカーインタフェース・エンジンの実装ファイル）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクター制限・レジーム乗数
    - position_sizing.py — 発注株数・リスク制限
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC 等の解析
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI を利用）および ai_scores への書込みロジック
    - regime_detector.py — マクロ + ETF MA を使ったレジーム判定（OpenAI を利用）
  - data/  （実行時に DB / flag / pid が置かれる想定。リポジトリに含まれていない場合は作成）
- その他:
  - pyproject.toml / .git / .env.example （プロジェクトルートに存在する想定）

トラブルシューティング（よくある注意点）
- .env の自動読み込みに失敗する場合:
  - プロジェクトルートが正しく検出されているか（.git か pyproject.toml が必要）を確認
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認
- OpenAI 関連:
  - API キーが未設定だと score_news / score_regime は ValueError を投げます。テストでは関数引数で api_key を渡すことも可能。
- DuckDB / SQLite のパス:
  - 権限やファイルロックで接続エラーが出る場合はパスとアクセス権を確認してください。
- PID / stop flag / kill flag:
  - 管理用ファイル（data/execution.pid, data/stop_requested.flag, data/kill.flag）を使ってプロセス管理をしています。手動操作は慎重に行ってください。

貢献・拡張のヒント
- AI 呼び出し部分はリトライ・エラーハンドリングを含む実装になっています。テスト時は _call_openai_api をパッチして模擬レスポンスを返すことでユニットテストが容易です。
- DuckDB を用いたファクター計算は SQL の最適化が効くため、大量データの分析に適しています。prices_daily / raw_financials 等のテーブルスキーマを拡張して更改可能です。

---

この README はコード内のドキュメンテーションとエントリポイントに基づいて作成しています。実行や運用に先立ち、`.env.example` を参考に環境変数を設定の上、依存ライブラリをインストールしてから稼働させてください。必要があれば各モジュールの詳細な開発ドキュメント（API仕様・DBスキーマなど）も追って作成できます。