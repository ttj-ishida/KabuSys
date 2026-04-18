# KabuSys

日本株自動売買システムのパッケージ（ライブラリ + 起動スクリプト群）。  
このリポジトリは戦略・ポートフォリオ構築、実行エンジン、監視、AI 補助（ニュース NLP / レジーム検出）などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた自動売買基盤です。

- 戦略・ファクター算出（DuckDB ベースの価格・財務データ参照）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制約）
- 注文実行エンジン（本番／ペーパートレード分離、BrokerClient の抽象化）
- 監視（システム状態、注文状態、リスク監視、Kill Switch）
- AI 補助（ニュースセンチメントスコアリング、マクロレジーム判定） — OpenAI API を利用
- 運用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計上の特徴:
- DuckDB（分析）と SQLite（監視 / 発注ログ）を併用
- 環境ごとの DB 分離（ペーパートレード時は専用 SQLite を使用）
- LLM 呼び出しは失敗に寛容（フェイルセーフ）で部分成功を残す設計
- ログ・プロセス優先度調整など運用面にも配慮

---

## 機能一覧（主要コンポーネント）

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV により paper_trading を切替）
  - run_monitoring.py — SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 環境設定 / 検証
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — .env / config/*.yaml の事前検証 CLI
- ポートフォリオ
  - portfolio_builder.py — 候補選定・スコア順ソート・等重/スコア重み
  - position_sizing.py — 発注株数計算（リスクベース、等分配等）、単元調整、aggregate cap
  - risk_adjustment.py — セクター上限、レジーム乗数
- リサーチ
  - research/factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - research/feature_exploration.py — 将来リターン、IC、統計サマリ等
- AI（OpenAI）
  - ai/news_nlp.py — ニュースを LLM でセンチメント評価し ai_scores に書き込み
  - ai/regime_detector.py — ETF MA とマクロ記事の LLM 評価を合成し market_regime を決定
- 監視
  - monitoring/system_monitor.py — CPU/メモリ/DISK、データ鮮度、実行プロセス監視
  - monitoring/trade_monitor.py —（注文に関する監視ロジック）
  - monitoring/risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring/kill_switch.py — kill.flag の作成・削除・評価
  - monitoring/monitoring_db.py — SQLite スキーマ初期化・単純 CRUD ラッパ
  - monitoring/monitoring_engine.py — 各モニタを束ねたポーリングエンジン
- ユーティリティ
  - utils/logging_setup.py — 統一的なロギング設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - tools/paper_verification_report.py — ペーパートレード DB から検証レポート生成

---

## 必須 / 推奨依存ライブラリ

（プロジェクトの requirements.txt があればそちらを使ってください。ここは主要依存の例）

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイルのパース検証に任意で必要）
- その他: 標準ライブラリのみのユニットも多いですが、実行環境に合わせて追加してください。

インストール例（最低限）:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   pip install -r requirements.txt
   または
   pip install duckdb psutil openai PyYAML

4. 環境変数設定
   - 対話式で .env を作成:
     python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
   - 主要なデフォルト:
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO

5. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

6. ディレクトリ / 初期ファイル
   - data/ ディレクトリは自動作成されます（ログや DB の出力先）。
   - kill.flag / stop_requested.flag / execution.pid 等は data/ に作成されます。

---

## 使い方（起動例）

- ExecutionEngine を起動（通常）
  python -m kabusys.run_execution

- ペーパートレードで起動（ペーパートレード専用 DB を使用）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  note: ペーパートレードでは MockBrokerClient を用い、data/paper_trading.db に記録されます（本番 DB と分離）。

- Monitoring を起動（SystemMonitor のポーリング）
  python -m kabusys.run_monitoring

  - ポーリング間隔の変更:
    export MONITOR_POLL_INTERVAL=30  # 秒
    python -m kabusys.run_monitoring

  - run_monitoring は KABUSYS_ENV に関係なく sqlite_path（通常は本番 monitoring.db）を使用します。

- 停止 / Kill Switch
  - 実行スクリプトは data/stop_requested.flag を監視します。ファイルが存在すると run_monitoring/run_execution は順次終了します。
  - kill_switch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path でパス指定可）。
  - ExecutionEngine の PID ファイル: data/execution.pid

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで DB ファイルパスを上書き可能。

---

## 環境変数（主要なもの）

（詳細は kabusys.config.Settings を参照）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- OPENAI_API_KEY — AI 機能を使う場合必須
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — 分析用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

---

## ログ・運用

- ログ: logs/<app_name>.log（utils/logging_setup.py による日次ローテーション、30日保持）
- コンソールログは stdout に出力（cron 等で stdout をまとめて扱いやすくするため）
- プロセス優先度: 起動時に set_process_priority("high") が呼ばれます（psutil を利用、権限がない場合は警告してスキップ）
- DB マイグレーション: monitoring_db.init_monitoring_db は必要なカラムの追加入力を行い冪等で初期化します

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — マクロ + MA によるレジーム判定
  - monitoring/
    - monitoring_db.py — SQLite スキーマ・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (通知管理: LINE 等 — 実装箇所を確認)
  - execution/ (注文実行関連 — Broker クライアント / Engine / Order 管理など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

その他: data/（DB・フラグ・PID 等）、logs/（ログファイル）

---

## 注意事項・運用上のヒント

- 本番環境（KABUSYS_ENV=live）では LINE 通知や kill_flag の扱いに特に注意してください。validate_config は live 時に追加警告を出します。
- OpenAI API を利用する処理は API 失敗時にフォールバック動作を実装していますが、API キー漏洩・料金に注意してください。
- データ鮮度チェックは DuckDB 側の prices_daily テーブル内容に依存します。バックフィルやデータ更新パイプラインを運用してください。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります（warnings/ログを確認してください）。
- .env は秘密情報を含むためリポジトリにコミットしないでください（config_setup.py の注記参照）。

---

## 開発・テスト

- モジュールは可能な限り副作用を避ける（DuckDB 接続を引数で渡す等）設計になっています。ユニットテストを書きやすい構造です。
- LLM 呼び出し部分は内部関数を patch してモック化できるよう設計されています（例: _call_openai_api の patch）。

---

必要であれば、README に以下の追加情報も作成できます:
- 詳細な起動手順（systemd / supervisor / Docker でのデプロイ例）
- config/*.yaml の説明テンプレート
- よくあるトラブルシュート（DB 欠損、ログ権限、psutil のパーミッション等）

続けてどの部分（デプロイ手順 / systemd ユニット / Dockerfile / 詳細な env 例）を補足しますか？