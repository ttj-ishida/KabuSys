# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（軽量プロトタイプ）

このリポジトリは日本株のデータ収集（J-Quants）、ニュース収集・NLP、ETL、研究用ファクター計算、監査ログ、及び市場レジーム判定などを提供するモジュール群を含む Python パッケージ `kabusys` のソースコードです。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API 用クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レートリミット・保存）
  - 日次 ETL パイプライン（株価・財務・市場カレンダー）
  - 市場カレンダーの差分更新ジョブ

- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、gzip 対応）
  - OpenAI（gpt-4o-mini）によるニュースセンチメント（銘柄単位）スコアリング（batch, JSON Mode）
  - マクロニュースを使った市場レジーム判定（ETF 1321 の MA + マクロセンチメント合成）

- 研究・ファクター処理
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- データ品質チェック（quality モジュール）
  - 欠損検出、重複チェック、スパイク検出、日付整合性チェック
  - 品質問題を QualityIssue オブジェクトで収集

- 運用・監査
  - 監査ログ用スキーマ初期化（signal_events / order_requests / executions）
  - 監査用 DuckDB 初期化ユーティリティ（UTC タイムゾーン固定）

- 設定管理
  - .env ファイル自動読み込み（プロジェクトルート検出・.env / .env.local 優先順）
  - 必須環境変数のラッパー（settings オブジェクト）

---

## 事前要件

- Python 3.10+（型ヒントの union と一部新構文を想定）
- 必要パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は pip でインストールしてください）

例（推奨仮想環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発インストール（プロジェクトルートで）
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそれを使用してください）

---

## 環境変数 / 設定

kabusys は環境変数経由で設定を読み取ります。プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（CWD ではなくパッケージ位置からプロジェクトルートを検出）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（ETL, jquants_client）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必要な場合）
- SLACK_CHANNEL_ID       : Slack 送信先チャンネル ID
- KABU_API_PASSWORD      : kabuステーション API パスワード（実行モジュールが使用する場合）

オプション / デフォルト
- OPENAI_API_KEY         : OpenAI API キー（news_nlp.score_news / regime_detector.score_regime で使用）
- KABUSYS_ENV            : 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL              : ログレベル ("DEBUG","INFO",...)
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : SQLite（監視用）パス（デフォルト: data/monitoring.db）

settings オブジェクトからアクセス可能:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順（ローカルでの基本的な準備）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに `.env` を作成し必須環境変数を設定
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C00000000
     KABUSYS_ENV=development
     ```
5. DuckDB データベースの準備
   - デフォルトパスは `data/kabusys.duckdb`。初期スキーマはプロジェクト内で定義された別モジュールから初期化できます（既存のスキーマ初期化関数は別途提供してください）。監査ログ用 DB 初期化は以下の関数を使用できます。

---

## よく使う使い方（API 例）

以下は代表的なモジュールの呼び出し例です。DuckDB へは `duckdb.connect()` で接続し、conn を渡します。

- 日次 ETL 実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（指定日分）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が環境変数に必要
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化（監査専用 DB）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済み DuckDB 接続
```

- 研究用ファクター計算例:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# Z スコア正規化（例）
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- データ品質チェック:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

---

## 自動 .env 読み込みについて

- パッケージの起動時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると `.env` と `.env.local` を自動で読み込みます。
- 読み込み順は: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## ロギング / 実行環境

- settings.log_level でログレベルを制御（環境変数 LOG_LEVEL）。
- settings.env で実行モードを切り替え（development / paper_trading / live）。本番発注系の挙動を分離するために使用します。

---

## 主要ディレクトリ構成（src/kabusys）

以下はパッケージの主要モジュールと公開 API の概要です。

- kabusys/
  - __init__.py (パッケージ初期化、__version__)
  - config.py (環境変数 / settings)
  - ai/
    - __init__.py (score_news を再エクスポート)
    - news_nlp.py (銘柄単位ニュースセンチメント -> ai_scores へ書き込み)
    - regime_detector.py (1321 MA + マクロセンチメントから市場レジーム判定)
  - data/
    - __init__.py
    - calendar_management.py (market_calendar 管理、営業日判定)
    - etl.py (ETLResult エクスポート)
    - pipeline.py (run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl 等)
    - stats.py (zscore_normalize)
    - quality.py (品質チェック)
    - audit.py (監査スキーマ初期化 / init_audit_db)
    - jquants_client.py (J-Quants API クライアント、fetch/save 系)
    - news_collector.py (RSS 取得・前処理・raw_news 保存補助)
  - research/
    - __init__.py (研究用公開 API)
    - factor_research.py (calc_momentum, calc_volatility, calc_value)
    - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る設計で、外部リソースへの直接的な副作用（発注など）を最小限にしてテスト容易性を高めています。

---

## 注意事項 / 運用上のポイント

- OpenAI / J-Quants など外部 API を呼び出す部分は API キーやレート制限に注意してください。テストでは各種 _call_openai_api 等をモックする想定です。
- ETL / ニュース処理は「ルックアヘッドバイアス」を避けるために date 引数を必ず明示する設計になっています（内部で date.today() を参照しない関数が多い）。
- DuckDB の executemany に関する互換性（空リスト渡せない等）の扱いに注意しています（pipeline / news_nlp などにコメントあり）。
- ニュース収集は SSRF 対策やレスポンスサイズチェックを行いますが、実運用でのフィード一覧やメンテナンスは別途管理してください。

---

## さらに読みたいところ / 開発のヒント

- jquants_client.py: API のリトライ・401 リフレッシュ・ページネーション・保存ロジックの実装を参照
- news_collector.py: RSS の正規化・SSRF 保護・gzip 対応・記事ID の生成方法
- news_nlp.py / regime_detector.py: LLM 呼び出しのバッチ・再試行・JSON Mode を使った堅牢なパース
- data.pipeline.run_daily_etl: 日次の処理フローと品質チェックの例

---

この README はコードベースの概要と利用法をまとめたものです。実際の運用での詳細（DB スキーマの初期化 SQL、CI / デプロイ手順、追加の依存パッケージ、.env.example 等）はプロジェクトに応じて補完してください。必要であれば README をより具体的なコマンドや初期化サンプルで拡張できます。