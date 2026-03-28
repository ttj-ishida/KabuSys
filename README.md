# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ（軽量版）

このリポジトリは、J-Quants / JPX / RSS などからデータを取得して DuckDB に保存し、
AI（OpenAI）を使ったニュースセンチメント評価や市場レジーム判定、研究用ファクター計算、
監査ログ（発注〜約定トレーサビリティ）などを提供する Python パッケージです。

主な用途:
- 日次 ETL（株価・財務・市場カレンダー）の差分取得と品質チェック
- ニュースの収集と銘柄別センチメントスコア算出（LLM）
- ETF ベースの市場レジーム判定（MA + マクロニュース）
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（signal → order_request → execution）テーブルの初期化

---

## 機能一覧

- 環境変数管理
  - .env / .env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須変数未設定時は Settings で例外を投げる

- データ ETL（kabusys.data.pipeline）
  - J-Quants API から株価（daily_quotes）・財務（statements）・市場カレンダーを差分取得
  - DuckDB へ冪等保存（ON CONFLICT / INSERT ... DO UPDATE など）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得・前処理・SSRF 対策・トラッキング除去・raw_news 保存

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）による銘柄別センチメント評価（JSON Mode）
  - バッチ処理・リトライ・レスポンス検証・スコアクリップ

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成
  - 日次で market_regime テーブルへ冪等書き込み

- 研究用モジュール（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算・IC（Spearman）・統計サマリー
  - z-score 正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの DDL とインデックス
  - 監査テーブルの初期化ユーティリティ（init_audit_schema / init_audit_db）

- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制御・リトライ・401 時のトークン自動リフレッシュ
  - ページネーション対応のデータ取得・DuckDB への保存関数

---

## 前提・必要パッケージ

（プロジェクトに合わせて適宜バージョン固定してください）

- Python 3.9+
- duckdb
- openai
- defusedxml
- （標準ライブラリのみで実装された箇所も多いですが、上記は主要外部依存）

インストール例（仮のパッケージ名や extras があれば適宜調整）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発環境ならパッケージを editable インストール
pip install -e .
```

---

## 環境変数（主なもの）

.env もしくは OS 環境変数で設定します。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます。
自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主なキー:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出し時に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（本パッケージ内の他モジュールが使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンし仮想環境を作成
2. 依存パッケージをインストール
3. プロジェクトルートに `.env` を作成（上記参照）
4. DuckDB ファイルの親ディレクトリを作成（必要なら）
5. 監査 DB 初期化（任意。詳しくは下記）

例:
```bash
git clone <repo_url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# もしくは pip install -e .
# .env を作成
mkdir -p data
```

---

## 使い方（代表的な例）

以下は Python インタラクティブやスクリプトでの利用例です。

- Settings（環境変数参照）
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path object
```

- DuckDB 接続を作成して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースセンチメントスコア算出（AI）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を直接渡すか、OPENAI_API_KEY を環境変数で設定しておく
n = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"scored {n} codes")
```

- 市場レジームのスコア算出
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
# conn は DuckDB 接続
score_regime(conn, target_date=date(2026,3,20))
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

- 監査ログ DB の初期化（監査テーブルを作る）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を使うか別DBを指定
audit_conn = init_audit_db(settings.duckdb_path)
```

注意点:
- OpenAI 呼び出しはレート・コストに注意してください。レスポンス検証やリトライが組み込まれていますが、API キーは必ず保護してください。
- J-Quants API はレート制限があります。jquants_client モジュールは内部でレート制御を行います。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化、version 等
- config.py — 環境変数 / Settings（.env 自動ロード機能含む）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（銘柄別センチメント）
  - regime_detector.py — ETF + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集・前処理
  - calendar_management.py — 市場カレンダー操作・更新ジョブ
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック
  - audit.py — 監査ログ DDL / 初期化
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー等
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

（上記は本リポジトリで実装されている主要モジュールです。細かな補助関数や定数は各ファイル内に記載されています。）

---

## 運用上の注意

- 環境: settings.env により開発 / paper_trading / live を区別できます。is_live / is_paper / is_dev プロパティで振る舞いを分岐できます。
- Look-ahead バイアス対策: 多くの関数は date 引数を明示的に受け取り、内部で date.today() を参照しない設計になっています。バックテスト時は必ず過去時点の DB スナップショットまたは適切な target_date を渡してください。
- 冪等性: ETL / 保存関数は冪等動作を意識して実装されています（ON CONFLICT 句など）。
- テスト: 各種 API 呼び出し（OpenAI / J-Quants / HTTP）は差し替え可能に実装されており、ユニットテストではモックを使えるようになっています。

---

## 参考（トラブルシューティング）

- .env が読み込まれない:
  - 自動ロードはプロジェクトルートの検出に .git または pyproject.toml を利用します。パッケージをインストールした環境ではプロジェクトルート探索が期待通り動作しないことがあるため、その場合は明示的に環境変数を export してください。
  - 自動ロードを完全に無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。

- J-Quants の認証エラー:
  - jquants_client.get_id_token は settings.jquants_refresh_token を使用します。refresh token の有効性を確認してください。401 発生時は自動で 1 回リフレッシュを試みます。

- OpenAI の呼び出し失敗:
  - ネットワーク or レート制限に対しては内部でリトライとバックオフ処理があります。API キーがない場合は ValueError が発生します。

---

この README はプロジェクトの主要ポイントをまとめたものです。各モジュールの詳細な仕様・パラメータや DDL（テーブルスキーマ）、運用手順についてはソースコード内の docstring やコメントを参照してください。必要であれば追加のドキュメント（運用手順・設計資料）を作成します。