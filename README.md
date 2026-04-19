# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買フレームワーク「KabuSys」の一部実装です。
本 README はコードベース（src/kabusys 以下）を基に、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 本ドキュメントはリポジトリに含まれるコードを参照して作成しています。実行環境や追加の依存関係（OS固有の設定や外部 API鍵など）が必要です。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / 依存関係
- セットアップ手順
- 環境変数（主要）
- 使い方（主要コマンド）
- よく使うユーティリティ / CLI
- ディレクトリ構成（ファイル一覧）
- 運用上の注意

---

プロジェクト概要
- KabuSys は日本株自動売買のためのモジュール群を提供します。
- 主な要素
  - ExecutionEngine（発注・注文管理、リスク管理等）を起動する run_execution スクリプト
  - 監視プロセス（System / Trade / Risk）を走らせる run_monitoring スクリプト
  - ポートフォリオ構築（候補選定、配分、ポジションサイズ）
  - リサーチ（ファクター計算、特徴量解析）
  - AI 支援モジュール（ニュースのセンチメント付与・レジーム判定） — OpenAI API を利用
  - 監視ログ保存用の SQLite 層と DuckDB を用いた分析層
- 設定は .env ファイル（自動読み込み機能あり）で管理。対話式ウィザードや検証ツールが含まれます。

---

主な機能一覧
- 設定管理
  - .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml）
  - Settings クラスによる型付きアクセス
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行エンジン
  - run_execution.py: ExecutionEngine を起動（paper_trading モード時は MockBroker を使用）
  - ExecutionEngine はリスク管理・オーダー管理・リコンサイル等と連携
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可能）
  - MonitoringEngine: System / Trade / Risk Monitor を束ね、kill switch やアラートを評価
  - MonitoringDB: SQLite に監視ログ / trade_logs / positions / risk_logs / dashboard を永続化
  - KillSwitch: しきい値超過時に data/kill.flag を書いて Execution を停止させる仕組み
- ポートフォリオ構築
  - 候補選定（select_candidates）
  - 等配分 / スコア加重配分（calc_equal_weights, calc_score_weights）
  - セクターキャップ適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes） — lot 単位丸め、利用可能現金でスケール調整など
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
  - DuckDB を利用した高速な分析処理
- AI モジュール
  - news_nlp: raw_news を集約して OpenAI に送信、銘柄ごとにセンチメントを ai_scores テーブルへ書込
  - regime_detector: ETF（1321）の MA200 とマクロ記事センチメントを組み合わせて日次レジーム判定
  - 両モジュールは OpenAI API キー（OPENAI_API_KEY）が必要。失敗時に適切にフォールバックする設計
- ツール
  - paper_verification_report: ペーパートレード DB を集計しパス/フェイル判定するレポート出力

---

前提条件 / 依存関係
- Python 3.10+
  - 型ヒントで | を使用しているため 3.10 以上が推奨
- 主な Python ライブラリ（最低限）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml のパース検証時）
- システム
  - SQLite ファイル（デフォルト: data/monitoring.db）
  - DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- ネットワークアクセス
  - 実際に注文する場合は kabuステーション等の API にアクセスできること
  - OpenAI を利用する場合は API キーとネットワークアクセス

インストール例（仮）
- 仮想環境の作成（例）
  - python -m venv .venv
  - source .venv/bin/activate
- 必要パッケージのインストール（最低限）
  - pip install duckdb psutil openai
  - （検証用）pip install pyyaml

※ 実際の requirements.txt がないため、プロジェクトで想定する追加パッケージがあればそれを使用してください。

---

セットアップ手順（概要）
1. リポジトリをクローンし、作業ディレクトリをルート（pyproject.toml や .git がある場所）にする
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. 環境変数設定
   - 対話式ウィザード:
     - python -m kabusys.config_setup
     - これによりプロジェクトルートに .env が作成されます（デフォルト: data/*.db 等も設定）
   - あるいは .env を手動作成。必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （OpenAI を使う場合）OPENAI_API_KEY を環境に設定
5. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱い
6. DB の初期化:
   - run_execution / run_monitoring は起動時に必要なテーブルを（冪等に）作成します
   - 明示的に init したい場合は簡易スクリプト等を用意してください（monitoring_db.init_monitoring_db を使用）

---

環境変数（主要）
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- API / 認証
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY（AI モジュール利用時）
- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
- 動作制御
  - MONITOR_POLL_INTERVAL（監視ループの秒間隔、run_monitoring の上書き。デフォルト 60）
  - PAPER_FILL_MODE（paper_trading 時の約定モード: instant | partial | never | reject、デフォルト instant）
  - KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag を自動クリア）
  - LOG_LEVEL（デフォルト INFO）
- ログ
  - LOG_DIR（デフォルト logs/）
  - LOG_LEVEL

最低限必要な変数は validate_config で警告/エラーを確認できます。

---

使い方（主要コマンド）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します
  - 起動中の停止は data/stop_requested.flag を作成することで外部から停止できます（スクリプトが監視）
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に production 用 sqlite_path（Settings.sqlite_path）を使用します
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）
- AI レジーム判定 / ニューススコアリング
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をスクリプトやスケジューラから呼ぶ
  - 実行には OPENAI_API_KEY の設定が必要
- ログ設定
  - 各起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び、logs/<app_name>.log に日次ローテーションで出力します

停止フラグ / Kill Switch
- data/stop_requested.flag: run_execution/run_monitoring が存在を確認してグレースフルに終了します
- data/kill.flag: KillSwitch が書き込み、ExecutionEngine 側で検出して停止する仕組み。KILL_FLAG_CLEAR_ON_START=1 で起動時にクリア可能（本番では推奨しない）

---

ユーティリティ / CLI（まとめ）
- python -m kabusys.config_setup — .env ウィザード
- python -m kabusys.validate_config — 設定検証
- python -m kabusys.run_execution — ExecutionEngine 起動
- python -m kabusys.run_monitoring — SystemMonitor（ポーリング）起動
- python -m kabusys.tools.paper_verification_report — ペーパートレード検証レポート

---

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py — Settings / .env 自動読み込みロジック
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - utils/
    - __init__.py
    - logging_setup.py — ログ設定ユーティリティ（console + 日次ローテーションファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化と永続化 API
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - trade_monitor.py — （trade 関連の監視 — 一部実装あり）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — （アラート送信管理）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注株数決定 ロジック
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計
    - __init__.py
  - ai/
    - news_nlp.py — ニュースの LLM ベースセンチメント集計 & ai_scores 書き込み
    - regime_detector.py — MA200 と LLM で市場レジーム判定
    - __init__.py
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading の検証レポート生成

その他
- デフォルトで期待されるファイル・ディレクトリ
  - data/ — SQLite / PID / フラグファイル等（実行時に自動作成されることがある）
  - logs/ — ログ出力先（logging_setup で自動作成を試みます）
  - config/*.yaml — 各種設定テンプレート（存在しない場合は警告）

---

運用上の注意
- 本番環境（KABUSYS_ENV=live）では環境変数や通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等）を慎重に設定してください。validate_config が本番向けチェックを行います。
- kill.flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番では推奨されません（誤って Kill Switch を無効化する恐れがあります）。
- OpenAI API を使う機能は外部サービスに依存するため、ネットワークや API レート制限に起因する失敗を考慮して下さい（コード中にリトライ・フォールバック処理を備えています）。
- DB の変更（スキーマ変更）やマイグレーションがある場合はバックアップを取り、マイグレーション手順を慎重に実行してください。

---

参考: よくある操作例
- .env を作成して設定を検証してから監視プロセスを起動する
  1. python -m kabusys.config_setup
  2. python -m kabusys.validate_config
  3. python -m kabusys.run_monitoring
- Execution を paper_trading モードで試す
  1. KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  2. 実行結果やトレードログは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に保存されます
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要部分を説明しています。詳細な実装や追加のオプション、テスト手順、CI 設定等はプロジェクトの他ドキュメントやコードコメントを参照してください。必要であれば、実行例や sample .env、requirements.txt のテンプレートを追加で作成しますので指示してください。