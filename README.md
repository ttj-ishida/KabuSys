# KabuSys

日本株向けのデータプラットフォーム / 研究・自動売買基盤のライブラリ群です。  
このリポジトリは主に次を目的としています：J-Quants など外部データソースからの ETL、ニュースの収集・NLP スコアリング、研究用ファクター計算、および監査用テーブル等の DB 操作ユーティリティを提供します。

バージョン: 0.1.0

---

## 主要機能一覧

- データ取得・ETL（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得 / 保存（冪等）
  - ページネーション / レート制御 / トークン自動リフレッシュ / リトライ処理付き

- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合などの検出

- カレンダー管理
  - JPX マーケットカレンダーの更新・営業日判定・前後営業日の取得など

- ニュース収集（RSS）
  - RSS フィード取得、URL 正規化・SSRF 対策・前処理、raw_news への冪等保存補助

- ニュース NLP（LLM を用いたセンチメント）
  - 銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）でスコア化して ai_scores に保存するロジック（バッチ・リトライ・検証付き）

- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次でレジーム（bull / neutral / bear）判定

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化

- 監査ログ（トレーサビリティ）初期化
  - signal_events / order_requests / executions テーブル等の DDL とインデックスを冪等で作成するユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | None` を使用）
- system に Git、ネットワーク接続（API 利用時）があること

1. リポジトリをクローン（既にある場合は省略）
   ```bash
   git clone <このリポジトリ URL>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 依存パッケージをインストール
   - 最低限必要なパッケージ例:
     - duckdb
     - openai
     - defusedxml
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 開発時はパッケージを editable install する場合:
   ```bash
   pip install -e ".[dev]"  # setup に extras がある場合
   ```

4. 環境変数の設定
   - ルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（主要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必要に応じて）
     - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン（必要に応じて）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector が利用）
   - 任意:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると自動 .env 読み込みを無効化
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite ファイルパス（デフォルト: data/monitoring.db）
   - .env の例（.env.example を参考に作成してください）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（主要な API サンプル）

以下は簡単な Python スニペット例です。DuckDB 接続は `duckdb.connect(path)` で取得します。

- 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定しておくか、api_key に直接渡す
count = score_news(conn, target_date=date(2026, 3, 19))
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 19))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ディレクトリが無ければ自動作成
```

- 研究用関数例（モメンタム計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 19))
# records は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

注意点:
- LLM（OpenAI）を利用する関数は API キーが必要です。関数引数で `api_key` を渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- モジュールはルックアヘッドバイアスを避けるため、内部で `date.today()` 等を不用意に参照しない設計になっています（API 呼出しや計算は明示的な target_date を受け取る形）。

---

## 主要モジュール / ディレクトリ構成

（src 配下を基準にした抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（API トークンやパス等）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースをまとめて LLM に送り銘柄毎にスコアを生成
    - regime_detector.py — ETF MA とマクロニュースを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプラインと run_daily_etl 等
    - etl.py — ETL の公開インターフェース（ETLResult の再エクスポート）
    - news_collector.py — RSS 取得・前処理・保存のユーティリティ
    - calendar_management.py — 市場カレンダーの管理・営業日ロジック
    - quality.py — データ品質チェック群
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査用テーブル・インデックスの初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank
  - ai/、research/ は主に研究・解析・AI スコアリング向けのロジックを含みます。

その他:
- monitoring, strategy, execution といった名前は __init__ の __all__ に含まれますが、このスニペットでは実装詳細が省かれている可能性があります（プロジェクト全体の実装状況に従ってください）。

---

## 運用上の注意・設計に関する要点

- 自動 .env 読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 冪等性
  - J-Quants から取得したデータ保存やニュースの挿入は原則冪等（ON CONFLICT / INSERT ... DO UPDATE / INSERT ... ON CONFLICT DO NOTHING 等）に設計されています。

- フェイルセーフ
  - LLM API エラーや外部 API の一時エラーは、フェイルセーフの挙動（ゼロスコアやスキップ）を採っています。致命的な障害発生時はログに記録され、呼び出し元で適切にハンドリングしてください。

- Look-ahead bias 対策
  - ほとんどの処理は target_date を明示的に受け取り、内部で現在時刻を参照してループ内で誤って未来データを使用しないよう設計されています。バックテスト等で利用する際は ETL の取り扱いに注意してください。

---

## テスト / 開発ヒント

- OpenAI / ネットワークを伴う関数はテスト時にモック化することを想定しており、内部の API 呼出し関数（例: _call_openai_api 等）を patch して差し替え可能です。
- news_collector などはネットワーク・外部リソースに依存するため、ユニットテストでは fetch_rss の内部ネットワーク呼び出しをモックしてください。
- DuckDB はインメモリ（":memory:"）接続もサポートしているため、テスト用 DB を作成しやすくなっています。

---

問題や補足したい点があれば、どの機能の README を詳しくするか（例：ETL の詳細な実行例、schema DDL、.env.example のフルテンプレート等）を教えてください。必要に応じて追加の使用例や運用ガイドを作成します。