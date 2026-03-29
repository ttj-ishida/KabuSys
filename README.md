# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集・NLP、ファクター計算、マーケットレジーム判定、監査ログ（発注→約定トレーサビリティ）などのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムや研究（Research）環境向けに設計された Python パッケージです。主な役割は次の通りです。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL
- DuckDB を用いたデータ保存と品質チェック
- RSS ニュース収集と LLM によるニュースセンチメント評価（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの合成）
- ファクター計算（Momentum / Value / Volatility 等）と特徴量解析ツール
- 監査ログ（signal → order_request → executions）テーブル初期化・管理
- 設定は環境変数／.env ファイルで管理（自動読み込みあり）

設計方針として、バックテスト時のルックアヘッドバイアス防止、再現性、冪等性（idempotency）、ネットワークリトライやフェイルセーフを重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants からのデータ取得（株価、財務、カレンダー、上場銘柄情報）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - リトライ・レートリミット・認証トークン自動リフレッシュ実装
- data/pipeline.py
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL 実行（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果を ETLResult として返却
- data/quality.py
  - 欠損、重複、スパイク（急変）、日付整合性チェック
- data/news_collector.py
  - RSS 取得・正規化・前処理・raw_news への冪等保存（SSRF/サイズ/XML 攻撃対策あり）
- ai/news_nlp.py
  - OpenAI（gpt-4o-mini）で銘柄別ニュースセンチメントを評価し ai_scores に保存
  - バッチ化、リトライ、レスポンス検証を実装
- ai/regime_detector.py
  - ETF(1321) の 200 日 MA 乖離と LLM によるマクロセンチメントを重み合成して market_regime に保存
- research/*
  - ファクター計算（momentum, value, volatility）と特徴量探索（forward returns, IC, summary）
- data/audit.py
  - 監査テーブル（signal_events, order_requests, executions）DDL と初期化ヘルパー
- config.py
  - 環境変数/.env ロードと Settings クラス（アプリ設定一元管理）
  - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）から行われる。無効化可

---

## 必要条件 / 推奨環境

- Python 3.10 以上（PEP 604 の `X | Y` 型ヒントを使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

（環境によって他に logging, urllib 等の標準ライブラリで十分です）

requirements.txt の例（プロジェクトに応じて調整してください）:

```
duckdb>=0.7
openai>=1.0
defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーに配置

2. Python 仮想環境を作成して有効化（例: venv）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .\.venv\Scripts\activate
     ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   または開発中であれば
   ```
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を置く（.env.example を参考に作成）
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD（必須）: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN（必須）: Slack Bot トークン
     - SLACK_CHANNEL_ID（必須）
     - OPENAI_API_KEY（AI 機能を使う場合、環境変数または各関数の api_key 引数で指定）
   - 任意 / デフォルト:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   自動 .env 読み込みを無効にする場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（簡単なコード例）

以下は代表的な利用例です。実行はプロジェクトルートで行ってください。

- DuckDB 接続と日次 ETL 実行

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値: 書き込んだ銘柄数
print("wrote", written)
```

- 市場レジーム判定（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査専用 DB を分けて作成する例）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルを参照・更新できます
```

- 研究用ファクター計算（例: momentum）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

注意事項:
- AI 関連関数は OpenAI の API を呼び出します。API キーと利用コストに注意してください。
- ETL 関数は J-Quants API を利用します。J-Quants の利用規約・レート制限に従ってください。

---

## よく使うヘルパー・API

- kabusys.config.settings — 環境設定（.env / 環境変数経由）
- kabusys.data.jquants_client — J-Quants に対する fetch_* / save_* 関数
- kabusys.data.pipeline.run_daily_etl — 日次 ETL ワンストップ実行
- kabusys.data.quality.run_all_checks — ETL 後の品質チェック
- kabusys.data.news_collector.fetch_rss — RSS フィード取得ユーティリティ
- kabusys.ai.news_nlp.score_news — ニュース NLP スコア生成・保存
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定・保存
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査テーブル初期化

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント / DuckDB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult の再エクスポート
    - quality.py                     — データ品質チェック
    - news_collector.py              — RSS ニュース収集 / 前処理
    - calendar_management.py         — 市場カレンダー管理（is_trading_day 等）
    - stats.py                       — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Value/Volatility 等
    - feature_exploration.py         — forward returns / IC / summary
  - (その他)                          — strategy / execution / monitoring のための名前空間は __all__ に定義済み

---

## 開発上の注意点 / 設計上のポイント

- ルックアヘッドバイアス対策:
  - 日付関連処理で datetime.today()/date.today() を不用意に参照しない設計（関数引数で日付を渡す）。
  - DB クエリでは target_date 未満や排他条件を明示して未来データ参照を防止。
- 冪等性:
  - ETL 保存処理は ON CONFLICT を利用した冪等保存を行います。
  - ニュース記事 ID は正規化 URL の SHA-256 先頭で生成し重複挿入を防止。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）失敗時はリトライやスコアのフォールバックを行い、例外で処理全体が止まらないようにしています。
- セキュリティ:
  - news_collector は SSRF・XML Bomb・過大レスポンス対策を備えています。
- テスト容易性:
  - OpenAI 呼び出しやネットワーク I/O はモック差し替え可能な設計（内部 _call_openai_api 等をモック可能）。

---

## トラブルシューティング

- .env が読み込まれない / テストで読み込みを抑制したい:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI / J-Quants の認証エラー:
  - 環境変数（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）が正しく設定されているか確認してください。
  - jquants_client は 401 を受けた場合トークンを自動リフレッシュしますが、refresh トークンが無効だと失敗します。
- DuckDB 操作でエラーが出る:
  - DuckDB のバージョン差異により一部の SQL バインド挙動が異なる場合があります。必要に応じて duckdb のバージョンを合わせてください。

---

README に書かれている挙動、API 名称・引数はソースコードに依存します。まずはローカルで少量データを用いて ETL→品質チェック→ニューススコア→レジーム判定 を順に試し、期待する DB スキーマや出力を確認してください。必要であれば README をプロジェクト実態に合わせて更新してください。