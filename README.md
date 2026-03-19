# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群。  
DuckDB を用いたデータ層、J-Quants API クライアント、特徴量生成・シグナル生成、ニュース収集、ETL パイプライン、マーケットカレンダー管理、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL
- 生データ → 整形データ → 戦略向け特徴量 → シグナル生成 のパイプライン
- RSS ベースのニュース収集と銘柄コード紐付け
- マーケットカレンダー管理（営業日判定、次/前営業日取得等）
- 発注・約定・ポジション等の監査テーブル定義（監査用途）
- 研究（research）用のファクター計算 / ファクター探索ユーティリティ

設計方針として、ルックアヘッドバイアスを避けるために target_date 時点のみのデータを使用すること、DB 書き込みは冪等（ON CONFLICT）で行うこと、外部 API 呼び出しは明示的に分離すること等が採用されています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
  - raw_prices / raw_financials / market_calendar などへの冪等保存
- ETL
  - 差分取得（最終取得日を参照）・バックフィル対応
  - 日次 ETL 実行（run_daily_etl）
  - 品質チェック（quality モジュールと連携）
- 特徴量生成（strategy.feature_engineering）
  - モメンタム・ボラティリティ・バリュー等のファクター取得
  - ユニバースフィルタ（最低株価・平均売買代金）
  - Z スコア正規化、±3 でクリップして `features` テーブルに UPSERT
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算
  - Bear レジームの抑制、BUY/SELL のルール実装（閾値・ストップロス等）
  - signals テーブルへの日付単位置換（冪等）
- ニュース収集（data.news_collector）
  - RSS フィード取得（SSRF対策、gzip/サイズ/トラッキング除去）
  - raw_news 保存、記事IDは正規化 URL の SHA-256（先頭32文字）
  - テキスト前処理、銘柄コード抽出・news_symbols 保存
- マーケットカレンダー管理（data.calendar_management）
  - カレンダー差分取得・更新、営業日判定と next/prev_trading_day 等
- スキーマ初期化（data.schema）
  - DuckDB の全テーブル定義とインデックスを作成する init_schema()

---

## 要件 (推奨)

- Python 3.10+
- 主な依存（例）
  - duckdb
  - defusedxml
- その他: ネットワークアクセス (J-Quants, RSS)

※ 実際の setup.py / pyproject.toml に記載の依存を確認してください。

---

## セットアップ手順

1. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   # またはプロジェクトルートで
   pip install -e .
   ```

3. 環境変数の準備
   プロジェクトルートの `.env` または `.env.local` に必要な環境変数を設定してください。自動ロード順は以下の通りです（プロジェクトルートは .git もしくは pyproject.toml を基準に探索）:
   - OS 環境変数
   - .env.local
   - .env

   自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack BOT トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: sqlite（監視用）パス（省略時: data/monitoring.db）
   - KABUSYS_ENV: development|paper_trading|live（省略時: development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（省略時: INFO）

---

## 使い方（簡単な例）

以下は主要な操作のサンプルです。各モジュールは duckdb の接続オブジェクトを受け取る設計です。

1. スキーマ初期化（DuckDB ファイル作成）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # or init_schema(":memory:")
   ```

2. 日次 ETL 実行（J-Quants から差分取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量作成（features テーブルへ）
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   count = build_features(conn, target_date=date(2024, 1, 1))
   print(f"features upserted: {count}")
   ```

4. シグナル生成（signals テーブルへ）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total = generate_signals(conn, target_date=date(2024, 1, 1))
   print(f"signals written: {total}")
   ```

5. ニュース収集（RSS を取得して保存、銘柄紐付け）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   # known_codes は銘柄コードセット（例: {'7203', '6758', ...}）
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

6. J-Quants API クライアントを直接使う（トークン取得・データ取得）
   ```python
   from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes

   id_token = get_id_token()  # settings.jquants_refresh_token を使う
   records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = save_daily_quotes(conn, records)
   ```

7. カレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job

   saved = calendar_update_job(conn)
   print(f"market_calendar saved: {saved}")
   ```

---

## 環境変数の動作メモ

- .env のパースはシェル形式の一般的な表記に対応します（export で始まる行のサポート、クォート内のエスケープ、行内コメント処理 等）。
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動読み込みをスキップします（テスト用途など）。
- 必須変数を参照したときに未設定であれば ValueError を送出します（Settings クラスのプロパティが _require を通して参照します）。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 配下に配置されています。主なファイル・モジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                                  # 環境変数・設定読み込み
  - data/
    - __init__.py
    - jquants_client.py                         # J-Quants API クライアント（取得・保存）
    - news_collector.py                         # RSS ニュース収集
    - schema.py                                 # DuckDB スキーマ定義・init_schema
    - stats.py                                  # zscore_normalize 等の統計ユーティリティ
    - pipeline.py                               # ETL パイプライン（run_daily_etl 等）
    - features.py                               # data 層の特徴量ユーティリティ再エクスポート
    - calendar_management.py                    # カレンダー管理（営業日判定等）
    - audit.py                                  # 監査ログ向けスキーマ
    - (その他 monitoring / execution 用モジュール など)
  - research/
    - __init__.py
    - factor_research.py                         # ファクター計算（momentum/volatility/value）
    - feature_exploration.py                     # 将来リターン / IC / サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py                     # features 作成ロジック
    - signal_generator.py                        # シグナル生成ロジック
  - execution/                                   # 発注・実行関連の骨組み（空パッケージ等）
  - monitoring/                                  # 監視・アラート関係（別途実装）

各モジュールには docstring と設計ノートが豊富に書かれているため、内部の挙動やアルゴリズム仕様（例: StrategyModel.md / DataPlatform.md を参照する形の実装方針）を参照できます。

---

## 開発・貢献

- コードは型ヒント・ログ出力を多用しています。ユニットテストの追加、品質チェックの拡充を歓迎します。
- 環境依存部分（外部 API 呼び出しやネットワーク）はモック可能な設計です。テスト時は環境変数やモジュール関数を差し替えてください。
- 自動ロードされる `.env` の取り扱いには注意してください。テスト実行時に意図せぬ環境変数が混入しないよう KABUSYS_DISABLE_AUTO_ENV_LOAD を利用することを推奨します。

---

## トラブルシューティング

- settings 参照時に未設定エラーが出る場合は `.env` の内容と OS 環境変数を確認してください。必須変数は JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID です。
- DuckDB の初期化でディレクトリ作成エラーが出る場合は `DUCKDB_PATH` の親ディレクトリの権限を確認してください。
- J-Quants API 呼び出しで 401 が返る場合、refresh token が期限切れ／誤りの可能性があります。get_id_token の挙動を確認してください。

---

必要であれば README にサンプル .env.example、詳細な API 参照（関数一覧と引数の説明）、あるいは運用手順（cron / Airflow での ETL スケジューリング例）を追記します。どの情報を優先して追加しますか？