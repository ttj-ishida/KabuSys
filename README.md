# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants）経由でマーケットデータを収集・保存し、ニュースNLP・市場レジーム判定・ファクター計算などの研究・運用用ユーティリティを提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で date.today() を無作為に参照しない等）
- DuckDB を一次データストアとして利用、ETL は冪等操作（ON CONFLICT）を重視
- 外部API呼び出し（OpenAI / J-Quants 等）はリトライ・レート制御を備える
- 監査（audit）テーブルでシグナル→発注→約定までトレース可能

バージョン: 0.1.0

---

## 機能一覧

- 設定/環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と必須変数チェック
- データETL（kabusys.data.pipeline, jquants_client）
  - J-Quants から株価（日足）、財務、マーケットカレンダーを差分取得・保存
  - 日次 ETL バッチ（run_daily_etl）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、カレンダー更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存（SSRF/サイズ制限/XML防護）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルとインデックスの初期化
  - init_audit_db, init_audit_schema
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC 計算、統計サマリー、Zスコア正規化
- AI（kabusys.ai）
  - ニュースセンチメント集計（score_news）
  - 市場レジーム判定（score_regime） — ETF 1321 の MA200 乖離 + マクロニュース LLM を合成
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize 等

---

## 動作環境 / 依存パッケージ（推奨）

- Python 3.10+
- 必要な主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

※requirements.txt は本リポジトリに含まれていないため、利用環境に応じて上記パッケージを導入してください。例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数（必要なもの）を設定
   - 自動的にプロジェクトルートの `.env` と `.env.local` を読み込む（優先度: OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
5. DuckDB/SQLite 等のデータディレクトリが必要に応じて作成されます（settings のデフォルトパスは data/ 以下）。

推奨される主要環境変数（.env 例）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# kabu ステーション（必要に応じて）
KABU_API_PASSWORD=your_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- settings.jquants_refresh_token は必須です（ETL 実行時に参照）。
- OPENAI_API_KEY は score_news / score_regime の呼び出し時に必要（引数で渡すことも可能）。

---

## 使い方（簡易サンプル）

以下は Python スクリプトからの基本的な利用例です。日付引数は明示的に渡すことを推奨します（ルックアヘッドバイアス回避）。

1) DuckDB 接続の準備（デフォルトパスを使用）
```
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 監査ログ DB の初期化（監査テーブルを別 DB に作る例）
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" でメモリ DB も可
```

3) 日次 ETL を実行
```
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

4) ニュースセンチメントを算出して ai_scores に書き込む
```
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026,3,20))
print("書き込んだ銘柄数:", n_written)
```

5) 市場レジームを算出して market_regime テーブルへ書き込む
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

6) 研究モジュールの利用例（ファクター計算 → Z スコア正規化）
```
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

エラー例:
- 環境変数未設定（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）は ValueError を送出します。`.env.example` を参照して設定してください。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env 等

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, id_token=None, ... ) -> ETLResult

- kabusys.data.jquants_client
  - fetch_daily_quotes(...), fetch_financial_statements(...), save_daily_quotes(...), save_financial_statements(...), fetch_market_calendar(...), save_market_calendar(...), get_id_token(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - preprocess_text(text) 等ユーティリティ

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path) -> duckdb connection

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None) -> 書込銘柄数

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None) -> int

- kabusys.research.factor_research
  - calc_momentum(conn, target_date)
  - calc_value(conn, target_date)
  - calc_volatility(conn, target_date)

- kabusys.research.feature_exploration
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート / src/kabusys 以下）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/……（その他ユーティリティ）

（上記以外に strategy / execution / monitoring 用のパッケージが __all__ に定義されていますが、本コードベースの抜粋では主に data / ai / research が中心です。）

---

## 運用上の注意点

- OpenAI 呼び出しは API レート・リトライ制御を行いますが、利用料・レート制限に注意してください。テスト時は api_key を明示的に渡すか、環境変数をモック可能です。
- J-Quants API 呼び出しはレートリミット（120 req/min）を守るよう内部で制御していますが、トークン期限やネットワークエラーに注意してください。get_id_token は refresh token を使って id_token を取得します。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に関する制約（空リスト不可）を考慮してコードで保護していますが、DuckDB のバージョン依存に注意してください。

---

## トラブルシューティング

- ValueError: 環境変数が未設定
  - 必須環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）が正しく設定されているか確認してください。
- DuckDB 接続周り
  - settings.duckdb_path のディレクトリが存在するか、権限があるかを確認してください。init_audit_db は親ディレクトリを自動作成します。
- RSS 取得で SSRF/接続失敗
  - news_collector は安全性のためプライベートIP/スキームを排除します。URL と公開アクセス性を確認してください。

---

この README はリポジトリ内のコードコメントと API 仕様を要約したものです。実際に運用する際は .env.example をもとに環境を整備し、テスト環境で各モジュール（ETL / news_nlp / regime_detector 等）を個別に検証してください。