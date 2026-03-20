# KabuSys

日本株向けの自動売買基盤（KabuSys）の簡易 README。  
このリポジトリはデータ収集・ETL、特徴量生成、戦略シグナル生成、監査/実行レイヤを想定したモジュール群を含んでいます。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成される、日本株の自動売買プラットフォーム用ライブラリです。

- Data Layer: J-Quants API からのデータ取得、RSS ニュース収集、DuckDB スキーマ定義、ETL パイプライン
- Research Layer: ファクター計算・特徴量探索（ルックアヘッドバイアスに配慮）
- Strategy Layer: 正規化済み特徴量から戦略シグナル（BUY/SELL）を生成
- Execution / Monitoring: 発注・約定・ポジション・監査ログ管理のためのスキーマ／ユーティリティ（execution パッケージは発注実装のための拡張点）

設計上のポイント:
- DuckDB を内部データベースとして利用（ローカルファイル or in-memory）
- 冪等性（ON CONFLICT / upsert）を意識した保存処理
- API レート制御・リトライ・トークン自動更新を考慮した J-Quants クライアント
- ルックアヘッドバイアスを避けるため、target_date 時点の利用可能データのみで計算

---

## 主な機能一覧

- jquants_client: J-Quants API から日足・財務・カレンダーを取得（ページネーション、リトライ、レートリミット）
- news_collector: RSS からニュース収集・前処理・DB 保存（SSRF対策、gzip制限、トラッキングパラメータ除去、銘柄抽出）
- data.schema: DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
- data.pipeline: 差分 ETL（calendar / prices / financials）と品質チェック呼び出し／ETL 結果レポート
- research.factor_research: momentum / volatility / value 等のファクター計算
- research.feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy.feature_engineering: ファクター正規化・ユニバースフィルタ・features テーブルへの保存
- strategy.signal_generator: features + ai_scores を統合して final_score を計算、BUY/SELL シグナル生成・signals テーブル保存
- data.news_collector: RSS 取得→raw_news 保存→銘柄紐付けの統合ワークフロー

---

## 必要条件

- Python 3.9+（型アノテーションや一部の構文を想定）
- 必須 Python パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード 等）

（インストールはプロジェクトの requirements.txt / pyproject.toml に従ってください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリを取得
   - git clone ...
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - またはプロジェクトの pyproject.toml / requirements.txt を利用してインストール
4. パッケージを編集モードでインストール（任意）
   - pip install -e .
5. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

---

## 環境変数（主なもの）

このライブラリは Settings を経由して環境変数を参照します。主に以下を設定してください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注機能利用時）
- SLACK_BOT_TOKEN: Slack 通知利用時の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先のチャンネルID

オプション（デフォルト値あり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 等（デフォルト: data/monitoring.db）

注意: 自動ロードの優先順位は OS 環境変数 > .env.local > .env です。

---

## 使い方（主要ユースケース）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

1) DB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb を作成して接続
```

2) 日次 ETL（市場カレンダー・株価・財務の差分取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能（デフォルトは today）
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"total signals generated: {total}")
```

5) ニュース収集（RSS）と DB 保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes に有効な銘柄コードセットを渡すと銘柄紐付けが行われる
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

注意点:
- run_daily_etl は ETL の各ステップで発生したエラーを収集して結果オブジェクトに格納します。戻り値 ETLResult を確認して異常を検出してください。
- strategy と research の関数はルックアヘッドバイアスを避けるため target_date 時点のデータのみを参照します。

---

## ディレクトリ構成（主要ファイル）

以下はこのコードベースの主要構成（src/kabusys 以下）です。実際のリポジトリにはさらに補助モジュールやテスト等が含まれる可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py       -- RSS 収集・解析・保存
    - schema.py               -- DuckDB スキーマ定義と init_schema
    - pipeline.py             -- 日次 ETL / 差分 ETL
    - stats.py                -- zscore_normalize 等の統計ユーティリティ
    - features.py             -- data.stats の公開ラッパー
    - calendar_management.py  -- market calendar ヘルパ
    - audit.py                -- 監査ログ用スキーマ定義
  - research/
    - __init__.py
    - factor_research.py      -- momentum/volatility/value の算出
    - feature_exploration.py  -- 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py  -- features テーブル構築（正規化・フィルタ）
    - signal_generator.py     -- final_score 計算と signals 生成
  - execution/
    - __init__.py             -- 発注層の拡張ポイント
  - monitoring/               -- 監視・通知関連（パッケージ化準備）
    - (モジュールは実装に応じて追加)

---

## 補足・運用上の注意

- 環境（KABUSYS_ENV）により本番（live）・ペーパートレード（paper_trading）・開発（development）を切り替えられます。live 運用時は十分なテストと安全対策（ストップロス、発注冗長対策等）を行ってください。
- J-Quants API のレートリミット（120 req/min）や API 認証フローにより、データ取得は遅延が発生する可能性があります。jquants_client はレート制御とリトライを備えていますが運用設計で考慮してください。
- news_collector は外部RSSを扱うため SSRF・XML Bomb・大容量応答等の防御処理を実装していますが、追加のフィードを登録する際は信頼できるソースを選択してください。
- DuckDB のファイルパスはデフォルトで data/kabusys.duckdb。バックアップや権限管理・I/O 性能にも注意してください。

---

もし README に追記したい利用例（cron / Airflow / systemd の実行例や、Slack 通知フロー、kabu ステーション発注の接続フローなど）があれば、その用途に合わせてさらに章を追加します。必要な情報を教えてください。