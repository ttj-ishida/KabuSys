# KabuSys — 日本株自動売買システム

簡易紹介とドキュメントです。KabuSys は日本株向けのデータパイプライン、リサーチ、特徴量生成、シグナル生成、バックテスト、疑似約定シミュレータを備えた自動売買フレームワークです。モジュールは概ね以下の責務に分かれています。

- data: 外部API（J-Quants）やRSSからのデータ取得／保存、DuckDB スキーマ定義、ETL パイプライン
- research: ファクター計算・探索（モメンタム、ボラティリティ、バリュー等）
- strategy: 特徴量正規化（features テーブル作成）／シグナル生成（signals テーブル）
- backtest: バックテストエンジン、ポートフォリオシミュレータ、評価指標
- execution: 発注・実行まわり（モジュール境界のため発注API依存を避ける設計）
- monitoring: （将来的な監視機能用エントリ）

以下、README に含める内容をまとめます。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要ユースケースの例）
- ディレクトリ構成（主要ファイルの説明）
- 環境変数一覧と注意点

---

## プロジェクト概要

KabuSys は次の要件を満たすことを目的としています。

- J-Quants 等外部データソースからの差分取得と DuckDB への冪等保存
- research 層で計算した生ファクターを用いた特徴量作成（Zスコア正規化、ユニバースフィルタ等）
- 正規化済みファクターと AI スコアを統合したシグナル生成（BUY/SELL）
- signals に従った疑似約定でのバックテスト（スリッページ・手数料モデル、ポジション管理）
- RSS ニュース収集と記事から銘柄抽出（SSRF・gzip・XML攻撃対策等）

設計方針として、ルックアヘッドバイアス防止・冪等性・外部APIへ直接の発注依存回避・テスト容易性を重視しています。

---

## 機能一覧

主な機能（一部）

- データ取得・保存
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - RSS ニュース収集（SSRF対策、記事IDを正規化して冪等保存）
  - DuckDB スキーマ定義・初期化（init_schema）
- データ品質・ETL
  - 差分ETL（最終取得日を見て差分取得）
  - 品質チェック（欠損・スパイク等、quality モジュールと連携）
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ（ATR）、バリュー（PER/ROE）等
  - 将来リターン計算（forward returns）、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング
  - 正規化（Zスコア）、ユニバースフィルタ（株価・流動性）、features テーブルへのUPSERT
- シグナル生成
  - momentum/value/volatility/liquidity/news の統合スコア計算
  - Bear レジーム検出で BUY 抑制、SELL のエグジット判定（ストップロス等）
  - signals テーブルへ日次置換（冪等）
- バックテスト
  - インメモリ DuckDB に必要データをコピーして日次ループでシミュレーション
  - PortfolioSimulator（スリッページ・手数料・約定ロジック）
  - メトリクス計算（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio）
  - CLI 実行用エントリポイント（python -m kabusys.backtest.run）
- ニュース処理
  - RSS 取得・前処理・raw_news へ保存・記事⇄銘柄紐付け

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 記法などを使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全対策）

推奨手順（UNIX 系）:

1. 仮想環境作成 & 有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   最低限必要なパッケージ例：
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトをパッケージ化済みであれば `pip install -e .` 等）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB スキーマ初期化
   Python REPL などで:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
   ```

---

## 環境変数（主要）

KabuSys は環境変数から設定を読み込みます。必須・任意は config.Settings に準拠します。

必須（少なくとも実行する機能に応じて設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層利用時）
- SLACK_BOT_TOKEN — Slack 通知（必要時）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

注意:
- .env ファイルは .env → .env.local の順で読み込まれ、OS 環境変数が優先されます。
- テストなどで自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（主要ユースケース）

以下は簡易的な使用例です。すべて duckdb の接続オブジェクト（kabusys.data.schema.init_schema/ get_connection）の利用を前提としています。

1) DuckDB スキーマ初期化（前述）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

2) データ取得（J-Quants から株価を差分取得し保存）
（data.pipeline.run_prices_etl を利用する想定；pipeline モジュールの他関数と組み合わせて使用）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# target_date は取得終了日（通常は当日）
prices_fetched, prices_saved = run_prices_etl(conn, target_date=date.today())
conn.close()
```

3) 特徴量作成（features テーブルへの書込）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024,1,31))
print("features upserted:", count)
conn.close()
```

4) シグナル生成（signals テーブルへ）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2024,1,31))
print("signals written:", total)
conn.close()
```

5) バックテスト（CLI）
用意済みの DB（prices_daily, features, ai_scores, market_regime, market_calendar が必要）に対して
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
実行結果として主要メトリクス（CAGR, Sharpe, MaxDD 等）が stdout に出力されます。

6) ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
conn.close()
```

---

## ディレクトリ構成（概要）

以下は主要なモジュールとその役割の一覧（src/kabusys 以下）。

- __init__.py
  - パッケージ初期化、公開モジュール一覧

- config.py
  - 環境変数の自動ロードと settings オブジェクト（必須設定取得・検証）

- data/
  - jquants_client.py — J-Quants API クライアント（レート制御・リトライ・保存関数）
  - news_collector.py — RSS 収集・記事前処理・raw_news 保存・銘柄抽出
  - pipeline.py — ETL パイプライン（差分取得・保存の高位API）
  - schema.py — DuckDB スキーマ定義と init_schema/get_connection
  - stats.py — Zスコア正規化など統計ユーティリティ

- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py — forward returns, IC, factor summary, rank
  - __init__.py — 便利関数の公開

- strategy/
  - feature_engineering.py — features テーブル作成（正規化・ユニバースフィルタ）
  - signal_generator.py — features + ai_scores -> signals 生成
  - __init__.py — API公開（build_features, generate_signals）

- backtest/
  - engine.py — バックテストの主要ループ（run_backtest）
  - simulator.py — PortfolioSimulator（疑似約定・履歴管理）
  - metrics.py — バックテスト評価指標計算
  - run.py — CLI エントリポイント
  - clock.py — SimulatedClock（拡張用）

- execution/
  - （発注・実行に関する実装・プレースホルダ）

- monitoring/
  - （監視機能用の実装・プレースホルダ）

---

## 注意点 / 運用のヒント

- ルックアヘッドバイアス対応: strategy/research の関数は target_date 時点のデータのみを参照するよう設計されています。ETL、features、signal 生成の順序を守ってください。
- 冪等性: DB への保存は ON CONFLICT などで冪等化されています。日付単位での置換（DELETE→INSERT）で再実行が安全になるよう設計されています。
- テスト容易性: config の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で抑止できます。jquants_client の HTTP 呼び出し部分や news_collector._urlopen はテスト時にモック可能です。
- Python バージョン: 本コードベースは Python >= 3.10 を想定しています（型注釈の | 等）。

---

以上がプロジェクトの簡易 README です。必要であれば以下の追加情報を作成します：
- 開発環境用の requirements.txt / pyproject.toml 例
- より詳しい ETL 実行例（run_prices_etl の残りの挙動や calendar の扱い）
- CI / テスト実行手順

どれが必要か教えてください。