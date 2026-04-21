# KabuSys

日本株自動売買システム（モジュール群）のリポジトリ説明書です。  
この README はリポジトリ内の主要スクリプト／モジュールの使い方、セットアップ手順、機能一覧、ディレクトリ構成をまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。主な責務は次の通りです：

- 市場データ（DuckDB）を用いたリサーチ（ファクター計算、特徴量探索）
- シグナルに基づくポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- ExecutionEngine による発注管理（本番 / ペーパートレードを切り替え可能）
- 監視（System / Trade / Risk）とキルスイッチ（危険検知時に発注エンジン停止）
- AI（OpenAI）を利用したニュースセンチメントや市場レジーム判定
- ペーパートレード検証レポート生成ツール

設計方針として、可能な限りフェイルセーフ（API失敗時は安全側にフォールバック）、ルックアヘッドバイアスの回避、DBの冪等操作を重視しています。

---

## 主な機能一覧

- 設定管理（`kabusys.config`）
  - `.env` 自動ロード機能（プロジェクトルート検出ベース）
  - Settings クラスで環境変数をラップ

- 環境設定ウィザード / 検証
  - `kabusys.config_setup` : 対話式に `.env` を生成／更新
  - `kabusys.validate_config` : 起動前に環境・設定の検証

- 実行・監視プロセス
  - `run_execution.py` : ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading なら MockBroker を使用）
  - `run_monitoring.py` : SystemMonitor（監視ループ）起動スクリプト（MONITOR_POLL_INTERVAL で調整可能）

- 監視サブシステム（monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存確認など
  - TradeMonitor：滞留注文・約定異常等の検出（trade_logs を参照）
  - RiskMonitor：ドローダウンやポジション上限の監視（dashboard / positions を利用）
  - KillSwitch：しきい値に到達した場合に `data/kill.flag` を書き込み、ExecutionEngine に停止信号を送る
  - MonitoringDB：監視ログの永続化（SQLite）とスキーマ初期化／マイグレーション

- ポートフォリオ構築（portfolio）
  - 候補選定（スコア順）、等重／スコア重みの計算
  - セクター上限の適用（apply_sector_cap）
  - ポジションサイズ計算（ロット丸め、リスクベース、利用可能現金スケーリング等）

- リサーチ（research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（ai）
  - `news_nlp`：ニュースを LLM（OpenAI）で評価して銘柄別スコアを ai_scores に書き込む
  - `regime_detector`：ETF の MA 値とマクロニュースの LLM 評価を合成して市場レジームを判定

- ユーティリティ
  - ログ設定（`utils.logging_setup`）：stdout と日次ローテーションファイルハンドラを設定
  - プロセス優先度 / CPU affinity 設定（`utils.process_priority`）

- ツール
  - `tools.paper_verification_report`：ペーパートレード DB から検証レポートを生成（稼働率・注文成功率・レイテンシ等）

---

## セットアップ手順（ローカル開発向け）

以下は一般的なセットアップ手順です。プロダクションでのデプロイは運用ポリシーに従ってください。

1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 以下パッケージが必要な主要依存です（プロジェクトに requirements.txt が無い場合、手動でインストールしてください）:
     - duckdb
     - psutil
     - openai
     - PyYAML (validate_config の YAML 検証に必要; 任意)
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは `.env.example` を基に手動作成（リポジトリに example がなければ下記最低値を設定してください）:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development
     - OPENAI_API_KEY=（AI 機能を使う場合に必須）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO

   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

4. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります

5. データディレクトリ作成
   - デフォルトの SQLite / DuckDB ファイルは `data/` に置かれます。`data/` と `logs/` ディレクトリを作成しておくと良いです。
     - mkdir -p data logs

6. 実行前の注意
   - 本番 (`KABUSYS_ENV=live`) では `KILL_FLAG_CLEAR_ON_START` を `0` にすることを推奨します（自動クリアは危険）。
   - `LOG_DIR` を環境変数で指定することでログ出力先を変更できます。

---

## 使い方（起動例）

- 監視ループを起動（デフォルト 60 秒ポーリング）:
  - MONITOR_POLL_INTERVAL 環境変数で秒数を変更可能（例: 30 秒）
  - 実行:
    - python -m kabusys.run_monitoring
    - 例（30秒に変更）: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  - 動作概要:
    - process priority を "high" に設定
    - Settings から sqlite_path（監視 DB）と duckdb_path を読み、DB 初期化
    - SystemMonitor の check_once を定期実行し、監視テーブル等に記録
    - `data/stop_requested.flag` が存在するとループを終了する

- ExecutionEngine を起動（本番 / ペーパー切替あり）:
  - KABUSYS_ENV によって動作が変わる:
    - paper_trading: MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録
    - live: 実ブローカ API を使用
  - 実行:
    - python -m kabusys.run_execution
  - 動作概要:
    - process priority を "high" に設定
    - DB（paper_trading なら専用 DB）接続・初期化
    - BrokerClientFactory で broker を生成
    - ExecutionEngine をスレッドで起動し、`data/stop_requested.flag` が存在したら停止
    - PID ファイル（data/execution.pid）を管理

- .env を対話式で作成 / 更新:
  - python -m kabusys.config_setup

- 設定の検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - レポートには稼働率、注文成功率、レイテンシの P95 などが出力され、閾値を満たすか PASS/FAIL 判定します。

- AI 関連（ニューススコア・レジーム判定）
  - OpenAI API キーを `OPENAI_API_KEY` 環境変数で設定する必要があります。
  - news_nlp.score_news, regime_detector.score_regime を呼び出して ai_scores / market_regime を更新します（通常はバッチジョブとして実行）。

---

## 主要環境変数（抜粋）

- セキュリティ関連（必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）

- 実行環境 / 挙動
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch フラグファイルパス（デフォルト data/kill.flag）

- ロギング / 実行設定
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログファイル保存先（デフォルト logs/）

- AI / OpenAI
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合に必須）
  - PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）

（その他、validate_config.py で参照しているオプション変数もあります。詳しくは `kabusys.config.Settings` を参照してください。）

---

## ディレクトリ構成（主要ファイル）

プロジェクトは `src/kabusys` 以下にモジュールが配置されています。主要な構成は次の通りです：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py     — 市場レジーム判定（MA + LLM）

  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / DB 操作ラッパ
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （trade 関連の監視）※実装ファイルあり
    - risk_monitor.py        — ドローダウン・ポジション制限監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — （通知管理）※実装ファイルあり

  - execution/
    - execution_engine.py    — ExecutionEngine（注文セッション管理）
    - broker_factory.py      — ブローカークライアント生成（実ブローカ / Mock 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・スケーリング
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py     — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン / IC / summary
    - __init__.py

  - data/                    — （実行時に生成されるデータファイル / DB を想定）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — ログ設定
    - process_priority.py    — プロセス優先度設定
    - __init__.py

その他、config/*.yaml（system_config.yaml 等）を想定した設定テンプレートがあり、validate_config によって存在確認・簡易パースが行われます（PyYAML がインストールされている場合）。

---

## 運用上の注意点

- KABUSYS_ENV=live の場合は設定値に慎重に（特に API パスワード・LINE 通知設定・KILL_FLAG_CLEAR_ON_START）。
- kill.flag / stop_requested.flag による外部停止・再起動フローが存在するため、運用側でもフラグの扱いを明確にしてください。
- ログはデフォルトで `logs/<app_name>.log` に日次ローテートされます。ログディレクトリが作れない場合はコンソール出力のみになります。
- OpenAI 利用は API キーが必須で、API 利用料がかかります。レート制限・エラーはバックオフで扱う設計ですが、費用管理は運用側で行ってください。
- データベース（DuckDB / SQLite）は起動時に必要なテーブルを自動で作成します。バックアップ・マイグレーションは運用手順を整備してください。

---

## 追加情報 / 開発メモ

- DB スキーマ変更は `monitoring_db.init_monitoring_db` のマイグレーションロジックに従って行われます（既存カラムの存在チェック→ALTER ADD）。
- LLM 呼び出しの実装はテスト容易性を考え、内包関数 `_call_openai_api` をモック差し替えてテスト可能です。
- リサーチ関連関数は DuckDB 接続を受け取り SQL と Python ロジックで計算するため、ローカルの DuckDB に価格データ・財務データをロードすれば単体で評価実行できます。

---

必要であれば、この README をベースに `docs/` を作成したり、運用手順（起動スクリプトの systemd / supervisor 設定例、バックアップ手順、障害時対応フロー）を追記できます。どの情報を追加したいか教えてください。