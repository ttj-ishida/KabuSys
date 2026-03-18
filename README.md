# KabuSys

日本株の自動売買・データ基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ取得（J-Quants）、DuckDB を使ったデータスキーマ／ETL、ニュース収集、特徴量計算、監査ログなどを含むモジュール群を提供します。

> 注意: この README はソースコード（src/kabusys 以下）の実装を元に作成しています。実行には環境変数や外部 API の認証情報が必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けインフラ／ライブラリです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークンリフレッシュを考慮）
- DuckDB を用いたスキーマ定義と冪等なデータ保存
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と記事→銘柄紐付け
- 研究用のファクター／特徴量計算（モメンタム・ボラティリティ・バリュー等）
- 監査ログ（signal → order → execution のトレーサビリティ）

設計方針として、可能な限り外部影響を抑え（DuckDB のみ永続化）、Look-ahead bias を避けるために取得時刻の記録や厳格な品質チェックを行うようにしています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ページネーション・レート制限・リトライ・id_token 自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）

- data/schema.py
  - DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - init_schema(db_path) で DB を初期化

- data/pipeline.py
  - 日次 ETL（run_daily_etl）: カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック
  - 差分更新・バックフィルをサポート

- data/news_collector.py
  - RSS フィード取得（SSRF 防御、gzip 制限、defusedxml）
  - 記事正規化 + id（SHA-256 先頭32文字）生成、raw_news への冪等保存
  - 銘柄コード抽出（4 桁）と news_symbols への紐付け

- data/quality.py
  - 欠損、スパイク、重複、日付不整合などの品質チェック（QualityIssue のリストを返す）

- research/factor_research.py / research/feature_exploration.py
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - data.stats の zscore_normalize をエクスポート

- data/audit.py
  - 監査ログの DDL（signal_events, order_requests, executions）と初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10 以上（ソースで | 型ヒント等を使用）
- 必要な外部パッケージ: duckdb, defusedxml
  - 例: pip install duckdb defusedxml

リポジトリ内パッケージとして開発インストールする例:

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクトで requirements.txt があればそちらを使ってください）

3. ローカルパッケージとしてインストール（オプション）
   - pip install -e .

環境変数設定:
- 本ライブラリは環境変数から設定を読み込みます（.env / .env.local の自動ロードあり）。
- 主要な環境変数:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD     : kabu ステーション発注用パスワード（必須）
  - KABU_API_BASE_URL     : kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV           : 環境 ("development", "paper_trading", "live")（デフォルト development）
  - LOG_LEVEL             : ログレベル ("DEBUG","INFO",...)（デフォルト INFO）
- 自動 .env ロードを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みを無効化します。
- .env の読み込み順:
  - OS環境変数 > .env.local > .env
  - プロジェクトルートの判定は .git または pyproject.toml を基準に実施

注意: settings（kabusys.config.settings）から安全に環境値を取得できます。必須の未設定時には ValueError が発生します。

---

## 使い方（クイックスタート）

以下は Python REPL / スクリプトでの簡単な利用例です。

- Settings を使う（環境変数を参照）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 環境変数が未設定なら例外
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成・親ディレクトリも自動作成
```

- 日次 ETL 実行（市場カレンダー／価格／財務／品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日を対象に実行
print(result.to_dict())
```

- ニュース収集ジョブ実行（既知銘柄セットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
summary = run_news_collection(conn, known_codes=known_codes)
print(summary)  # {source_name: 新規保存件数, ...}
```

- J-Quants から日足取得のみ（低レベル API）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- ファクター計算（研究用）
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
from datetime import date

mom = calc_momentum(conn, date(2024,1,31))
fwd = calc_forward_returns(conn, date(2024,1,31))
# factor_records = mom のような list[dict] を想定
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

- 品質チェックの手動実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2024,1,31))
for i in issues:
    print(i)
```

- 監査ログスキーマ初期化（audit 専用 DB）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## ディレクトリ構成

主要なファイル／モジュール（src/kabusys 以下）の構成と簡単な説明:

- kabusys/
  - __init__.py
  - config.py               : 環境変数管理・Settings
  - data/
    - __init__.py
    - jquants_client.py     : J-Quants API クライアント（取得 / 保存）
    - news_collector.py     : RSS 収集・記事正規化・DB 保存・銘柄抽出
    - schema.py             : DuckDB スキーマ定義・初期化
    - pipeline.py           : ETL パイプライン（run_daily_etl 等）
    - features.py           : 特徴量関連の公開インターフェース
    - stats.py              : 統計ユーティリティ（zscore_normalize）
    - calendar_management.py: 市場カレンダー管理ユーティリティ
    - audit.py              : 監査ログ（信頼性の高いトレーサビリティ）
    - etl.py                : ETL 関連の公開型（ETLResult）
    - quality.py            : データ品質チェック
  - research/
    - __init__.py
    - factor_research.py    : モメンタム・ボラ・バリュー計算
    - feature_exploration.py: 将来リターン・IC・サマリー等
  - strategy/
    - __init__.py
    (戦略モデル・ポートフォリオ最適化等はここに実装)
  - execution/
    - __init__.py
    (発注連携・kabuステーション接続等)
  - monitoring/
    - __init__.py
    (監視・メトリクス・アラート)

各モジュールはソース内ドキュメント（docstring）で設計方針・前提・戻り値を詳細に記載しています。実装はできるだけ副作用を抑え、DuckDB 接続や id_token を引数で注入できるようにしてテストを容易にしています。

---

## 追加情報 / 注意事項

- 実行時には J-Quants API の認証情報（JQUANTS_REFRESH_TOKEN）が必須です。API の利用規約・レート制限（120 req/min）を尊重してください（クライアントは内部でスロットリングを行います）。
- RSS 取得などネットワーク I/O を含む処理は外部の失敗に強く作られていますが、運用時はログと監視を必ず行ってください。
- DuckDB のバージョンや SQL 機能（例: RETURNING、INDEX、制約の挙動）は環境差が出る場合があります。問題が出たら duckdb のバージョンを合わせて確認してください。
- 本コードは本番口座での自動発注に用いる場合、安全性・リスク管理の追加実装（レート制御、二重発注防止、接続監視、テスト口座での検証など）が必要です。

---

もし README に追記してほしい具体的な使用例（たとえば、特定の ETL スケジュール設定や戦略シミュレーションのサンプルスクリプト）があれば教えてください。それに合わせた手順やサンプルコードを追加します。