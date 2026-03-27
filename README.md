# KabuSys

日本株向けのデータプラットフォーム＋リサーチ／自動売買支援ライブラリ。
本リポジトリは J-Quants / kabuステーション / RSS / OpenAI（LLM）等を組み合わせて、
データの ETL、ニュースセンチメント解析、ファクター計算、監査ログ管理などを行うモジュール群を提供します。

主な目的
- J-Quants から株価・財務・市場カレンダーを差分取得して DuckDB に蓄積
- RSS からニュースを収集して銘柄ごとのニュースセンチメントを LLM で評価
- ETF とマクロニュースを用いて市場レジームを判定
- ファクター計算 / 特徴量探索（リサーチ用途）
- 発注監査ログ（トレーサビリティ）用スキーマ初期化ユーティリティ

---

## 機能一覧（概要）

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出：.git / pyproject.toml）
  - 必須環境変数チェック（settings オブジェクト）

- データ ETL（kabusys.data.pipeline）
  - 日次 ETL（株価 / 財務 / カレンダー）
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）

- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh token → id token）
  - ページネーション対応・レートリミット・リトライ実装
  - DuckDB への冪等保存（ON CONFLICT）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策、トラッキングパラメタ除去、前処理）
  - raw_news / news_symbols 連携用の前処理ロジック

- ニュース NLP（kabusys.ai.news_nlp）
  - gpt-4o-mini を用いた銘柄別ニュースセンチメント評価（JSON mode）
  - チャンクバッチ、リトライ、レスポンスバリデーション
  - ai_scores テーブルへスコア保存（部分失敗を考慮した置換処理）

- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して
    market_regime テーブルへ書き込み

- 研究モジュール（kabusys.research）
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - zscore 正規化ユーティリティ（kabusys.data.stats）

- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の DDL とインデックス定義
  - DuckDB に対する冪等初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## 動作環境・依存

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, logging など）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
```

（プロジェクト配布用には poetry / pipx / requirements.txt を用意してください）

---

## 環境変数（主なもの）

最低限設定が必要な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD    : kabuステーション API パスワード
- SLACK_BOT_TOKEN      : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID     : Slack 通知先チャネル ID
- OPENAI_API_KEY       : OpenAI 呼び出しに使用（news_nlp / regime_detector）

任意（デフォルトあり）:
- KABUSYS_ENV          : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL            : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH          : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH          : 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動ロードを無効化

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml のある階層）にある `.env` / `.env.local` を自動読み込みします。
- OS 環境変数 > .env.local > .env の優先順位で設定されます。
- テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン / コピ―
2. 仮想環境を作成して依存をインストール（上記参照）
3. プロジェクトルートに .env を作成し、上記必須変数を設定
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```
4. DuckDB ファイルの親ディレクトリを作成（自動で作られるユーティリティもありますが、確実に作っておくと良い）
   ```
   mkdir -p data
   ```
5. （任意）監査ログ用 DB を初期化:
   - Python スクリプト例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema

     conn = duckdb.connect("data/audit.duckdb")
     init_audit_schema(conn, transactional=True)
     ```
   - または:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要ユースケース）

1) 日次 ETL を実行してデータを取得・保存する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックの順で処理します。
- ID トークンは jquants_client 内部で settings.jquants_refresh_token を用いて自動取得されます（必要なら id_token を引数で注入可能）。

2) ニュースセンチメントを計算して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```
- OpenAI API キーは OPENAI_API_KEY 環境変数、または api_key 引数で指定可能。
- 1回の呼び出しは複数銘柄をチャンクでまとめて処理します（_BATCH_SIZE = 20）。

3) 市場レジームを判定して market_regime テーブルへ保存
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```
- ETF 1321 の MA200 乖離とマクロニュースの LLM スコアで合成します。
- OpenAI の呼び出しは内部で指数バックオフやリトライを行い、失敗時は macro_sentiment=0.0 でフェイルセーフ動作します。

4) ファクター計算 / リサーチ
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ... }, ...]
```
- 他に calc_volatility / calc_value、feature_exploration の関数群があります。

5) 監査ログスキーマ初期化（監査 DB を分ける場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```
- init_audit_schema は transactional フラグで BEGIN/COMMIT 包装が可能です（DuckDB のトランザクションに注意）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（settings オブジェクト）
  - ai/
    - __init__.py              — score_news の公開
    - news_nlp.py              — ニュースセンチメント（LLM 呼び出し・バッチ処理）
    - regime_detector.py       — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py              — ETL パイプライン / run_daily_etl 等
    - news_collector.py        — RSS 収集・前処理
    - calendar_management.py   — 市場カレンダー管理・営業日判定
    - quality.py               — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                 — zscore_normalize 等の統計ユーティリティ
    - audit.py                 — 監査ログ DDL / 初期化ユーティリティ
    - etl.py                   — ETLResult を re-export
  - research/
    - __init__.py
    - factor_research.py       — momentum/volatility/value 等
    - feature_exploration.py   — 将来リターン / IC / factor_summary / rank
  - research/…（その他の研究向けユーティリティ）
  - (その他: strategy, execution, monitoring パッケージ用の公開は __all__ に含める想定)

---

## 注意点・運用上の設計方針

- Look-ahead bias 防止
  - 多くの関数は内部で date.today() を直接参照せず、target_date を明示的に受け取ります。
  - ETL / スコアリング等をバックテストで用いる際は、必ず target_date を正しく与えること。

- 冪等性
  - jquants_client の保存関数は ON CONFLICT DO UPDATE を使用して冪等性を確保。
  - audit の order_request_id は冪等キーとして設計。

- API レート・リトライ
  - J-Quants: 120 req/min の制御、リトライ（408/429/5xx）、401 は自動トークンリフレッシュ。
  - OpenAI 呼び出し: リトライとバックオフ実装あり。失敗時はフェイルセーフ（スコア 0 等）で継続。

- セキュリティ
  - news_collector は SSRF 対策（リダイレクト検査・プライベート IP ブロック）を実施。
  - defusedxml を使った XML パースで XML 攻撃を軽減。

---

## トラブルシューティング

- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認
  - プロジェクトルート（.git / pyproject.toml）が正しく存在するか確認
  - 明示的に os.environ に設定するか、テスト時は settings をモックしてください

- J-Quants API エラー（401 / 429）
  - 401 は自動リフレッシュを試行しますが、refresh token が無効な場合は更新してください
  - 429 などはログに Retry-After が記録されるので、レートを下げるかスケジューリングを調整してください

- OpenAI 呼び出し結果の JSON パース失敗
  - モデル応答に余計なテキストが混入する場合があるため、news_nlp は最外の `{}` 抽出などを行います
  - 失敗したチャンクはスキップし、ログを確認してください

---

## 貢献 / 開発

- 型ヒントとドキュメンテーション文字列を参照して安全に拡張してください
- テストを書く際は外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックして実行してください
- settings や _call_openai_api など内部の API 呼び出しポイントはテスト差し替えがしやすい設計です

---

以上が README.md のサマリです。README の追加情報（例: CI / GitHub Actions の設定、より詳しいスキーマ定義、サンプル .env.example 等）が必要であれば教えてください。必要に応じて README を拡張してテンプレートや CLI 実行例も追加します。