# KabuSys

バージョン: 0.1.0

日本株向けの自動売買・データ基盤ユーティリティ群。  
J-Quants からの市場データ取得、DuckDB によるデータ保管・スキーマ管理、ETL パイプライン、ニュース収集、データ品質チェック、ファクター計算（リサーチ用）や監査ログ用スキーマなど、トレーディングシステムのデータ層〜リサーチ層をカバーするライブラリ群です。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX カレンダー取得
  - レート制御（120 req/min 固定スロットリング）、リトライ、ID トークン自動リフレッシュ
  - ページネーション対応

- DuckDB ベースのデータスキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層を想定したテーブル群（冪等な DDL）
  - インデックス定義とスキーマ初期化ユーティリティ

- ETL パイプライン
  - 差分更新（最終取得日を基に差分を自動取得）
  - バックフィル機能（直近数日を再取得して API の後出し補正を吸収）
  - 日次 ETL 集約（カレンダー → 株価 → 財務 → 品質チェック）

- ニュース収集（RSS）
  - RSS フィード取得、前処理、記事ID生成（正規化URL の SHA-256 先頭 32 文字）
  - SSRF 対策、サイズ制限、XML の安全パース（defusedxml）
  - raw_news / news_symbols への冪等保存

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
  - 問題を QualityIssue オブジェクトとして収集（警告／エラー区別）

- マーケットカレンダー管理
  - JPX カレンダーの差分取得、営業日判定・前後営業日取得、範囲内営業日の抽出
  - DB 値優先・未登録日は曜日フォールバック

- 研究用（Research）モジュール
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティの提供

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 までのトレーサビリティを保持するスキーマ
  - order_request_id を冪等キーとして二重発注防止をサポート

- セキュリティ・信頼性への配慮
  - ネットワーク・XML・SSRF 保護、API レート制御、トランザクション管理（DuckDB）

---

## 動作環境・前提

- Python 3.10 以上（型注釈に | 演算子等を使用）
- 必要な外部パッケージ（最低限）
  - duckdb
  - defusedxml
- 推奨: 仮想環境（venv / virtualenv）を利用

例（最低限のインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクト化／パッケージ化されている場合は、requirements.txt / pyproject.toml に従ってインストールしてください。

---

## 環境変数（主に必須）

自動的にルートの `.env` / `.env.local` をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必要な環境変数の代表例:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注系）
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイル（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

設定例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

.env の読み込みルール:
- OS 環境変数が優先
- .env を読んだ後 .env.local を優先して上書き（.env.local は override）
- export KEY=val 形式やクォート、コメントの扱いに対応

---

## セットアップ手順（簡易）

1. リポジトリをチェックアウト / クローン
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（例: duckdb, defusedxml）
4. ルートに .env を作成して必須環境変数を設定
5. DuckDB スキーマを初期化

例:
```python
from kabusys.data import schema

# データベースファイルの初期化（ファイルの親フォルダは自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログ専用 DB を別に作ることも可能
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（主要な API とサンプル）

基本的なデータ初期化と日次 ETL 実行の例:

```python
from datetime import date
from kabusys.data import schema, pipeline
import duckdb

# DB 初期化（既に初期化済みなら既存を開く）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（当日分）
res = pipeline.run_daily_etl(conn)
print(res.to_dict())
```

個別ジョブの呼び出し例:

- 株価差分 ETL
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- カレンダージョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes: 有効な銘柄コード集合を渡すと自動的に銘柄紐付けを行う
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
```

- J-Quants から生データを取得して保存する（直接呼ぶ場合）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
count = save_daily_quotes(conn, records)
```

- 研究モジュール例（ファクター・IC 計算）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize
# DuckDB 接続 conn を渡して各ファクターを計算
momentum = calc_momentum(conn, target_date=date(2024,3,1))
forward = calc_forward_returns(conn, target_date=date(2024,3,1))
# IC を計算（factor_col と return_col は各戻り値のキー名）
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
# 正規化
normed = zscore_normalize(momentum, ["mom_1m","mom_3m","mom_6m"])
```

- 品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

ログレベルや実行環境フラグは環境変数で制御できます（KABUSYS_ENV, LOG_LEVEL）。

---

## 重要な設計・利用上の注意

- J-Quants API 呼び出しはレート制御とリトライ（指数バックオフ）を組み合わせて安全に行います。独自に高頻度で呼ぶ場合は注意してください。
- save_ 系の関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）になっており、ETL の再実行が可能です。
- news_collector は外部 URL を扱うため SSRF・XML 脆弱性対策を実装していますが、信頼できないソースや大規模収集では追加対策が必要です。
- DuckDB のトランザクション特性に注意してください（`init_audit_schema` の transactional 引数など）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まないため、テスト時に環境変数の注入を容易にできます。
- 実口座での発注（kabu API 等）を行うモジュールは別途設定や安全チェックが必要です。本リポジトリでは主にデータ基盤・リサーチ・監査周りを提供します。

---

## ディレクトリ構成（抜粋）

以下は本コードベースの主要ファイル・パッケージ構成（src/kabusys 配下）です:

- kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定ロード（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得＋保存ユーティリティ）
    - news_collector.py               — RSS ニュース収集・保存
    - schema.py                       — DuckDB スキーマ定義・init_schema
    - stats.py                        — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - features.py                     — 特徴量インターフェース（再エクスポート）
    - calendar_management.py          — 市場カレンダー管理
    - audit.py                        — 監査ログスキーマ（signal/order/execution）
    - etl.py                          — ETL 型の公開インターフェース（再エクスポート）
    - quality.py                      — データ品質チェック
  - research/
    - __init__.py                     — 研究用ユーティリティの公開
    - feature_exploration.py          — 将来リターン / IC / サマリー
    - factor_research.py              — momentum/value/volatility の計算
  - strategy/                          — 戦略関連（未実装ファイル群のプレースホルダ）
  - execution/                         — 発注・約定等（プレースホルダ）
  - monitoring/                        — 監視用（プレースホルダ）

---

## 貢献・拡張ポイント（今後の想定）

- 発注・約定のブローカー API 統合（kabu ステーション連携の実装拡充）
- 戦略層（position sizing、risk management、scheduler）の追加
- テレメトリ／監視（Prometheus / Grafana 等）との統合
- テストカバレッジの拡充（各モジュールのユニット／統合テスト）
- ニュースの自然言語処理（感情スコア算出）や AI スコアの追加

---

README に掲載した API 呼び出し例は概要を示す目的です。実運用前に必ずテスト環境（paper_trading / development）で動作確認を行い、キー管理・シークレット管理や発注系の安全策（取引上限、サンドボックス）を整備してください。質問や補足の希望があれば用途に合わせて具体的なサンプルや手順（例: CI/CD、backfill 戦略、運用監視）を追加します。