# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレース）などを提供します。

---

## 主な特徴（機能一覧）

- 確実で冪等な ETL パイプライン
  - 差分取得 / バックフィル / 品質チェック（欠損・スパイク・重複・日付不整合）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- ニュース収集 & NLP
  - RSS 収集（SSRF対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores）生成
- 市場レジーム判定
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman） / 統計サマリー、Zスコア正規化
- マーケットカレンダー管理
  - JPX カレンダーの差分取得と営業日判定ユーティリティ（next/prev/is_trading_day 等）
- 監査ログ（audit）
  - signal → order_request → executions のトレーサビリティ用テーブル定義・初期化（DuckDB）
- データ品質チェックモジュール（quality）
  - ETL 後の問題検出を一括収集

---

## 必要条件（主な依存ライブラリ）

- Python 3.9+
- duckdb
- openai
- defusedxml
- （標準ライブラリのみで動く部分も多いですが、上記は主要機能のため必要です）

インストールはプロジェクトの requirements.txt を用意している想定で次のように行います（requirements.txt がある場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 直接パッケージを開発モードでインストールする場合
pip install -e .
```

requirements.txt がない時は最低限次を入れてください:

```bash
pip install duckdb openai defusedxml
```

---

## 環境変数・設定

パッケージ起動時にルートプロジェクト（.git または pyproject.toml を基準）に配置された `.env` と `.env.local` を自動読み込みします。読み込み順は OS 環境変数 > .env.local > .env です。自動読み込みを無効にするには環境変数を設定します:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

重要な環境変数（本パッケージで参照される代表例）:

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 関連関数で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

README に含める簡易 .env 例:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_pass
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定は `kabusys.config.settings` 経由で参照できます。必須値が欠けていると ValueError が発生します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. ルートに `.env`（または `.env.local`）を配置して必要な環境変数を設定
5. DuckDB ファイルの格納先ディレクトリ（例: data/）を作成（自動作成される箇所もありますが事前準備推奨）

---

## 使い方（主要ユースケース例）

以下は最小限の Python 例です。スクリプトやジョブから呼び出して利用します。

- 日次 ETL 実行（run_daily_etl）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai_scores へ書き込み）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境で参照
print("written:", n_written)
```

- 市場レジーム判定（market_regime テーブルへ書き込み）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ（audit）スキーマ初期化（専用 DB 作成）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
# テーブルが作成され、UTC タイムゾーン設定が行われます
```

- マーケットカレンダー機能例

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

- リサーチ関数（例: モメンタム計算）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# レコードは dict のリストで返却されます
```

注意:
- AI 関連の関数は OpenAI API を呼びます。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フェイルセーフ処理がありますが、クォータや料金に注意してください。
- DuckDB の SQL スキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar など）は、プロジェクトの初期化スクリプトやマイグレーションで作成する想定です（このリポジトリに schema 初期化用の関数があるならそれを用いてください）。

---

## ディレクトリ構成（主要ファイル）

（root 以下に `src/kabusys` 配下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント生成（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py    — 市場レジーム判定（MA200 + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save / auth）
    - pipeline.py           — ETL パイプライン（run_daily_etl 他）
    - etl.py                — ETLResult の再エクスポート
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - news_collector.py     — RSS 収集・raw_news への保存
    - quality.py            — データ品質チェック
    - stats.py              — 共通統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログ（トレース可能なテーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py    — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py— 将来リターン, IC, 統計サマリー 等
  - research/（上記に続く…）
  - （将来的に strategy, execution, monitoring サブパッケージを公開する設計）

各モジュールはドキュメント文字列やログ出力により設計方針（ルックアヘッドバイアス回避、フェイルセーフ、冪等性等）を明記しています。

---

## 開発・テスト上の注意点

- .env の自動読み込みはプロジェクトルートを .git / pyproject.toml で探索して行われます。テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI API 呼び出しはテストでモック可能なように内部呼び出し関数を分離しています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB のバージョン差異に起因する挙動（executemany の空リスト等）に配慮した実装がなされています。テスト時はローカルの DuckDB 接続（:memory: も可）を使用すると早く検証できます。

---

## ライセンス / 貢献

本 README はコードベースの説明用です。実際のライセンスや貢献ポリシーはリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

必要であれば、README に含めるコマンドラインツール例（cron ジョブ、systemd ユニット、Dockerfile、docker-compose）や初期 DB スキーマ作成 SQL の追加、requirements.txt の推奨内容なども作成します。どの情報を追記しましょうか？