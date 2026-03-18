# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログ等の実装を含み、戦略開発・バックテスト・運用のための基盤機能を提供します。

主な設計方針
- DuckDB を中心としたローカル/軽量データベース構成（Raw / Processed / Feature / Execution 層）
- J-Quants API のレート制御・リトライ・トークン自動更新対応
- ニュース収集は SSRF や XML Bomb 等のセキュリティ対策を実装
- 研究（research）モジュールは本番発注 API に一切アクセスしない設計
- 冪等性を意識した DB 保存（ON CONFLICT / INSERT ... RETURNING 等）

---

## 機能一覧

- 環境変数管理
  - .env / .env.local を自動ロード（必要に応じて無効化可能）
  - 必須環境変数の検査

- データ取得 / 保存（data.jquants_client）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - 取得データを DuckDB に冪等保存（raw_prices / raw_financials / market_calendar 等）
  - レートリミッタ、リトライ、401 時のトークン自動更新など堅牢な HTTP 層

- ETL（data.pipeline）
  - 差分更新・バックフィル・カレンダー先読みを行う日次 ETL ランナー
  - 品質チェック（data.quality）との統合

- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合（未来日付 / 非営業日データ）検出
  - QualityIssue オブジェクトで問題を集約

- スキーマ管理（data.schema / data.audit）
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - 監査ログ用スキーマ（signal_events / order_requests / executions 等）

- ニュース収集（data.news_collector）
  - RSS フィード収集・前処理・記事 ID 生成（URL 正規化 + SHA256）
  - SSRF / プライベートアドレス・サイズ上限・XML エスケープ対策
  - raw_news / news_symbols への冪等保存

- 研究用ユーティリティ（research）
  - momentum / value / volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）、ファクター統計量
  - データ正規化ユーティリティ（zscore）

---

## セットアップ手順

前提
- Python 3.9+（typing|duckdb 等の使用を考慮）
- DuckDB を利用（pip でインストール可能）

推奨手順（UNIX 系）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトが配布用に requirements.txt/pyproject.toml を用意している場合はそれに従ってください）

3. リポジトリを編集中にローカルインストール（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成してください。
   - 自動読み込みはデフォルトで有効です（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      — kabuステーション API パスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN        — Slack 通知を行う場合
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID

オプション（デフォルトあり）
- KABUSYS_ENV            — development / paper_trading / live（デフォルト：development）
- LOG_LEVEL              — DEBUG/INFO/...（デフォルト：INFO）
- KABU_API_BASE_URL      — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — モニタリング用 SQLite パス（デフォルト data/monitoring.db）

例: .env
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な例）

以下は Python コードでライブラリを利用する基本例です。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# conn は init_schema で得た DuckDB 接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使う文字列集合（例: {"7203", "6758", ...}）
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)
```

- 研究用ファクター計算（例: momentum）
```python
from datetime import date
from kabusys.research import calc_momentum
records = calc_momentum(conn, target_date=date(2024, 1, 31))
# records は list[dict]（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

- 将来リターンと IC 計算
```python
from kabusys.research import calc_forward_returns, calc_ic
fwd = calc_forward_returns(conn, target_date=date(2024, 1, 31), horizons=[1,5,21])
# factor_records は事前に算出済みのファクターリスト
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- 監査スキーマの初期化（別 DB に分ける場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点
- research/* モジュールは DuckDB 上の prices_daily/raw_financials テーブルのみを参照し、本番発注 API にはアクセスしません（安全に解析・実験が可能）。
- jquants_client は内部でレート制御・リトライ・トークン自動更新を行いますが、API キーは必ず安全に管理してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検索して行います。テストや別の起動方法で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成

主要ファイル/モジュールの簡易説明を含めた構成です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定の読み込みと検証
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py      — RSS 収集・前処理・DB 保存
    - schema.py              — DuckDB スキーマ定義と init_schema()
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — 特徴量インターフェース（再エクスポート）
    - calendar_management.py — カレンダー管理（営業日判定 / calendar_update_job）
    - audit.py               — 監査ログ（signal/order/execution 等）のスキーマ
    - etl.py                 — ETL 用の公開型エイリアス（ETLResult）
    - quality.py             — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン/IC/summary 等
    - factor_research.py     — momentum/value/volatility 等のファクター計算
  - strategy/                — 戦略関連（未実装部分のプレースホルダ）
  - execution/               — 発注/ブローカー連携（未実装部分のプレースホルダ）
  - monitoring/              — 監視/メトリクス（未実装プレースホルダ）

---

## 補足 / 運用に関する注意

- 本ライブラリはデータ取得・ETL・特徴量算出に重点を置いており、実際の証券会社 API 統合や資金管理ルールは別途実装する必要があります。
- 本番（live）環境での運用時は KABUSYS_ENV を `live` に設定し、発注ロジックや安全弁（レート制限・最大注文サイズ・ドローダウン制御等）を十分検討してください。
- DuckDB ファイルはローカルに置くことを想定しています。運用規模が大きくなる場合はストレージ・バックアップ戦略を検討してください。
- ニュース収集や外部 HTTP 呼び出しにはセキュリティ上のリスクが伴います。適切なネットワーク環境と秘密情報管理を行ってください。

---

問題の報告や機能追加の提案がある場合は、ソースリポジトリの issue に記載してください。