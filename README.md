# KabuSys — 日本株自動売買システム

軽量なデータプラットフォーム・リサーチ・AI 評価・監査ログ機能を備えた日本株向け自動売買支援ライブラリです。J-Quants / RSS / OpenAI（gpt-4o-mini）等と連携してデータ取得・品質チェック・特徴量計算・ニュースセンチメント評価・市場レジーム判定・監査ログ管理を行います。

主な利用ケース：
- 日次 ETL（株価・財務・市場カレンダー）の自動取得と保存
- ニュースを用いた銘柄別 AI センチメントの算出（ai_scores）
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- 研究用途のファクター計算（モメンタム、ボラティリティ、バリュー等）
- 発注〜約定までの監査ログ（audit）テーブル初期化

---

## 機能一覧

- 環境設定管理（.env / 環境変数、自動ロード）
- J-Quants API クライアント（差分取得・ページネーション・トークンリフレッシュ・レートリミット）
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS の安全対策・正規化・重複回避）
- ニュース NLP（OpenAI を用いた銘柄別センチメント算出、score_news）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメント合成、score_regime）
- 研究用モジュール（ファクター計算・将来リターン・IC 計算・Z スコア正規化）
- 監査ログ初期化ユーティリティ（監査テーブル・インデックス作成、init_audit_db）

---

## 要件

- Python 3.10+
- 必要な主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - typing-extensions（必要に応じて）
- OS: 特に制約はありませんが、ネットワークアクセス（J-Quants / RSS / OpenAI）を行います。

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージを配置）
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存をインストール
   - プロジェクト配布方法によりますが、開発時は editable install + 必要パッケージをインストールすることを推奨します：
   ```bash
   pip install -e ".[dev]"   # pyproject.toml / setup.cfg がある場合
   # または
   pip install duckdb openai defusedxml
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   代表的な環境変数（最低限必要なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（発注周り）
   - KABU_API_BASE_URL: kabu API のベース URL（省略可）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
   - DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV: development | paper_trading | live
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

   （プロジェクトに .env.example があればそちらをコピーして編集してください）

5. DB ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的なハンドル）

以下は Python REPL / スクリプトから直接呼び出す最小例です。実運用ではジョブスケジューラやワーカーから呼び出します。

- DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores テーブルに書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # API キーは環境変数 OPENAI_API_KEY を参照
print(f"wrote {written} ai scores")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化（ファイル作成 + テーブル作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # transactional=True が内部で使われます
```

- 設定を参照する（コード内）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)
```

注意点：
- score_news/score_regime は OpenAI API を使用します。API キーは引数で直接渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- ETL や保存系は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）を前提としています。スキーマ初期化は別途スキーマ定義関数を用意するか、既存 DB を使用してください。

---

## よく使うユーティリティ

- 設定自動ロード:
  - プロジェクトルートの `.env` / `.env.local` を探索して環境変数を読み込みます（CWD ではなくパッケージ設置位置からプロジェクトルートを探索）。
  - テストなどで自動ロードを止めたい場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- J-Quants クライアント:
  - トークンの自動リフレッシュ、レートリミット、リトライを備えた実装。
  - 主な関数:
    - get_id_token(refresh_token=None)
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_daily_quotes(conn, records)
    - save_financial_statements(conn, records)
    - save_market_calendar(conn, records)

- データ品質チェック:
  - run_all_checks(conn, target_date=..., reference_date=..., spike_threshold=...)

- ニュース収集:
  - fetch_rss(url, source, timeout=30)
  - 内部で安全対策（SSRF 防止・受信サイズ制限・XML パースの安全化）を実施

---

## ディレクトリ構成（抜粋）

（主要ファイル・モジュールの概観）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント解析（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL 型定義の再公開（ETLResult）
    - calendar_management.py     — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py          — RSS 取得・整形・保存ロジック
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログ（テーブル定義／初期化）
  - research/
    - __init__.py
    - factor_research.py         — モメンタム/ボラティリティ/バリュー等の計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリ等

各モジュールは DuckDB 接続を受け取り SQL + Python の組合せで処理を行う設計になっており、バックテストや本番でのルックアヘッドバイアスに注意した実装方針が取られています（date の扱いに注意）。

---

## 開発・デプロイ上の注意

- すべての外部 API 呼び出し（J-Quants / OpenAI / RSS）はネットワーク障害やレートリミットに対してリトライやフォールバックを組み込んでいますが、プロダクション環境ではモニタリングとアラートを設定してください。
- OpenAI 呼び出しは JSON Mode を利用して厳密な JSON を期待する設計になっていますが、レスポンスの中に余計なテキストが混入することを想定してパーサの復元処理を行っています。
- DuckDB 実行時の executemany に空リストを渡すとエラーになるバージョンがあるため、空リストチェックを行っている箇所があります。DuckDB のバージョン互換性に注意してください。
- audit テーブルは削除しない前提の監査ログで、UTC タイムゾーンで TIMESTAMP を保存します。

---

README はこのコードベースの主要な使い方と構造の要約です。より詳細なドキュメント（API 仕様・スキーマ定義・運用手順・例外一覧）は別ファイル（Design/Docs）に分けることを推奨します。必要であれば、サンプルスクリプトや初期スキーマ SQL、.env.example のテンプレートも作成できます。必要でしたら作成しますのでお知らせください。