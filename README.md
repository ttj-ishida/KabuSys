# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株の自動売買システム KabuSys のコアモジュール群です。  
本 README はコードベース（src/kabusys/*.py）を元に、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤です。主な機能群は以下です。

- 実行エンジン（ExecutionEngine）による発注処理（実口座またはペーパートレード）
- 監視（Monitoring）：プロセス/システム状態、注文の滞留や約定異常、リスク監視、Kill Switch
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算・セクター制限）
- リサーチ／ファクター計算（モメンタム／ボラティリティ／バリュー等）
- AI（OpenAI）ベースのニュース NLP（銘柄ごとのセンチメント評価）および市場レジーム判定
- ユーティリティ（プロセス優先度設定、各種ツール、検証・設定ウィザード）
- 永続化：DuckDB（分析用） + SQLite（監視ログ / ペーパートレード DB）

設計方針の一部：
- 本番 DB とペーパートレード DB を分離（KABUSYS_ENV により切替）
- ルックアヘッドバイアスを避ける実装（日時の扱いに注意）
- フェイルセーフ：外部 API 失敗時は安全なフォールバック動作
- テストや CI 用に各種関数は副作用を持たない純粋関数として設計されている箇所が多数

---

## 主な機能一覧（抜粋）

- 設定・起動
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行・監視
  - 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - 監視ポーリング起動スクリプト: python -m kabusys.run_monitoring
- 監視コンポーネント
  - SystemMonitor: システム資源・データ鮮度・Execution プロセス確認
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件成立時に data/kill.flag を作成して Execution を停止
  - MonitoringDB: SQLite に監視ログを永続化
  - MonitoringEngine: 上記モニタ群をまとめてポーリング・アラート発行
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重、リスクベースのポジションサイズ計算、セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI
  - news_nlp: raw_news を OpenAI に問い合わせて銘柄別 ai_score を生成・書き込み
  - regime_detector: マクロ記事 + ETF MA を組み合わせて市場レジームを判定
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## 前提・依存

必須（主なもの）
- Python 3.10+ を想定
- パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - （開発時）PyYAML（config 検証で利用、なくても実行可能だが YAML 検証をスキップ）

実際のインストールはプロジェクトの requirements.txt / pyproject.toml を参照してください（本コードベースには示されていません）。

---

## セットアップ手順（ローカル実行向け）

1. リポジトリをクローン
   - git clone <repo>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （必要に応じて PyYAML などを追加: pip install pyyaml）

4. 環境変数設定（.env）
   - プロジェクトルートに .env を作成するか、ウィザードを使う:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主なオプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB）
     - PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（1=起動時に kill.flag をクリア、デフォルト 0 を推奨）
   - 自動ロード:
     - .env / .env.local がプロジェクトルートにある場合、自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict オプションをつけると警告も失敗扱い（exit 1）

---

## 使い方（主要コマンド）

- 設定ウィザード（対話式で .env を生成）
  - python -m kabusys.config_setup

- 設定の静的検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジンスクリプト（ExecutionEngine を起動）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録します（本番 DB と完全分離）。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行時は data/execution.pid に PID を書きます。停止は stop flag や kill.flag によって制御されます。

- 監視ポーリング（SystemMonitor の起動）
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 SQLITE_PATH を使用するようになっています（run_monitoring の挙動）。
    - 停止は data/stop_requested.flag の検出でループを抜けます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 簡易的に稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL を判定します。
  - DB の参照先は --db オプション、環境変数 PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db の順で決まります。

- AI 機能（news_nlp / regime_detector）
  - 実行には OPENAI_API_KEY が必要です（api_key 引数で明示的に渡すことも可能）。
  - news_nlp.score_news, regime_detector.score_regime の呼び出しで DuckDB 接続を渡して利用します。
  - 実行は CLI ではなくライブラリ関数として利用する設計です（運用側でスケジュールして呼び出す想定）。

---

## 停止・Kill Switch の仕組み

- stop_requested.flag（run_execution / run_monitoring で使用）
  - プロジェクトルートの data/stop_requested.flag を作成すると、監視ループや実行スレッドが検知して安全に停止します。

- kill.flag（KillSwitch）
  - kill.flag（パスは Settings.kill_flag_path、デフォルト data/kill.flag）を作成すると ExecutionEngine 側が停止します。
  - KillSwitch は監視結果（ドローダウンやポジション上限など）を評価して flag を書き込みます。
  - 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（起動時に自動クリアすると危険です）。

---

## 主要な環境変数（抜粋とデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY（AI 機能を使う場合）
- KABUSYS_ENV = development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH = data/kabusys.duckdb
- SQLITE_PATH = data/monitoring.db
- PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
- PAPER_FILL_MODE = instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL = INFO（等）
- MONITOR_POLL_INTERVAL = 60（run_monitoring のポーリング間隔秒）
- KILL_FLAG_CLEAR_ON_START = 0 | 1
- PID_FILE_PATH / KILL_FLAG_PATH など（Settings で参照）

詳しい説明は src/kabusys/config.py を参照してください（Settings クラスに各項目の説明があります）。

---

## 開発者向けメモ

- DB 初期化:
  - run_execution/run_monitoring 起動時に monitoring DB のテーブル作成（init_monitoring_db）が行われます（冪等）。
- ロギング:
  - 各モジュールは logging を利用しています。LOG_LEVEL を環境変数で設定してください。
- テスト性:
  - 多くのユーティリティ関数は副作用を持たない純粋関数として実装されています（例: portfolio/*.py, research/*.py）。単体テストが書きやすい設計です。
- 外部 API 呼び出し:
  - OpenAI へのコールは retry/backoff とレスポンスバリデーションが入っていますが、API キーやネットワーク障害へのフォールバック動作を確認してください。

---

## ディレクトリ構成（src/kabusys 内の主要ファイル）

- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動ロード・Settings クラス）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py — ニュース NLP（OpenAI）で ai_scores 生成
  - regime_detector.py — マクロ + ETF MA による市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — 条件に応じた kill.flag 書き込み
  - monitoring_engine.py — 各 Monitor のまとめ（ポーリング）
  - alert_manager.py — （アラート通知管理。ファイルは本コード断片では未完）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算・キャップ処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー等の計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

その他: data/（ランタイムで作られる PID / flag / DB ファイル等を置く想定）、config/*.yaml（運用用設定テンプレート）

---

## よくある操作例

- .env を作って設定検証まで行う（推奨初回手順）
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ペーパートレードでエンジンを起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視デーモンを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading の検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 注意事項 / 運用上の推奨

- .env は絶対にリポジトリにコミットしないこと（config_setup.py のファイルヘッダにも明記）。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨（起動時の自動クリアを禁止）。
- OpenAI を使う機能は API コスト・レイテンシ・利用制限に注意してスケジュールしてください。
- 監視・Kill Switch の設定値（ドローダウン閾値や最大ポジション数など）は運用方針に合わせて調整してください。

---

この README はコード内ドキュメント（docstring・コメント）をもとに作成しています。詳細な実装や追加オプションは各モジュール（src/kabusys/*.py）を参照してください。必要であれば README の補足（起動シーケンス図、設定例ファイルのテンプレート、運用チェックリストなど）を追記できます。