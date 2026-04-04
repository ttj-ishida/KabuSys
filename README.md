# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・AI によるニュースセンチメント、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを含みます。

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務データ、JPX マーケットカレンダーを差分取得して DuckDB に保存（冪等処理・レート制御・自動トークンリフレッシュ）
  - ETL の品質チェック（欠損・スパイク・重複・日付不整合検出）
- ニュース処理
  - RSS からニュースを収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - ニュースと銘柄の紐付け、raw_news 保存
- AI（OpenAI）連携
  - ニュースに対する銘柄別センチメント算出（gpt-4o-mini を想定）
  - マクロニュースと ETF（1321）の 200 日移動平均乖離を組み合わせて市場レジーム判定（bull / neutral / bear）
  - API 呼び出しは冗長性考慮（リトライ・バックオフ・レスポンス検証）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z スコア正規化
- 監査（audit）
  - シグナル → 発注 → 約定までをトレースする監査テーブル定義・初期化ユーティリティ（DuckDB）
- 設定管理
  - .env ファイルまたは OS 環境変数から設定を自動ロード（プロジェクトルート検出・.env/.env.local 優先順序）

---

## 前提条件

- Python 3.10 以上（3.11 推奨）
- 必要なパッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml

requirements.txt を用意している場合は次のようにインストールしてください:

```bash
python -m pip install -r requirements.txt
```

もしくは開発インストール:

```bash
python -m pip install -e .
```

（プロジェクトルートに pyproject.toml / setup.cfg 等がある前提です）

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成し有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   python -m pip install duckdb openai defusedxml
   ```
4. 環境変数（または .env ファイル）を用意
   - プロジェクトは起動時に自動でプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探し、`.env` → `.env.local` の順で読み込みます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必要な環境変数（主なもの）
   - J-Quants / データ ETL:
     - JQUANTS_REFRESH_TOKEN=xxxxxxxx
   - OpenAI（AI モジュールを使用する場合）:
     - OPENAI_API_KEY=sk-...
   - kabu ステーション（実行系 / 発注）:
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # デフォルト
   - LINE 通知（任意）:
     - LINE_CHANNEL_ACCESS_TOKEN=
     - LINE_USER_ID=
   - DB / パス等:
     - DUCKDB_PATH=data/kabusys.duckdb  # デフォルト
     - SQLITE_PATH=data/monitoring.db
   - 監視・監督関連:
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0
   - システム設定:
     - KABUSYS_ENV=development|paper_trading|live  # デフォルト development
     - LOG_LEVEL=INFO|DEBUG|...

   （プロジェクト配布時は .env.example を参考に .env を作成してください）

---

## 簡単な使い方（コード例）

以下は最小限の利用例です。全て DuckDB 接続を渡して呼び出します。Look-ahead バイアスを防ぐため、関数は target_date を明示して呼ぶことが推奨されています。

- ETL（日次パイプライン）を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を用いるのが推奨
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースに対して銘柄別 AI スコアを算出（score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY 環境変数を設定している場合、api_key 引数は省略可能
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 の MA + マクロ記事の LLM スコア合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB を初期化する

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を用いて監査テーブルにアクセス可能
```

- 設定オブジェクト参照（環境変数のラッパー）

```python
from kabusys.config import settings

print(settings.duckdb_path)          # Path オブジェクト
print(settings.jquants_refresh_token)  # 未設定なら例外
```

注意：
- OpenAI を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY の設定が必須です（関数へ api_key を渡すことも可能）。
- J-Quants API を使う ETL は JQUANTS_REFRESH_TOKEN が必須です。

---

## ディレクトリ構成（主要ファイル説明）

プロジェクトは src/kabusys 配下のモジュール群で構成されています。主要ファイル：

- src/kabusys/__init__.py
  - パッケージのバージョンと公開モジュール定義
- src/kabusys/config.py
  - 環境変数の自動読み込み・設定ラッパー（Settings クラス）
- src/kabusys/data/
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - pipeline.py: ETL パイプライン（run_daily_etl など）
  - etl.py: ETL 結果型の再エクスポート（ETLResult）
  - jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py: RSS 取得・前処理・raw_news 保存ロジック
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py: 共通統計ユーティリティ（zscore_normalize など）
  - audit.py: 監査ログテーブル定義・初期化ユーティリティ
- src/kabusys/ai/
  - news_nlp.py: ニュースをまとめて LLM に投げる処理（銘柄別スコア算出）
  - regime_detector.py: ETF MA とマクロ記事 LLM を組み合わせた市場レジーム判定
- src/kabusys/research/
  - factor_research.py: Momentum / Volatility / Value ファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー等
  - __init__.py: 研究用ユーティリティのエクスポート

（上記以外に strategy / execution / monitoring 等のモジュールがパッケージルートに含まれる想定）

---

## 実運用上の注意

- ルックアヘッドバイアス防止
  - AI / ETL / リサーチ関数群は内部で date.today() を参照しない設計です。ターゲット日を明示して呼び出してください。
- 冪等性
  - J-Quants から保存する関数は ON CONFLICT DO UPDATE 等で冪等に保存するように実装されています。
- API レート制御 / リトライ
  - J-Quants クライアントは固定間隔のスロットリング（120 req/min）と再試行ロジックを搭載しています。
  - OpenAI 呼び出しは JSON の検証・リトライとフォールバック（失敗時は 0.0 等）を行います。
- セキュリティ
  - news_collector は SSRF 対策（リダイレクト検査・プライベートアドレスブロック）を実装しています。
  - .env などに秘密情報を保存する場合はファイルのアクセス権に注意してください。

---

## 貢献 / 開発

- 新しい ETL 対応や API の追加、研究用関数の追加は modules 以下に機能別ファイルを追加してください。
- テストを書く際は環境変数自動ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。
- OpenAI / ネットワーク呼び出しを含む箇所はモック可能なように設計されています（内部の _call_openai_api 等を patch）。

---

この README はコードベースの要点をまとめたものです。詳細は各モジュールの docstring を参照してください。質問や追加のドキュメント化が必要であればお知らせください。