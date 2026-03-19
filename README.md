# KabuSys

日本株向け自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量構築、シグナル生成、ニュース収集、監査用スキーマなどを含むモジュール群を提供します。DuckDB を主要なオンディスクデータベースとして利用する設計です。

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成される、自動売買プラットフォームの基盤ライブラリです。

- Data layer: J-Quants API からの生データ取得、DuckDB スキーマ定義、ETL パイプライン
- Research layer: ファクター計算・解析（モメンタム、ボラティリティ、バリュー等）
- Strategy layer: 特徴量作成（正規化）およびシグナル生成（BUY/SELL）
- Execution / Monitoring: 発注・約定・ポジション表現や監査ログのスキーマ（実際の証券会社 API は実装していません）
- News collection: RSS 取得および記事 → 銘柄紐付け機能

設計上のポイント:
- ルックアヘッドバイアスに配慮し、target_date 時点のデータのみを使用
- DuckDB への保存は冪等（ON CONFLICT）を前提
- ネットワークリトライ・レート制御・SSRF 対策など堅牢化実装あり
- 自動で .env/.env.local をプロジェクトルートから読み込む（必要に応じて無効化可能）

---

## 主な機能一覧

- J-Quants クライアント（data.jquants_client）
  - 日足（OHLCV）・財務データ・マーケットカレンダーの取得（ページネーション対応）
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（save_* 関数）
- ETL パイプライン（data.pipeline）
  - 差分取得、バックフィル、品質チェックの統合 run_daily_etl
- DuckDB スキーマ初期化（data.schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義とインデックス
  - init_schema() / get_connection()
- ファクター計算（research.factor_research）
  - momentum / volatility / value の計算（prices_daily / raw_financials を参照）
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターの統合、ユニバースフィルタ、Zスコア正規化、features テーブルへの保存
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出、BUY/SELL を判定し signals テーブルへ保存
- ニュース収集（data.news_collector）
  - RSS フィードの取得、前処理、raw_news 保存、記事 → 銘柄コード抽出・紐付け
- 共通ユーティリティ
  - 統計ユーティリティ（data.stats: zscore_normalize）
  - マーケットカレンダー管理（data.calendar_management）
  - 監査ログスキーマ（data.audit）

---

## 必要要件（主な依存）

- Python 3.9+（typing の一部記法に依存）
- duckdb
- defusedxml

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージをプロジェクトとして使う場合（開発インストール）
pip install -e .
```

※ setup.py / pyproject.toml がある前提で pip install -e . を想定しています。無ければ直接 Python パスに追加して利用してください。

---

## 環境変数 / 設定

自動でプロジェクトルートの `.env` および `.env.local` を読み込みます（ただし OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須で使う場合）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン（必須で通知を使う場合）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須で通知を使う場合）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

Settings は kabusys.config.settings から参照できます。必須変数が未設定だと ValueError を投げます。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・依存インストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -U pip
   - pip install duckdb defusedxml
   - pip install -e .  # パッケージ開発インストール（任意）
3. .env を作成
   - プロジェクトルートに `.env` を置き、必要な環境変数を設定
4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで init_schema を実行（下記例参照）

---

## 使い方（簡単な例）

以下は最小限の実行例です。実運用ではログ設定や例外ハンドリングを適切に行ってください。

1) DuckDB スキーマを初期化する:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行する（J-Quants トークンは環境変数で設定）:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量を構築してシグナルを生成する:
```python
from datetime import date
from kabusys.strategy import build_features, generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 15)

n_feats = build_features(conn, target)
n_signals = generate_signals(conn, target)
print(f"features: {n_feats}, signals: {n_signals}")
```

4) ニュース収集ジョブを走らせる:
```python
from kabusys.data.news_collector import run_news_collection
conn = get_connection("data/kabusys.duckdb")
# known_codes を与えると記事中の4桁銘柄コードを紐付けを行う
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)
```

5) J-Quants から日足データを直接取得して保存:
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,15))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定読み込み
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（取得・保存）
  - news_collector.py       — RSS → raw_news / news_symbols
  - schema.py               — DuckDB スキーマ定義・初期化
  - stats.py                — zscore_normalize 等の統計ユーティリティ
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - features.py             — data.stats の再エクスポート
  - calendar_management.py  — market_calendar 管理ユーティリティ
  - audit.py                — 監査ログ用スキーマ定義
- research/
  - __init__.py
  - factor_research.py      — momentum / volatility / value 計算
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py  — features の作成（正規化・フィルタ）
  - signal_generator.py     — final_score の計算と signals 生成
- execution/                 — 発注層（パッケージ用意）
- monitoring/                — 監視・Slack 通知用（パッケージ用意）

（README に含まれているもののみ抜粋しています）

---

## 注意点・トラブルシューティング

- 環境変数が未設定の場合、settings（kabusys.config.settings）が ValueError を投げます。ログを読んで `.env` を用意してください。
- DuckDB のファイルパスの親ディレクトリが無ければ init_schema が自動作成しますが、ファイルシステム権限に注意してください。
- J-Quants API 呼び出しはレート制限（120 req/min）を守るよう内部で制御していますが、極端に短時間で大量の並列実行は避けてください。
- RSS の取得では SSRF 対策とサイズ制限を実装しています。内部ネットワークの URL や大きなレスポンスは拒否されます。
- tests は含まれていません。ユニットテストや CI を追加することを推奨します。

---

## 今後の拡張案（例）

- execution 層のブローカー接続（kabuステーション / 他ブローカー）の完全実装
- AI スコア計算パイプラインの実装と ai_scores テーブルの自動投入
- Web ダッシュボード / モニタリング通知の正式化
- テストスイート、CI/CD の整備

---

この README はコード内のドキュメント文字列（docstring）と設計ノートを基に作成しています。実運用前に各モジュールの挙動（特に API トークン周り、DB 初期化やファイル権限）をローカルで十分に確認してください。