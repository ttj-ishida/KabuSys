# KabuSys — README

このリポジトリは日本株向けの自動売買・分析フレームワーク「KabuSys」です。  
README は日本語で、プロジェクト概要、機能、セットアップ、基本的な使い方、ディレクトリ構成をまとめています。

注意: 本 README はソースコード（src/ 配下）を参照して作成しています。実際の運用前に必ず環境変数や設定ファイルを確認してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する以下の主要機能を備えたモジュール群です。

- 実行エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード対応）
- 監視モジュール（Monitoring）によるシステム・注文・リスク監視と Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- ユーティリティ（環境設定ウィザード・設定検証・プロセス優先度設定 等）
- 各種ツール（ペーパートレード検証レポート生成）

設計方針の一部:
- 本番 DB とペーパートレード DB は分離（paper_trading モード時）
- DuckDB を分析用、SQLite を監視・注文ログ用として利用
- OpenAI 連携は明示的に API キーを渡すか環境変数から取得
- ルックアヘッドバイアス防止のため日付参照は明示的に渡す設計

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV により本番 / paper_trading を切替。
  - paper_trading では MockBroker を使い data/paper_trading.db に記録。
- run_monitoring.py
  - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔指定可能。
- monitoring モジュール
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態 / データ鮮度を監視
  - TradeMonitor：滞留注文・約定価格異常を検知
  - RiskMonitor：ドローダウン・ポジション上限を監視
  - KillSwitch：フラグファイルを書き込むことで ExecutionEngine を停止
  - AlertManager（アラート送信ロジックを担当、実装に応じて LINE 等へ通知）
- portfolio モジュール
  - 候補選定、等配分・スコア加重、ポジションサイズ計算、セクターキャップ・レジーム調整
- research モジュール
  - ファクター（モメンタム・ボラティリティ・バリュー）計算、将来リターン、IC、サマリー統計
- ai モジュール
  - news_nlp.score_news：OpenAI を用いてニュース記事を銘柄ごとにセンチメント化し ai_scores に保存
  - regime_detector.score_regime：ETF MA とマクロセンチメントを合成して市場レジーム判定
- utils
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ
- tools
  - paper_verification_report: ペーパートレード DB を解析して PASS/FAIL 判定のレポート出力
- 環境管理
  - config_setup.py: .env を対話式で初期作成 / 更新するウィザード
  - validate_config.py: .env や config/*.yaml の検証 CLI

---

## セットアップ手順（開発・ローカル）

最低限必要な Python パッケージ（例）:
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を行う場合）

例:
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）pip install PyYAML

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数の準備
   - プロジェクトルートに .env を作る（config_setup を使うと対話式に作れます）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他よく使う環境変数（例とデフォルト）:
     - KABUSYS_ENV=development | paper_trading | live  (デフォルト: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE=instant | partial | never | reject  (デフォルト: instant)
     - KILL_FLAG_CLEAR_ON_START=0 | 1

自動 .env 読み込みについて:
- モジュール import 時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロードします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方

以下は主要なコマンド例です。プロジェクトルートで実行してください（src がパッケージとしてインポートできる状態）。

1. 環境設定ウィザード（.env の作成）
   - python -m kabusys.config_setup
   - 対話的に .env を作成・更新します。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit 1）になります。

3. ExecutionEngine（発注エンジン）起動
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合、MockBroker が用いられ data/paper_trading.db に記録されます（本番 DB と分離）。
     - 起動時に data/stop_requested.flag が存在すると起動を中止します。
     - 実行中に同フラグを書き込むことでエンジンに停止シグナルを送れます（kill.flag とは別）。

4. Monitoring 起動（SystemMonitor 単体のループ）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
   - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（環境に関わらず本番監視 DB を想定）。

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - またはデフォルト DB を使う場合: python -m kabusys.tools.paper_verification_report
   - --db で別パス指定可。環境変数 PAPER_TRADING_SQLITE_PATH も参照。

6. AI 機能（プログラムから呼び出し）
   - news_nlp.score_news(conn, target_date, api_key=...)
     - conn は duckdb 接続（duckdb.connect(...)）
     - target_date は date オブジェクト
   - regime_detector.score_regime(conn, target_date, api_key=...)
   - 注意: OpenAI API キーは引数または環境変数 OPENAI_API_KEY を指定する必要があります。

7. プロセス優先度 / CPU affinity（ユーティリティ）
   - from kabusys.utils.process_priority import set_process_priority, set_cpu_affinity
   - set_process_priority("high") 等でプロセス優先度を設定（プラットフォーム依存、権限による制限あり）

停止・制御用ファイル
- data/stop_requested.flag
  - run_monitoring.py、run_execution.py が監視する停止フラグ。
- data/kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine の即時停止トリガーなどで使用される想定。
- data/execution.pid
  - ExecutionEngine が生成する PID ファイル。SystemMonitor はこのファイルでプロセス存在チェックを行う。

ログレベル
- LOG_LEVEL 環境変数で制御（DEBUG / INFO / WARNING / ERROR / CRITICAL）

---

## .env（例）

以下は .env の簡易例（実際の値は機密情報のため置き換えてください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

注意: .env は絶対に Git にコミットしないでください。

---

## ディレクトリ構成（概観）

（プロジェクトルート）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — ペーパートレード検証レポート
    - ai/
      - __init__.py
      - news_nlp.py             — ニュース NLP スコアリング（OpenAI 連携）
      - regime_detector.py      — 市場レジーム判定（LLM + ETF MA）
    - monitoring/
      - monitoring_db.py       — SQLite 操作用ラッパ
      - monitoring_engine.py   — 各 Monitor を束ねるエンジン
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py       — （アラート送信）
    - execution/                — 発注関連（OrderManager, Engine 等）※詳細はコードベース参照
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - data/                     — デフォルトの DB ファイルやフラグを置く想定（リポジトリ外で生成することが多い）

---

## 注意事項・運用上の留意点

- 本番環境（KABUSYS_ENV=live）では全設定を慎重に確認してください。validate_config は live 時に追加の注意を出します。
- Kill Switch / stop flag による停止は冪等性を保つよう実装されていますが、実運用では運用手順を文書化してください。
- OpenAI 等外部 API を使用する場合は API 利用制限（レート、コスト）に注意し、リトライやフェイルセーフの設定を確認してください（news_nlp, regime_detector にリトライ実装あり）。
- DB マイグレーション: monitoring_db.init_monitoring_db は必要なカラムが無ければ自動で追加（簡易マイグレーション）しますが、重大変更時は手動での検証が必要です。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化すると便利です。

---

必要に応じてこの README をプロジェクト固有の導入手順や運用手順に合わせて追記・修正してください。運用前に設定検証 (python -m kabusys.validate_config) を強く推奨します。