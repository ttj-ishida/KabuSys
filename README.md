# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
DuckDB をデータストアにして、J-Quants からのデータ取得（株価・財務・カレンダー）、ETL、ニュース収集、特徴量作成、戦略シグナル生成、発注監査などを層別に実装したモジュール群です。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみ使用）
- DuckDB を用いた冪等な保存（ON CONFLICT / トランザクション）
- API 呼び出しのレート制御・リトライ・トークンリフレッシュ
- RSS ニュース収集での SSRF / XML 攻撃対策
- シンプルなテスト容易性（id_token 注入など）


## 機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 環境変数から各種設定を取得（J-Quants トークン、kabu API、Slack、DB パス 等）
- データ取得（J-Quants）
  - 日次株価（OHLCV）のページネーション取得・保存
  - 財務データ（四半期）取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制限、再試行、トークン自動リフレッシュ
- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
- ETL パイプライン
  - 差分取得（差分・バックフィル）、保存、品質チェックフック
  - 日次 ETL の実行エントリ run_daily_etl
- ニュース収集
  - RSS フィード取得、前処理、raw_news 保存、記事と銘柄コードの紐付け
  - SSRF/サイズ/圧縮/XML 脆弱性対策
- 研究 / ファクター計算
  - momentum / volatility / value 等のファクター計算（prices_daily, raw_financials を参照）
  - 将来リターン計算、IC（Spearman）や統計サマリ
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング & シグナル生成
  - build_features: 生ファクターの正規化・ユニバースフィルタ・features テーブルへの UPSERT
  - generate_signals: features と ai_scores を統合して final_score を算出し BUY/SELL シグナル作成
  - SELL はストップロスやスコア低下で判定（保有ポジションとの連携）
- 発注・監査
  - audit モジュールで戦略→シグナル→発注→約定までトレース可能な監査テーブル群を提供


## 必要要件

- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

（プロジェクトをパッケージ化している場合は pip install -e . などを使ってください）


## 環境変数（主要）

以下はコード内で参照する主な環境変数（README 用に抜粋）。プロジェクトルートの .env / .env.local から自動読み込みされます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL


## セットアップ手順（概略）

1. リポジトリをクローンして必須パッケージをインストール
   - Python 3.10 以降を用意
   - pip で duckdb / defusedxml 等をインストール

2. 環境変数を設定
   - プロジェクトルートに .env（.env.local）を作成
   - 必須キー（上記）を設定

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   - Python から schema.init_schema を呼び出して DB を作成します（":memory:" も可）。

   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

4. J-Quants の認証情報を準備
   - JQUANTS_REFRESH_TOKEN を .env に設定（get_id_token は内部でリフレッシュ実行）

5. （任意）kabu API 設定、Slack 設定を行う


## 使い方（主要 API とワークフロー例）

以下は日次処理の基本的な流れ（Python スクリプトから）です。

1) スキーマ初期化（初回のみ）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量の構築（features テーブル作成）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（features + ai_scores → signals）
```python
from datetime import date
from kabusys.strategy import generate_signals

n = generate_signals(conn, target_date=date.today())
print(f"signals written: {n}")
```

5) ニュース収集の実行例
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)
```

6) 監査ログ / 発注フローは audit モジュール群を利用して監査テーブルへ記録します（order_requests / executions 等）。


## 便利な内部ユーティリティ

- get_id_token / jquants_client._request: J-Quants 認証・API 呼び出し
- data.stats.zscore_normalize: クロスセクション Z スコア正規化
- research.calc_forward_returns / calc_ic / factor_summary: 研究用途の解析ユーティリティ
- data.calendar_management: 営業日判定や next_trading_day / prev_trading_day / get_trading_days
- data.pipeline.run_daily_etl: 一連の ETL をまとめて実行


## 注意点 / 実装上のポリシー

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探す）を基準に行われます。テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB への挿入は基本的に冪等（ON CONFLICT）で実装されています。
- J-Quants API のレート制御は固定間隔スロットリング（120 req/min）で行われます。429/5xx 等でリトライと指数バックオフを行います。
- RSS フィード取得は SSRF・XML/Bomb 対策を随所に施しています（スキーム検証、プライベートIP拒否、サイズ上限、defusedxml など）。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかで、is_live / is_paper / is_dev プロパティで判定できます。


## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- kabusys/
  - __init__.py              — パッケージメタ（version, __all__）
  - config.py                — 環境変数 / 設定管理（Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存関数）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py               — zscore_normalize などの統計ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - features.py            — data.stats の再エクスポート
    - audit.py               — 監査ログ用テーブル定義
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（正規化・ユニバースフィルタ）
    - signal_generator.py    — generate_signals（最終スコア計算・BUY/SELL 判定）
  - execution/               — 発注・実行層（パッケージ準備）
  - monitoring/              — 監視・メトリクス（ディレクトリ置き場）
  - その他: research/*, data/* に多くのサブ機能が実装されています

（上記はリポジトリ内のソースから抜粋して要約したものです。）


## 追加情報 / 開発者向けメモ

- 戦略仕様やデータプラットフォームの設計意図はソース中のコメント（StrategyModel.md, DataPlatform.md 相当の注記）に従っています。
- 単体テストや CI を導入する場合、jquants_client._request や _urlopen などをモックして外部依存を切り離してください。
- 本番稼働時は KABUSYS_ENV=live を指定し、発注層（execution）と実際のブローカー API 連携を慎重に実装してください。

---

不明点や README に追記してほしい内容（例:具体的な .env.example、実行スクリプト例、テーブル定義の詳細など）があれば教えてください。必要に応じてサンプル .env.example や運用手順も作成します。