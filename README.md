# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行ユーティリティ群）。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）・アラート、ポートフォリオ組成、リサーチ、AI を用いたニュース解析などのコンポーネントを含みます。

NOTE: 本 README はソースコード（src/kabusys 以下）から主要な挙動・設定を抜粋してまとめたドキュメントです。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 取引エンジン（ExecutionEngine）：シグナル → 発注 → 状態管理 → リコンシリエーション
- 監視サブシステム（Monitoring）：システム状態、注文状況、リスク（ドローダウン・ポジション数）を定期チェックし、ログ／アラート／kill スイッチを提供
- ポートフォリオ構成：候補選定、重み算出、ポジションサイズ計算、セクター制限、レジーム乗数適用
- リサーチ：ファクター算出、将来リターン、IC計算、統計サマリ
- AI モジュール：ニュースのセンチメント解析（OpenAI）、市場レジーム判定
- 付帯ツール：Paper Trading 検証レポート生成、Streamlit ダッシュボード等

設計上の特徴：
- DuckDB / SQLite を用いたデータ永続化・分析
- Paper Trading（KABUSYS_ENV=paper_trading）時は本番 DB と分離（専用 SQLite）
- 監視処理は環境に関係なく production の monitoring DB を使用（run_monitoring の実装による）
- OpenAI API 呼び出しはリトライや入力・出力のバリデーションを行うフェイルセーフ設計

---

## 主な機能一覧

- Execution
  - 発注の発行・同期（OrderManager、OrderRepository）
  - ブローカーとの突合・再同期待機（Reconciler）
  - Paper Trading 対応（MockBrokerClient を使用し専用 DB に記録）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存確認、データ鮮度チェック
  - TradeMonitor：滞留注文／約定価格の異常検出
  - RiskMonitor：ドローダウン、ポジション上限の監視とアラート記録
  - KillSwitch：しきい値超過で data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager：LINE プッシュ通知（クールダウン制御）
  - Streamlit ダッシュボード（監視結果の可視化）
- Portfolio
  - 候補選別、等重／スコア重み、リスクベース発注サイズ、セクターキャップ、レジーム乗数
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を参照）
  - 将来リターン、IC、統計サマリ
- AI
  - news_nlp: raw_news を LLM（OpenAI）でスコアリングして ai_scores に書込
  - regime_detector: ma200 とマクロニュースの LLM 評価を統合して market_regime に書込
- ユーティリティ
  - process_priority：クロスプラットフォームでプロセス優先度 / CPU affinity を設定
  - tools.paper_verification_report：Paper Trading 結果から検証レポート出力

---

## セットアップ手順（開発環境向け）

前提：
- Python 3.9+（ソースは型ヒントに 3.9+ 型注釈を使用）
- DuckDB, psutil, requests, openai, streamlit などが必要

1. リポジトリをクローンし、作業ディレクトリに移動
   - 推奨構成: ソースは `src/` に配置済み（現状）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（手動で必要パッケージを追加してください）
   - 例（最低限）:
     - pip install duckdb psutil requests openai streamlit
   - 実運用では requirements.txt または poetry を用いて依存管理してください。

4. Python パスの設定（パッケージを「開発インストール」するのが便利）
   - プロジェクトルート（src の親）で:
     - pip install -e .

   もしくは実行時に PYTHONPATH を通す:
   - PYTHONPATH=src python -m kabusys.run_monitoring

5. .env の用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
   - 任意／デフォルト:
     - KABUSYS_ENV=development | paper_trading | live  (デフォルト: development)
     - SQLITE_PATH=data/monitoring.db (監視 DB)
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject (デフォルト: instant)
     - OPENAI_API_KEY=...（AI モジュール利用時）
     - LINE_CHANNEL_ACCESS_TOKEN=..., LINE_USER_ID=...（通知用）
     - LOG_LEVEL=INFO

6. data ディレクトリ
   - 監視やフラグファイルは `data/` 以下に作られます。実行前にディレクトリを作成しておくと良いです。
     - mkdir -p data

---

## 使い方（主要スクリプト・コマンド）

前提としてプロジェクトルートで `pip install -e .` してパッケージが import 可能であるか、または PYTHONPATH=src を設定してください。

- ExecutionEngine（取引エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録して本番 DB と分離
    - プロセス優先度を「high」に設定
    - 停止は `data/stop_requested.flag` を作成することで検知（プロセスはフラグを見て停止する）
    - Execution 用 PID ファイル: data/execution.pid（Settings.pid_file_path から変更可）

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト: 60）
      - 0 以下や不正値はデフォルトにフォールバック（警告ログ）
    - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path (`SQLITE_PATH` / data/monitoring.db) を使用する点に注意
    - 停止フラグ: src 側で定義された `data/stop_requested.flag` を検知してループ終了

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザでダッシュボードを表示し、positions / trade_logs / system_status / risk_logs を確認できます

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（avg / max / P95）などを標準出力へ表示し PASS / FAIL を判定

- AI 関連
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をスクリプト内やジョブとして呼び出す
  - いずれも OPENAI_API_KEY が必要（引数で渡すことも可能）
  - News NLP は raw_news / news_symbols を参照し ai_scores に書き込み

- フラグ / 停止制御
  - ExecutionEngine 停止要求（外部）: data/kill.flag を書き込む（KillSwitch が監視）
  - run_execution / run_monitoring 停止リクエスト: data/stop_requested.flag を作成

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 動作モード・ログ等
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

- DB / ファイルパス（デフォルト値は括弧内）
  - DUCKDB_PATH (data/kabusys.duckdb)
  - SQLITE_PATH (data/monitoring.db) — 監視 DB（monitoring は常にこの本番 sqlite_path を参照）
  - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
  - PID_FILE_PATH (data/execution.pid)
  - KILL_FLAG_PATH (data/kill.flag)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効化

- Paper Trading 挙動
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）

- OpenAI / LINE
  - OPENAI_API_KEY — AI モジュール実行時に必要
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager による通知

- Monitoring
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールを抜粋した構成です（ファイル名は代表例）。

- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数 / 設定管理（Settings クラス）
    - run_execution.py                  — ExecutionEngine 起動スクリプト
    - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
    - utils/
      - __init__.py
      - process_priority.py             — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - __init__.py
      - monitoring_db.py                — SQLite 監視ログ永続化層（init / MonitoringDB）
      - monitoring_engine.py            — 各 Monitor を束ねるループ
      - system_monitor.py               — CPU/Memory/Disk / データ鮮度 / PID チェック
      - trade_monitor.py                — 滞留注文 / 約定異常監視
      - risk_monitor.py                 — ドローダウン・ポジション上限監視
      - kill_switch.py                  — kill.flag 制御
      - alert_manager.py                — LINE 通知
      - streamlit_dashboard.py          — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - ... (ブローカーファクトリや API 抽象)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py                      — ニュース NLP スコアリング（OpenAI 呼出）
      - regime_detector.py               — レジーム判定（ma200 + macro sentiment）
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py     — Paper Trading 検証レポート生成ツール
    - data/ (実行時に使用される想定フォルダ)
      - monitoring.db (SQLite)
      - paper_trading.db (SQLite)
      - kabusys.duckdb
      - execution.pid
      - kill.flag
      - stop_requested.flag

---

## 運用時の注意点 / 実装上の重要事項

- 監視 (run_monitoring) は Settings.env に関わらず monitoring DB（Settings.sqlite_path）を使用する実装になっています。Paper Trading を分離したい場合などは起動スクリプトの仕様に注意してください。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用し、本番 DB と完全に分離します。
- process priority 設定は psutil を使います。権限不足や未対応 OS の場合は警告ログを出してスキップします。
- OpenAI の呼び出しはネットワーク障害や 429/5xx に対して再試行ロジックがありますが、キー未設定時は例外を投げます。
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine の安全停止を促します。kill.flag を使う際は内容（理由）を書き込む設計です。
- データ鮮度チェックは DuckDB の prices_daily テーブルから最終日付を取得して判定します（SystemMonitor）。
- Paper Trading の検証レポートは、DB のスキーマが揃っていない場合でもエラーを吸収して N/A 表示する作りになっています。

---

## よくある操作例

- 開発環境で監視を一度だけ回して動作確認（インポート前提）
  - from Python REPL:
    - from kabusys.monitoring.monitoring_engine import MonitoringEngine
    - ...（MonitoringEngine を組み立て run_once() 実行）

- Paper Trading レポート（期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要に応じて README に追記します。たとえば:
- 実際の依存関係一覧（requirements.txt）
- Docker / systemd ユニットのサンプル
- より詳しい運用手順（ログローテーション、バックアップ）
などがあれば、それに合わせてドキュメントを拡張します。