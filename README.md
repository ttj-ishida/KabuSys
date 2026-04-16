# KabuSys

日本株向け自動売買 / 研究用フレームワーク（プロトタイプ）

このリポジトリは、発注エンジン、監視基盤、ポートフォリオ構築、調査・ファクター計算、AI（ニュースセンチメント / レジーム判定）などを含む日本株自動売買システムのモジュール群を提供します。各コンポーネントは比較的独立しており、ライブラリとしてもコマンドラインツールとしても利用できます。

## 主な特徴（機能一覧）

- Execution（発注）
  - ExecutionEngine（発注セッション実行、別スレッドで実行）
  - BrokerClientFactory による実際のブローカー/モック切り替え（`KABUSYS_ENV=paper_trading` 時は MockBrokerClient を利用）
  - Reconciler による起動時の注文・ポジション照合（自動復旧）
  - OrderManager / OrderRepository による注文状態管理

- Monitoring（監視）
  - SystemMonitor：プロセス生存・CPU/MEM/DISK 使用率・データ鮮度の監視
  - TradeMonitor：滞留注文 / 約定価格異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視とリスクログ
  - KillSwitch：条件により `data/kill.flag` を書込み ExecutionEngine を停止
  - AlertManager：LINE Messaging API によるプッシュ通知（クールダウン付き）
  - Streamlit ベースの監視ダッシュボード

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重配分
  - セクター集中制限、レジーム乗数適用
  - 発注株数計算（ロット丸め、リスクベース配分、aggregate cap のスケーリング）

- Research（調査 / ファクター計算）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算（DuckDB を利用）
  - 将来リターン / IC（スピアマン） / 統計サマリー等の解析ユーティリティ

- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（ai_scores テーブルへ保存）
  - マクロニュース + ETF（1321）の MA200乖離を合成した市場レジーム判定（market_regime 書込）
  - API 失敗時のフォールバック、バッチ処理、リトライ（指数バックオフ）実装

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率、注文成功率、レイテンシ等）
  - Streamlit ダッシュボード（監視用）

## 必要な依存ライブラリ

代表的な依存（pip でインストールしてください）:

- python >= 3.10
- duckdb
- psutil
- requests
- openai
- streamlit
- （SQLite は標準ライブラリ）

実際のプロジェクトでは requirements.txt を用意して pip install -r で管理してください。

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。

   - 例:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows

2. 必要パッケージをインストールします（例）:

   pip install duckdb psutil requests openai streamlit

3. 環境変数の設定:
   - プロジェクトルートに `.env` または `.env.local` を作成して設定できます。
   - 自動ロードは既定で有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化）。
   - `.env.example` を参考に設定してください（存在しない場合はREADMEの「環境変数」を参照）。

4. data ディレクトリの作成（必要に応じて）:

   mkdir -p data

5. DuckDB / SQLite の初期ファイルはアプリが起動時に作成・マイグレーションされます（デフォルト: data/kabusys.duckdb、data/monitoring.db）。

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動環境。`development`（デフォルト） / `paper_trading` / `live`
- LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト INFO）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: Monitoring 用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject、デフォルト "instant"）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU/MEM/DISK 閾値など

注意:
- Monitoring は環境にかかわらず「本番 sqlite_path（SQLITE_PATH）」を使用する実装になっています（run_monitoring.py のコメント参照）。
- Execution（run_execution）は `KABUSYS_ENV=paper_trading` の場合、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離します。

## 使い方（実行方法）

- 監視プロセスの起動:

  python -m kabusys.run_monitoring

  オプション: 環境変数 MONITOR_POLL_INTERVAL を変更してポーリング間隔を上書きできます（秒）。
  例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  監視はプロセス優先度を "high" に設定して起動します。停止は `data/stop_requested.flag` を作成するか、Ctrl+C。

- 実行エンジン（ExecutionEngine）の起動:

  python -m kabusys.run_execution

  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、Paper DB（data/paper_trading.db）へ記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - 実行中に `data/stop_requested.flag` が作成されるとエンジンに停止シグナルを送り、安全に終了します。

- Paper Trading 検証レポート生成:

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  例: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

  戻り値は標準出力のレポート。PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能。

- Streamlit ダッシュボード（監視可視化）:

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  起動後ブラウザでダッシュボードを閲覧できます（読み取り専用）。

- AI 関連（プログラム的に呼ぶ例）:

  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="…")

    OPENAI_API_KEY がない場合は ValueError が発生します。

  - レジーム判定：
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="…")

  テスト／開発時は内部の API 呼び出し関数をモック（例: unittest.mock.patch）してネットワークを切ることができます（コード中にその旨のコメントあり）。

## ディレクトリ構成

リポジトリ内の主要ファイル（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / .env ロード / Settings クラス
    - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポートツール
    - monitoring/
      - __init__.py
      - monitoring_db.py             — SQLite 永続化層（テーブル定義・マイグレーション）
      - system_monitor.py            — システム監視（CPU/MEM/DISK/プロセス/データ鮮度）
      - trade_monitor.py             — 注文滞留・約定異常監視
      - risk_monitor.py              — ドローダウン・ポジション上限監視
      - kill_switch.py               — kill.flag 書込ロジック
      - alert_manager.py             — LINE Push 送信
      - monitoring_engine.py         — モニタを束ねるエンジン
      - streamlit_dashboard.py       — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - execution_engine.py
      - ...（発注/ブローカ関連）
    - portfolio/
      - portfolio_builder.py         — 候補選定、等分・スコア加重
      - risk_adjustment.py           — セクター上限、レジーム乗数
      - position_sizing.py           — 株数決定、aggregate cap、ロット丸め
      - __init__.py
    - research/
      - factor_research.py           — モメンタム/ボラティリティ/バリュー等
      - feature_exploration.py       — 将来リターン、IC、統計サマリ
      - __init__.py
    - ai/
      - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py           — レジーム判定（MA200 + マクロセンチメント）
      - __init__.py
    - utils/
      - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py
    - data/ (実行時に使用される: .db/.pid/.flag など)

（上記は提供されたファイル群から抜粋しています。プロダクトリポジトリではさらに多数のモジュール・ユーティリティが存在する想定です。）

## 運用上の注意 / トラブルシューティング

- データベースマイグレーション:
  - init_monitoring_db() は冪等にテーブル作成・簡単なカラム追加を行います。既存 DB に対する互換性保持を考慮した実装がありますが、重大なスキーマ変更時はバックアップを推奨します。

- 環境の分離:
  - Paper Trading（テスト目的）では `KABUSYS_ENV=paper_trading` により発注 DB が本番から分離されます（data/paper_trading.db）。Monitoring は設計上本番 sqlite_path を使用する箇所に注意してください。

- OpenAI / 外部 API:
  - AI モジュールは OPENAI_API_KEY が必要です。API 失敗時はフェイルセーフ（0.0など）で継続するロジックがある一方、キー未設定では ValueError が投げられます。
  - レート制限や一時エラーに対しては指数的バックオフでリトライします。

- Process 優先度 / CPU affinity:
  - 実行時に `psutil` を使って優先度を変更しますが、権限不足で失敗する場合は警告ログが出ます（挙動は OS に依存）。

- フラグファイル:
  - `data/stop_requested.flag`：両スクリプトの監視ループ / 実行ループを安全に停止させるために利用されます。
  - `data/kill.flag`：KillSwitch が書き込むことで ExecutionEngine 停止を要求します。kill.flag をクリアする場合は KillSwitch.clear() を利用、あるいは手動で削除してください。

## 開発・テストのヒント

- AI 呼び出しを回避したいユニットテストでは、モジュール内の `_call_openai_api` を patch してモックレスポンスを返すようにしてください（コード中にその旨の注記あり）。
- DuckDB 接続を渡す形でファクター計算や scoring 関数を呼べるため、テスト用に小さな DuckDB を用意してローカルで検証できます。
- `MonitoringEngine.run_once()` を使うと一回だけ全 Monitor を実行できるため自動テストに便利です。

---

この README はコードベースから主要なポイントを抽出して簡潔にまとめたものです。導入時は .env サンプル（.env.example）や開発者向けドキュメント（PortfolioConstruction.md、StrategyModel.md 等）があれば併せて参照してください。必要があれば README をプロジェクトの実態に合わせて拡張します。