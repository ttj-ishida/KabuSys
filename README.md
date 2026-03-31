# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
主に以下の機能を提供します：データの差分ETL（J-Quants）、マーケットカレンダー管理、ニュース収集とNLPによるセンチメント評価、マーケットレジーム判定、リサーチ用のファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など。

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムを構築するための内部モジュール群を集めたライブラリです。設計方針として以下を重視しています。

- Look-ahead bias を防ぐ（datetime.today()/date.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータ基盤
- J-Quants API からの差分取得 + 冪等保存（ON CONFLICT）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON Mode）
- ニュース収集における SSRF / XML BOM 対策
- ETL の品質チェック・監査テーブルによるトレーサビリティ

主な依存技術：
- duckdb
- openai
- defusedxml
（HTTP は標準 urllib を使用）

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants から株価日足、財務データ、マーケットカレンダーを差分取得・保存
  - run_daily_etl で日次パイプライン実行（カレンダー → 株価 → 財務 → 品質チェック）

- カレンダー管理
  - market_calendar テーブル管理 / 営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
  - 夜間バッチでのカレンダー更新（calendar_update_job）

- ニュース収集 / NLP
  - RSS 収集（トラッキングパラメータ削除、SSRF 防止、Gzip 対応）
  - OpenAI を使ったセンチメント評価（news_nlp.score_news）
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定（regime_detector.score_regime）

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z-score 正規化

- データ品質チェック
  - 欠損データ、重複、スパイク、日付不整合の検出（quality.run_all_checks）

- 監査ログ（Audit）
  - signal_events, order_requests, executions 等の監査テーブル定義・初期化（init_audit_schema / init_audit_db）
  - UUID ベースのトレーサビリティと更新タイムスタンプ（UTC）

- J-Quants クライアント
  - レート制限（120 req/min）の固定間隔スロットリング
  - リトライ（指数バックオフ）、401 時のトークンリフレッシュ対応
  - DuckDB へ冪等保存（save_daily_quotes 等）

---

## セットアップ手順

前提
- Python >= 3.10（Union 構文や型注釈、pathlib の挙動を利用）
- Git（.env 自動読み込みはプロジェクトルートの検出に .git や pyproject.toml を使います）

1. リポジトリをチェックアウト / コピー
   - この README に合わせたパッケージは src/ 配下に配置されています。

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   （実際の requirements ファイルはプロジェクト側で管理してください。代表的なパッケージ例を示します）
   - pip install duckdb openai defusedxml

   開発用にパッケージをまとめる場合：
   - pip install -e .   （プロジェクトに setup.cfg/pyproject.toml がある場合）

4. 環境変数（.env）を準備
   - プロジェクトルートの .env および .env.local が自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須の環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN: Slack 通知で使用する Bot トークン
   - SLACK_CHANNEL_ID: Slack のチャンネル ID
   - KABU_API_PASSWORD: kabu ステーション API パスワード

   任意 / デフォルト付き:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な例）

以下は Python REPL やスクリプトからの利用例です。実行前に必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- 共通の準備（DuckDB 接続、設定読み取り）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())  # ETL の実行結果（取得件数や品質問題など）
```

- ニュースセンチメントを算出して ai_scores テーブルへ保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定していれば api_key は省略可
written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"書込銘柄数: {written}")
```

- 市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ用の DuckDB を初期化（audit DB を別ファイルで保持する場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は監査テーブルが作成済みの DuckDB 接続
```

- RSS フィードを取得する（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- リサーチ系の関数例（モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, target_date=date(2026,3,20))
# factors は各銘柄ごとの dict のリスト
```

---

## 主要モジュールと API（抜粋）

- kabusys.config.settings — 環境設定（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）
- kabusys.data.pipeline.run_daily_etl — 日次 ETL のメイン
- kabusys.data.jquants_client — J-Quants API クライアント（fetch_* / save_*）
- kabusys.data.news_collector.fetch_rss — RSS 取得（SSRF 対策あり）
- kabusys.data.quality.run_all_checks — データ品質チェック
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査テーブル初期化
- kabusys.ai.news_nlp.score_news — ニュース NLP による銘柄センチメント算出
- kabusys.ai.regime_detector.score_regime — ETF MA200 とマクロニュースを合成した市場レジーム判定
- kabusys.research.* — ファクター計算・特徴量解析ユーティリティ

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - etl.py
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: schema/etl helpers 等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research / data 共通ユーティリティ群（zscore_normalize 等）

（実際のリポジトリにはさらに細かいファイルやサブパッケージが含まれます。上は主要ファイルの抜粋です。）

---

## 運用上の注意事項

- 環境変数の扱い
  - .env / .env.local は自動読み込みされます（プロジェクトルートが .git または pyproject.toml で検出されます）。
  - テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止できます。

- OpenAI 呼び出し
  - news_nlp / regime_detector は OpenAI（gpt-4o-mini）を JSON Mode で使用します。API のエラー時はフェイルセーフとしてスコアを 0 にフォールバックする処理が入っていますが、API キーは必須です。

- J-Quants
  - レートリミット（120 req/min）を守る実装が組み込まれています。get_id_token はリフレッシュロジックに対応しています。

- DuckDB
  - 一部処理（executemany に空リストを渡すと失敗する等）を考慮した実装になっています。DuckDB バージョンに依存する振る舞いに注意してください。

---

## テスト・開発

- モジュール内では外部 API 呼び出し部分を差替え（モック）できるように設計されています（例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替え）。
- 単体テストを実装する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して環境依存を排除することを推奨します。

---

必要に応じて README の補足（例: CI の設定例、requirements.txt、サンプル .env.example ファイルの追加、各モジュールの詳細ドキュメント化）を作成できます。どの部分を詳述したいか教えてください。