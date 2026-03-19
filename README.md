# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。J-Quants から市場データを取得して DuckDB に格納し、研究用ファクター計算・特徴量作成・シグナル生成・ニュース収集・カレンダー管理などを提供します。発注／実行層は分離されており、戦略ロジックは発注 API に直接依存しない設計です。

主な設計方針：
- ルックアヘッドバイアスを防ぐため「target_date 時点のデータのみ」を利用
- DuckDB をデータレイヤに採用し、Idempotent な保存（ON CONFLICT）を行う
- ネットワーク操作に対する堅牢なエラーハンドリング（リトライ・レート制限）
- RSS ニュース収集における SSRF / XML 攻撃対策

---

## 特徴（機能一覧）

- データ取得・ETL
  - J-Quants API クライアント（株価日足 / 財務 / マーケットカレンダー）
  - 差分更新とバックフィル対応の ETL パイプライン（run_daily_etl）
  - DuckDB スキーマ定義と初期化（init_schema）
- データ処理 / 統計
  - クロスセクション Z スコア正規化ユーティリティ（zscore_normalize）
  - 将来リターン計算 / IC 計算等の研究用ユーティリティ
- ファクター・特徴量
  - Momentum / Volatility / Value 等のファクター計算（research）
  - 特徴量正規化と features テーブルへの書き込み（strategy.build_features）
- シグナル生成
  - 正規化済みファクター + AI スコアを統合して final_score を算出
  - BUY / SELL シグナル生成（売りはストップロスやスコア低下で判断）
  - signals テーブルへ冪等的に書き込み（generate_signals）
- ニュース収集
  - RSS フィードからの収集・記事正規化・銘柄抽出・DB 保存（news_collector）
  - SSRF 対策・gzip/サイズ制限・XML 保護
- マーケットカレンダー管理
  - JPX カレンダーの差分更新 / 営業日判定ユーティリティ
- 監査 / 実行レイヤ用スキーマ
  - signal_events / order_requests / executions 等の監査テーブル

---

## 動作環境・依存

- Python 3.10 以上（Union 型 `X | None` を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- その他：標準ライブラリ中心で実装されていますが、J-Quants API 利用時はネットワークアクセスが必要です。

インストール例（仮）:
```bash
python -m pip install duckdb defusedxml
# またはプロジェクトに setup があれば: pip install -e .
```

---

## 環境変数（設定）

本プロジェクトは .env（プロジェクトルート）および .env.local を自動読み込みします（優先度: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（主にテスト用）。

主に使用する環境変数（.env 例）:
- JQUANTS_REFRESH_TOKEN=<あなたの J-Quants リフレッシュトークン>  (必須)
- KABU_API_PASSWORD=<kabuステーション API パスワード> (必須)
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  (省略可、デフォルトあり)
- SLACK_BOT_TOKEN=<Slack Bot Token> (必須)
- SLACK_CHANNEL_ID=<Slack Channel ID> (必須)
- DUCKDB_PATH=data/kabusys.duckdb  (省略時デフォルト)
- SQLITE_PATH=data/monitoring.db  (省略時デフォルト)
- KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
- LOG_LEVEL=INFO|DEBUG|...  (デフォルト: INFO)

.env の自動ロードは、パッケージ内の logic により .git または pyproject.toml のあるディレクトリをプロジェクトルートとして探索して行われます。

---

## セットアップ手順

1. リポジトリをクローン / ソース配置
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 必要な環境変数を .env に設定（プロジェクトルート）
   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=zzzz
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```
5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # または init_schema("data/kabusys.duckdb")
     ```
   - インメモリで試す場合は init_schema(":memory:")

---

## 使い方（主要ワークフロー例）

以下は典型的なワークフローのコード例です。各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

1) 日次 ETL（市場カレンダー・株価・財務データ取得・品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # デフォルトは今日を対象
print(result.to_dict())
```

2) 特徴量作成（features テーブルへの書き込み）
```python
from kabusys.strategy import build_features
from datetime import date

# conn: DuckDB 接続（init_schema または get_connection）
count = build_features(conn, date(2026, 3, 1))
print(f"upserted features: {count}")
```

3) シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
from datetime import date

n_signals = generate_signals(conn, date(2026, 3, 1), threshold=0.6)
print(f"written signals: {n_signals}")
```

4) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使う有効な銘柄コード集合（例: set(["7203", "6758", ...])）
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # ソースごとの新規保存数
```

5) カレンダー夜間ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved calendar records: {saved}")
```

6) 研究用ユーティリティ（将来リターン / IC 等）
```python
from kabusys.research import calc_forward_returns, calc_ic, calc_momentum

fwd = calc_forward_returns(conn, date(2026,3,1))
mom = calc_momentum(conn, date(2026,3,1))
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

---

## 注意点 / 運用メモ

- J-Quants API のレート制限（デフォルト 120 req/min）に従うよう RateLimiter が実装されています。
- HTTP エラー（408/429/5xx）に対する指数バックオフと最大リトライ回数が実装されています。401 は自動でリフレッシュトークンを使って再取得します。
- News Collector は RSS フィード取得時に SSRF や XML 攻撃対策、レスポンスサイズ制限を行います。
- features / signals 等のテーブル更新は「日付単位の置換（DELETE→INSERT）」で冪等性を担保しています。
- テスト等で自動 .env ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV を `live` にすると is_live フラグが有効になります。運用時は設定に注意してください。

---

## ディレクトリ構成（概要）

リポジトリ内の主なファイルとモジュール:

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（fetch/save）
    - news_collector.py              -- RSS ニュース収集・保存
    - schema.py                      -- DuckDB スキーマ定義・初期化
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - stats.py                       -- 統計ユーティリティ（zscore_normalize）
    - features.py                    -- features 用再エクスポート
    - calendar_management.py         -- カレンダー更新 / 営業日ユーティリティ
    - audit.py                        -- 監査ログ DDL
    - ...（その他実装ファイル）
  - research/
    - __init__.py
    - factor_research.py             -- Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py         -- 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         -- features の正規化・UPSERT
    - signal_generator.py            -- final_score 計算・BUY/SELL シグナル生成
  - execution/                        -- 発注 / execution 層 (空ファイルあり)
  - monitoring/                       -- 監視 / Slack 通知等（実装想定）

上記は主要モジュールの抜粋です。詳細はソースコード内の docstring を参照してください。

---

## 貢献 / 拡張案

- 発注層（execution）と証券会社 API の統合（kabuステーション / 各ブローカー）
- AI スコア生成パイプラインの統合（ai_scores の生成）
- モニタリング / Slack 通知の実装（monitoring）
- テスト（単体テスト・統合テスト）の整備
- パフォーマンス監視と ETL の最適化（並列化など）

---

もし README に追記してほしい具体的な項目（例: CI/CD 手順、デプロイ方法、より具体的なコード例など）があれば教えてください。README に反映して更新します。