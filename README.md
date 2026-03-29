# KabuSys

KabuSys は日本株のデータ取得・前処理・ファクター計算・AI ベースのニュース評価・市場レジーム判定・監査ログを含む日本株自動売買システムのコアライブラリです。本リポジトリは主に以下の役割を持ちます：

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いた ETL パイプライン（差分取得・保存・品質チェック）
- RSS ベースのニュース収集と LLM を用いたニュースセンチメント評価
- ファクター計算 / 研究用ユーティリティ（モメンタム、バリュー、ボラティリティ、IC 等）
- 市場レジーム判定（MA とマクロニュースの合成）
- 発注・約定に関する監査ログスキーマの初期化・管理
- 設定管理（.env 自動読み込み、環境変数検証）

以下はこのコードベースの README（日本語）です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要なユースケース例）
- ディレクトリ構成と主要モジュールの説明
- 設計上の注意点 / 仕様メモ

---

## プロジェクト概要

KabuSys は日本株のデータ基盤と解析・研究・自動売買に必要な共通処理群を提供する Python パッケージです。  
データ取得は J-Quants API と RSS（ニュース）を利用し、DuckDB を中心にデータを永続化します。AI（OpenAI）を用いたニュース解析・市場レジーム判定機能、研究用のファクター計算、ETL の品質チェックや監査ログ（発注→約定トレース）までをカバーします。

設計上の重視点：
- ルックアヘッドバイアス防止（バックテストでの安全）
- ETL / 保存の冪等性（ON CONFLICT / upsert）
- API 呼び出しに対する堅牢なリトライ・レート制御
- モジュール分離（AI モジュールはテスト差し替えしやすい）

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検査（settings オブジェクト）
- データ取得（jquants_client）
  - 株価日足（daily_quotes）取得 / 保存
  - 財務データ取得 / 保存
  - JPX マーケットカレンダー取得 / 保存
  - レートリミット制御 / トークン自動リフレッシュ / ページネーション対応
- ETL パイプライン（data.pipeline）
  - run_daily_etl：カレンダー → 株価 → 財務 → 品質チェックの一括処理
  - 差分更新、バックフィル設定対応、ETL 結果を ETLResult で報告
- データ品質チェック（data.quality）
  - 欠損データ、スパイク、重複、日付不整合の検出
- カレンダー管理（data.calendar_management）
  - 営業日判定、前後の営業日取得、カレンダー更新ジョブ
- ニュース収集（data.news_collector）
  - RSS 取得（SSRF 対策、サイズ制限、正規化）と raw_news への冪等保存処理を想定
- AI 関連（ai.news_nlp, ai.regime_detector）
  - ニュースを銘柄単位にまとめて LLM に投げ、銘柄ごとの ai_score を ai_scores に保存
  - ETF (1321) の 200 日 MA 乖離 と マクロニュース LLM センチメントを合成した市場レジーム判定
  - OpenAI（gpt-4o-mini）を JSON mode で利用。429/ネットワーク/5xx 等は指数バックオフでリトライ
- 研究用ユーティリティ（research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（スピアマン）計算、ファクターサマリー、Z スコア正規化
- 監査ログ（data.audit）
  - signal_events, order_requests, executions テーブルの DDL を備え、監査 DB 初期化関数を提供

---

## セットアップ手順

前提：
- Python 3.9+（型アノテーションや union types を利用しているため）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローンしてインストール（開発時）
   - 推奨：プロジェクトルートが .git または pyproject.toml を含むことにより .env 自動読み込みが有効化されます。

   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

   もしくは必要なパッケージを個別にインストール：
   ```bash
   pip install duckdb openai defusedxml
   ```

2. 環境変数 / .env の準備
   - .env.example を参考に .env をプロジェクトルートに作成してください（.env.example は存在する想定）。
   - 主要な環境変数:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション等の API パスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI 呼び出し時に環境変数で指定する場合（API 呼び出し時に関数引数で上書き可能）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視等）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: environment（development / paper_trading / live）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   - .env ロード挙動:
     - 自動的にプロジェクトルートの .env → .env.local を読み込みます（OS 環境変数を保護）。
     - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. DuckDB 初期化（監査 DB など）
   - 監査ログ用 DB を初期化する例：

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

4. OpenAI クライアント
   - OPENAI_API_KEY は環境変数か、関数呼び出し時に api_key 引数で渡してください。
   - LLM 呼び出しはリトライやフェイルセーフの挙動が組み込まれています（失敗時はスコアを 0 にフォールバック等）。

---

## 使い方（主要ユースケース例）

Python から直接呼び出す例を示します。基本的には DuckDB 接続を作成し、各モジュールの関数を呼びます。

1. ETL（日次パイプライン）を実行する

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（settings.duckdb_path は Path オブジェクト）
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を省略すると今日が対象）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースのセンチメントをスコアリングして ai_scores に保存する

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None の場合 ENV の OPENAI_API_KEY を使用
print("書き込んだ銘柄数:", n_written)
```

3. 市場レジーム判定を行う

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4. RSS フィードを取得する（ニュース収集の一部）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

5. 監査 DB の初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降、order_requests 等のテーブルが利用可能
```

6. 研究用ファクター計算（例：モメンタム）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の辞書リスト
```

---

## ディレクトリ構成（主要ファイルの説明）

パッケージは src/kabusys 以下に実装されています。主要なサブパッケージとファイル：

- src/kabusys/
  - __init__.py            : パッケージ初期化、バージョン
  - config.py              : 環境変数読み込み・設定オブジェクト（settings）
- src/kabusys/ai/
  - __init__.py            : ai パブリック API（score_news を公開）
  - news_nlp.py            : ニュースの LLM ベースセンチメント評価と ai_scores 書き込み
  - regime_detector.py     : ETF MA とマクロニュースを組み合わせた市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py      : J-Quants API クライアント（取得／保存・レート制御・リトライ）
  - pipeline.py            : ETL パイプラインの実装（run_daily_etl など）
  - etl.py                 : ETL 用の公開型（ETLResult の再エクスポート）
  - news_collector.py      : RSS 取得・前処理ロジック
  - quality.py             : データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - calendar_management.py : JPX カレンダー管理（営業日判定、更新ジョブ）
  - audit.py               : 監査テーブル DDL と初期化ユーティリティ
  - stats.py               : 汎用統計ユーティリティ（zscore_normalize 等）
- src/kabusys/research/
  - __init__.py
  - factor_research.py     : モメンタム／バリュー／ボラティリティなどの計算
  - feature_exploration.py : forward returns / IC / 統計サマリー等

各モジュールはドキュメント文字列で設計方針や注意点が記載されているため、実装の挙動や期待される DB スキーマ・参照テーブル（例：prices_daily、raw_prices、raw_financials、raw_news、news_symbols、ai_scores、market_regime など）を参照してください。

---

## 設計上の注意点 / 仕様メモ

- ルックアヘッドバイアス防止:
  - 多くのモジュールで datetime.today() や date.today() を内部で無制限に参照しない設計になっています。target_date を呼び出し側で指定して評価を行うことが推奨されます。
- 冪等性:
  - jquants_client.save_* 系は ON CONFLICT DO UPDATE（upsert）で冪等保存を行います。
  - news_collector は URL 正規化 → SHA256 先頭 32 文字で ID を作る想定で冪等を確保します。
- API レート制御 / リトライ:
  - J-Quants は固定間隔スロットリング（120 req/min）で保護されています。OpenAI 呼び出しは JSON mode を利用し、429/ネットワーク/5xx は指数バックオフで再試行します。
- フェイルセーフ:
  - AI 呼び出し失敗や API エラー時は致命的に落とさず、スコアを 0 にフォールバックする設計が随所に採用されています（運用継続性優先）。
- テスト容易性:
  - LLM 呼び出しや HTTP の低レイヤーはモック差し替えを想定している部分があり、ユニットテストで安定化しやすい構造です。

---

必要であれば、README に下記を追加してカスタマイズできます：
- CI / テスト実行方法（pytest 等）
- データベーススキーマ（DDL のフルリスト）
- .env.example の雛形
- 実運用時のデプロイ手順（systemd / コンテナ / クラウドジョブの例）
- Slack 通知・モニタリングの利用方法

――――――

以上です。必要なら実際の .env.example のテンプレート、または各 DB テーブルの詳細 DDL を README に追記しますか？