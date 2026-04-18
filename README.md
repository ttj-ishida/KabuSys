KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリです。  
主な役割は次のとおりです。

- 発注エンジン（ExecutionEngine）と注文管理
- 監視（System / Trade / Risk）と Kill Switch（異常時の自動停止）
- ポートフォリオ構築（候補選定・重み算出・株数決定）
- 研究用モジュール（ファクター計算・特徴量探索）
- Paper Trading 向け検証ツール
- ニュースの NLP によるセンチメント評価 & 市場レジーム判定（OpenAI を利用）

この README はリポジトリ内のスクリプト／モジュールを使い始めるためのガイドです。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 実環境（live）/ ペーパートレード（paper_trading）を切替可能
  - paper_trading 時は MockBrokerClient を使い、専用 SQLite（data/paper_trading.db）を使用
- Monitoring ポーリング（run_monitoring.py）
  - System / Trade / Risk モニタを定期実行しログ（SQLite）へ永続化
  - MONITOR_POLL_INTERVAL で間隔変更可（デフォルト 60 秒）
- Kill Switch（data/kill.flag）による外部停止シグナル
- 監視 DB：SQLite（monitoring_db モジュール）で system_status, trade_logs, positions, risk_logs, dashboard を管理
- Portfolio モジュール（選定・重み付け・ポジションサイズ計算・セクター制約）
- Research モジュール（duckdb を使ったファクター計算、IC 計算、統計要約）
- AI 関連
  - news_nlp: OpenAI を使ったニュースセンチメントスコアの取得（ai_scores テーブルへ格納）
  - regime_detector: ETF（1321）の MA とマクロニュースの LLM スコアを合成してレジーム判定
- 便利ツール
  - 環境設定ウィザード（config_setup.py）で .env を対話的に生成
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

セットアップ手順
----------------
前提
- Python 3.9+（typing の一部記法に依存）
- sqlite3 は標準ライブラリ
- 必要な外部パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（設定ファイル検証を使う場合、任意）

推奨インストール（仮想環境内で）
- pip install duckdb psutil openai pyyaml

環境変数（.env）
- プロジェクトルートに .env/.env.local を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 代表的なキー（config_setup の項目に依る）:
  - KABUSYS_ENV: development | paper_trading | live （必須）
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用 DB、デフォルト）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading の専用 DB）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: （任意・本番アラート用）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）
  - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の約定動作）

.env を対話的に作る:
- python -m kabusys.config_setup
  -> 対話で入力後 .env を保存します

設定検証:
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱いして exit code 1

使い方（主要スクリプト）
-----------------------

1) 監視ループの起動
- 用途: System / Trade / Risk の定期チェックと monitoring DB への記録
- 実行:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定可（例: MONITOR_POLL_INTERVAL=30）
- 特記事項:
  - 監視は常に settings.sqlite_path（本番監視 DB）を使用します
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil 権限が必要）
  - 終了は data/stop_requested.flag ファイルの存在で検知して安全終了

2) ExecutionEngine（発注エンジン）起動
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db を用いる
  - 実行中は data/execution.pid に PID を書きます
  - data/stop_requested.flag があると起動せず終了。監視からの停止や手動停止のトリガに対応
  - Execution 側もプロセス優先度を "high" に設定します

3) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数を使うことも可）
- 出力: 稼働率、注文成功率、送信率、P95 レイテンシ 等を算出して PASS/FAIL 判定を行う

4) AI 系（ニュース NLP / レジーム判定）
- プログラムから直接呼ぶ:
  - from kabusys.ai import score_news
    - score_news(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: Optional[str]) -> int
  - from kabusys.ai import (regime_detector を直接 import)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)
- 注意:
  - OpenAI API キーは引数に渡すか OPENAI_API_KEY 環境変数を設定
  - 429 / ネットワーク断 / タイムアウト / 5xx に対してはリトライ実装あり
  - API 失敗時は安全側のフォールバック（スコア 0.0 など）で例外を上位に伝えない設計の箇所がある

監視・停止フラグ
----------------
- data/kill.flag
  - KillSwitch が書き込むファイル。存在すると ExecutionEngine 停止を示す（外部からの強制停止トリガにも使用）
  - KillSwitch は条件（ドローダウンやポジション上限等）を評価して必要時に書き込みます
- data/stop_requested.flag
  - run_monitoring / run_execution のループを安全に抜けるためのフラグ（存在検知でループ終了）
- data/execution.pid
  - ExecutionEngine が PID を書き込むファイル。SystemMonitor は stale PID を検出して削除します

構成（ディレクトリ構成）
-----------------------
以下は主要ファイル／ディレクトリ（src/kabusys 以下）の概要です。実際のリポジトリ内に合わせて参照してください。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュースを OpenAI で評価して ai_scores へ書込
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
    - __init__.py            — score_news をエクスポート
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ定義・CRUD（冪等）
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 滞留注文 / 約定異常の監視
    - risk_monitor.py        — ドローダウン / ポジション上限チェック
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各モニタを束ねるループ
    - alert_manager.py       — （アラート通知の集約・送信）※実装に依存
  - portfolio/
    - portfolio_builder.py   — 候補選定・等重/スコア重み
    - position_sizing.py     — 株数算出・利用可能資金に基づくスケール処理
    - risk_adjustment.py     — セクター上限・レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - execution/
    - (Order/Engine/Broker 関連のモジュール群) — ExecutionEngine のコア（省略）
  - utils/
    - process_priority.py    — psutil を使った優先度 / CPU affinity 設定ユーティリティ
  - data/                    — 実行時 DB やフラグファイルを置く場所（例: data/*.db, *.flag, *.pid）
- config/
  - system_config.yaml, data_config.yaml, ... （実行設定用 YAML。存在しない場合は警告）

注意点・運用メモ
----------------
- .env は機密情報を含むため絶対に Git にコミットしないこと
- 本番環境では KILL_FLAG_CLEAR_ON_START を 0 にセットすること（誤って Kill Switch をクリアしない）
- paper_trading モードは本番 DB と完全に分離される（PAPER_TRADING_SQLITE_PATH を使用）
- psutil による優先度変更や CPU affinity は権限が必要な場合がある（Linux の nice あるいは Windows 特権）
- DuckDB は分析用途のローカル高速列指向 DB。research / ai モジュールで使用
- PyYAML がないと validate_config の YAML 検証はスキップされます（警告）

よく使うコマンド例
-----------------
- .env を対話式に作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視起動（デフォルト 60s 間隔）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

ライセンス・貢献
----------------
- この README はコードベースの説明用テンプレートです。実際のライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

補足
----
- 追加パッケージや外部サービス（OpenAI、kabuステーション、J-Quants）との接続情報は .env にて設定します。まずは config_setup で基本値を作成し、validate_config で検証することを推奨します。
- 本ドキュメントで触れていない詳細（ExecutionEngine の内部、Broker クライアント実装など）は各モジュールの docstring を参照してください。

もし README に追記してほしい点（例: 実行例のスクリーンショット、CI 設定、詳細な DB スキーマ解説など）があれば教えてください。必要に応じて追記します。