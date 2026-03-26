# KabuSys

KabuSys は日本株のデータ取得・特徴量生成・シグナル生成・ポートフォリオ構築・バックテストを行う自動売買（研究/バックテスト）フレームワークです。モジュールは純粋関数／メモリ計算を重視し、Look‑ahead バイアス防止や冪等性、堅牢な ETL を設計方針に含みます。

バージョン: 0.1.0

---

## プロジェクト概要

- DuckDB を用いて価格・財務・ニュース等のデータを管理し、研究（factor 計算） → 特徴量生成 → シグナル生成 → ポートフォリオ構築 → バックテスト、のワークフローを提供します。
- J-Quants API 経由で株価 / 財務 / マーケットカレンダーを取得するクライアントを含みます（Rate limiting・リトライ・トークン自動更新対応）。
- RSS からニュースを収集して raw_news / news_symbols に保存するニュース収集機能（SSRF 対策、サイズ制限、ID 正規化など）。
- バックテスト用エンジンとシミュレータを備え、CAGR / Sharpe / MaxDrawdown / 勝率 等の評価指標を算出します。
- 設定は .env（または環境変数）で管理。自動ロード機能あり（プロジェクトルートの検出：.git または pyproject.toml）。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env 自動読み込み（`.env` → `.env.local`、OS 環境変数優先）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN 等）
- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（fetch / save 用関数）
  - RSS ニュース収集器（SSRF 対策、gzip ハンドリング、ID 正規化）
- 研究用モジュール（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン / IC / ファクター統計サマリ
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - ファクター正規化（Z-score）・ユニバースフィルタ適用・features テーブルへの UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - コンポーネントスコア計算（momentum/value/volatility/liquidity/news）
  - final_score に基づく BUY/SELL シグナル生成（Bear レジーム抑制、エグジット条件）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、重み計算（等金額／スコア加重）、リスクベースのポジションサイジング
  - セクター集中制限、レジームに基づく乗数
- バックテスト（kabusys.backtest）
  - インメモリ DuckDB へのコピーで安全にバックテスト実行
  - ポートフォリオシミュレータ（スリッページ・手数料・部分約定・マークツーマーケット）
  - メトリクス計算、CLI 実行用エントリポイント

---

## セットアップ手順（開発・実行環境）

前提:
- Python 3.10 以上（PEP 604 の Union 型（|）を使用）
- DuckDB を使用（duckdb パッケージ）
- defusedxml（ニュース収集で XML の安全パースに使用）

例: 仮想環境作成とインストール
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

2. 必要パッケージをインストール（最低限）
   - pip install duckdb defusedxml

   （プロジェクト配布用に requirements.txt / pyproject.toml を用意している場合はそちらを参照してください）

3. 開発インストール（パッケージとして扱う場合）
   - pip install -e .

環境変数 / .env:
- プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
- 主な環境変数:
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
  - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
  - KABU_API_BASE_URL (省略可) — デフォルト http://localhost:18080/kabusapi
  - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
  - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
  - DUCKDB_PATH (省略可) — デフォルト data/kabusys.duckdb
  - SQLITE_PATH (省略可) — 監視用 DB デフォルト data/monitoring.db
  - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例 .env（テンプレート）
  JQUANTS_REFRESH_TOKEN=your_refresh_token
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development

---

## 使い方（主要コマンド・API）

1. DuckDB スキーマ初期化
   - コード内で `from kabusys.data.schema import init_schema` を使い、DuckDB 接続を取得します。
   - 例: conn = init_schema("data/kabusys.duckdb")

   （schema モジュールはスキーマ定義／テーブル作成を行う想定です）

2. J‑Quants データ取得と保存
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar, fetch_listed_info
   - 例:
     id_token = get_id_token()  # 内部で settings.jquants_refresh_token を使用
     records = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
     save_daily_quotes(conn, records)

3. ニュース収集
   - from kabusys.data.news_collector import run_news_collection
   - 例:
     run_news_collection(conn, sources=None, known_codes=set_of_codes)

4. 特徴量生成
   - from kabusys.strategy import build_features
   - 例:
     count = build_features(conn, target_date)

5. シグナル生成
   - from kabusys.strategy import generate_signals
   - 例:
     n = generate_signals(conn, target_date, threshold=0.6)

6. バックテスト実行（プログラム内呼び出し）
   - from kabusys.backtest.engine import run_backtest
   - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, allocation_method="risk_based", ...)
   - 返り値: BacktestResult (history, trades, metrics)

7. バックテスト CLI
   - モジュールを直接実行できます:
     python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
   - 主要オプション:
     --start, --end (必須)
     --cash, --slippage, --commission, --max-position-pct, --allocation-method (equal|score|risk_based), --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size, --db (必須)

8. 例: シンプルなバックテスト（CLI）
   - python -m kabusys.backtest.run --start 2022-01-01 --end 2022-12-31 --db data/kabusys.duckdb

注意:
- generate_signals / build_features / research 関数は DuckDB の接続（prices_daily, features, ai_scores, raw_financials 等のテーブル）が正しく用意されていることを前提とします。
- J-Quants のトークンや .env の設定を正しく行わないと一部機能が動作しません。

---

## ディレクトリ構成（主要ファイル）

以下は主要モジュールの構成です（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                      — 環境設定の読み込み・検証
  - data/
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - news_collector.py             — RSS ニュース収集・DB 保存
    - (その他: schema, calendar_management 等 想定)
  - research/
    - factor_research.py            — momentum / volatility / value 等のファクター計算
    - feature_exploration.py        — 将来リターン・IC・統計サマリ
  - strategy/
    - feature_engineering.py        — features の構築・正規化
    - signal_generator.py           — final_score 計算と BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 株数決定・丸め・制限
    - risk_adjustment.py            — セクター制限・レジーム乗数
  - backtest/
    - engine.py                     — バックテストエンジン（run_backtest）
    - simulator.py                  — ポートフォリオシミュレータ（約定処理）
    - metrics.py                    — バックテスト評価指標計算
    - run.py                        — CLI エントリポイント
    - clock.py                      — 模擬時計クラス
  - execution/                       — (発注実装用フォルダ、現在空の __init__ が存在)
  - monitoring/                      — 監視関連（sqlite 等、別モジュール想定）
  - portfolio/__init__.py            — 主要関数のエクスポート
  - strategy/__init__.py             — 主要関数のエクスポート
  - research/__init__.py             — 主要関数のエクスポート
  - backtest/__init__.py             — 主要関数のエクスポート

（実際のリポジトリにはさらに schema や calendar_management、data/stocks マスタ、monitoring 用 DB ライブラリ等が含まれる想定です）

---

## 実装上の注意点 / ヒント

- 環境変数の自動ロードはプロジェクトルートを .git または pyproject.toml から推定します。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants の API 呼び出しは内部で固定間隔レートリミッタを使用します。大量取得時のスロットリングに注意してください。
- ニュース収集では外部の RSS を取得するので、テスト時はネットワーク依存を排除するため fetch_rss / _urlopen をモックすることを推奨します。
- バックテストは本番 DB を汚染しないためにインメモリの DuckDB にデータをコピーして実行します。大規模な期間を指定する場合はメモリ使用量に注意してください。

---

## よくある質問（FAQ）

Q: データベースのスキーマ初期化はどのモジュールを使う？
A: kabusys.data.schema の init_schema(db_path) を想定しています（スキーマ定義をここで一括作成してください）。

Q: live 環境で自動発注を行うモジュールはありますか？
A: このコードベースは主に研究・バックテスト／データ ETL に焦点を当てています。execution 層は分離されており、kabuステーション等への実注文ロジックは execution 配下で実装する想定です。運用時は paper_trading / live モードで十分テストを行ってください。

---

必要があれば、README に含める具体的な .env.example、requirements.txt、または各モジュールの使用例（コードスニペット）を追加で作成します。どの情報を優先して追記しましょうか？