# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのライブラリ集です。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログ、DuckDB ベースの永続化など、量的投資システムの典型的なコンポーネントを提供します。

この README はコードベースの概要、機能一覧、セットアップ手順、使い方（主要 API の例）、およびディレクトリ構成をまとめたドキュメントです。

---

## プロジェクト概要

- 目的: J-Quants 等から市場データを取得して DuckDB に蓄積し、研究→特徴量化→シグナル生成→発注（エグゼキューション）へと繋がる自動売買パイプラインをサポートする。
- 設計の特徴:
  - 各レイヤは冪等（idempotent）で設計され、DB へは ON CONFLICT / トランザクションで安全に書き込む。
  - ルックアヘッドバイアスに配慮し、target_date 時点のデータのみを用いるよう設計。
  - ネットワーク処理はレート制限・リトライ・トークン自動更新を含む堅牢な実装（J-Quants クライアント）。
  - ニュース収集では SSRF 対策、XML の安全パース（defusedxml）、トラッキングパラメータ除去などを実装。

---

## 主な機能一覧

- 環境設定管理
  - `.env` / `.env.local` 自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN）
- データ取得・保存（J-Quants クライアント）
  - 株価日足（OHLCV）取得、財務データ、マーケットカレンダー
  - ページネーション対応・レート制御・自動トークンリフレッシュ
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン
  - 差分更新（バックフィル考慮）、品質チェック、日次 ETL ジョブ
- スキーマ管理
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 研究系ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング
  - 生ファクターを正規化（Z-score）・合成して `features` テーブルへ保存
  - ユニバースフィルタ（最低株価・平均売買代金）
- シグナル生成
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL シグナル生成、signals テーブルへの保存
- ニュース収集
  - RSS フィード取得・前処理・raw_news 保存・銘柄抽出（4桁コード）
  - SSRF / 大容量レスポンス / XML 攻撃対策
- 監査ログ（audit）
  - シグナル→発注→約定を UUID 連鎖でトレース可能なテーブル設計（信頼性・不変証跡）

---

## 必要要件（依存）

最低限の依存（選択的に追加で必要な場合あり）:

- Python 3.9+
- duckdb
- defusedxml

インストール例（プロジェクトに合わせて適宜調整）:

```bash
python -m pip install duckdb defusedxml
# パッケージとしてローカル開発インストールする場合
pip install -e .
```

（プロジェクトに pyproject.toml / setup があればそちらを使ってください）

---

## 環境変数（主なもの）

config.Settings で参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL (省略可) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (省略可) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (省略可) — デフォルト: data/monitoring.db
- KABUSYS_ENV (省略可) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (省略可) — DEBUG/INFO/WARNING/ERROR/CRITICAL

.env 自動読み込みの挙動:

- 自動ロードはプロジェクトルート (.git または pyproject.toml を基準) を探索して `.env` → `.env.local` の順で読み込みます。`.env.local` は `.env` を上書きします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

簡単な .env 例:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化

```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

2. 依存をインストール

```bash
pip install -r requirements.txt   # 存在する場合
# もしくは最低限:
pip install duckdb defusedxml
```

3. 環境変数を設定（.env を作成）

プロジェクトルートに `.env` を作成し、上記の必須変数を記述します。

4. DuckDB スキーマ初期化

以下の Python スニペットを実行して DB とテーブルを初期化します。

```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```

---

## 使い方（主要 API の例）

以下はライブラリを直接インポートして使う例です。実行は Python スクリプトまたは REPL から行います。

- DuckDB 接続 & スキーマ初期化

```python
from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")  # テーブル作成して接続を返す
# もしくは既存 DB に接続するだけ:
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）

```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 特徴量作成（target_date に対して features テーブルを構築）

```python
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, date(2026, 3, 20))
print(f"features upserted: {count}")
```

- シグナル生成（features + ai_scores → signals テーブル）

```python
from kabusys.strategy import generate_signals
from datetime import date
n_signals = generate_signals(conn, date(2026, 3, 20))
print(f"signals created: {n_signals}")
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
# known_codes は有効な銘柄コードの集合（抽出用）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

- J-Quants 生データ取得（クライアントを直接利用）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用して取得
records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))
# 保存は save_daily_quotes を使う
from kabusys.data.jquants_client import save_daily_quotes
saved = save_daily_quotes(conn, records)
```

注意点: 実運用での発注処理や Slack 通知などは追加の設定（証券会社 API、Slack トークン等）が必要です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと概要です（コードベース抜粋に基づく）。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数読み込み・設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - schema.py — DuckDB スキーマ定義・初期化
    - pipeline.py — ETL パイプライン（差分取得・日次 ETL）
    - news_collector.py — RSS ニュース収集・保存・銘柄抽出
    - stats.py — Z スコア正規化など統計ユーティリティ
    - calendar_management.py — market_calendar の管理・営業日ユーティリティ
    - audit.py — 監査ログ用 DDL / 初期化（監査テーブル）
    - features.py — データ層の特徴量ユーティリティ再エクスポート
    - (その他: quality 等の補助モジュールが想定される)
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value 計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクターの正規化・features への書き込み
    - signal_generator.py — final_score 計算・BUY/SELL 生成
  - execution/ — 発注関連の実装（パッケージ化済み）
  - monitoring/ — 監視/メトリクス系（動作想定）
  - その他モジュール群（例: data.quality など）  

---

## 運用上の注意

- J-Quants の API レート制限（120 req/min）やリトライポリシーに留意してください。大規模な backfill を行う際は API への負荷管理が必要です。
- DuckDB のファイルはバックアップ・ローテーションを検討してください（単一ファイルのためサイズ増加に注意）。
- 本リポジトリのコードは主要ロジックを実装していますが、実取引（live）で使う際は十分なテスト、監査、リスク管理（テスト用ストラテジーや paper_trading 環境）を行ってください。
- 環境（KABUSYS_ENV）を `live` にすると実発注を行う箇所で挙動が変わる想定なので本番運用前に review を行ってください。

---

## 参考・次のステップ

- ユニットテスト／統合テストの追加（特に ETL とエッジケース）
- 発注エンジン（kabu API）との接続テスト（paper_trading モード）
- モニタリング・アラート（Slack 通知、Prometheus 等）
- ドキュメントの拡充（StrategyModel.md / DataPlatform.md 等の参照ドキュメントをプロジェクトに含める）

---

README に書かれている手順で動かなかったり、より細かい API の利用例（引数説明や期待されるテーブルスキーマ）を希望される場合は、どの機能について詳しく知りたいかを教えてください。具体例（ETL の実行ログ、features/signal のテーブル定義の抜粋等）も提供します。