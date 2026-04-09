# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤の実装例です。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、研究（ファクター計算・特徴量探索）、AI を使ったニュースセンチメント評価、監査ログ（発注→約定のトレーサビリティ）などの主要コンポーネントを含みます。

---

## 主な特徴（機能一覧）

- データ収集 / ETL
  - J-Quants API から株価（日次OHLCV）、財務データ、JPXカレンダーを差分取得・保存
  - RSS からニュース取得、正規化、DB保存（raw_news / news_symbols）
  - 日次 ETL パイプライン（run_daily_etl）を提供

- データ品質管理
  - 欠損、重複、将来日付、スパイク検出などのチェック（quality モジュール）
  - ETL 実行結果を表す ETLResult を返却

- 研究・因子計算
  - Momentum / Value / Volatility / Liquidity 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化

- AI（OpenAI）統合
  - ニュース記事から銘柄ごとのセンチメントを計算して ai_scores に保存（news_nlp.score_news）
  - マクロニュースとETF（1321）の MA200 乖離を合成して市場レジーム（bull/neutral/bear）を判定（regime_detector.score_regime）
  - LLM 呼び出しはリトライとフォールバックを組み込み（API失敗時は安全側の値で継続）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを保持する監査テーブルの初期化・ヘルパー（init_audit_schema / init_audit_db）
  - 発注の冪等キーやステータス管理をサポート

- 環境設定
  - .env ファイル または OS 環境変数を自動ロード（config.Settings）
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能

---

## 必要条件

- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がない場合は上記をインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# または: pip install -e .
```

---

## 環境変数（主なもの）

以下はコード内で参照される主要な環境変数（必須/任意を併記）：

- 必須（実行する機能に応じて）
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 実行で必要）
  - KABU_API_PASSWORD — kabu ステーション API パスワード（発注機能がある場合）
- OpenAI 関連
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- 任意（デフォルト値あり）
  - KABUSYS_ENV (development | paper_trading | live) — 実行環境（デフォルト: development）
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — ログレベル（デフォルト: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
  - PAPER_FILL_MODE — Paper Trading のモック充足設定（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH / KILL_FLAG_PATH / その他監視設定

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動的に読み込みます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ざっくり）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存ライブラリをインストール（duckdb, openai, defusedxml など）
4. `.env` を作成して必要な環境変数を設定
5. DuckDB ファイル用ディレクトリ（`data/` など）を作成（自動で作られることが多いが事前準備しておくと安心）

例:
```bash
git clone https://.../kabusys.git
cd kabusys
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
mkdir -p data
# .env を作成
```

---

## 使い方（コード例）

以下は代表的な呼び出し例です。適宜 import パスや引数を調整して利用してください。

- DuckDB 接続の準備（設定からパスを取得）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア計算（ai -> ai_scores に書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY 環境変数を設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（regime: bull/neutral/bear を market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ（Audit）用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # または別パス
# これで監査テーブル群が作成される
```

- RSS フィード取得（ニュースコレクタの単体利用）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 主要モジュールと役割（ディレクトリ構成）

リポジトリの主要なファイル構成（抜粋）:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                      # 環境変数 / 設定管理
   ├─ ai/
   │  ├─ __init__.py
   │  ├─ news_nlp.py                 # ニュース -> 銘柄センチメント (score_news)
   │  └─ regime_detector.py          # マクロ + ETF MA200 で市場レジーム判定 (score_regime)
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py           # J-Quants API クライアント + DuckDB 保存関数
   │  ├─ pipeline.py                 # ETL パイプライン（run_daily_etl 等）
   │  ├─ etl.py                      # ETL の公開インターフェース (ETLResult)
   │  ├─ calendar_management.py      # 市場カレンダー管理（is_trading_day 等）
   │  ├─ news_collector.py           # RSS 取得・前処理・保存ロジック
   │  ├─ quality.py                  # データ品質チェック
   │  ├─ audit.py                    # 監査ログ用スキーマ / 初期化
   │  └─ stats.py                    # 汎用統計ユーティリティ（zscore_normalize など）
   └─ research/
      ├─ __init__.py
      ├─ factor_research.py          # Momentum/Value/Volatility 等のファクター計算
      └─ feature_exploration.py      # 将来リターン計算、IC、統計サマリ、rank
```

各モジュールはドキュメント文字列（docstring）で設計方針や処理フローが詳細に説明されています。実装を追うことで挙動を把握しやすくなっています。

---

## トラブルシューティング / 注意点

- 環境変数未設定時、config.Settings の必須プロパティは ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。
- OpenAI API 呼び出しはリトライやフォールバック（記事なしや API エラー時は 0.0 を返す等）を組み込んでいますが、API キーとレート制限設定を適切にしてください。
- J-Quants API はレート制限（120 req/min）を守るよう実装されていますが、並列処理を行う場合は注意が必要です。
- DuckDB のバージョン差異により一部の executemany/バインド挙動が異なる点に注意（コード中に互換処理あり）。

---

## 開発 / 貢献

- 各モジュールはユニットテストで差し替え可能なように外部呼び出しをラップしてあり、モックを使ったテストが容易です（例: OpenAI 呼び出し関数の差し替え）。
- 新しい ETL ジョブや API 統合を追加する際は、既存の ETLResult / quality チェックに合わせてエラー・品質管理を行ってください。

---

この README はコードベースからの抜粋に基づく簡易ドキュメントです。詳細な実装や追加設定は各モジュールの docstring / ソースコードを参照してください。