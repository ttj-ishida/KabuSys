# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys の README（日本語）

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・ファクター研究・AI ベースのニュース分析・市場レジーム判定・監査ログ（トレーサビリティ）を主要機能とするツール群です。主に DuckDB をデータレイヤーとし、J-Quants API や RSS、OpenAI（gpt-4o-mini）などの外部サービスと連携して、ETL パイプラインや戦略研究、監視・監査を行えるよう設計されています。

設計上のポイント:
- ルックアヘッドバイアスを意識した日付ハンドリング（関数は date を引数で受け取り、 datetime.today() を直接参照しない）
- 冪等（idempotent）な DB 書き込み（ON CONFLICT / DELETE→INSERT など）
- フェイルセーフ：外部 API 失敗時も処理を継続する設計（スコアを 0 にする等）
- テストしやすさ（モック差し替え箇所の明確化）

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants から株価（daily quotes）や財務データ、JPX マーケットカレンダーを差分取得・保存（`kabusys.data.pipeline`）
  - 差分取得、バックフィル、品質チェックを備えた日次 ETL（`run_daily_etl`）

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（`kabusys.data.quality`）

- ニュース収集・前処理
  - RSS 収集、URL 正規化、SSRF 対策、記事ID生成、raw_news 保存（`kabusys.data.news_collector`）

- AI ベースの NLP
  - 銘柄別ニュースセンチメント（`score_news` / `kabusys.ai.news_nlp`）
  - マクロ＋ETF（1321）による市場レジーム判定（`score_regime` / `kabusys.ai.regime_detector`）

- リサーチ（ファクター計算）
  - モメンタム、バリュー、ボラティリティ等（`kabusys.research.*`）
  - 将来リターン計算、IC 計算、統計サマリー（`feature_exploration`）

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の監査テーブル定義と初期化ユーティリティ（`kabusys.data.audit`）

- J-Quants クライアント
  - レート制限、トークンリフレッシュ、ページネーション、保存ユーティリティ付き（`kabusys.data.jquants_client`）

---

## 要件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS フィード）

※ 実行環境に合わせて pyproject.toml / requirements.txt を参照してください（本サンプルコードから想定される依存）。

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements/pyproject があればそちらを使用）

4. パッケージを開発インストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（優先順: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=...        （必須：J-Quants リフレッシュトークン）
     - OPENAI_API_KEY=...              （AI 呼び出し用）
     - KABU_API_PASSWORD=...           （kabu API を使う場合）
     - KABU_API_BASE_URL=...           （デフォルトは http://localhost:18080/kabusapi）
     - DUCKDB_PATH=data/kabusys.duckdb  （DuckDB ファイルパス）
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|... 

   .env のパースはシェル風（export も可）、引用符やコメントの取り扱いに対応しています。

---

## 使い方（クイックスタート）

以下は最低限の主要ユースケースの例です。DuckDB を用いる前提です。

1) DuckDB 接続を作る
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants トークンは環境変数または id_token 引数で渡す）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントスコア生成（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込銘柄数:", count_written)
```

4) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを用いる）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB 初期化（監査用 DuckDB を作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

6) AI 呼び出しのテスト時や CI では OpenAI 呼び出し部分をモックすることが推奨されています。
- 関数内部で API 呼び出しを行う箇所には差し替え用のポイントがあり、unittest.mock.patch で _call_openai_api 等を差し替えてテストできます。

---

## 環境変数（.env 例）

例（プロジェクトルートの .env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

説明:
- `.env.local` はローカル上書き用で自動的に .env より優先して読み込まれます。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 代表的な API / 関数一覧（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, id_token=None, run_quality_checks=True, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - preprocess_text(...)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(...)
  - factor_summary(...)

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理（.env 自動読み込みロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - news_collector.py        — RSS 収集・前処理
    - calendar_management.py   — マーケットカレンダー管理（営業日判定等）
    - quality.py               — データ品質チェック
    - stats.py                 — 基本統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログスキーマ初期化
    - etl.py                   — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン・IC・統計サマリー等
  - ai/、research/、data/ 以下にテスト差し替えポイントや docstring が豊富

---

## 注意事項 / トラブルシューティング

- OpenAI / J-Quants の API キーが未設定だと該当関数は ValueError を送出します。テスト時はモックで外部呼び出しを置き換えてください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探します）を基準として行われます。パッケージ配布後も動作するように __file__ を起点に探索します。
- DuckDB に対する executemany の空リストは古いバージョンでエラーになるため、コード内で空チェックが行われています。DuckDB のバージョン互換に注意してください。
- RSS 取得には SSRF 対策や最大受信サイズチェックが組み込まれています。外部 URL を利用する際は許可されたドメインを確認してください。
- audit のスキーマ初期化時は TimeZone を UTC に固定します（SET TimeZone='UTC' を実行）。

---

## 開発・貢献

- コードは docstring と内部コメントで設計意図や安全策が明確に記述されています。ユニットテストを書く際は外部 API 呼び出し箇所（OpenAI クライアント呼び出し、urllib、_urlopen 等）をモックしてください。
- 自動ロードされる環境変数を切り替える場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してテスト環境用の環境構築をおこなってください。

---

以上が KabuSys の README（日本語）です。追加で「実行例のスクリプト」や「.env.example の具体的なテンプレート」を作成したい場合は、その旨を教えてください。