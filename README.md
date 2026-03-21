# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリです。データ収集（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略開発〜実運用のための基盤機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成される自動売買システム向けユーティリティ群を備えています。

- Data（data）: J-Quants からのデータ取得クライアント、DuckDB スキーマ定義、ETL パイプライン、ニュース収集、カレンダー管理、品質チェック等
- Research（research）: ファクター計算（Momentum/Volatility/Value）や将来リターン、IC 計算、ファクター統計
- Strategy（strategy）: ファクター正規化・合成（feature_engineering）とシグナル生成（signal_generator）
- Execution（execution）: 発注・約定・ポジション管理のスキーマやインターフェース（実装の拡張を想定）
- Monitoring（monitoring）: 監視通知等（拡張ポイント）
- Config（config）: 環境変数／設定の読み込みと検証

設計上のポイント:
- DuckDB を中心にローカルで高速に処理可能
- J-Quants API はレート制御・リトライ・トークン自動リフレッシュ対応
- ETL / DB 書き込みは冪等（ON CONFLICT / トランザクション）を意識
- ルックアヘッドバイアス回避のため、target_date 時点の情報のみを使用する設計

---

## 主な機能一覧

- 環境設定管理（.env 自動ロード、必須変数検証）
- J-Quants API クライアント
  - 日足取得（ページネーション対応、レートリミット）
  - 財務諸表取得
  - 市場カレンダー取得
  - 保存ユーティリティ（raw_prices / raw_financials / market_calendar への冪等保存）
- DuckDB スキーマ初期化・コネクション管理
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 特徴量計算（Momentum / Volatility / Value）
- Zスコア正規化ユーティリティ
- 戦略向け特徴量ビルド（features テーブル作成）
- シグナル生成（final_score 計算、BUY/SELL 判定、signals テーブル保存）
- ニュース収集（RSS フィード）と銘柄抽出・保存
- マーケットカレンダー管理（営業日判定・前後営業日検索）
- 監査ログスキーマ（signal_events / order_requests / executions 等）

---

## 前提 / 必要環境

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml
- ネットワークで J-Quants API にアクセスするための環境（API トークン等）

（実際のインストールはプロジェクトに合わせて requirements.txt / pyproject.toml を準備してください）

---

## セットアップ手順

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements がある場合はそちらを利用）

3. リポジトリをインストール（開発モード）
   - pip install -e .

4. 環境変数を設定（.env ファイル推奨）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索）。

必須環境変数の例（.env）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション API（発注連携がある場合）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（省略時: data/kabusys.duckdb, data/monitoring.db）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロードを無効にする（テスト等）:
- 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

---

## 使い方（簡単な例）

以下は代表的なワークフローの Python インタラクティブ例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants トークンは settings が参照）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量（features）をビルド
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2024, 1, 31))
print(f"built features: {count}")
```

4) シグナルを生成
```python
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, date(2024, 1, 31))
print(f"signals written: {n}")
```

5) ニュース収集（RSS）を実行
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は既知の銘柄コード集合（抽出に使う）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

6) J-Quants の ID トークンを直接取得する
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意:
- run_daily_etl などは内部で例外を捕捉しつつ処理を継続する設計です。戻り値の ETLResult でエラーや品質問題を確認してください。
- デフォルトでは features / signals / raw_* テーブルに対して「日付単位の置換（削除→挿入）」を行い冪等性を保っています。

---

## ディレクトリ構成

主要なファイルとモジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - schema.py
    - stats.py
    - features.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - calendar_management.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
    (execution 層の実働部分は拡張ポイント)
  - monitoring/
    - (監視・通知用の拡張ポイント)

各モジュールの責務:
- config.py: .env/環境変数のロードと Settings オブジェクト
- data/schema.py: DuckDB スキーマ定義・初期化
- data/jquants_client.py: J-Quants API 通信・保存ユーティリティ
- data/pipeline.py: ETL ワークフロー
- data/news_collector.py: RSS 取得・前処理・DB 保存
- research/*.py: ファクター計算・評価ユーティリティ
- strategy/*.py: 特徴量構築・シグナル生成ロジック

---

## 開発上の注意点 / 設計メモ

- ルックアヘッドバイアスを防ぐため、戦略ロジックは target_date 時点までのデータのみを参照するよう実装されています。
- DuckDB への書き込みはトランザクションと冪等化（ON CONFLICT）を用いているため、ジョブの再実行が安全です。
- J-Quants API 利用時はレート制御・リトライ・401 リフレッシュなどの堅牢性処理が実装されています。
- ニュース収集は SSRF 対策や XML 爆弾対策（defusedxml）、レスポンスサイズ制限などセキュリティを考慮しています。

---

## 今後の拡張ポイント

- execution 層の証券会社 API 連携実装（kabuステーション連携など）
- 監視/アラート（Slack 連携の実装例）
- テストケース・CI 設定
- 実運用向けのリトライ・バックオフや監査ログの可視化ダッシュボード

---

もし README の内容を環境変数一覧の追記や具体的なコマンド例（systemd / cron / Docker）などで拡張したければ、用途に合わせて追記します。