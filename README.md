# KabuSys

日本株向けの自動売買システム（研究・データパイプライン・バックテスト・ポートフォリオ構築・注文シミュレーションを含む）です。  
このリポジトリは、J-Quants などからのデータ収集、特徴量生成、シグナル生成、ポートフォリオ構築、バックテストシミュレーション、ニュース収集までのワークフローを提供します。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントから構成されます。

- データ収集・ETL（J-Quants API クライアント、ニュース収集）
- リサーチ（ファクター計算、特徴量探索）
- 特徴量エンジニアリング（features テーブルの作成）
- シグナル生成（features / AI スコア統合による BUY/SELL 判定）
- ポートフォリオ構築（候補選定・重み計算・サイジング・セクター制約）
- バックテスト（シミュレータ、メトリクス計算、エンジン）
- 補助ユーティリティ（カレンダー管理、DB スキーマ初期化 等）

設計方針として、ルックアヘッドバイアスを避けるために「target_date 時点で利用可能な情報のみ」を用いること、DuckDB を中心にローカル DB を使う点、外部への発注層とは分離された純粋関数・冪等操作を重視しています。

---

## 主な機能一覧

- J-Quants API クライアント
  - ページネーション対応、レート制限、リトライ、トークン自動更新、DuckDB への冪等保存
  - fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar / fetch_listed_info 等
- ニュース収集（RSS）
  - URL 正規化、SSRF 対策、記事 ID の冪等処理、銘柄コード抽出、raw_news/news_symbols への保存
- リサーチモジュール
  - モメンタム・ボラティリティ・バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算（forward returns）、IC（Spearman）計算、ファクターサマリー
- 特徴量生成（feature_engineering）
  - research からの生ファクター集約、ユニバースフィルタ、Z スコア正規化、features テーブルへの UPSERT
- シグナル生成（signal_generator）
  - features + ai_scores の統合スコア計算、Bear レジーム抑制、SELL（エグジット）判定、signals テーブルへの書き込み
- ポートフォリオ構築
  - 候補選定（select_candidates）、重み計算（等配分/スコア加重）、リスクベースサイジング、セクター制約、レジーム乗数
- バックテストフレームワーク
  - インメモリでの DuckDB コピー、シミュレータ（部分約定・スリッページ・手数料）、日次ループ、メトリクス（CAGR / Sharpe / MaxDD / WinRate / Payoff 等）
  - CLI エントリポイントあり（python -m kabusys.backtest.run）
- その他
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）、設定管理（kabusys.config.Settings）

---

## 要件

- Python 3.10+（型ヒントに | 型やその他の構文を使用しているため、少なくとも 3.10 を想定）
- duckdb
- defusedxml
- （その他、プロジェクトの setup.cfg / pyproject.toml に記載の依存をご確認ください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして仮想環境を作成／有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install -e .    # 開発インストール（依存は pyproject.toml / setup.cfg に基づく）

3. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます。
     - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます（テスト用途）。
   - 必須の環境変数（Settings が参照するもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - 任意／デフォルトあり:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト development）
     - LOG_LEVEL（DEBUG|INFO|...、デフォルト INFO）

4. DuckDB スキーマ初期化
   - リポジトリ内の DB スキーマ初期化関数を利用:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - （schema 初期化スクリプトが repository に含まれているはずです。DB を作成し必要テーブルを作成してください。）

---

## 使い方（主要ワークフロー）

以下は代表的な操作例です。

- バックテスト（CLI）
  - 必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar）が事前に用意された DuckDB を指定して実行します。
  - 例:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db data/kabusys.duckdb
  - オプションで初期資金、スリッページ、手数料、allocation_method（equal|score|risk_based）等を指定できます。

- 特徴量生成（Python API）
  - from kabusys.strategy.feature_engineering import build_features
  - conn = init_schema("data/kabusys.duckdb")
  - from datetime import date
  - build_features(conn, date(2024, 1, 31))

- シグナル生成（Python API）
  - from kabusys.strategy.signal_generator import generate_signals
  - generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, sources=None, known_codes=set_of_codes)
  - 内部では fetch_rss → save_raw_news → news_symbols 保存の流れになります。

- J-Quants データ取得と保存
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  - token = get_id_token()
  - recs = fetch_daily_quotes(id_token=token, date_from=..., date_to=..., code="7203")
  - save_daily_quotes(conn, recs)

- バックテストのプログラム的呼び出し
  - from kabusys.backtest.engine import run_backtest
  - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, allocation_method="risk_based", ...)

---

## 環境変数と .env の自動読み込み

- このパッケージはプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を起点に `.env` と `.env.local` を自動で読み込みます（kabusys.config）。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env のパースはシェルの `export KEY=val` 形式やクォート、行末コメントなどに対応します。

---

## ディレクトリ構成（主要ファイル）

概観（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - jquants_client.py          — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py         — RSS ニュース取得・前処理・DB 保存
    - (schema.py, calendar_management.py, stats.py 等が想定される)
  - research/
    - factor_research.py        — momentum/volatility/value 等のファクター計算
    - feature_exploration.py    — 将来リターン計算、IC、統計サマリー
  - strategy/
    - feature_engineering.py    — features の構築（正規化・UPSERT）
    - signal_generator.py       — features + ai_scores 統合 → signals 生成
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数決定（risk_based / equal / score）
    - risk_adjustment.py        — セクターキャップ、レジーム乗数
  - backtest/
    - engine.py                 — バックテストループ、データコピー、戦略適用
    - simulator.py              — 約定シミュレータ（スリッページ・手数料・履歴）
    - metrics.py                — バックテスト評価指標
    - run.py                    — CLI 入口（python -m kabusys.backtest.run）
    - clock.py                  — 模擬時計（将来拡張用）
  - execution/                   — 実運用の発注/接続に関するモジュール（今後）
  - monitoring/                  — 監視・アラート関連（今後）

各モジュールは README の該当箇所やモジュール内コメント（docstring）に詳細な設計・前提・注意点が書かれています。特にデータ取得・保存・バックテストの整合性（Look-ahead 防止）についての設計意図が明記されています。

---

## よくある操作例（抜粋）

- バックテスト（簡易例）
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

- DB スキーマ初期化（Python コンソール）
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 特徴量構築（Python）
  - from datetime import date
  - from kabusys.strategy.feature_engineering import build_features
  - build_features(conn, date(2024, 1, 31))

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, sources=None, known_codes={"7203", "6758"})

---

## 開発・貢献

- バグや機能追加は issue を立ててください。プルリクエストはテストと説明を添えてください。
- 重要: データ取得やバックテストの再現性に関する処理は Look-ahead バイアスを避ける設計になっています。実装を変更する際はその点を維持してください。

---

## 補足（設計上の注意点）

- J-Quants API 呼び出しはレート制限を守るため固定間隔の RateLimiter を使っています。大量のデータ収集は時間を要することに注意してください。
- news_collector は RSS の外部リソースを扱うため SSRF 等の安全対策（ホスト検査・リダイレクト検査・応答サイズ制限）を施しています。
- バックテストは本番 DB を直接書き換えないよう、インメモリ DuckDB に必要なテーブルをコピーして実行します。

---

必要であれば、セットアップ手順の具体的コマンド一覧、schema.md（DB スキーマの説明）や StrategyModel.md / PortfolioConstruction.md の要約を追加できます。どの情報を先に充実させたいか教えてください。