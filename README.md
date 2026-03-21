# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
DuckDB をデータ層に用い、J-Quants API／RSS ニュース等からデータを収集し、リサーチ → 特徴量生成 → シグナル生成 → 発注監査までを想定したモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐため「target_date 時点で利用可能なデータのみ」を扱う
- DuckDB 上で SQL と Python を組み合わせて高性能に処理
- 冪等性（idempotency）を重視した DB 保存処理
- 外部 API 呼び出しは再試行・レート制御・トークン自動リフレッシュに対応

---

## 機能一覧
- データ収集（J-Quants API）
  - 日足株価（OHLCV）、財務諸表、JPX カレンダーの取得（ページネーション対応／レート制御／リトライ）
- データ保存（DuckDB）
  - raw / processed / feature / execution 層のスキーマ定義と初期化
  - ON CONFLICT を用いた冪等保存
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックの実行（run_daily_etl）
- リサーチ（研究用）
  - モメンタム／ボラティリティ／バリュー等のファクター計算（prices_daily, raw_financials を参照）
  - 将来リターン計算、IC（Spearman）やファクター統計の計算
- 特徴量エンジニアリング
  - リサーチで算出した raw factor の Z スコア正規化、ユニバースフィルタ適用、features テーブルへの UPSERT（build_features）
- シグナル生成
  - features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを生成（generate_signals）
  - Bear レジーム判定、エグジット（ストップロス等）判定
- ニュース収集
  - RSS 取得、前処理、安全対策（SSRF 対応・XML 攻撃防御）、raw_news 保存、銘柄抽出と紐付け
- マーケットカレンダー管理
  - 営業日判定、next/prev trading day、夜間 calendar update ジョブ

---

## 前提（Prerequisites）
- Python 3.10 以上（型の | 演算子等を使用）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）
- J-Quants / Slack 等のアクセストークン（環境変数）

推奨：仮想環境（venv / conda）で動かすこと。

---

## セットアップ手順（例）
1. 仮想環境作成、アクティブ化
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # macOS/Linux
   .venv\Scripts\activate       # Windows
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements.txt があればそれを使ってください。最低限の例）
   ```bash
   pip install duckdb defusedxml
   ```

3. リポジトリを配置（開発時）
   - パッケージを editable install する場合：
     ```bash
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（module: kabusys.config）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

例（.env の最小例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化（DuckDB スキーマ）
DuckDB のスキーマを初期化して接続を得るには以下を実行します。

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

init_schema は必要な全テーブルとインデックスを作成します（冪等）。

---

## 使い方（主要な例）

- 日次 ETL（株価・財務・カレンダーの差分取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（features テーブルに保存）
```python
from datetime import date
from kabusys.strategy import build_features

# conn は init_schema で得た DuckDB 接続
count = build_features(conn, target_date=date.today())
print(f"{count} 銘柄の features を作成しました")
```

- シグナル生成（signals テーブルに保存）
```python
from datetime import date
from kabusys.strategy import generate_signals

total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"生成されたシグナル数: {total_signals}")
```

- ニュース収集（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄セットを用意
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"market_calendar に保存したレコード数: {saved}")
```

---

## 環境／設定についての補足
- 環境変数は kabusys.config.Settings からアクセスできます（例: settings.jquants_refresh_token）。
- 読み込み優先順位: OS 環境変数 > .env.local > .env。自動読み込みは .git または pyproject.toml の存在を基準にプロジェクトルートを探索して行います。
- LOG_LEVEL や KABUSYS_ENV（development / paper_trading / live）により挙動が変わります（is_live などのフラグを利用して安全な運用を行ってください）。

---

## ディレクトリ構成（抜粋）
以下は本リポジトリの主要ファイル／モジュール構成です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存関数）
    - schema.py                — DuckDB スキーマ定義・初期化
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - news_collector.py        — RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py   — market_calendar 管理・営業日判定
    - features.py              — data.stats の再エクスポート
    - audit.py                 — 発注監査ログスキーマ（注文→約定トレーサビリティ）
    - ...（quality 等が想定される）
  - research/
    - __init__.py
    - factor_research.py       — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py   — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py   — features 作成（build_features）
    - signal_generator.py      — シグナル生成（generate_signals）
  - execution/                 — 発注関連（空ファイル・拡張ポイント）
  - monitoring/                — 監視／運用系（拡張ポイント）

---

## 運用上の注意
- J-Quants API にはレート制限（120 req/min）があるため jquants_client は内部で制御します。大量のバックフィル時は時間がかかることがあります。
- 本コードベースは発注 API（ブローカー接続）とは分離されています。ライブ運用前に paper_trading 環境で十分に検証してください。
- 発注や資金管理を行う場合は execution / audit 層を適切に実装し、冪等キーや監査ログを必ず有効にしてください。
- センシティブなトークン類はリポジトリに含めず、Vault 等で安全に管理してください。

---

## 貢献・拡張
- research / strategy / data 層は独立性を保つ設計です。新しいファクター、シグナルロジック、外部データソースは既存 API に合わせて追加できます。
- テスト時は環境変数自動読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）してローカルで制御すると便利です。

---

README に書かれている API の一部はこのリポジトリ内のドキュメント（StrategyModel.md, DataPlatform.md 等）に依存する想定です。必要に応じてそれらの設計文書も参照してください。