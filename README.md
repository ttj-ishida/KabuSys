# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のリポジトリ向け README。  
本ドキュメントはプロジェクト概要、機能一覧、セットアップ手順、主要な使い方例、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、日本株のデータ収集・ETL・特徴量生成・シグナル生成〜発注監査までを想定したモジュール群を提供する Python ライブラリです。J-Quants API からのデータ取得（株価・財務・市場カレンダー）、RSS ベースのニュース収集、DuckDB によるデータ保存・スキーマ管理、戦略用特徴量の作成、シグナル算出、監査ログ用スキーマなどを含みます。

設計上の特徴：
- DuckDB を単一の分析 DB として利用（インメモリ or ファイル）
- API レート制御（固定間隔スロットリング）、リトライ、トークン自動リフレッシュ
- DB への保存は冪等（ON CONFLICT / DO UPDATE 等）で再実行可能
- ルックアヘッドバイアス対策：計算は target_date 時点の知見のみを利用
- ニュース収集での SSRF 対策・XML 攻撃対策（defusedxml）などセキュリティ考慮

---

## 主な機能一覧

- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー取得
  - レート制限・リトライ・トークンリフレッシュ対応
- ETL パイプライン
  - 差分更新、バックフィル、品質チェック（quality モジュール）
  - 日次 ETL 実行エントリポイント
- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution 層のテーブル群
- ニュース収集
  - RSS 取得、HTML/URL 前処理、記事IDの正規化（SHA-256）
  - raw_news・news_symbols への冪等保存、SSRF 防止、XML 安全化
- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days など
  - 夜間バッチ更新ジョブ（calendar_update_job）
- 特徴量計算・特徴量パイプライン（research 層）
  - Momentum / Volatility / Value のファクター計算
  - z-score 正規化ユーティリティ
- 特徴量合成（strategy.feature_engineering）
  - ユニバースフィルタ（最低株価・売買代金）、正規化、features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator）
  - ファクター + AI スコア統合 → final_score、BUY/SELL シグナル生成、SELL はエグジット条件判定
- 監査ログスキーマ（data.audit）: Signal → Order → Execution のトレーサビリティ設計

---

## 必要要件 / 依存パッケージ

ここに記載するのはソースコードから推定されるランタイム依存です。実際の setup.py / pyproject.toml を参照してください。

必須（最低限）:
- Python 3.10+（型ヒントに union の省略記法等を使用）
- duckdb
- defusedxml

その他（運用に合わせて）:
- requests 等の HTTP ライブラリは urllib を使用しているため不要（現実運用では好みに応じて追加）
- Slack 連携や実際の発注統合は別途パッケージや実装が必要

---

## 環境変数（設定）

kabusys は .env ファイルまたは環境変数から設定を読み込みます（モジュール: kabusys.config）。プロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動読み込みします。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須のもの・デフォルトを持つもの）：

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード（発注連携用）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack ボットトークン（通知等）
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

例（.env）:
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install "duckdb" "defusedxml"
   - （開発用）pip install -e .

   ※ pyproject.toml / requirements.txt があればそれに従ってください。

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成して必要なキーを記載するか、シェル環境へエクスポートしてください。

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで初期化を実行します（例は次節「使い方」に記載）。

---

## 使い方（主要ユースケース）

以下はライブラリ API の簡易例です。実際はログ設定や例外処理、運用フロー（スケジューラ/ジョブ管理）を組み合わせて使います。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を使用
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = init_schema(":memory:")
```

- 日次 ETL 実行（J-Quants から市場カレンダー・株価・財務を差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- マーケットカレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- ニュース収集ジョブ（RSS から raw_news に保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出に利用するコードの集合（例: all valid 4桁銘柄）
known_codes = {"7203", "6758", "9984", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- 特徴量構築（target_date の features テーブルを作成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 3, 1))
print("features upserted:", count)
```

- シグナル生成（features + ai_scores + positions を参照して signals を書き込む）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2025, 3, 1))
print("signals written:", total)
```

- 設定（settings）の利用例
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

注意点:
- ETL や特徴量構築は DuckDB 内の適切なテーブル（prices_daily, raw_financials 等）が存在することが前提です。初回は init_schema を実行してください。
- 自動的に .env を読み込む機能は kabusys.config モジュールで実装されています。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成

リポジトリの主要なファイル・モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py                     -- DuckDB スキーマ定義 / init_schema / get_connection
    - jquants_client.py             -- J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py             -- RSS ニュース収集 / 保存
    - calendar_management.py        -- カレンダー管理 / 営業日判定 / calendar_update_job
    - features.py                   -- zscore_normalize の再エクスポート
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - audit.py                      -- 監査ログ用 DDL / スキーマ（途中まで）
    - pipeline.py                   -- ETL 管理（既出）
  - research/
    - __init__.py
    - feature_exploration.py        -- IC / forward returns / factor summary
    - factor_research.py            -- momentum/value/volatility 等ファクター計算
  - strategy/
    - __init__.py
    - feature_engineering.py        -- features の合成・正規化・保存
    - signal_generator.py           -- final_score の計算と signals テーブルへの書き込み
  - execution/                      -- 発注・execution 層（プレースホルダ）
  - monitoring/                     -- 監視系モジュール（未記載 / プレースホルダ）

上記以外に、ドキュメント（DataPlatform.md, StrategyModel.md など）や設定例（.env.example）をプロジェクトルートに置くことが推奨されます。

---

## 運用上の注意 / 実装上の留意点

- 本リポジトリは「データ収集・分析・シグナル生成」レイヤまでの実装が中心で、ブローカー発注の具体的な統合は環境依存です。kabuステーション等の発注連携は別途実装を接続してください。
- DuckDB のファイルはバックアップ・管理を行ってください（単一ファイルに全データが格納されます）。
- J-Quants API のレート制限・認証トークンの管理に注意してください。トークンは環境変数で管理する想定です。
- RSS の取得では SSRF 防止や XML の安全なパースを行っていますが、運用する RSS ソース一覧は制限することをおすすめします。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 として .env の自動読み込みを抑制し、テスト用の設定をインメモリで注入してください。

---

## 貢献 / 拡張ポイント

- 発注エンジン（execution 層）と証券会社 API の接続実装
- AI スコア生成 / モデル学習パイプラインの追加
- 品質チェック（quality モジュール）の実装・拡張
- Grafana/Prometheus などを用いたモニタリング連携
- CI/CD による定期 ETL 実行、スケジューリング（Airflow / cron 等）

---

README で網羅した以外にも、各モジュールには詳細な docstring と設計コメントが含まれています。実際の導入時はまず init_schema → run_daily_etl → build_features → generate_signals の順に試してみるのが早い確認方法です。必要があれば、より詳しい使い方（例: CI, テスト、運用ガイド）を追加します。