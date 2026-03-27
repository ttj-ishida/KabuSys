# KabuSys

KabuSys は日本株のデータ収集・品質チェック・ファクター計算・ニュース NLP・市場レジーム判定・監査ログ（トレーサビリティ）を目的としたライブラリ群です。ETL パイプラインや研究（Research）用途、戦略の監査・ログ基盤までを一貫して提供します。

---

## 主要な特徴

- データ取得（J-Quants API 経由）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー等の差分取得・保存（ページネーション・レート制御・リトライ対応）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）、前処理、記事の銘柄紐付け
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント算出）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 監査ログ（signal → order_request → executions）用の DuckDB スキーマ／初期化ユーティリティ
- 研究用途のファクター計算・特徴量探索（モメンタム・ボラティリティ・バリュー・IC 等）
- DuckDB を中心とした軽量な永続化

---

## 要件

- Python 3.9+
- 主な依存ライブラリ（抜粋）
  - duckdb
  - openai (OpenAI の新しい SDK を想定している実装)
  - defusedxml
- （ネットワークアクセスが必要）
- J-Quants API のリフレッシュトークン・OpenAI API キー等の環境変数

※ 実際のインストール時はプロジェクトの pyproject.toml / requirements.txt を参照してください（本 README はコードベースからの説明です）。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトし、パッケージを編集可能モードでインストール（開発環境例）:
   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 必要な依存をインストール（例）:
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます）
   - プロジェクトは .git または pyproject.toml を基準にルートを検出し、`.env` / `.env.local` を自動で読み込みします。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB データベースの準備（デフォルトは `data/kabusys.duckdb`）:
   - デフォルトの DB パスは環境変数 `DUCKDB_PATH` で上書きできます。
   - 監査ログ専用 DB を初期化する場合は後述のスニペットを参照してください。

---

## 環境変数（主なもの）

以下は本プロジェクト内で参照される代表的な環境変数です。`.env.example` を作成して管理してください。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出し用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的なコードスニペット）

まず DuckDB 接続と settings の利用例:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する（株価・財務・カレンダー取得＋品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースの NLP スコアを算出し ai_scores テーブルへ書き込む

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written_count = score_news(conn, target_date=date(2026, 3, 20))
print("written:", written_count)
```

3) 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用の DuckDB を初期化（新規 DB を作成して監査スキーマを作る）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または既存接続にスキーマを追加
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

5) 監査テーブル（signal_events / order_requests / executions）を初期化する
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

ログ・レベルは環境変数 `LOG_LEVEL` で制御します。

注意:
- OpenAI を使う機能（news_nlp / regime_detector）は `OPENAI_API_KEY` を必要とします。API 呼び出しにはコストとレート制限が伴います。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在）から行われます。テスト時などは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
  - パッケージ基点。version 等を管理。
- config.py
  - 環境変数の読み込み・Settings クラス。`.env` / `.env.local` の自動読み込みロジックを含む。
- ai/
  - news_nlp.py: ニュースを LLM で評価して ai_scores へ書き込む。
  - regime_detector.py: ETF 1321 の MA とマクロニュースを合成して market_regime に書き込む。
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得・保存ロジック、リトライ・レート制御）。
  - pipeline.py: ETL パイプラインと個別 ETL ジョブ（run_daily_etl 等）。
  - quality.py: データ品質チェック群（欠損・スパイク・重複・日付不整合）。
  - news_collector.py: RSS 取得・前処理・raw_news への保存ロジック（SSRF 対策・サイズ制限等）。
  - calendar_management.py: 市場カレンダー、営業日判定・次営業日/前営業日取得・カレンダー更新ジョブ。
  - stats.py: zscore_normalize 等の統計ユーティリティ（research と共有）。
  - audit.py: 監査ログ（signal / order_request / executions）の DDL / 初期化ユーティリティ。
  - etl.py: ETL の公開インターフェース（ETLResult の再エクスポート）。
- research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算。
  - feature_exploration.py: 将来リターン・IC・統計サマリ・ランク付け等。
  - __init__.py: 研究用ユーティリティの再エクスポート。

（ファイルごとに docstring に詳しい設計意図・処理フローがあります）

---

## 開発メモ / 注意点

- ルックアヘッドバイアス対策: 多くの処理は date 引数や DB の過去データのみを参照し、datetime.today() を無条件に使わない設計になっています。バックテスト時は必ず過去日に対して呼び出してください。
- OpenAI 呼び出しはリトライ・フォールバック（失敗時は 0.0 などの中立値）を持ちますが、コストとレイテンシに注意してください。
- J-Quants API 呼び出しは rate limit（120 req/min）に合わせた RateLimiter を実装しています。大量取得時は時間がかかる点に注意。
- DuckDB のバージョンによる挙動差異（executemany の空リストなど）に配慮した実装になっています。
- news_collector は SSRF 対策・受信サイズ制限・gzip 対応・トラッキングパラメータ除去等の安全対策を実装しています。

---

## トラブルシューティング

- 環境変数が読み込まれない／Settings がエラーを出す場合:
  - プロジェクトルートに `.env` を置いているか確認（.git または pyproject.toml の存在が自動ロードの条件）。
  - 自動読み込みを無効化して手動で環境変数をセットして動作確認してください。
- OpenAI/ J-Quants の認証エラー:
  - トークン・キーが正しいか、期限切れでないか確認してください。jquants は refresh token から id_token を取得する実装です。
- DuckDB にテーブルがない場合:
  - ETL の最初にスキーマ初期化処理（プロジェクト側で用意している schema init がある場合）を行ってください。監査用スキーマは `init_audit_schema` を呼ぶことで作成できます。

---

この README はコード内の docstring を元に要点をまとめた概要です。各モジュール・関数の詳細はソースの docstring を参照してください。必要であればセットアップスクリプトや詳細な運用手順（cron/jupyter/CI 連携、Slack 通知フロー等）も作成できます。