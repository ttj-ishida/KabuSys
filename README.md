# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤コンポーネント群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター計算、研究用ユーティリティ、監査ログ（約定トレーサビリティ）など、自動売買システムに必要となる共通基盤を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の用途を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理・記事保存（raw_news / news_symbols）
- OpenAI を使ったニュースセンチメント（銘柄別）とマクロセンチメントのスコアリング
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ
- 市場カレンダー管理（営業日・SQ 判定等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / execution）スキーマの初期化と管理

設計上、バックテスト時のルックアヘッドバイアス対策や API エラー時のフォールバック、冪等性（ON CONFLICT）などに配慮しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、トークン自動リフレッシュ、レート制御）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 取得、URL 正規化、SSRF 対策、前処理）
  - データ品質チェック（missing/duplicates/spike/date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news：銘柄別 ai_score を ai_scores テーブルへ）
  - 市場レジーム判定（score_regime：ETF (1321) の MA とマクロニュースを合成して regime を判定）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC など（calc_forward_returns / calc_ic / factor_summary / rank）

---

## 必要条件

- Python 3.10 以上（typing の union 型表記や __future__ annotations を使用）
- 必須パッケージ（代表）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- その他: 標準ライブラリの urllib 等を利用（追加の外部 HTTP ライブラリは不要）

インストール例（最低限）:
```
python -m pip install "duckdb" "openai" "defusedxml"
```

プロジェクトを editable install する場合:
```
pip install -e .
```
（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境変数 / 設定

KabuSys は .env ファイルまたは環境変数から設定を読み込みます（自動ロード機能あり）。自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われ、優先順位は OS 環境変数 > .env.local > .env です。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視DB、デフォルト: data/monitoring.db)
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live (デフォルト: development)
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

注意: Settings クラスは未設定の必須キーに対して ValueError を投げます。`.env.example` を参考に .env を準備してください（本リポジトリに例ファイルがない場合は README のキー一覧を参照して作成してください）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install -r requirements.txt   # 存在する場合
   # または最低限:
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   プロジェクトルートに `.env` を作成するか、環境に直接設定します。必須キーを忘れないでください。
   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=zzzz
   SLACK_CHANNEL_ID=AAAAAA
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB ファイル/ディレクトリ作成（必要に応じて）
   デフォルトの duckdb パスは `data/kabusys.duckdb` です。`kabusys.data.audit.init_audit_db()` を使って監査 DB を初期化できます（下記参照）。

---

## 使い方（主要な API と例）

以下はモジュールを直接インポートして利用する最小例です。いずれも DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を渡します。

- DuckDB 接続の作成例
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path を返します
conn = duckdb.connect(str(settings.duckdb_path))
```

- ETL（日次パイプライン）実行
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しなければ今日が対象（但し ETL 内で trading day に調整される）
result = run_daily_etl(conn, target_date=None)
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キー必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# APIキーは環境変数 OPENAI_API_KEY または api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} symbols")
```

- 市場レジーム判定（OpenAI API キー必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査スキーマ初期化（監査用 DuckDB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions 等が作成される
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- 市場カレンダーの判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## 注意点 / トラブルシューティング

- OpenAI 呼び出しはネットワークやレート制限を考慮したリトライロジックを備えていますが、APIキーの管理（環境変数 OPENAI_API_KEY）を必ず行ってください。
- J-Quants API の認証はリフレッシュトークンベースです。`JQUANTS_REFRESH_TOKEN` を設定してください。ID トークンは内部で自動取得・キャッシュされます。
- .env の自動ロードはプロジェクトルートの検出に .git または pyproject.toml を使用します。CI などで自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB への executemany に空リストを渡すとエラーになるバージョン差分があるため、該当箇所では空チェックが入っています（ライブラリバージョン依存に注意）。

---

## ディレクトリ構成

主要ファイル／モジュールのツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (pipeline の再エクスポート)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他データ関連ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージ化済みだがここには記載されていない補助モジュール群が想定される)
  - execution/ (発注・証券会社連携レイヤー想定)
  - strategy/ (戦略層想定)

上記は実装済みの主要モジュールで、ETL / data / ai / research にフォーカスしています。

---

## 貢献 / 拡張

- 新しいデータソースやフィーチャを追加する際は、ETL パイプラインの差分更新・品質チェックの流れに従ってください。
- AI モジュール（news_nlp / regime_detector）は OpenAI のレスポンスとフォーマットに依存します。モデル変更やプロンプト改善はレスポンスバリデーションに影響するため、テストを追加してください。
- 監査ログスキーマは冪等性・トレーサビリティ重視です。必要に応じてインデックスや制約の追加を検討してください。

---

必要な情報の追加や README の改良（例: CLI 実行例、.env.example の追加、requirements.txt の生成等）を希望される場合は教えてください。