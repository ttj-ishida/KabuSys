# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリです。  
ETL、データ品質チェック、ニュース収集・NLP、ファクター算出、監査ログ（オーディット）、および市場レジーム判定を含む一連の機能を提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 簡単な使い方（例）
- 環境変数（.env）と自動ロード挙動
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からのデータ取得（株価日足、財務データ、上場・カレンダー情報）
- DuckDB を用いたローカルデータ保存と ETL（差分更新・バックフィル）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング削除）
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント解析（銘柄別 / マクロ）
- 市場レジーム判定（ETF + マクロセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 等）
- 発注フローの監査ログ（監査テーブルの初期化・DB 操作）

設計上の方針として、Look-ahead bias を避けるため「現在時刻を直接参照しない」実装や、API 呼び出しに対する堅牢なリトライ・フェイルセーフを重視しています。

---

## 主な機能一覧

- 環境設定読み込み（.env / .env.local、自動ロード）
- J-Quants クライアント（fetch / save / 認証・トークン更新・レート制御）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（missing_data / spike / duplicates / date_consistency）
- 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
- ニュース収集（RSS パーシング、前処理、SSRF 対策）
- ニュース NLP（銘柄別スコア: score_news）
- 市場レジーム判定（score_regime：ETF ma200 とマクロセンチメントを合成）
- 研究用モジュール（ファクター計算: momentum/value/volatility、forward returns、IC、zscore 正規化）
- 監査ログ（init_audit_db / init_audit_schema）

---

## セットアップ手順

前提:
- Python 3.9+（型アノテーションや一部表現に合わせた推奨バージョン）
- Git（プロジェクトルート検出に .git を使用）

依存パッケージ（主なもの）:
- duckdb
- openai
- defusedxml

インストール例（仮にパッケージ化されている/ローカル開発）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
   開発時は editable インストール:
   - pip install -e .

3. 環境変数の準備
   プロジェクトルートに `.env`（および `.env.local`：ローカル上書き用）を置くと自動で読み込まれます（後述）。

---

## 環境変数（主なもの）

必須（動作に必要）:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（get_id_token に利用）
- KABU_API_PASSWORD      — kabu ステーション API パスワード（発注系がある場合）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID       — Slack チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動で .env を読み込まない

OpenAI:
- OPENAI_API_KEY         — score_news / score_regime のデフォルト API キー（関数引数からも渡せます）

DB パス（デフォルトが設定されていますが .env で変更可）:
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用（monitoring）などに利用する SQLite パス（デフォルト: data/monitoring.db）

簡易的な .env 例（プロジェクトルートに置く）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

自動ロード挙動:
- パッケージ import 時に、カレントワーキングディレクトリに依存せず、パッケージ内 file を基準に親ディレクトリを探索して `.git` または `pyproject.toml` が見つかればプロジェクトルートと見なして `.env` / `.env.local` をロードします。
- `.env.local` は `.env` の上書きとして読み込まれます。
- 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで便利です）。

---

## 簡単な使い方（コード例）

下記は基本的な利用例です。詳細な引数や戻り値は各モジュールの docstring を参照してください。

1) DuckDB 接続を作成して ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄ごと）をスコア化して ai_scores に保存
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```
- OPENAI_API_KEY を環境変数に設定していない場合、score_news の第3引数に api_key を渡せます。

3) 市場レジーム判定（ETF 1321 の MA200 とマクロ記事の組合せ）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（発注・約定トレース用）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

5) 調査用（ファクター・IC など）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
fwd = calc_forward_returns(conn, date0, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

エラーハンドリングやログ、各関数のフェイルセーフ挙動（API 失敗時のフォールバック等）は各モジュールの docstring に記載されています。

---

## 注意点・運用上のヒント

- OpenAI の呼び出しはリトライを行いますが、API 利用料金・レート制限を考慮して適切に運用してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、ETL 実装で保護処理が入っています。アップデート時は互換性に注意してください。
- ニュース収集では SSRF 対策、レスポンスサイズ上限、XML パース時の defusedxml を使った安全化が実装されています。外部 RSS を追加する際も信頼性を確認してください。
- カレンダーが未取得の場合は曜日ベースのフォールバックを使いますが、カレンダーを定期的に更新しておくことを推奨します（calendar_update_job）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルとモジュール構成の要約です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（銘柄別）
    - regime_detector.py            — 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL 型の再エクスポート
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - stats.py                      — zscore_normalize 等の統計ユーティリティ
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログテーブル定義 / 初期化
    - news_collector.py             — RSS ニュース収集（SSRF 対策）
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility など
    - feature_exploration.py        — forward returns / IC / summary / rank
  - research/（他ユーティリティ）
  - その他モジュール...

（実際のファイルはさらに詳細に分かれています。上記は主要モジュールの抜粋です。）

---

もし README に追加してほしい内容（例えば CLI コマンド例、unit test の実行方法、CI/CD 設定、より詳しい API 使用例など）があれば教えてください。必要に応じてサンプル .env.example や簡易起動スクリプト例も作成します。