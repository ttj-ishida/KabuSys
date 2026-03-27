# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
J-Quants / kabuステーション / OpenAI を組み合わせ、データ取得（ETL）・品質チェック・特徴量算出・ニュースNLP・市場レジーム判定・監査ログなどを提供します。

主な対象
- 日次の株価・財務データ ETL（J-Quants）
- ニュース収集と LLM を用いた銘柄別センチメント算出
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- 研究用ファクター計算・特徴量探索（バックテスト前処理向け）
- 発注・約定の監査ログスキーマ（DuckDB ベース）

---

## 機能一覧

- 環境設定管理（.env 自動読み込み／保護）
- J-Quants API クライアント
  - 株価（日次 OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 日次 ETL（カレンダー→株価→財務）＋品質チェック
  - 差分更新 / バックフィル対応
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集
  - RSS 取得（SSRF 対策・gzip 制限・トラッキング除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI を利用）
  - 銘柄ごとのセンチメント算出（gpt-4o-mini の JSON モード）
  - バッチ・トリム・リトライ制御（部分失敗に耐える設計）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離とマクロニュース LLM スコアの合成
  - 結果を market_regime テーブルへ冪等書き込み
- 研究（research）モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマンランク）や統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマ定義と初期化
  - 監査DB初期化ユーティリティ（DuckDB）

---

## 必要条件

- Python 3.10+
- ランタイム依存（最低限）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS フィード）

※実行環境に合わせて追加のライブラリやコマンドが必要になる場合があります。

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開

2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   # または開発用に editable install
   pip install -e .
   ```

4. 環境変数 / .env を準備  
   プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（ただしテスト等で無効化可能）。
   必要な主要環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（LLM を使う場合必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注等で使用）
   - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知に使う Slack 設定
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

   .env の自動読み込みを無効化する場合:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## データベース初期化（監査ログ例）

監査ログ用に DuckDB を初期化するサンプル:

```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn は duckdb.DuckDBPyConnection
```

init_audit_db は parent ディレクトリを自動作成し、UTC タイムゾーン設定を行った上でテーブルを作成します。

---

## 使い方（代表的な API）

以下は主要な操作の簡単な例です。実行前に .env 等で必要な環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

- 日次 ETL 実行（prices / financials / calendar の差分取得 + 品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄別スコア算出:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA200 + マクロニュース LLM）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究（ファクター計算）例:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- 環境設定参照:

```python
from kabusys.config import settings
print(settings.duckdb_path, settings.env, settings.is_live)
```

---

## 注意点 / 設計上のポリシー

- ルックアヘッドバイアス防止:
  - モジュールの多くは date 引数を受け取り、内部で datetime.today() を参照しない設計です（バックテストに適した設計）。
- 冪等性:
  - J-Quants 保存処理やニュース保存は冪等（ON CONFLICT など）を意識しています。
- フェイルセーフ:
  - LLM や外部 API のエラーは原則スコアに 0.0 を使ったり処理をスキップして継続する設計（部分失敗耐性）。
- セキュリティ:
  - ニュース収集では SSRF 防止、XML パースに defusedxml を使用、レスポンスサイズ制限などの対策を実装。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定の管理、自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM センチメント算出、batch・retry・検証ロジック
    - regime_detector.py — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py — J-Quants API クライアント + 保存処理
    - news_collector.py — RSS 収集・前処理・保存（SSRF 対策等）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログスキーマ定義・初期化
    - etl.py — ETL 用の公開インターフェース再エクスポート
    - pipeline.py (上記)
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリューの計算
    - feature_exploration.py — 将来リターン, IC, 統計サマリー 等
  - ai、data、research 以外にも strategy / execution / monitoring 等がパッケージ公開の対象（将来的な拡張を想定）

---

## トラブルシューティング

- .env が読み込まれない場合:
  - プロジェクトルート判定は __file__ の親ディレクトリを辿って `.git` または `pyproject.toml` を探します。テスト環境やパッケージ化後は自動検出されない場合があります。その場合は明示的に環境変数をエクスポートするか `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動ロードを無効にしてください。
- OpenAI / J-Quants の認証エラー:
  - 環境変数 OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN を確認してください。J-Quants クライアントはリフレッシュトークンから id_token を取得する実装です。
- DuckDB 関連:
  - executemany に空リストを渡すと問題になる箇所があるため、呼び出し前に空チェックを行っています。DB パスや権限を確認してください。

---

## ライセンス / コントリビューション

この README はコードベースに基づく概要ドキュメントです。実際のライセンス・貢献ガイドはリポジトリの root にある LICENSE / CONTRIBUTING 等のファイルを参照してください。

---

README の内容をプロジェクト実態（pyproject.toml / requirements.txt / LICENSE 等）に合わせて調整することを推奨します。必要であれば実行例の追加や CI / デプロイ手順のテンプレートも作成します。