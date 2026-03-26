# KabuSys

KabuSys は日本株向けの自動売買・研究フレームワークです。  
研究（ファクター計算、特徴量作成）→ シグナル生成 → ポートフォリオ構築 → バックテスト（擬似約定）までの一連の処理をモジュール化しています。DuckDB を用いたデータ管理、J-Quants API や RSS からのデータ収集機能を備えています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要ユースケース）
- ディレクトリ構成
- 環境変数 / 設定
- 補足

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- DuckDB を用いた市場データ・財務データ・ニュースデータの収集と保存
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量正規化（Z スコア等）と特徴量テーブル生成
- ファクター + AI スコアの統合によるシグナル生成（BUY / SELL）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制限、レジーム調整）
- バックテストエンジン（擬似約定、スリッページ・手数料モデル、評価指標）

設計方針として「ルックアヘッドバイアスの防止」「DB を明確に管理した上での冪等処理」「ネットワーク周りの堅牢性（レート制限、リトライ）」を重視しています。

---

## 主な機能一覧

- 環境設定読み込み（.env / .env.local、自動ロード、保護キー）
- J-Quants API クライアント（ページネーション、トークンリフレッシュ、レートリミット、保存ロジック）
- RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID生成、DB保存）
- research:
  - ファクター計算: mom（1/3/6M）, MA200偏差, ATR, avg turnover, PER, ROE 等
  - ファクター探索: 将来リターン計算、IC（Spearman）など
- strategy:
  - 特徴量作成（Z スコア正規化、ユニバースフィルタ）
  - シグナル生成（ファクター + AI スコアの統合、Bear レジーム抑制、SELL 条件判定）
- portfolio:
  - 候補選定（スコア順）
  - 重み付け（等分 / スコア加重 / リスクベース）
  - ポジションサイズ計算（単元丸め、aggregate cap、部分約定調整）
  - セクター制限、レジーム乗数
- backtest:
  - run_backtest(): データコピーしたインメモリ DuckDB 上で営業日ループを回し擬似約定
  - Simulator: BUY/SELL の擬似約定、マーク・トゥ・マーケット、トレード履歴
  - 評価指標（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）
  - CLI エントリポイント: python -m kabusys.backtest.run

---

## セットアップ手順

以下は一般的なセットアップ例です。実際の依存関係はプロジェクトの pyproject.toml / requirements.txt を参照してください（本コード例では一部ライブラリを仮定しています）。

1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成して有効化（例: Python 3.10+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他パッケージを追加）
4. 環境変数を設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.git または pyproject.toml が存在するディレクトリがプロジェクトルートとして検出されます）。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット
5. データベース初期化
   - パッケージ内のスキーマ初期化関数を使用して DuckDB ファイルを生成・初期化します（例: kabusys.data.schema.init_schema）。
   - （schema モジュールはデータ定義を実装している想定です）

必須環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID（必須）

任意 / デフォルトあり
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — DEBUG|INFO|...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH / SQLITE_PATH — DB ファイルパス（デフォルト値あり）

---

## 使い方

以下は代表的な利用例です。DuckDB の接続初期化は `kabusys.data.schema.init_schema(db_path)` を想定しています（schema 実装に依存）。

- バックテスト（CLI）

  データベースに必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が事前に準備されていることを前提に、以下のように実行します。

  例:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb

  利用可能なオプションは CLI ヘルプ参照 (--help)。主なオプション:
  - --start / --end : 開始日・終了日（YYYY-MM-DD）
  - --cash : 初期資金
  - --slippage / --commission : スリッページ・手数料率
  - --allocation-method : equal | score | risk_based
  - --lot-size : 単元株数（日本株は通常 100）

- 特徴量作成（feature table へ UPSERT）

  Python スクリプト内から呼び出す例:

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy.feature_engineering import build_features

  conn = init_schema("data/kabusys.duckdb")
  try:
      cnt = build_features(conn, target_date=date.fromisoformat("2024-01-31"))
      print(f"upserted {cnt} features")
  finally:
      conn.close()
  ```

- シグナル生成（features と ai_scores を参照して signals テーブルを更新）

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy.signal_generator import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  try:
      total = generate_signals(conn, target_date=date.fromisoformat("2024-01-31"))
      print(f"generated {total} signals")
  finally:
      conn.close()
  ```

- J-Quants からのデータ取得と保存（データ収集 ETL）

  モジュール `kabusys.data.jquants_client` に fetch/save 関数があります。例:

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  try:
      records = fetch_daily_quotes(date_from=..., date_to=...)
      n = save_daily_quotes(conn, records)
      print(f"saved {n} rows")
  finally:
      conn.close()
  ```

- ニュース収集ジョブ

  `kabusys.data.news_collector.run_news_collection` を呼び出すことで RSS ソース群から記事を収集して DB に保存できます（既知銘柄コードの紐付け機能あり）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なモジュール構造（提供コードに基づく抜粋）です。

- kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - data/
    - jquants_client.py            — J-Quants API クライアント／保存処理
    - news_collector.py            — RSS ニュース収集・保存
    - (schema.py 等: DB 初期化／DDL を想定)
  - research/
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — ファクター探索・IC・統計
  - strategy/
    - feature_engineering.py       — 特徴量正規化・features テーブル書込
    - signal_generator.py          — シグナル生成（BUY/SELL）
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み付け
    - position_sizing.py           — 株数計算・aggregate cap
    - risk_adjustment.py           — セクター上限・レジーム乗数
  - backtest/
    - engine.py                    — バックテストエンジン（run_backtest）
    - simulator.py                 — 擬似約定・ポートフォリオ管理
    - metrics.py                   — バックテスト評価指標
    - run.py                       — CLI ラッパー
    - clock.py                     — 模擬時計（将来用途）
  - execution/                      — 発注・実行レイヤ（パッケージ化済み）
  - monitoring/                     — 監視・アラート用モジュール（想定）

---

## 環境変数 / 設定

主な環境変数（Settings クラスで参照）:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション / デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL — デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db

自動 .env ロードの挙動:
- プロジェクトルートはこのパッケージのファイル位置を起点に上位ディレクトリで `.git` または `pyproject.toml` を探索して決定します。
- ロード順: OS 環境 > .env.local > .env
- テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 補足

- DuckDB を利用した設計のため、バックテストやデータ分析はローカル DB を準備することで再現可能です。
- J-Quants API 利用時は API レートや認証トークンの管理に注意してください（本実装では自動リフレッシュ、レート制限ガード、リトライロジックを実装済み）。
- ニュース取得モジュールは SSRF 対策や XML パースに対するハードニング（defusedxml）を行っています。
- 実稼働（live）モードでの発注・接続は安全面・法規面での配慮が必要です。paper_trading モードで十分な確認を行ってください。

---

もし README に追加したい内容（例: CI/CD 手順、より詳しい DB 初期化コマンド、pyproject/requirements の具体的な記載、API キーの管理例など）があれば教えてください。必要に応じてサンプル .env.example も作成できます。