# KabuSys

日本株向けの自動売買／リサーチ基盤ライブラリです。  
価格・財務データ取得、ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集までを含むモジュール群を提供します。

主な設計方針：
- DuckDB をデータストアに使用（ローカル DB に対する ETL と分析を想定）
- バックテストはメモリ上シミュレータで再現性のあるロジックを提供
- Look-ahead バイアス防止のため、時刻情報（fetched_at）や日次単位の参照に注意
- 冪等性（DB への upsert / ON CONFLICT）や例外処理を重視

---

## 機能一覧

- data/
  - J-Quants API クライアント（ページネーション、レートリミット、トークンリフレッシュ、DuckDB 保存用ユーティリティ）
  - ニュース（RSS）収集・前処理・DB 保存（SSRF/サイズ上限対策、記事ID生成、銘柄抽出）
- research/
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - ファクター探索・IC 計算・統計サマリー
  - Z スコア正規化ユーティリティ（kabusys.data.stats 参照）
- strategy/
  - 特徴量エンジニアリング（features テーブルの作成・正規化・クリップ）
  - シグナル生成（features + ai_scores 統合 → final_score → BUY/SELL）
- portfolio/
  - 候補選定、重み計算（等配分・スコア加重）
  - リスク調整（セクター上限、レジーム乗数）
  - サイジング（リスクベース / 等配分 / スコアベース、単元丸め、aggregate cap）
- backtest/
  - シミュレータ（擬似約定、スリッページ・手数料モデル、履歴・約定記録）
  - エンジン（データコピーしてインメモリ DuckDB でバックテスト実行）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, 勝率等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- config.py
  - .env 自動読み込み（プロジェクトルート検出）と必須環境変数取得ラッパー

---

## セットアップ手順

前提
- Python 3.9+（typing の一部機能や型ヒントに依存）
- DuckDB（Python パッケージ）
- ネットワーク接続（J-Quants API や RSS フィード利用時）

推奨手順（Unix 系 / Windows PowerShell 共通）:

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # PowerShell: .venv\Scripts\Activate.ps1
   ```

2. 必要パッケージをインストール（最低限）
   ※プロジェクトに requirements.txt がある想定での例。なければ必要なパッケージを個別に入れてください。
   ```bash
   pip install duckdb defusedxml
   # 追加で必要に応じて: pip install .
   ```

3. 環境変数（.env）を設定
   プロジェクトルートに `.env`（または `.env.local`）を作成すると自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須環境変数（Settings 参照）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層を使う場合）
   - SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

   任意 / デフォルト可:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - LOG_LEVEL — (DEBUG/INFO/...)
   - DUCKDB_PATH — デフォルト data/kabusys.duckdb
   - SQLITE_PATH — デフォルト data/monitoring.db

4. DuckDB スキーマ初期化
   プロジェクトに schema 初期化ユーティリティがある前提で、DB ファイルを作成・テーブルを作成してください。
   （実装例: kabusys.data.schema.init_schema を利用）

---

## 使い方（主なユースケース）

1. バックテスト実行（CLI）
   DuckDB に prices_daily / features / ai_scores / market_regime / market_calendar が準備されている必要があります。

   ```bash
   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2023-12-31 \
     --cash 10000000 \
     --db path/to/kabusys.duckdb \
     --allocation-method risk_based \
     --lot-size 100
   ```

   実行後、標準出力にバックテストメトリクスが表示されます。

2. 特徴量の生成（プログラム的に）
   Python から直接呼び出し可能です。DuckDB 接続（kabusys.data.schema.init_schema で作成した接続）を渡します。

   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy.feature_engineering import build_features

   conn = duckdb.connect("path/to/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024, 1, 4))
   print(f"upserted {count} features")
   conn.close()
   ```

3. シグナル生成（プログラム的に）
   features / ai_scores / positions が整備されている DuckDB 接続を渡します。

   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy.signal_generator import generate_signals

   conn = duckdb.connect("path/to/kabusys.duckdb")
   n = generate_signals(conn, target_date=date(2024, 1, 4))
   print(f"generated {n} signals")
   conn.close()
   ```

4. ニュース収集ジョブ
   RSS ソースから記事を取得して raw_news / news_symbols に保存します。

   ```python
   import duckdb
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = duckdb.connect("path/to/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # stocks テーブルから取得するのが理想
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   conn.close()
   ```

5. J-Quants データ取得・保存
   fetch_* 系関数でデータを取得し、save_* 関数で DuckDB に保存します。
   例: fetch_daily_quotes → save_daily_quotes

   注意: API 利用には JQUANTS_REFRESH_TOKEN を設定してください。

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py — パッケージのエントリ
- config.py — 環境変数・.env 自動読み込み・設定ラッパー（Settings）

data/
- jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
- news_collector.py — RSS 収集、前処理、raw_news 保存、銘柄抽出

research/
- factor_research.py — momentum / volatility / value 等のファクター計算
- feature_exploration.py — 将来リターン計算、IC 計算、統計サマリー
- __init__.py — 便利関数エクスポート

strategy/
- feature_engineering.py — features テーブル作成（正規化・クリップ・UPSERT）
- signal_generator.py — features と ai_scores を使った BUY/SELL シグナル生成
- __init__.py

portfolio/
- portfolio_builder.py — 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
- position_sizing.py — 株数決定・制限・単元丸め（calc_position_sizes）
- risk_adjustment.py — セクターキャップ・レジーム乗数（apply_sector_cap, calc_regime_multiplier）
- __init__.py

backtest/
- engine.py — バックテストエンジン（データコピー・ループ・注文作成）
- simulator.py — ポートフォリオシミュレータ（擬似約定、履歴管理）
- metrics.py — バックテスト評価指標計算
- run.py — CLI エントリポイント
- clock.py — 将来拡張用の模擬時計

その他:
- execution/ — 実行層（kabuステーション API 等、今後の実装想定）
- monitoring/, portfolio/ の追加ユーティリティ群

---

## 注意事項・運用メモ

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）から行われます。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API にはレート制限とリトライロジックがあります。大量取得はレート制限を尊重してください。
- バックテスト用に利用する DuckDB は本番用 DB を直接上書きしないこと。run_backtest は必要なテーブルをインメモリにコピーして実行しますが、投入データの準備は事前に行ってください。
- NewsCollector は外部フィードの解析を行うため SSRF/サイズ上限/XML インジェクション等の対策を実装していますが、データ品質・エンコードに起因する例外は発生し得ます。ログを確認してください。
- 本ライブラリは研究/実運用の両方で利用できるよう設計されていますが、実際の資金運用に用いる場合は十分な監査・テストを実施してください（特に execution 層の接続/認証・注文ロジック）。

---

この README はコードベースから抽出した概要です。詳細な API 使用法や DB スキーマ（tables/columns）、実運用手順・CI 設定・例示データについては付属ドキュメント（Design docs / md ファイル）やコード内 docstring を参照してください。ご質問があれば、使用したいユースケースに合わせて具体例を追加します。