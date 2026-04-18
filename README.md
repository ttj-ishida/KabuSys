# KabuSys

日本株向け自動売買フレームワーク（ライブラリ / 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・レポート等を含む自動売買システムのコア実装群を収めています。モジュールはできるだけ副作用を持たない純粋関数と小さな責務に分割されており、ペーパートレード用の分離・監視機構・LLM を用いたニュース評価機能などが実装されています。

バージョン: 0.1.0

---

## 主な機能

- 実行エンジン（ExecutionEngine）起動用スクリプト
  - KABUSYS_ENV により paper_trading（モックブローカー）/ live（実ブローカー）を切替
  - paper_trading は専用 SQLite DB（data/paper_trading.db）に記録して本番 DB と分離
  - プロセス優先度設定・PID ファイル管理・停止フラグ対応

- 監視（Monitoring）
  - System / Trade / Risk を監視する Monitor 群とポーリングエンジン
  - 監視ログを SQLite（data/monitoring.db）へ蓄積
  - Kill Switch（kill.flag）で ExecutionEngine に安全停止信号を送出
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）

- ポートフォリオ構築（選定・重み付け・ポジションサイジング）
  - 等重み・スコア加重・リスクベースの株数計算
  - セクターキャップ適用・レジームに応じた乗数

- 研究用モジュール（DuckDB ベース）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン・IC 計算、特徴量サマリ

- AI（LLM）連携
  - ニュースのセンチメント評価（OpenAI / gpt-4o-mini を想定）
  - マクロニュースを用いた市場レジーム判定（regime_detector）
  - API 呼び出しはリトライ・バリデーション・クリッピング済み

- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証ツール（validate_config）
  - ログ設定、プロセス優先度設定ユーティリティ

- ツール
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）

---

## 必須 / 推奨環境

- Python 3.10+
  - 型アノテーションで | を使用するため 3.10 以降を推奨
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - optional: PyYAML（config/*.yaml の構文検証に使用）
- SQLite（組み込み）、ファイルシステムへの書き込み権限

インストール例（venv 推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai
# PyYAML を使う場合
pip install pyyaml
```

---

## 環境変数 / .env

- 自動ロード:
  - プロジェクトルートにある `.env` と `.env.local` を自動的に読み込みます（OS 環境変数を上書きしない）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- 主な環境変数:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - LOG_DIR（ログ出力先のディレクトリ、デフォルト: logs/）
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト: 60）
  - PID_FILE_PATH, KILL_FLAG_PATH, など（Settings で参照）

おすすめ手順:
1. `python -m kabusys.config_setup` を実行して対話式に `.env` を作成
2. `python -m kabusys.validate_config` で設定の検証

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. `.env` を作成（`python -m kabusys.config_setup`）
5. 設定検証（任意）:
   - `python -m kabusys.validate_config`
   - `--strict` を付けると警告も失敗扱いになります
6. デフォルトのデータディレクトリ（data）や logs ディレクトリがなければ起動時に作成されます

---

## 使い方（主要な実行コマンド）

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution エンジン起動
  - 本番/ペーパー混在を settings の KABUSYS_ENV により切替
  ```
  python -m kabusys.run_execution
  ```
  動作ポイント:
  - 起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を書込みます。
  - 停止フラグファイル data/stop_requested.flag が存在すると起動しない/停止します。
  - paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。

- Monitoring 起動（デフォルト 60 秒ごと）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は本番用 sqlite_path を利用（環境に関係なく同じ監視 DB を参照）

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は `--db` で指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が既に設定されていればそちらが優先）

- AI 機能（ライブラリ API）
  - `kabusys.ai.score_news(conn, target_date, api_key=None)` — ニュースセンチメントを ai_scores テーブルへ書込
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)` — market_regime を更新

---

## ログ / ファイル

- ログ出力
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler で日次ローテーション・30日保持）
  - 標準出力にも出力（stdout）
  - ログレベルは LOG_LEVEL 環境変数で指定

- 監視・実行関連ファイル（デフォルトパス）
  - data/monitoring.db — 監視ログ（monitoring_db が作成）
  - data/paper_trading.db — ペーパートレード用 DB（KABUSYS_ENV=paper_trading の場合使用）
  - data/kabusys.duckdb — DuckDB（デフォルト path）
  - data/execution.pid — ExecutionEngine の PID（起動時作成）
  - data/stop_requested.flag — 外部からプロセス終了を要求するフラグ（run_* スクリプトはこれを検出して終了）
  - data/kill.flag — Kill Switch が発動したときに作成される停止フラグ（Execution 側で読まれる）

---

## 実装上のポイント / 注意事項

- Settings モジュール
  - .env / .env.local をプロジェクトルートから自動ロード（ただし OS 環境変数は上書きされない）
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能

- DB 分離
  - 監視（monitoring）は常に監視用 sqlite_path（デフォルト data/monitoring.db）を使用
  - paper_trading は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離

- AI 呼び出し
  - OpenAI API 呼び出しはリトライ・結果バリデーション・スコアクリップを行う
  - OPENAI_API_KEY を環境変数または関数引数で渡す必要あり

- プロセス制御
  - run_* スクリプトは最初にプロセス優先度を high に変更しようとします（失敗しても警告で継続）
  - 停止はフラグファイル（data/stop_requested.flag）を使う仕組み

---

## ディレクトリ構成（主要ファイル）

src/
  kabusys/
    __init__.py
    config.py                      — 環境変数 / Settings
    config_setup.py                — .env 対話ウィザード
    validate_config.py             — 設定検証 CLI
    run_execution.py               — ExecutionEngine 起動スクリプト
    run_monitoring.py              — Monitoring 起動スクリプト
    tools/
      paper_verification_report.py — Paper Trading レポート
    ai/
      news_nlp.py                  — ニュース NLP（OpenAI 連携）
      regime_detector.py          — 市場レジーム判定（OpenAI 連携）
      __init__.py
    monitoring/
      monitoring_db.py             — SQLite 監視 DB 層
      system_monitor.py            — システム・データ鮮度監視
      trade_monitor.py             — 注文監視（存在）
      risk_monitor.py              — ドローダウン／ポジション上限監視
      kill_switch.py               — kill.flag 書込ロジック
      monitoring_engine.py         — Monitor を束ねるエンジン
      alert_manager.py             — アラート送信ロジック（存在）
    portfolio/
      portfolio_builder.py         — 候補選定、重み計算
      position_sizing.py           — 発注株数算出、集約キャップ
      risk_adjustment.py           — セクターキャップ、レジーム乗数
      __init__.py
    research/
      factor_research.py           — ファクター計算（DuckDB）
      feature_exploration.py       — IC / 解析ユーティリティ
      __init__.py
    utils/
      logging_setup.py             — 統一ロギング設定
      process_priority.py          — 優先度 / CPU affinity
      __init__.py
    execution/                      — 発注関連（OrderManager 等、実装あり）
    data/                           — データ取得 / pipeline（prices_daily 等）

（実際の細部はリポジトリ内のファイルを参照してください）

---

## よくある質問

- Q: ペーパートレードと実取引の DB は混ざりますか？
  - A: 混ざりません。paper_trading モードでは paper_sqlite_path が使用され、本番 monitoring DB とは別です。

- Q: 実行を止めたいときはどうする？
  - A: data/stop_requested.flag を作成すると、run_execution/run_monitoring は次回のループで検出して安全に停止します。Kill Switch の場合は data/kill.flag を作成します（監視から作成される）。

- Q: DuckDB のテーブルはどこで参照しますか？
  - A: research / ai モジュールは DuckDB 接続を受け取り prices_daily / raw_news / raw_financials 等を参照します。DuckDB のパスは DUCKDB_PATH で指定します。

---

## 参考・次のステップ

- 初回セットアップ:
  1. env 作成: `python -m kabusys.config_setup`
  2. 設定検証: `python -m kabusys.validate_config`
  3. DuckDB / SQLite に必要なテーブルやデータを投入（データパイプラインを実行）
  4. 監視起動: `python -m kabusys.run_monitoring`
  5. 実行起動（稼働確認済みで）: `python -m kabusys.run_execution`

- 開発:
  - 各モジュールは純粋関数ベースで設計されているため単体テストが書きやすい構成です。
  - AI 呼び出し部は一箇所にまとめられており、テスト時は該当関数をモックできます。

---

ご不明点や README に追記してほしい内容があれば教えてください。README のサンプル .env 例や起動フローチャート等も追加できます。