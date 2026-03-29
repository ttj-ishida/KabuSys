# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・LLM によるセンチメント評価、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、運用に必要なユーティリティを含みます。

## 主な特徴
- J-Quants API からの日次株価（OHLCV）・財務データ・マーケットカレンダーの差分取得（ページネーション・レート制限・自動トークンリフレッシュ対応）
- DuckDB ベースの ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策・サイズ制限・トラッキング除去）
- OpenAI（gpt-4o-mini）によるニュースセンチメント / マクロセンチメント評価（JSON Mode を利用）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）および特徴量探索ツール（IC, forward returns 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）、DB 初期化ユーティリティ

---

## 必要条件（概要）
- Python 3.9+（型注釈に新しい機能が使われているため推奨）
- ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

（プロジェクトに requirements.txt があればそれを使ってください。ない場合は上記パッケージをインストールしてください。）

例:
pip install duckdb openai defusedxml

---

## 環境変数
kabusys は .env / .env.local または OS 環境変数から設定を読み込みます（プロジェクトルートに .git または pyproject.toml があると自動読み込みされます）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（注文連携等で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知連携）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意／デフォルトあり:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime は引数で上書き可能）

.env.example を用意している場合はそれを参考に .env を作成してください。

---

## セットアップ手順（推奨）
1. リポジトリをクローン / 展開
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install -r requirements.txt  （ある場合）
   - または個別に: pip install duckdb openai defusedxml
4. .env を作成して必須環境変数を設定
5. DuckDB 用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 初期化（監査DBなど）
監査ログ専用 DB を初期化するユーティリティがあります。例:

from pathlib import Path
import duckdb
from kabusys.data.audit import init_audit_db
conn = init_audit_db(Path("data/audit.duckdb"))

または既存の接続に監査スキーマを追加する:
from kabusys.data.audit import init_audit_schema
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)

注: init_audit_db / init_audit_schema はタイムゾーンを UTC に固定します。

---

## 使い方（代表的な API）
以下は主要な処理を呼び出す簡易例です。各関数は DuckDB 接続を受け取ります。

共通準備:
from datetime import date
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL の実行（prices / financials / calendar / 品質チェック）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())

2) ニュースセンチメントのスコアリング（OpenAI キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）
from kabusys.ai.news_nlp import score_news
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("書き込んだ銘柄数:", n_written)

3) マーケットレジームのスコアリング（ETF 1321 の MA200 + マクロセンチメント）
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20), api_key=None)

4) RSS フィードの取得（ニュース収集の一部）
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])

5) ファクター計算（例: momentum）
from kabusys.research.factor_research import calc_momentum
momentum = calc_momentum(conn, target_date=date(2026,3,20))
print(len(momentum), "銘柄の計算結果")

6) データ品質チェック（ETL 後に自動実行されるが個別で呼ぶことも可能）
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i.check_name, i.severity, i.detail)

---

## 自動環境変数読み込みの挙動
- パッケージ読み込み時に .env / .env.local を自動でプロジェクトルート（.git または pyproject.toml を基準）から読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースは shell ライクな書式（export を許可、クォート・コメント処理あり）に対応しています。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ定義、version。

- src/kabusys/config.py
  - 環境変数管理（自動 .env ロード、Settings クラス）。

- src/kabusys/ai/
  - news_nlp.py — ニュースを銘柄ごとに集約して OpenAI に送り、ai_scores に書き込む処理。
  - regime_detector.py — ETF(1321) MA200 乖離とマクロニュースの LLM 評価を合成して market_regime に書き込む。

- src/kabusys/data/
  - pipeline.py — ETL パイプライン（run_daily_etl 等）。
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB へ保存）。
  - news_collector.py — RSS 取得・前処理・raw_news 保存ロジック。
  - calendar_management.py — 市場カレンダーの管理・営業日判定ユーティリティ。
  - stats.py — z-score 正規化などの統計ユーティリティ。
  - quality.py — 品質チェック（欠損・重複・スパイク・日付不整合）。
  - audit.py — 監査ログ（signal/order_request/execution）DDL と初期化ユーティリティ。
  - etl.py — ETLResult の再エクスポート。
  - その他 jquants_client の fetch/save 関数群。

- src/kabusys/research/
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算。
  - feature_exploration.py — forward returns, IC, ranking, summary。
  - __init__.py で研究用ユーティリティを公開。

- （注） __all__ に strategy / execution / monitoring が含まれますが、今回提示されたコードスニペットにはそれらの実装が含まれていません。注文実行や戦略管理・監視の実装は別モジュール／別リポジトリで提供される想定です。

---

## 運用上の注意
- Look-ahead bias を防ぐ設計が随所に入っており、各関数は内部で datetime.today() を直接参照しない等の配慮があります。バックテスト目的で利用する場合は、取得データの「いつ知り得たか（fetched_at）」を考慮してください。
- OpenAI / J-Quants の API 呼び出しは外部サービス依存のため、API キー・レートリミット・コストに注意してください。エラー時は多くの箇所でフェイルセーフ（スコア 0 として継続）する実装になっていますが、要件に応じて例外伝播やリトライ動作を調整してください。
- DuckDB を使用するため、同時書き込みや運用上のロックに関する設計は実際の運用環境に合わせて検討してください。

---

README はここまでです。必要であれば次の内容を追加できます:
- requirements.txt の具体例
- .env.example のテンプレート
- よくあるトラブルシューティング（OpenAI レスポンスパース失敗、J-Quants 401 対応など）
- strategy / execution 層のサンプルワークフロー

どれを追加しますか？