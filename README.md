# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
データ収集（J-Quants、RSS）、ETL・品質チェック、監査ログ、AI を用いたニュースセンチメント評価、研究用のファクター計算・特徴量解析などの機能を提供します。

主な設計方針は「ルックアヘッドバイアスの回避」「冪等性」「フェイルセーフ（API失敗時の継続）」です。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ユーティリティ
- データ収集 / ETL
  - J-Quants API クライアント（OHLCV、財務、マーケットカレンダー、上場情報）
  - 差分取得／ページネーション／トークン自動リフレッシュ／レート制御
  - ETL パイプライン（市場カレンダー・株価・財務の差分取得、品質チェック）
- データ品質チェック
  - 欠損、スパイク（急変）、重複、日付不整合の検出
  - QualityIssue 型による集約
- ニュース収集
  - RSS フィード取得（SSRF対策、URL正規化、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存設計（処理は news_collector）
- AI（OpenAI）連携
  - ニュースセンチメント（銘柄別） => ai_scores への書き込み（gpt-4o-mini / JSON mode）
  - マクロセンチメントと ETF MA 乖離を組み合わせた「市場レジーム判定」
  - API 呼び出しはリトライ／バックオフ済み、失敗時は安全なフォールバック
- 研究用モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）算出、ファクター統計サマリー
  - 汎用 zscore 正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions とインデックスの初期化機能
  - 監査DB初期化ユーティリティ（UTCタイムゾーン固定）

---

## 要件（主なライブラリ）

- Python 3.10+
- duckdb
- openai
- defusedxml

（プロジェクトに合わせて他の標準ライブラリ・ユーティリティを使用）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   - リポジトリルートに `pyproject.toml` / `.git` がある前提で自動.env読み込みが動作します。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -e .
   - あるいは個別に:
     - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env`（および `.env.local` を必要に応じて）を配置します。
   - 自動読み込みはデフォルトで ON（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

例 .env（最低限の必須項目）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易サンプル）

以下は主要ユースケースの Python 例です。実行前に必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続の作成例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # 存在しない場合は作成される
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア（銘柄別）を生成して DB に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 MA200 とマクロニュースの合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を用いて監査テーブルへ書き込み・検索が可能
```

- J-Quants API クライアントの直接呼び出し
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# get_id_token() は settings.jquants_refresh_token を使って id_token を返す
quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
```

- RSS フィード取得（簡易）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- OpenAI を利用する機能（score_news / score_regime 等）は API キーが必要です。api_key 引数に渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- 各処理はルックアヘッドバイアスを避けるため、内部で date.today() を不用意に参照しない設計です（target_date を明示的に渡すことを推奨します）。

---

## 設定・運用のポイント

- 自動 .env ロード
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込みます。
  - テスト等で自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 読み込み順: OS 環境変数 > .env.local > .env

- ログレベル / 環境
  - `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - `KABUSYS_ENV`（development / paper_trading / live）

- フェイルセーフ
  - 外部 API（OpenAI / J-Quants 等）失敗時は、設計上はできるだけ局所的にフォールバックして処理継続を試みます（例: マクロスコアの失敗時は 0.0）。
  - ただし ETL 等で致命的なエラーがあれば ETLResult.errors に記録されます。

---

## ディレクトリ構成

（主要ファイル・モジュール）
```
src/
  kabusys/
    __init__.py
    config.py                    # 環境変数・設定管理
    ai/
      __init__.py
      news_nlp.py                # ニュースセンチメント（銘柄別）
      regime_detector.py         # 市場レジーム判定
    data/
      __init__.py
      calendar_management.py     # マーケットカレンダー管理
      etl.py                     # ETL パイプライン公開入口
      pipeline.py                # ETL 実装（prices/financials/calendar）
      stats.py                   # 統計ユーティリティ（zscore 等）
      quality.py                 # データ品質チェック
      audit.py                   # 監査ログスキーマ初期化
      jquants_client.py          # J-Quants API クライアント（取得 & 保存）
      news_collector.py          # RSS ニュース収集
      ...                        # その他関連モジュール
    research/
      __init__.py
      factor_research.py         # ファクター計算（momentum/value/vol）
      feature_exploration.py     # 将来リターン / IC / 統計サマリ
    research/                     # 研究用モジュール群
    ...                          # strategy, execution, monitoring 等の名前空間（存在を示唆）
```

---

## 開発・テストのヒント

- OpenAI / J-Quants 呼び出し部分は外部呼び出しを抽象化しているため、テスト時は該当関数（例: _call_openai_api, _urlopen, jquants_client._request）をモックしてレスポンス制御してください。
- DuckDB のインメモリ接続は `duckdb.connect(":memory:")` で利用可能です。ETL/pipeline の単体テストで便利です。
- ニュース収集の RSS パーサは defusedxml を利用しているため、XML に対する安全対策が組み込まれています。

---

## 注意事項

- 本ライブラリは "実際の発注" を行うコンポーネント（execution, strategy, monitoring 等）と連携する設計ですが、コード提供された範囲では発注 API の呼び出し・実運用ルールは含まれません。実運用で利用する際はリスク管理（複数段階の確認、サンドボックスでの十分なテスト、監査ログの整備）を必ず実施してください。
- API キー・トークンは安全に管理し、不要になったらローテーションしてください。

---

ご要望があれば、README にサンプル .env.example ファイル、より詳細な ETL 実行手順（cron / GitHub Actions 例）、あるいは strategy / execution 層の利用例テンプレートを追加します。どの情報を優先して追記しますか？