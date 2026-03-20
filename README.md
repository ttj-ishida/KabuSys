# KabuSys

日本株向けの自動売買・データパイプライン基盤（モジュール群）のリポジトリです。  
本READMEはコードベース（src/kabusys 以下）に基づく概要・セットアップ・使い方のまとめです。

---

## プロジェクト概要

KabuSys は以下の責務を分離した Python パッケージ群です。

- データ収集（J-Quants API 経由の株価・財務・カレンダー、RSS ニュース）
- ETL / 品質チェックパイプライン（差分取得・保存・検査）
- リサーチ（ファクター計算・特徴量解析）
- 戦略（特徴量の正規化・シグナル生成）
- Execution / Audit（発注・約定・ポジション・監査のスキーマ）
- マーケットカレンダー管理、ニュース収集、安全対策（SSRF等）

設計上の特徴：
- DuckDB を使ったローカルデータベース（冪等な保存・ON CONFLICT 戦略）
- ルックアヘッドバイアス防止（データ取得時の fetched_at の記録・基準日限定参照）
- API レート制御・リトライ・トークン自動更新（J-Quants クライアント）
- XML / RSS の安全パース（defusedxml）や SSRF 対策

---

## 機能一覧

主な機能（モジュール単位）：

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得（例: JQUANTS_REFRESH_TOKEN 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション、レート制限、リトライ）
  - schema: DuckDB スキーマ定義・初期化（raw/processed/feature/execution 層）
  - pipeline: 日次 ETL（run_daily_etl 等）、差分取得ロジック
  - news_collector: RSS 収集・前処理・銘柄抽出・DB 保存（SSRF 対策、gzip 制限等）
  - stats: zscore_normalize 等の統計ユーティリティ
  - calendar_management: JPX カレンダーの管理・営業日判定ユーティリティ
  - audit: 発注〜約定の監査テーブル定義
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリ
- kabusys.strategy
  - feature_engineering.build_features: 生ファクターを正規化・フィルタして features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナル生成
- その他セーフティ・ユーティリティ群（ニュースの URL 正規化、ID 生成など）

---

## 必要な環境変数

このパッケージではいくつかの必須・推奨環境変数を使用します。`.env` ファイルをプロジェクトルートに置くことで自動読み込みされます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（execution 層利用時）
- SLACK_BOT_TOKEN — Slack 通知（監視等）を使う場合
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/...）。デフォルト: INFO
- KABU_API_BASE_URL — kabu API ベース URL。デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視DB 等に使う SQLite パス。デフォルト: data/monitoring.db

---

## セットアップ手順（簡易）

前提: Python 3.10 以上を推奨（`Path | None` 等の型表記、標準ライブラリ機能を使用）

1. リポジトリをクローン
   - git clone ... (本 README は src/kabusys を想定)

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要ライブラリをインストール
   - 主要依存例:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使用してください。）

4. 環境変数設定
   - プロジェクトルートに `.env` を作成（`.env.example` を参照できる想定）
   - 必要な値を設定（JQUANTS_REFRESH_TOKEN 等）

   自動読み込みについて:
   - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込みます。
   - テスト等で無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化（Python REPL 等で）
   - 例:
     >>> from kabusys.data.schema import init_schema
     >>> conn = init_schema("data/kabusys.duckdb")

---

## 使い方（主要操作例）

以下はライブラリ API を直接呼ぶ簡単な利用例です。

- DuckDB 初期化（1回のみ）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  ```

- 特徴量作成（features テーブルに保存）
  ```python
  from datetime import date
  from kabusys.strategy import build_features

  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")
  ```

- シグナル生成（features / ai_scores / positions を参照）
  ```python
  from kabusys.strategy import generate_signals

  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection

  known_codes = {"7203", "6758", "9984"}  # 例: 保持している銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants からのデータ取得（クライアント利用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

注意:
- これらは直接 DuckDB 接続を受け取る同期 API です。運用時にはジョブスケジューラ（cron 等）やラッパーを用いてバッチ化してください。
- 実際の発注/execution 層を動かす場合は KABU API の接続情報（KABU_API_PASSWORD 等）を適切に設定し、テストは paper_trading 環境で十分に行ってください。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内（src/kabusys） の主要なファイル/パッケージ:

- kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（レート制御/リトライ/保存ユーティリティ）
    - schema.py — DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py — 日次 ETL 実装（run_daily_etl、run_prices_etl 等）
    - news_collector.py — RSS 収集・前処理・DB挿入・銘柄抽出
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - features.py — public re-export（zscore_normalize）
    - calendar_management.py — market_calendar 更新 & 営業日ユーティリティ
    - audit.py — 発注/約定/監査用テーブル定義
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — forward returns, IC, factor_summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（正規化・フィルタ）
    - signal_generator.py — generate_signals（最終スコア計算・BUY/SELL）
  - execution/  — （空ファイルがあるが実装は別モジュール/将来用）
  - monitoring/ — 監視・通知用モジュール（存在する場合）

付記:
- 各モジュールに詳細な docstring（設計方針・処理フロー・注意点）が付与されています。実装の理解・拡張時は該当モジュールの docstring を参照してください。

---

## 運用上の注意

- 環境切り替え: KABUSYS_ENV により挙動を分けられます（development / paper_trading / live）。実運用では live を慎重に扱ってください。
- データの整合性: ETL は差分取得＋バックフィルに対応しますが、API の変更やデータ欠損は品質チェック（pipeline.quality 参照）で検出する必要があります。
- セキュリティ:
  - RSS Fetcher: SSRF 対策、受信サイズ制限、defusedxml を利用
  - J-Quants クライアント: トークン管理・自動更新、レート制御
- テスト:
  - 自動的に .env を読み込むため、テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと制御しやすくなります。

---

## 開発者向け情報 / 貢献

- モジュール毎に docstring と設計意図が書かれているため、機能拡張はそれに従って実装してください。
- DB スキーマは kabusys.data.schema の DDL に集約されています。スキーマ変更は互換性に注意して行ってください（外部キーの扱い等、DuckDB の制約差に注意）。
- コードベースのテスト、モック（例: news_collector._urlopen の差し替え）を活用するとネットワーク依存部分を安全に検証できます。

---

必要があれば、サンプル .env.example、requirements.txt、運用の cron / systemd ユニット例、さらに詳しい開発者向けドキュメント（各アルゴリズムの式や StrategyModel.md、DataPlatform.md 参照）を作成します。どの情報が欲しいか教えてください。