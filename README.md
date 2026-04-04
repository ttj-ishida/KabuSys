# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。  
J-Quants / RSS / OpenAI（LLM）などを用いてデータ収集・ETL・品質チェック・AIスコアリング・市場レジーム判定・監査ログの管理を行うことを想定しています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を提供する Python パッケージです。

- J-Quants API を用いた株価・財務・市場カレンダーの差分取得（ETL）
- DuckDB を用いたデータ保存とクエリ（raw_prices, raw_financials, market_calendar 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS によるニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI を用いたニュースのセンチメント付与（銘柄ごとの ai_score / マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）
- 監査ログ（signal / order_request / executions）スキーマの初期化と管理
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー 等）

設計上、バックテストでのルックアヘッドバイアスを避けるため、各関数は内部で現在時刻を安易に参照せず、明示的な target_date を受け取る方式を採用しています。

---

## 機能一覧（抜粋）

- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL の結果を ETLResult オブジェクトで取得
- データ品質:
  - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
- ニュース:
  - fetch_rss / preprocess_text / news -> raw_news 保存ロジック（news_collector）
  - score_news (OpenAI による銘柄別センチメント)
- AI（マクロ / レジーム）:
  - score_regime (ETF 1321 の MA200 + マクロセンチメントから regime を判定)
- 研究:
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary
- 監査:
  - init_audit_db / init_audit_schema（監査ログ用 DuckDB 初期化）
- J-Quants クライアント:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 関数で DuckDB に冪等保存

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（PEP 604 の型記法や型ヒント表記のため）
- 必要パッケージ: duckdb, openai（OpenAI Python SDK v1系想定）, defusedxml 他

例（仮の仮想環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発中ならパッケージを編集可能インストール
pip install -e .
```

環境変数 / .env:
- プロジェクトは起点ファイルの親フォルダから `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先）。
- 自動ロードを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（settings からの抜粋）:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime が必要とする）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携を行う場合）
- KABU_API_BASE_URL: kabuAPI ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知連携（任意）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH: プロセス監視用パス（デフォルト data/...）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

推奨: リポジトリルートに `.env.example` を置き、必要な値をコピーして `.env` を用意してください。

---

## 使い方（主要な例）

まず DuckDB 接続を作成して処理を呼ぶのが基本パターンです。

共通準備:
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path 型
db_path = settings.duckdb_path.as_posix()
conn = duckdb.connect(db_path)
```

1) 日次 ETL を実行する（カレンダー・株価・財務・品質チェックを順に実行）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20), run_quality_checks=True)
print(result.to_dict())
```

2) ニュースをスコアリングして ai_scores を更新する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジームを判定して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit_duckdb.db"))
# init_audit_db はテーブル・インデックスを作成し接続を返す
```

5) 研究用ユーティリティの例（モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum_records = calc_momentum(conn, target_date=date(2026,3,20))
# 結果は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev 等）
```

注意:
- OpenAI 呼び出しを用いる関数は api_key 引数でキーを上書きできます（テスト向け）。
- DuckDB に対する書き込みは関数内部で BEGIN/COMMIT/ROLLBACK を行う箇所があります。呼び出し時に既存トランザクションがある場合は注意してください（init_audit_schema の transactional 引数等の説明を参照）。

---

## よく使うコマンド（開発時）

- パッケージを編集可能モードでインストール:
  pip install -e .

- テスト実行（unittest や pytest がある場合）:
  pytest

- 環境読み込みを無効にしてテストする:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 開発 / テスト向けヒント

- 環境依存を排除するため、AI 呼び出し等はモックしやすく設計されています。
  例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api") で応答を差し替え可能。
- news_collector のネットワーク呼び出しは kabusys.data.news_collector._urlopen をモックできます。
- J-Quants クライアントは id_token の自動リフレッシュと rate limiting を内蔵しています。単体テストでは fetch_* 系をモックしてください。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールの一覧（抜粋）です。実際のファイルは src/kabusys 配下に配置されています。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数と設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # 銘柄別ニュースセンチメント
    - regime_detector.py     # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API client + save_*（DuckDB 書込み）
    - pipeline.py           # ETL パイプラインと ETLResult
    - quality.py            # データ品質チェック
    - news_collector.py     # RSS ニュース収集
    - calendar_management.py# 市場カレンダー管理（is_trading_day など）
    - stats.py              # 統計ユーティリティ（zscore_normalize 等）
    - audit.py              # 監査ログスキーマ初期化
    - etl.py                # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py    # モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py# forward returns, IC, factor summary

（上記は抜粋です。詳細はリポジトリ内の src/kabusys を参照してください。）

---

## 注意点 / 制約

- Python のバージョン要件に注意してください（コードは 3.10 以上の構文を利用しています）。
- DuckDB バージョンにより executemany の空リスト挙動など互換性差があるため、空チェックが入っています。
- OpenAI / J-Quants API 呼び出しはレート制限およびエラー処理を実装していますが、API キー・トークンは安全に管理してください。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を基準）から検索されます。CI やテストで環境ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。

---

必要であれば、README に記載する .env.example のサンプルや、よくあるトラブルシュート（例: OpenAI レスポンスのパース失敗時の対処、DuckDB ファイルパスの権限問題など）も追加できます。どの情報をより詳しく載せたいか教えてください。