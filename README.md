# KabuSys

日本株向けの自動売買基盤ライブラリ（研究・データ収集・特徴量生成・シグナル生成・ETL・監査用ユーティリティを提供）

---

## プロジェクト概要

KabuSys は、J-Quants 等の外部データソースから日本株データを取得し、DuckDB に格納・整形し、特徴量（features）を生成、さらに戦略シグナル（buy/sell）を算出するためのライブラリ群です。  
主に次の用途を想定しています。

- データパイプライン（差分取得、保存、品質チェック）
- リサーチ（ファクター計算、特徴量探索、IC 計算）
- 戦略（特徴量正規化・融合、シグナル生成）
- ニュース収集（RSS から raw_news へ保存）
- DuckDB スキーマ初期化・監査ログの管理

設計方針として、ルックアヘッドバイアスを避ける、冪等性を担保する（ON CONFLICT / トランザクション）、外部に過剰依存しない（DuckDB と標準ライブラリ中心）ことを重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・レート制御・トークン自動リフレッシュ付き）
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（市場カレンダー／株価／財務データの差分取得と保存）
  - news_collector: RSS 取得→raw_news保存、銘柄抽出機能（SSRF対策・圧縮上限・トラッキング除去）
  - calendar_management: 営業日判定・次/前営業日・カレンダー更新ジョブ
  - stats: Z スコア正規化などの統計ユーティリティ
  - features: zscore_normalize の公開
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy/
  - feature_engineering.build_features: 生ファクターを正規化・ユニバースフィルタ適用して features テーブルへ UPSERT
  - signal_generator.generate_signals: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存
- monitoring / execution:
  - （拡張点）発注・約定・ポジション管理、監査ログなどを扱うためのスケルトン / DDL・ユーティリティを提供

---

## 要求環境 / 依存

- Python 3.10 以上（型ヒントに | 演算子を使用）
- 必須ライブラリ（最低限）:
  - duckdb
  - defusedxml
- その他: 標準ライブラリのみで動作する箇所が多いですが、実運用ではネットワーク（J-Quants 等）へのアクセスが必要です。

開発環境例（推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージとしてインストールできる場合:
pip install -e .
```

---

## 環境変数 / 設定

KabuSys は環境変数により設定を読み込みます。プロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabu ステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- Slack 通知
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- 実行モード / ログ
  - KABUSYS_ENV: development / paper_trading / live (デフォルト: development)
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

簡易 .env 例:
```
# .env
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は `kabusys.config.settings` 経由で取得できます。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   # またはプロジェクトに requirements / pyproject があれば `pip install -e .` 等
   ```

4. 環境変数を用意（`.env` / `.env.local` をプロジェクトルートに作成）
   - 必要な変数は上記参照

5. DuckDB スキーマ初期化
   Python REPL で：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可能
   conn.close()
   ```
   この呼び出しにより、必要なテーブルとインデックスが作成されます（冪等）。

---

## 使い方（主要なワークフロー例）

以下は代表的なワークフローの例です。すべて DuckDB 接続（kabusys.data.schema.init_schema が返す conn）を第1引数として渡します。

1) 日次 ETL（市場カレンダー・株価・財務の差分取得）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

2) 特徴量の構築（features テーブルへ書き込み）
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, date.today())
print(f"features upserted: {count}")
```

3) シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
from datetime import date

n = generate_signals(conn, date.today(), threshold=0.6)  # 重みをカスタム可能
print(f"signals generated: {n}")
```

4) ニュース収集ジョブ（RSS → raw_news / news_symbols）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "6752"}  # など、有効銘柄コードの集合（任意）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

5) リサーチ用ユーティリティ
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
from datetime import date

mom = calc_momentum(conn, date.today())
fwd = calc_forward_returns(conn, date.today(), horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

注意: 上記関数は DuckDB の該当テーブル（prices_daily, raw_financials, features, ai_scores, positions など）が存在し、必要なデータが格納されていることが前提です。

---

## よく使う API の説明（抜粋）

- kabusys.data.schema.init_schema(db_path)
  - DuckDB ファイルを初期化し接続を返す（テーブル作成は冪等）。
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
  - 日次 ETL を実行し ETLResult を返す（品質チェックオプションあり）。
- kabusys.data.jquants_client.fetch_daily_quotes(...)
  - J-Quants から日足を取得（ページネーション対応）。
- kabusys.data.news_collector.fetch_rss(url, source)
  - RSS 取得（SSRF 対策・gzip 対応・上限サイズ検査）。
- kabusys.strategy.build_features(conn, target_date)
  - 生ファクターを統合・正規化し features テーブルを更新。
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights)
  - features・ai_scores をもとに BUY/SELL シグナルを生成して signals に保存。

---

## 開発者向けメモ

- 環境の自動読み込みは config モジュールで `.env` / `.env.local` (プロジェクトルート判定は .git または pyproject.toml を探索) を行います。テストで自動読み込みを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants へのリクエストは内部でレート制限（120 req/min）を実装しており、429/408/5xx などはリトライします。401 はトークン自動更新を試します。
- ニュース収集はデフォルトで `DEFAULT_RSS_SOURCES`（Yahoo Finance のビジネス RSS）を使いますが引数で差し替え可能です。
- 多くの DB 操作はトランザクションを使用して原子性・冪等性を確保しています。例外発生時はロールバック処理があります。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - audit (追加の監査DDL / インデックス定義 等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (プレースホルダ / 将来的な監視機能)
- pyproject.toml / setup.cfg / .gitignore （プロジェクト設定ファイル等）

---

## ライセンス / 貢献

このドキュメントではライセンス情報を含めていません。実際のリポジトリに LICENSE ファイルや貢献ガイド（CONTRIBUTING.md）があればそちらを参照してください。

---

README に記載の内容はコードベースの現状（主要モジュール・API・使い方）に基づいてまとめています。運用環境では環境変数や API トークンの管理、バックアップ、監査ログ保存ポリシー、エラーハンドリングやモニタリング設定を適切に構築してください。