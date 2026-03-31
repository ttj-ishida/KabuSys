# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 連携）・ニュース収集・LLM を用いたニュースセンチメント・市場レジーム判定・ファクター計算・監査ログ等を含む設計済みモジュール群を提供します。

主な用途：
- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- RSS ニュース収集と LLM による銘柄センチメント算出（ai_scores）
- マクロニュース + ETF MA による市場レジーム判定
- 研究向けのファクター算出・特徴量探索ユーティリティ
- 発注監査ログ（audit テーブル群）初期化ユーティリティ

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local / OS 環境変数から自動で設定を読み込み（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- データ ETL（jquants_client + pipeline）
  - 差分取得、ページネーション対応、レート制御、リトライ、DuckDB への冪等保存
  - run_daily_etl による日次パイプライン（カレンダー → 株価 → 財務 → 品質チェック）
- ニュース収集（news_collector）
  - RSS フィード取得、URL 正規化、SSRF 対策、raw_news / news_symbols への保存準備
- ニュース NLP（news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（バッチ・JSON mode・リトライ・検証）
- 市場レジーム判定（regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して daily market_regime を作成
- 研究用ユーティリティ（research）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン計算、IC / 統計サマリ
- データ品質チェック（quality）
  - 欠損・スパイク・重複・日付不整合の検出
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化ヘルパ
- 汎用統計ユーティリティ（data.stats）
  - z-score 正規化 など

---

## 前提・依存関係

- Python 3.10+
- 必須ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- （任意）J-Quants API 利用、OpenAI 利用にはそれぞれの API キーが必要

requirements の例（プロジェクトに合わせて調整してください）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
   - パッケージが src 配下にある想定のため、editable インストール推奨:
     pip install -e .

2. 環境変数を準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可）。

   例: .env（最小必須キー）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   - 必須項目（Settings._require を参照）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - OpenAI API キーは関数呼び出し時に引数で注入可能。環境変数 `OPENAI_API_KEY` からも参照します。

3. DuckDB データベースの場所
   - デフォルト: data/kabusys.duckdb（settings.duckdb_path）
   - パスを作成しておく（init 関数群が自動的に親ディレクトリを作る箇所もありますが念のため）

---

## 使い方（代表的な例）

以下は簡単な Python からの呼び出し例です。実運用時は適切なログ設定・例外処理を追加してください。

- DuckDB に接続して日次 ETL を実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジームを判定して保存
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化（監査テーブル作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn をそのまま使って監査ログを操作できます
```

- 研究用ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records), "件")
```

---

## 環境変数 / 設定の詳細

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
  - 自動読み込みを無効化する場合:
    - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要な環境変数（設定クラス Settings で参照）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - OPENAI_API_KEY (OpenAI を使う関数のデフォルト参照先)
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

---

## 主要モジュールとディレクトリ構成

リポジトリは src/kabusys 配下に実装されています。主要なファイル・サブパッケージと役割は以下の通り。

- src/kabusys/
  - __init__.py: パッケージ初期化（version）
  - config.py: 環境変数 / .env の読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py: ニュースを LLM に投げて銘柄ごとの ai_score を作成
    - regime_detector.py: ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（fetch / save）
    - pipeline.py: 日次 ETL パイプライン run_daily_etl 等
    - etl.py: ETLResult の公開（再エクスポート）
    - news_collector.py: RSS 収集・前処理
    - calendar_management.py: market_calendar 管理・営業日判定ユーティリティ
    - stats.py: zscore_normalize などの統計ユーティリティ
    - quality.py: データ品質チェック
    - audit.py: 監査テーブル DDL と初期化ヘルパ
  - research/
    - __init__.py
    - factor_research.py: momentum/volatility/value の計算
    - feature_exploration.py: forward returns, IC, factor_summary, rank

---

## 運用上の注意点 / 設計方針の抜粋

- ルックアヘッドバイアス対策
  - モジュール内では基本的に datetime.today()/date.today() を参照せず、呼び出し側が target_date を指定する設計になっています（ETL やスコア算出で重要）。
- 冪等性
  - DuckDB への保存は ON CONFLICT DO UPDATE（あるいは挿入時のキー生成）で冪等に設計。
- フェイルセーフ
  - LLM や外部 API の呼び出しで失敗が発生しても、完全停止せず安全側の既定値（例: macro_sentiment=0.0）で継続する箇所が多くあります。
- セキュリティ
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml の利用等を行っています。
- ロギング
  - 各モジュールは logger を使用。環境変数 LOG_LEVEL で基本動作ログレベルを制御できます。

---

## よくある操作 / トラブルシュート

- 自動で .env を読み込まない／テスト時に明示的設定を使いたい
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境を準備してください。
- OpenAI 呼び出しをテストで差し替えたい
  - 各モジュールは内部の _call_openai_api を unittest.mock.patch で差し替えられるよう設計されています。
- DuckDB executemany の空パラメータ問題
  - 一部実装では DuckDB 0.10 の executemany に空配列を渡さないようガードしています。エラーが出る場合はバージョンやパラメータを確認してください。

---

必要であれば以下を追記します：
- 開発用の requirements-dev.txt / pre-commit 設定例
- .env.example の完全なテンプレート
- より詳細な API リファレンス（関数別 usage）