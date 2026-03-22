# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームの参考実装です。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集、そして発注/実行フレームワーク（設計）の主要コンポーネントを含みます。研究（research）と本番実装（strategy / execution / data）の分離、ルックアヘッドバイアス防止、冪等性（DB 保存）や堅牢なエラーハンドリングを重視した設計になっています。

主な目的は「日本株の定量戦略を開発・検証・運用するための基盤」を提供することです。

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）: レート制限、リトライ、トークン自動リフレッシュ対応
  - RSS ベースのニュース収集（SSRF対策、トラッキングパラメータ除去、記事IDのハッシュ化）
- データ基盤
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution レイヤー）
  - ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- 研究 / 特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター算出（prices_daily / raw_financials に基づく）
  - クロスセクション Z スコア正規化ユーティリティ
  - ファクターと将来リターンの相関 / IC 計算、統計サマリ
- 戦略系
  - 特徴量の合成と features テーブルへの保存（build_features）
  - features / ai_scores を統合して final_score を計算し signals を生成（generate_signals）
  - Bear レジーム抑制、BUY/SELL の日次入れ替えアップサート（冪等）
- バックテスト
  - インメモリにデータをコピーして日次ループでシミュレーション（run_backtest）
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）、日次スナップショット、トレード記録
  - バックテスト指標（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio）
- 実行 / モニタリング（設計骨子あり。発注 API 層や Slack 通知へ接続可能）

---

## 動作環境・依存関係（例）

- Python 3.10+
- duckdb
- defusedxml
- （標準ライブラリの urllib 等を利用）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージ化されていれば: pip install -e .
```

必要に応じて他のライブラリを追加してください（ログ集約、Slack クライアント等は別途）。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
2. 依存ライブラリをインストール（上記参照）
3. 環境変数を設定（.env をプロジェクトルートに置くことで自動読込されます）

重要な環境変数（必須 / 任意）:
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャネル ID
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, default: development) 値: development / paper_trading / live
- LOG_LEVEL (任意, default: INFO)

自動 .env ロードは config.py によりプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB スキーマ初期化
Python REPL またはスクリプトから:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: も可
conn.close()
```
これで必須テーブルとインデックスが作成されます。

---

## 使い方（主なユースケース）

- J-Quants からのデータ取得（ETL）
  - jquants_client.fetch_* で API から取得し、save_* で DuckDB に保存できます。
  - ETL ラッパー例（pipeline モジュール）を利用して差分取得や品質チェックを行えます。
  - 例（疑似コード）:
    ```python
    import duckdb
    from kabusys.data.schema import init_schema
    from kabusys.data import jquants_client as jq
    from datetime import date

    conn = init_schema("data/kabusys.duckdb")
    today = date.today()
    token = jq.get_id_token()  # settings.jquants_refresh_token を利用
    records = jq.fetch_daily_quotes(id_token=token, date_from=today, date_to=today)
    saved = jq.save_daily_quotes(conn, records)
    conn.close()
    ```

- ニュース収集
  - RSS から記事を取得して raw_news / news_symbols に保存します。
  - 例:
    ```python
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    from kabusys.data.schema import init_schema

    conn = init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
    results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    conn.close()
    ```

- 特徴量生成
  - DuckDB 接続と target_date を渡して features を作成します。
    ```python
    from kabusys.strategy import build_features
    from kabusys.data.schema import init_schema
    from datetime import date

    conn = init_schema("data/kabusys.duckdb")
    n = build_features(conn, target_date=date(2024, 1, 4))
    print(f"features upserted: {n}")
    ```

- シグナル生成
  - features / ai_scores / positions を参照して signals を生成します。
    ```python
    from kabusys.strategy import generate_signals
    from kabusys.data.schema import init_schema
    from datetime import date

    conn = init_schema("data/kabusys.duckdb")
    total = generate_signals(conn, target_date=date(2024,1,4), threshold=0.6)
    print(f"signals written: {total}")
    ```

- バックテスト（CLI）
  - コマンドラインから簡単にバックテストを実行できます（データベースが事前に必要）。
    ```
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
    ```
  - または Python API:
    ```python
    from kabusys.backtest.engine import run_backtest
    from kabusys.data.schema import init_schema
    from datetime import date

    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
    print(result.metrics)
    conn.close()
    ```

- その他ユーティリティ
  - zscore_normalize, calc_ic, calc_forward_returns, factor_summary など研究用ユーティリティが揃っています。

---

## 実装上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアスを防ぐため、各処理は target_date 時点のデータのみ参照するように設計されています（例: features / signals / backtest）。
- DuckDB への保存は可能な限り冪等（ON CONFLICT / DELETE+INSERT の日付単位置換）を維持します。
- ネットワーク処理（J-Quants / RSS）はレート制御・リトライ・SSRF対策等を備えています。
- research モジュールは DB 読取のみ・発注等の副作用を持たず、研究用に独立して動作します。
- バックテストは本番 DB を汚染しないためにインメモリにデータをコピーして実行します。

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py (パッケージエクスポート・バージョン)
  - config.py (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存ロジック)
    - news_collector.py (RSS 収集・前処理・保存)
    - schema.py (DuckDB スキーマ定義と init_schema)
    - stats.py (zscore_normalize 等統計ユーティリティ)
    - pipeline.py (ETL ワークフローと差分更新ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py (momentum/volatility/value の計算)
    - feature_exploration.py (forward returns / IC / summary)
  - strategy/
    - __init__.py
    - feature_engineering.py (ファクター正規化・features テーブル書込)
    - signal_generator.py (final_score 計算・signals 書込)
  - backtest/
    - __init__.py
    - engine.py (run_backtest と補助関数)
    - simulator.py (PortfolioSimulator, TradeRecord, DailySnapshot)
    - metrics.py (バックテスト指標計算)
    - run.py (CLI entrypoint)
    - clock.py (将来の分足シミュ用の模擬時計)
  - execution/ (発注・実行層のインタフェース：実装骨子)
  - monitoring/ (監視・通知関連：実装骨子)

---

## 参考・補足

- 設定取得は kabusys.config.settings 経由で行ってください（例: settings.jquants_refresh_token）。
- DuckDB の初期化は init_schema() を一度実行すること（既存のテーブルがあればスキップ）。
- テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動ロードを抑止できます。
- 本リポジトリは参考実装であり、本番運用時は追加の監査・テスト・エラー処理・セキュリティ対策が必要です（API キーの管理、秘密情報の扱い、十分なモニタリングなど）。

---

もし README に追加したい「例: CI ワークフロー、Docker 化、詳細な ETL スケジュール例」などがあれば、用途に応じて追記します。