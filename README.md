# KabuSys

日本株向けの自動売買 / データプラットフォーム支援ライブラリです。  
ETL（J-Quants 経由の価格・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は日本市場向けに設計されたデータプラットフォーム & リサーチ / 自動売買支援モジュール群です。主に以下を目的とします：

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- RSS ベースのニュース収集とニュース NLP（OpenAI を利用した銘柄別センチメント）
- 日次の市場レジーム判定（ETF + マクロニュースを組み合わせた判定）
- 研究用途のファクター計算（Momentum / Value / Volatility 等）
- データ品質チェック
- 監査ログ / 発注トレーサビリティ（DuckDB ベースの監査テーブル）
- DuckDB を主体としたローカルデータ管理

設計の共通方針として、ルックアヘッドバイアスを避ける実装、外部 API 呼び出しのリトライ・フェイルセーフ、DB 操作の冪等性（ON CONFLICT / DELETE→INSERT 等）を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系、ID トークン自動リフレッシュ、レートリミット管理）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 取得、前処理、SSRF 防御、トラッキングパラメータ除去）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 統計ユーティリティ（Zスコア正規化）
  - 監査ログ初期化（監査テーブル・インデックスの作成、init_audit_db）
- ai
  - ニュース NLP（銘柄ごとのセンチメントを OpenAI で評価: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロ記事センチメント合成: score_regime）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（将来リターン計算 / IC / 統計サマリー）
- その他
  - 設定読み込み（.env / 環境変数、settings オブジェクト）
  - 監視・通知のための Slack トークン設定（設定項目あり）

---

## 必要環境・依存関係

- Python 3.10 以上（typing の | 演算子等を使用）
- 主な Python パッケージ:
  - duckdb
  - openai (OpenAI Python SDK; 本コードは Chat Completions の JSON Mode を想定)
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging, gzip, hashlib など

（インストール例）
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

---

## セットアップ手順

1. リポジトリをクローン / パッケージを配置
2. Python と依存ライブラリをインストール（上記参照）
3. プロジェクトルートに `.env` を作成（自動読み込みあり）
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
4. 必要な環境変数を設定（例: `.env`）

推奨の .env（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX

# オプション
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

注意:
- OpenAI API キーは AI 関連機能（score_news, score_regime）で必須です。
- J-Quants の refresh token はデータ ETL に必須です。

---

## 使い方（簡単な例）

以下は代表的な使い方のサンプルです。DuckDB の接続オブジェクト（duckdb.connect）を渡して各関数を呼び出します。

- 日次 ETL を実行する（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（前日 15:00 JST ～ 当日 08:30 JST の期間を対象に銘柄別スコアを生成）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print("written:", n_written)
```

- 市場レジーム判定（ETF 1321 ベース + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ディレクトリ自動作成
# conn を保持して監査テーブルへアクセス可能
```

- RSS フィード取得（一例）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

src_url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(src_url, source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 環境変数・設定一覧

主に以下の環境変数が利用されます（必須・任意に注意）:

- 必須（ETL / AI を使う場合）
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
  - OPENAI_API_KEY — OpenAI API キー（score_news, score_regime）
  - KABU_API_PASSWORD — kabu API（発注関連）
  - SLACK_BOT_TOKEN — Slack 通知に使用
  - SLACK_CHANNEL_ID — Slack チャンネル ID

- オプション
  - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
  - DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値は任意）

Settings は `from kabusys.config import settings` で利用できます。

---

## よくある実行時注意点 / トラブルシューティング

- Missing Environment Variable
  - settings のプロパティは必須 env が未設定だと ValueError を送出します。`.env` を準備してください。
- OpenAI / J-Quants の API 呼び出し
  - ネットワークエラーやレート制限時はモジュール側でリトライやフォールバック（多くは 0.0 として継続）を行いますが、結果が欠損する場合があります。ログを確認してください。
- DuckDB スキーマ
  - ETL / 保存先のテーブルが無い場合はスキーマ初期化が必要です（スキーマ初期化ユーティリティはプロジェクトに含める想定）。監査スキーマは `init_audit_db` で作成できます。
- ニュース収集の SSRF 対策
  - news_collector は内部でホストの私的アドレス検査やリダイレクト検証を行います。社内の閉域 RSS 等特別な環境で失敗する場合は、ホストの解決や許可設定を確認してください。
- Python バージョン
  - このコードは Python 3.10+ を想定しています。型ヒントに | (Union) を使用しています。

---

## ディレクトリ構成

リポジトリのコードベース（主要ファイル・モジュール）は以下のような構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / .env 自動読み込み設定
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP スコアリング（score_news）
    - regime_detector.py     # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - jquants_client.py      # J-Quants API クライアント（fetch/save）
    - news_collector.py      # RSS ニュース収集
    - calendar_management.py # マーケットカレンダー管理
    - quality.py             # データ品質チェック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査ログ初期化（監査テーブル DDL）
    - etl.py                 # ETL 結果型再エクスポート
  - research/
    - __init__.py
    - factor_research.py     # Momentum / Value / Volatility 等
    - feature_exploration.py # forward returns / IC / factor summary
  - (その他)
    - strategy/              # 戦略関連（パッケージ公開は存在するがコードは別途）
    - execution/             # 約定 / ブローカー接続（別モジュール想定）
    - monitoring/            # 監視 / Slack 通知（別モジュール想定）

---

## 開発・拡張メモ

- テスト:
  - 各種外部依存（OpenAI, J-Quants, HTTP）の呼び出し部は差し替え（モック）可能なように実装されています。ユニットテストではモックして実行してください（例: news_nlp._call_openai_api を patch）。
- ログ:
  - settings.log_level でログレベルを制御。運用環境では INFO / WARNING、デバッグ時は DEBUG を推奨します。
- 冪等性:
  - J-Quants → DuckDB の保存関数は ON CONFLICT / DO UPDATE を用い、ETL の冪等性を確保しています。
- セキュリティ:
  - news_collector は SSRF 対策、defusedxml を使った XML パースなどを行っています。API キーは環境変数で安全に扱ってください。

---

### 最後に

この README はコードベースに含まれる主要モジュールの利用方法と設計方針を簡潔にまとめたものです。運用・導入時は各モジュールのドキュメントやログ出力を参照し、API キーや DB 初期化、スキーマ管理を適切に行ってください。必要であれば、具体的な導入手順（systemd ジョブ、コンテナ化、CI/CD、マイグレーション手順など）についても追補できます。