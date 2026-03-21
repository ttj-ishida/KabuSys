# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）

本リポジトリは、日本株のデータ取得・ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、監査ログ等を含む自動売買プラットフォームの主要コンポーネント群を提供します。モジュールは DuckDB によるローカル DB を中心に設計され、J-Quants API や RSS をデータソースとして扱います。

---

## 主要機能

- J-Quants API クライアント（レートリミット・自動トークンリフレッシュ・再試行ロジック付き）
  - 株価日足、財務データ、マーケットカレンダーの取得・保存
- ETL パイプライン（差分取得・バックフィル・品質チェック統合）
  - 日次 ETL の実行（run_daily_etl）
- DuckDB スキーマ定義と初期化（冪等）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（クロスセクション Z スコア正規化・ユニバースフィルタ）
- シグナル生成（各コンポーネントスコアの統合、BUY/SELL 判定、冪等な signals 保存）
- ニュース収集 (RSS) と記事→銘柄紐付け、raw_news 保存
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 汎用統計ユーティリティ（zscore_normalize、rank、IC 計算 等）

---

## 必要条件

- Python 3.10+
- 主要依存（プロジェクトに合わせて pip 等でインストールしてください）
  - duckdb
  - defusedxml
  - （標準ライブラリで実装している箇所が多いため最小依存は比較的少なめです）

（実際のプロジェクト配布では requirements.txt / pyproject.toml を参照してください）

---

## 環境変数 / 設定

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要となる環境変数（Settings が要求するもの）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

必須環境変数未設定時には Settings のプロパティアクセスで ValueError が送出されます。

---

## セットアップ手順（開発環境向け）

1. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください）

3. リポジトリを編集可能インストール（任意）
   ```
   pip install -e .
   ```

4. `.env` を作成（`.env.example` を参考にする想定）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 基本的な使い方（Python API）

ここでは代表的なワークフローを示します。すべて DuckDB の接続を渡して実行します。

1) DB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から株価・財務・カレンダーを差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量生成（features テーブルを構築）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

4) シグナル生成（signals テーブルに BUY/SELL を保存）
```python
from datetime import date
from kabusys.strategy import generate_signals

total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals written:", total)
```

5) RSS ニュース収集ジョブ（既知コードセットを渡して銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9432"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

---

## 運用モードについて

Settings.env により環境を切替可能です:
- development: 開発用
- paper_trading: ペーパー取引モード（発注抑制・サンドボックス等）
- live: 実口座（本番）モード（注意して使用）

Settings クラスは `is_live`, `is_paper`, `is_dev` プロパティを提供します。

---

## ログ / エラーハンドリング

- 各モジュールは logging を利用しています。環境変数 `LOG_LEVEL` で出力レベルを制御してください。
- ETL やジョブは個々のステップでエラーハンドリングを行い、可能な限り処理継続を試みる設計です。run_daily_etl は処理結果に errors / quality_issues の情報を返します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント・保存処理
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — data.stats の再エクスポート
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログ DDL
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py — ファクター統合・正規化 → features テーブル
    - signal_generator.py    — final_score 計算、BUY/SELL 判定 → signals テーブル
  - execution/
    - __init__.py            — 発注 / broker 連携はここに格納（未実装の部分あり）
  - monitoring/              — 監視・アラート用モジュール（場所確保）

---

## 開発上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス防止: target_date 時点のデータのみを使用する方針が各モジュールで守られています。
- 冪等性: DB への INSERT は可能な限り ON CONFLICT を利用して重複を防ぎます。
- API 呼び出しの堅牢性: レート制限・再試行・トークン自動リフレッシュ等を実装。
- セキュリティ: RSS の SSRF 対策、defusedxml による XML パース、安全な URL 正規化等を実装。
- DuckDB をデータ層に採用し、ローカルで高速な分析と永続化を両立します。

---

## よくある運用シーケンス（例）

1. 初期 DB 作成: init_schema()
2. 日次（夜間）ETL 実行: run_daily_etl()
3. 特色量更新: build_features()
4. シグナル生成: generate_signals()
5. 発注・約定処理（execution 層） → 監査ログ保存（audit）
6. ニュース収集ジョブを定期実行: run_news_collection()
7. モニタリング・アラート（Slack 通知等）

---

## 貢献 / 拡張

- execution（ブローカ連携）や監視・モニタリングの実装拡張が想定されています。
- 新しいファクターや AI スコア統合は strategy / research 層に追加できます。
- 設定項目やスキーマ変更を行う場合は schema.py / DataSchema.md に整合させてください。

---

この README はコードベースの公開 API と設計意図の要約です。詳細な設計・仕様はソース内の docstring（例: StrategyModel.md、DataPlatform.md を参照する旨の注釈）や各モジュールのコメントを参照してください。質問や追加の README 内容（運用例、CI 設定、デプロイ手順など）が必要であればお知らせください。