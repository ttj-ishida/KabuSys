# KabuSys

日本株を対象とした自動売買システムの実装（ライブラリ / 実行スクリプト群）。  
このリポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（実取引/ペーパートレード）、監視・アラート、AI を使ったニュースセンチメント評価などのコンポーネントで構成されています。

---

## プロジェクト概要

- モジュール化された自動売買フレームワーク。
- DuckDB を用いた研究・ファクター計算用データストア（prices_daily 等）。
- SQLite を用いた軽量の監視 / 発注ログ保存（monitoring.db / paper_trading.db）。
- 実取引 / ペーパートレードを切り替え可能（`KABUSYS_ENV`）。
- OpenAI API を用いたニュース NLP（センチメント）およびマーケットレジーム判定モジュール。
- ログはコンソール + 日次ローテーションファイル（logs/*.log）に出力。

---

## 主な機能一覧

- 実行エンジン
  - run_execution.py：ExecutionEngine を起動（実取引 or ペーパートレード）。
  - ペーパートレードは本番 DB と分離して `data/paper_trading.db` に記録。

- 監視 / Kill Switch
  - run_monitoring.py：SystemMonitor を定期ポーリングしてシステム状態を記録。
  - MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch。
  - 異常時に `data/kill.flag` を書き込むことで Execution の停止をトリガー。

- 研究・ファクター計算
  - research/factor_research.py / feature_exploration.py：モメンタム、ボラティリティ、バリュー等のファクターを DuckDB 上で計算。
  - forward returns、IC（Information Coefficient）等の統計ユーティリティ。

- ポートフォリオ構築
  - portfolio/*：候補選定、重み計算、セクターキャップ適用、ポジションサイズ算出（単元丸め等）。

- AI（OpenAI）連携
  - ai/news_nlp.py：ニュース記事を集約し OpenAI へバッチ送信して銘柄ごとのセンチメントを ai_scores テーブルへ書込む。
  - ai/regime_detector.py：MA 乖離とマクロニュースで市場レジーム（bull/neutral/bear）を判定して保存。

- ユーティリティ
  - utils/logging_setup.py：統一的なロギング設定（コンソール + 日次ローテーション）。
  - utils/process_priority.py：プロセス優先度 / CPU affinity 設定ユーティリティ。
  - config_setup.py / validate_config.py：.env 対話作成ウィザードと設定検証 CLI。

- 運用ツール
  - tools/paper_verification_report.py：ペーパートレード DB から稼働率・約定率・遅延等の検証レポートを生成。

---

## 要件（推奨）

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意使用）
- （仮想環境を推奨）pip でインストールしてください:
  - pip install duckdb psutil openai pyyaml

※ requirements.txt がある場合はそちらを使ってください。

---

## セットアップ手順

1. リポジトリをチェックアウト
   - git clone … && cd repo

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - OpenAI を使う場合: OPENAI_API_KEY を設定してください（ai モジュール用）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合:
     - python -m kabusys.validate_config --strict

6. 必要なディレクトリ（data/, logs/）は自動で作られることが多いですが、権限等で失敗する場合は手動で作成してください。

---

## 使い方

以下は主要な実行コマンド例です。パッケージはモジュール実行形式（-m）で起動できます。

- ExecutionEngine 起動（実行環境に応じて実取引 / ペーパートレードを自動選択）
  - python -m kabusys.run_execution
  - 特記事項:
    - 環境: KABUSYS_ENV の値で挙動を分岐（development / paper_trading / live）。
    - paper_trading の場合は MockBrokerClient を用い、デフォルト DB は data/paper_trading.db。
    - Execution は起動時に data/stop_requested.flag の存在を確認。存在する場合は起動せず終了。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring 起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を変更可能（デフォルト 60 秒）。
    - 例: export MONITOR_POLL_INTERVAL=30
  - 監視は常に本番用 sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 停止: data/stop_requested.flag を作成すると監視ループは終了します。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）。

- AI 関連（プログラムから呼び出す）
  - ニューススコア計算: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY または api_key 引数が必須（未指定だと ValueError）。

- 設定ファイル生成 / 検証
  - .env 作成: python -m kabusys.config_setup
  - 検証: python -m kabusys.validate_config [--strict]

- ログ
  - デフォルト: logs/<app_name>.log に日次ローテーションで出力（30日保持）。
  - 起動スクリプトは共通の logging_setup を利用しています。

- 停止・キルスイッチ
  - 運用中にリスクなどで停止が必要な場合、KillSwitch が `data/kill.flag` を書き込みます（起動設定で KILL_FLAG_CLEAR_ON_START=1 を設定しない限り自動クリアされません）。
  - ExecutionEngine は run_execution が参照する stop flag（data/stop_requested.flag）を検出して終了します。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須: J-Quants API 用トークン
- KABU_API_PASSWORD — 必須: kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE — ペーパートレードの成行処理モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（1 = 有効。production では 0 推奨）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込みロジック、Settings クラス
  - config_setup.py          — .env 対話ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート CLI
  - ai/
    - news_nlp.py            — ニュースセンチメントスコア取得・ai_scores 書込
    - regime_detector.py     — 市場レジーム判定・market_regime 書込
  - monitoring/
    - monitoring_db.py       — SQLite のスキーマ初期化・永続化 API
    - monitoring_engine.py   — 各 Monitor を束ねる Engine
    - system_monitor.py      — システム状態 / データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書込ロジック
    - ...（trade_monitor 等の他モジュール）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — momentum / volatility / value 計算
    - feature_exploration.py — forward returns / IC / summary 等
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - data/                    — 実行時に使用する SQLite / PID / flag ファイル等（デフォルト）

（上記は主要ファイルの抜粋です。詳細はソースを参照してください）

---

## 運用上の注意・補足

- .env は決して Git にコミットしないでください（config_setup.py のヘッダーにも注意喚起があります）。
- Monitoring は本番の sqlite_path を常に参照します（環境に依らず監視 DB は本番パスが使われます）。
- run_execution は KABUSYS_ENV=paper_trading の場合、本番 DB と完全に分離された `PAPER_TRADING_SQLITE_PATH` を使用します。
- OpenAI を利用する機能は API 呼び出しに失敗した場合フェイルセーフ（スコアを 0 にする等）で継続する設計になっていますが、API キーは必須です。
- logging_setup によりログディレクトリ作成に失敗するとファイル出力は無効になり、コンソール出力のみになります。
- 監視 / Kill Switch / RiskMonitor の閾値等は Settings（環境変数）やコード内のデフォルト値で制御できます。運用環境では十分にテストしてください。

---

以上がこのリポジトリの README 相当の概要です。必要であれば、実際の起動手順（systemd ユニット / docker-compose / cron など）や設定例（.env.example のテンプレート）も作成できます。どの情報を追加しますか？