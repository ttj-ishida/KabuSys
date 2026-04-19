KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なフレームワークです。
主な機能は戦略のポートフォリオ構築、ポジションサイズ算出、リサーチ用ファクター計算、
AI（LLM）を用いたニュースセンチメント評価、実行エンジン（発注）および監視/アラート機能です。

設計方針の要点
- DB 層は DuckDB（分析）と SQLite（監視・注文ログ）を利用
- Paper Trading（ペーパートレード）と Live（本番）を明確に分離
- LLM（OpenAI）を利用した機能は API キーを明示的に必要とする
- .env による環境変数管理をサポート、対話式ウィザードで初期化可能
- 監視・Kill Switch による安全停止機構を備える

主な機能
--------
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額・スコア重み付け
  - セクター上限の適用、レジーム乗数
  - ポジション数（株数）計算（risk_based / equal / score）
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（LLM）機能
  - ニュース記事のセンチメントスコア算出（OpenAI を利用）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（regime detector）
- 実行エンジン（ExecutionEngine）
  - 本番と paper_trading の分離（paper_trading では MockBroker を使用）
  - リスク管理、注文管理、再整合処理等
- 監視（Monitoring）
  - システム状態（CPU / メモリ / ディスク）、データ鮮度、注文ログの監視
  - Kill Switch（条件に応じて data/kill.flag を作成）
  - ログと監視 DB（SQLite）への永続化
- ツール
  - paper_trading の検証レポート生成スクリプト（paper_verification_report）

動作要件（推奨）
----------------
- Python 3.9+（typing の union 表記などを含むため）
- 推奨パッケージ（主要依存）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合に必要）
- 標準ライブラリ: sqlite3, logging, threading など

セットアップ手順
----------------
1. リポジトリをクローン／展開
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt がある場合はそちらを使用）
4. .env の初期化（対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話に従って J-Quants トークン / kabu API パスワード 等を入力
     - 生成・更新される .env は絶対に Git にコミットしないこと
5. 設定検証
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱い（exit code 1）になります

重要な環境変数（抜粋）
---------------------
以下は本リポジトリ内で参照される主な環境変数とデフォルト値（未設定時の挙動）です。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (LLM 機能を使う際に必要)
- KABUSYS_ENV (デフォルト: development)
  - 有効値: development, paper_trading, live
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 時に使用
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (デフォルト: logs/)
- MONITOR_POLL_INTERVAL (監視ループ間隔秒。run_monitoring のみ。デフォルト: 60)
- PAPER_FILL_MODE (paper_trading の fill モード: instant/partial/never/reject)

使い方（ランタイム）
-------------------

1) 実行エンジン（ExecutionEngine）を起動
- 通常起動:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag があると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。停止フラグの監視で安全停止します。

2) 監視ループを起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 監視は環境にかかわらず本番 sqlite_path を使って監視 DB を初期化（init_monitoring_db）
  - 停止はプロジェクト root/data/stop_requested.flag の存在検出または Ctrl+C

3) 設定検証（起動前推奨）
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

4) .env の対話式作成・更新
- python -m kabusys.config_setup

5) Paper Trading 検証レポートの生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

運用に関する注意
----------------
- .env を誤ってコミットしないこと（secret を含むため）。
- 本番 (KABUSYS_ENV=live) では kill flag 設定や KILL_FLAG_CLEAR_ON_START の値に注意する（自動クリアは危険）。
- OpenAI を使う機能（news_nlp / regime_detector）は API 利用に伴うコスト・レイテンシが発生します。API キーとモデルを適切に管理してください。
- 監視機能は data/kill.flag を作成する可能性があります。Kill Switch の条件はコード内のリスク監視ロジックに基づきます。

主要ファイル・ディレクトリ構成
----------------------------
（主要なモジュールと役割の簡易ツリー）

src/
  kabusys/
    __init__.py                  — パッケージ定義、バージョン
    config.py                    — 環境変数読み込み・Settings
    config_setup.py              — .env 対話式ウィザード
    validate_config.py           — 起動前設定検証 CLI
    run_execution.py             — ExecutionEngine 起動スクリプト
    run_monitoring.py            — Monitoring ポーリング起動スクリプト

    utils/
      logging_setup.py           — 統一的なログ設定ユーティリティ
      process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ
      __init__.py

    portfolio/
      portfolio_builder.py       — 候補選定・重み計算
      position_sizing.py         — 株数算出・投下制限・丸め処理
      risk_adjustment.py         — セクターキャップ・レジーム乗数
      __init__.py

    research/
      factor_research.py         — モメンタム / ボラ / バリューファクター
      feature_exploration.py     — 将来リターン / IC / 統計サマリー
      __init__.py

    ai/
      news_nlp.py                — ニュース NLP スコアリング（OpenAI）
      regime_detector.py         — マクロ+MA200 で市場レジーム判定
      __init__.py

    monitoring/
      monitoring_db.py           — SQLite 監視 DB の初期化と CRUD
      system_monitor.py          — システム状態（CPU, データ鮮度等）監視
      trade_monitor.py           — （注）trade_monitor 実装ファイルあり（ログ監視等）
      risk_monitor.py            — ドローダウン・ポジション上限監視
      kill_switch.py             — data/kill.flag 制御ユーティリティ
      monitoring_engine.py       — 各モニタを束ねる実行ループ
      alert_manager.py           — （注）アラート送信管理（LINE等）
      __init__.py

    tools/
      paper_verification_report.py — Paper Trading の検証レポート生成
      __init__.py

補足（実装上の振る舞い）
--------------------
- Settings は起動時にプロジェクトルート（.git または pyproject.toml）を探索して .env を自動読み込みします。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring の DB（SQLite）は init_monitoring_db() によりテーブル作成・簡易マイグレーション（カラム追加）を行います（冪等）。
- run_execution は paper_trading の場合、paper_sqlite_path を使用して本番 DB と完全に分離します。
- LLM 呼び出しはリトライや JSON バリデーションを実装しており、失敗した場合はフェイルセーフなデフォルト（0.0 等）で継続します。

開発・拡張ポイント（短いメモ）
------------------------------
- ファクター計算・研究関係は DuckDB を前提に SQL を多用しているため、データ準備（prices_daily / raw_financials 等）を整備することが重要です。
- ExecutionEngine、OrderRepository、BrokerClientFactory 等は発注ロジックやブローカ接続の中核です（実装の詳細に合わせて拡張してください）。
- tests 用に config の自動ロードを無効化する仕組みが用意されています（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

ライセンス・貢献
----------------
- 本 README はコードベースからの抜粋ドキュメントです。ライセンス情報・貢献ルールはリポジトリのトップレベルファイル（LICENSE, CONTRIBUTING 等）があればそちらを参照してください。

以上。必要であれば別途「各モジュールの API リファレンス」や「運用チェックリスト（デプロイ / モニタ手順）」のテンプレートも作成します。どの情報を追加したいか教えてください。