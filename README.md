# KabuSys

日本株向けの自動売買・研究フレームワーク（部分実装）。  
DuckDB をデータ層に使い、ファクター計算 → 特徴量構築 → シグナル生成 → バックテスト の一連の処理をライブラリ／CLI で提供します。

主に以下の用途を想定しています：
- 研究（factor / feature / IC 等の解析）
- 戦略のオフライン検証（バックテスト）
- データ収集（J-Quants / RSS ニュース収集）
- ポートフォリオ構築ロジックの共有・検証

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得・ETL
  - J-Quants API クライアント（fetch / save 用ユーティリティ、トークンリフレッシュ、レート制限、リトライ等）
  - RSS ニュース収集（SSRF対策、前処理、銘柄抽出、DuckDB への冪等保存）
- 研究（research）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、ファクター統計要約
  - Zスコア正規化ユーティリティ
- 特徴量構築（strategy.feature_engineering）
  - research で計算したファクターを結合・フィルタ・正規化して `features` テーブルへ保存
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算、BUY / SELL シグナル生成・`signals` テーブルへ保存
  - Bear レジーム抑制、SELL の優先ポリシー等の実装
- ポートフォリオ構築（portfolio）
  - 候補選定（スコア順）、等金額／スコア加重配分、リスクベースのサイジング
  - セクター集中制限、レジーム乗数
- バックテスト（backtest）
  - インメモリ DuckDB にデータをコピーして独立したバックテスト環境を構築
  - PortfolioSimulator（擬似約定、スリッページ、手数料、日次評価）
  - run_backtest() による戦略ループ実行、メトリクス算出（CAGR, Sharpe, MaxDrawdown, WinRate, Payoff 等）
  - CLI エントリポイント: `python -m kabusys.backtest.run`
- 設定管理（config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と環境変数ラッパー
  - 必須変数が設定されていない場合は例外

---

## 必要条件

- Python 3.10 以上（型注釈で | を使用しているため）
- 主な Python パッケージ（プロジェクトに合わせて適宜 requirements.txt を用意してください）
  - duckdb
  - defusedxml
  - （標準ライブラリ以外の利用箇所があれば追加）

※ 実運用では追加の依存（HTTP クライアント、Slack クライアント等）がある可能性がありますが、サンプル実装では上記が主要なものです。

---

## セットアップ手順（開発環境向けの最低手順）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 依存パッケージをインストール
   （プロジェクトに requirements.txt/pyproject.toml があればそれを使ってください。ここでは最小例）
   ```bash
   pip install duckdb defusedxml
   ```

4. 開発インストール（任意）
   ```bash
   pip install -e .
   ```

5. 環境変数の準備
   - プロジェクトルートに `.env`（と必要に応じて `.env.local`）を作成してください。
   - 自動ロードはデフォルトで有効です（config モジュールがプロジェクトルートを検出して `.env` を読み込みます）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 必須環境変数（主なもの）

config.Settings で要求される主要なキー（不足すると起動時に例外になります）：

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（データ取得に必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知用（オプション機能のため環境による）
- SLACK_CHANNEL_ID — Slack チャネル ID
- その他（任意／デフォルトあり）
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト "INFO"
  - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH — デフォルト "data/monitoring.db"

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方

以下は代表的な利用方法です。

1) バックテスト（CLI）
- DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）を予め用意しておいてください。スキーマ初期化は `kabusys.data.schema.init_schema()`（実装に依存）を利用する想定です。
- CLI 実行例:
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 \
    --db path/to/kabusys.duckdb
  ```
  オプションで slippage / commission / allocation-method / lot-size 等を指定できます（ヘルプ参照）。

2) ライブラリとして（DuckDB コネクションを渡す）
- features を構築する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features

  conn = duckdb.connect("path/to/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features upserted: {count}")
  conn.close()
  ```

- シグナル生成:
  ```python
  from kabusys.strategy.signal_generator import generate_signals
  cnt = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
  print("signals written:", cnt)
  ```

- バックテスト（プログラムから呼び出す）:
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("path/to/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)
  conn.close()
  ```

3) J-Quants / ニュース収集
- J-Quants から日足を取得して保存:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  recs = fetch_daily_quotes(date_from=..., date_to=..., id_token=None)
  save_daily_quotes(conn, recs)
  ```
- RSS ニュース収集:
  ```python
  from kabusys.data.news_collector import run_news_collection
  stats = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  ```

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の重要なモジュールと役割の一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込み、Settings ラッパー
  - data/
    - jquants_client.py — J-Quants API クライアント、保存ユーティリティ
    - news_collector.py — RSS 収集・前処理・保存
    - (schema.py, calendar_management 等はプロジェクト内に存在する想定)
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計要約
  - strategy/
    - feature_engineering.py — ファクター統合→features テーブルへ
    - signal_generator.py — final_score 計算 → signals テーブルへ
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・丸め・aggregate cap
    - risk_adjustment.py — セクター上限・レジーム乗数
  - backtest/
    - engine.py — バックテストループ、データコピー、発注ロジック結合
    - simulator.py — 擬似約定、ポートフォリオ状態管理
    - metrics.py — 評価指標計算
    - run.py — CLI エントリポイント
  - portfolio, backtest, research, strategy モジュールの __init__.py は外部公開 API を定義

---

## 開発／実装メモ

- 設計は「ルックアヘッドバイアス回避」を重視しており、各処理は target_date 時点で利用可能なデータのみを使用するように実装されています。
- DB 保存は基本的に冪等（ON CONFLICT / DELETE→INSERT の日付単位置換）を意識しています。
- J-Quants クライアントは固定間隔スロットリング（120 req/min）、リトライ、トークン自動リフレッシュに対応しています。
- news_collector は SSRF 対策、受信サイズ制限、XML の安全パーシング（defusedxml）など安全性に配慮しています。

---

## 注意事項

- サンプルコードは一部（schema 初期化、外部サービス連携の完全な実装等）を想定しています。実運用前にスキーマの整備・テスト・監査を行ってください。
- 金融商品取引に関わる実運用は法的な制約およびリスクが伴います。バックテストは過去の成績を示すものであり、将来の成果を保証するものではありません。
- 実際にライブ取引を行う場合は、kabuステーション等の注文APIや適切な監視・リスク管理を実装してください。

---

## ライセンス／貢献

- ライセンス情報・コントリビュートガイドはリポジトリのルートに LICENSE / CONTRIBUTING.md を配置してください（本 README ではプレースホルダとして掲載）。

---

README に記載すべき追加情報（例: 依存関係の正確な一覧、schema 初期化手順、CI／テスト方法）があれば教えてください。必要に応じて README を補足します。