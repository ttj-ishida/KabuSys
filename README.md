# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、研究用ファクター計算、監査ログ（取引トレース）など、バックテスト〜実運用に必要な各機能をモジュール化して提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境設定
  - .env ファイルまたは環境変数を自動ロード（プロジェクトルート検出）
  - 必須変数チェック（Settings クラス）
- データ取得 / ETL
  - J-Quants API クライアント（差分取得・ページネーション・再試行・レートリミット対応）
  - 日次 ETL パイプライン（prices / financials / market_calendar の差分取得・保存）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS 収集器（SSRF 対策、サイズ制限、トラッキング除去）
  - OpenAI（gpt-4o-mini）で銘柄ごとにニュースセンチメントを算出（batch・リトライ・JSON Mode対応）
- 市場レジーム判定
  - ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成で日次レジーム (bull/neutral/bear) を判定
- 研究（Research）
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクターサマリー、Zスコア正規化
- 監査（Audit）
  - signal → order_request → execution のトレース用テーブル定義と初期化ユーティリティ
- ユーティリティ
  - DuckDB を中心とした保存・クエリ設計
  - 外部 API 呼び出しの失敗に対するフェイルセーフ設計（可能な限り継続）

---

## 必要環境 / 依存パッケージ

主なランタイム依存（最低）:
- Python 3.10+（型注釈で union types 等を使用）
- duckdb
- openai
- defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ化されていれば：
# pip install -e .
```

---

## 環境変数（主なもの）

以下は本プロジェクトで参照される主要な環境変数です（.env でも指定可能）。README 内の例は .env ファイルとしてプロジェクトルートに置くことを想定しています。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API パスワード（注文機能を使う場合）

オプション / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（例: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector の api_key 引数が省略された場合に使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live (default: development)
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

サンプル .env（プロジェクトルート）:
```text
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

読み込み優先度:
OS環境変数 > .env.local > .env  
自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカルでの素早い開始）

1. リポジトリをクローン
2. 仮想環境作成 & アクティベート
3. 依存インストール
   ```
   pip install duckdb openai defusedxml
   ```
4. プロジェクトルートに `.env`（上のサンプル）を配置
5. DuckDB データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（API / スニペット）

以下は主要なユースケースの簡単な Python スニペットです。実行前に環境変数が準備されていることを確認してください。

- DuckDB 接続を用意:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行（J-Quants から差分取得して保存・品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に保存:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```
score_news は OpenAI の API キーを引数で渡すか、環境変数 OPENAI_API_KEY を参照します。

- 市場レジームを判定して market_regime テーブルへ書き込み:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンがセットされます
```

- ファクター計算（研究用途）:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- ユーティリティ（Zスコア正規化）:
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m"])
```

---

## 注意点 / 設計上の考慮

- Look-ahead bias を避けるため、各モジュールは内部で日付の扱いに注意（target_date 未満のデータのみ使用、datetime.today() を無条件に参照しない等）。
- OpenAI / 外部 API 呼び出しはリトライ・フェイルセーフ実装。API 失敗時は可能な限り処理継続（0.0 フォールバックやスキップ）となります。
- DuckDB の executemany に対する空リスト制約などバージョン互換性に配慮した記述あり。
- RSS 収集は SSRF や XML 攻撃対策（defusedxml、ホストのプライベート判定、最大レスポンスサイズ等）を行っています。

---

## ディレクトリ構成

主要ファイル / モジュールを抜粋した構成:

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                     -- ニュース NLP（score_news）
    - regime_detector.py              -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント + save_* 関数
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - etl.py                          -- ETL 結果型の公開
    - calendar_management.py          -- 市場カレンダー管理・営業日ロジック
    - news_collector.py               -- RSS 収集器
    - quality.py                      -- データ品質チェック
    - stats.py                        -- 統計ユーティリティ（zscore_normalize）
    - audit.py                        -- 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py              -- Momentum/Value/Volatility 等
    - feature_exploration.py          -- forward returns, IC, rank, summary
  - ai/ (上にあり)
  - research/ (上にあり)

---

## ロギング / デバッグ

- 環境変数 LOG_LEVEL でログレベルを指定できます（デフォルト: INFO）。
- 各モジュールは logging.getLogger(__name__) を使用しているため、必要に応じてアプリ側でロガーを設定してください。

---

## テスト・開発

- 自動 .env ロードはプロジェクトルート (.git または pyproject.toml) を基準に行います。テスト時に自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出し箇所はテスト時にモックしやすいように設計されています（モジュール内の _call_openai_api をパッチする等）。

---

必要であれば README に以下を追加できます:
- 詳しい API リファレンス（各関数の引数/返り値表）
- CI / テストの実行方法
- データベーススキーマ定義一覧（raw_prices, raw_financials, ai_scores, market_regime など）

README の拡張希望や、特定機能の詳しい使い方（例: ETL の設定パラメータ解説・監査ログの利用方法等）があれば教えてください。