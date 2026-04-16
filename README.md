# KabuSys

日本株自動売買システムの一部（ライブラリ・運用ツール群）。  
このリポジトリは発注実行、監視、ポートフォリオ構築、リサーチ、ニュースNLP 等のモジュールを提供します。

## 概要
KabuSys は以下の主要機能を持つモジュール群で構成されています。

- ExecutionEngine: ブローカー連携による注文送信・管理、リコンシリエーション
- Monitoring: システム状態／注文状態／リスクを定期監視しログ・アラートを出す
- Portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制約等の純粋関数
- Research: DuckDB 上の価格・財務データからファクター計算や特徴量解析
- AI: OpenAI を用いたニュースセンチメント（news_nlp）／市場レジーム判定（regime_detector）
- Tools: Paper Trading 検証レポート生成等のユーティリティスクリプト
- CLI / デーモン起動用スクリプト（run_execution, run_monitoring）や Streamlit ダッシュボード

## 主な機能一覧
- system_monitor: CPU/メモリ/ディスクやプロセス生存、データ鮮度を監視して SQLite に保存
- trade_monitor: 滞留注文や約定価格の異常を検出してリスクログへ記録
- risk_monitor + kill_switch: ドローダウン・ポジション上限に応じた停止フラグの発行（data/kill.flag）
- AlertManager: LINE Push によるアラート送信（トークン未設定時はログのみ）
- news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとにセンチメントを ai_scores に書き込む
- regime_detector: ETF 1321 の MA とマクロニュースセンチメントを合成して日次レジーム判定
- portfolio モジュール: 候補選定、等重／スコア重み付け、リスクに応じたポジションサイズ計算

## 必要条件（依存）
最低限の想定依存パッケージ（実際の requirements.txt を用意してください）:
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- sqlite3（標準ライブラリ）
その他、環境に応じてパッケージを追加してください。

## 設定と環境変数
設定は環境変数またはプロジェクトルートの `.env` / `.env.local` で行います。自動ロードはデフォルトで有効です（オフにするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

重要な環境変数（抜粋）:
- KABUSYS_ENV: 起動環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を利用する場合に必要（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（任意）
- SQLITE_PATH: 監視用 SQLite（デフォルト: `data/monitoring.db`）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: `data/kabusys.duckdb`）
- PAPER_TRADING_SQLITE_PATH: paper_trading モード時の SQLite（デフォルト: `data/paper_trading.db`）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定挙動（`instant|partial|never|reject`、デフォルト: `instant`）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト: `60`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: `.env` 自動ロードを無効化するフラグ（`1` で無効化）

設定クラスや自動読み込みの挙動は `src/kabusys/config.py` を参照してください。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、仮想環境を作成・有効化:
   - python -m venv .venv && source .venv/bin/activate (Windows は別コマンド)
2. 依存をインストール:
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上の必須パッケージを個別に pip install）
3. データディレクトリ作成:
   - mkdir -p data
4. `.env` を作成（`.env.example` を参考に必要な値を設定）
   - 例: KABUSYS_ENV=paper_trading, OPENAI_API_KEY=..., PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
5. DuckDB/SQLite の初期化は多くのスクリプトで自動的に行われます（init_monitoring_db を呼び出してテーブル作成・マイグレーション実行）。

## 起動・使い方（主要コマンド）
- 監視ループを起動 (Monitoring)
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor を作成し、MONITOR_POLL_INTERVAL（秒）でポーリング。停止はプロジェクトルートの `data/stop_requested.flag` を作成するか Ctrl+C。
  - 補足: Monitoring は環境にかかわらず本番の `SQLITE_PATH` を使います（ログ永続化先）。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 説明: KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を用い、`PAPER_TRADING_SQLITE_PATH` に書き込む。起動時に `data/stop_requested.flag` が存在すると起動しません。実行中は `data/execution.pid` が使われます。停止は `data/stop_requested.flag` を作成するか kill する方法により制御。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視ログを可視化。読み取り専用 URI を使って SQLite を開きます。

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: `--db PATH` で SQLite ファイルを指定（デフォルトは `data/paper_trading.db`）

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を必ず設定してください。スクリプト／関数は例外やリトライを備えフォールバック動作を取りますが、未設定時は ValueError を投げます。

## 停止・フラグ管理
- 停止フラグ（run_monitoring / run_execution）が参照するファイル:
  - data/stop_requested.flag — ループやエンジンが定期チェックして停止
- KillSwitch による強制停止:
  - data/kill.flag — KillSwitch が書き込むと ExecutionEngine 側で停止シグナルとして扱う
  - KillSwitch の評価は RiskMonitor の結果に基づく（ドローダウンやポジション上限）

## ディレクトリ構成（抜粋）
リポジトリ内の主要ファイル・ディレクトリと簡易説明:

- src/kabusys/
  - __init__.py — パッケージ情報
  - config.py — 環境変数／設定ロードロジック（.env 自動読み込み含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュースを OpenAI に投げて銘柄別センチメントを生成
    - regime_detector.py — マクロ＋ETF MA から市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（テーブル初期化含む）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — 停止フラグを書き込むユーティリティ
    - alert_manager.py — LINE Push による通知
    - monitoring_engine.py — 各 Monitor を束ねる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 注文の状態遷移とブローカー連携の外向き API
    - reconciler.py — 起動時リコンシリエーション（ブローカーと同期）
    - ...（BrokerFactory/Engine など、発注関連）
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - position_sizing.py — 株数計算・上限・単元丸め
  - research/
    - factor_research.py — モメンタム/バリュー/ボラティリティの計算
    - feature_exploration.py — 将来リターン／IC／統計サマリ
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記はコードベースの抜粋で、実際のファイルはさらに細分化されています）

## 注意事項・運用上のポイント
- Monitoring はデフォルト 60 秒間隔で動作します（環境変数 MONITOR_POLL_INTERVAL で上書き可能）。無効な値や 0 以下は警告されデフォルトに戻ります。
- run_monitoring は Settings.env にかかわらず本番の sqlite_path を使って監視ログを残します（意図的な設計）。
- Paper Trading モードでは本番 DB と分離された `PAPER_TRADING_SQLITE_PATH` を使用します。
- OpenAI API 呼び出しはリトライとフォールバック（失敗時は安全側の値）を備えていますが、API キーは必須です。
- process_priority.set_process_priority("high") を起動時に呼び出しているため、OS 権限の制約で Warning が出ることがあります（無害）。
- DB マイグレーションは `init_monitoring_db` 内で簡易に行います（存在しないカラムの追加など）。商用運用の際は別途マイグレーション管理を推奨します。

## トラブルシューティング
- .env が読み込まれない／自動ロードを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを行いません。
- OpenAI 関連で API エラーが出る場合はログを確認してください。429 や接続エラーは自動リトライ処理がありますが、API キーやネットワーク状態を確認してください。
- SQLite / DuckDB が開けない場合はファイルパスや権限を確認してください。Streamlit は読み取り専用 URI で DB を開きます。

---

さらに詳しい API 仕様や内部アルゴリズム（PortfolioConstruction.md、StrategyModel.md など）はリポジトリ内の設計ドキュメントを参照してください。必要であれば README に追記する内容（例: 実際の起動ユースケース、systemd ユニット例、より詳細な env.example）をご指定ください。