# KabuSys

日本株向けの自動売買 / 研究プラットフォームのコアライブラリ集です。  
 DuckDB をデータ層に用い、リサーチ → 特徴量生成 → シグナル生成 → ポートフォリオ構築 → バックテスト の一連処理をモジュール化しています。

主な設計方針
- ルックアヘッドバイアスを避ける（target_date 時点のみ参照する設計）
- DuckDB を用いた分析・ETL（オンメモリ / 永続 DB の両対応）
- 発注や外部 API 呼び出しを含む箇所は分離してあり、バックテストは純粋なメモリシミュレータで再現可能
- 冪等性、エラーハンドリング、レート制限などの実装配慮あり

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数の読み込み（自動ロード、無効化オプションあり）
  - 必須変数の検査（`kabusys.config.settings`）

- データ取得・ETL
  - J-Quants API クライアント（ページネーション、トークン自動更新、レート制御、保存ユーティリティ）
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID生成）
  - DuckDB への保存ユーティリティ（raw_prices / raw_financials / market_calendar / raw_news 等）

- 研究（research）
  - ファクター計算：モメンタム / ボラティリティ / バリュー（prices_daily / raw_financials を利用）
  - 特徴量探索：将来リターン計算、IC（Spearman）計算、統計サマリー

- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターの正規化（Z スコア）・ユニバースフィルタ・features テーブルへの UPSERT

- シグナル生成（strategy.signal_generator）
  - features + ai_scores を統合して final_score を算出
  - Bear レジームで BUY を抑制、SELL（ストップロス・スコア低下）判定
  - signals テーブルへの冪等書き込み

- ポートフォリオ構築（portfolio）
  - 候補選定、等金額 / スコア加重配分、リスクベースのサイジング
  - セクター集中制限、レジーム乗数（資金乗数）
  - 単元株丸め・aggregate cap 調整

- バックテスト（backtest）
  - ポートフォリオシミュレータ（擬似約定、スリッページ・手数料モデル）
  - バックテストエンジン（signals → 発注 → 約定 → マーク・トゥ・マーケット → 次日シグナルのループ）
  - 評価指標（CAGR / Sharpe / Max Drawdown / 勝率 / Payoff Ratio）
  - CLI エントリ（python -m kabusys.backtest.run）

---

## 要件

- Python 3.10 以上（PEP 604 の union 型（`X | Y`）等を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
- （運用で使う場合）J-Quants API のリフレッシュトークン等の環境変数

README 内のサンプルでは requirements.txt を想定しています。実際のプロジェクトでは setup / pyproject に依存関係が定義される想定です。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <this-repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （あるいはプロジェクトに requirements.txt がある場合）
   - pip install -r requirements.txt

4. 環境変数の設定
   - プロジェクトルートに .env（および .env.local）を置くことができ、モジュール起動時に自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   例 `.env`（実際の値は適宜置き換えてください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. DuckDB スキーマ初期化
   - 本リポジトリ内の `kabusys.data.schema` モジュール（プロジェクト内に存在する想定）に `init_schema(path)` があり、これを使って DB を初期化します。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

---

## 使い方

### バックテスト CLI
リポジトリに含まれるバックテスト用エントリポイントを使う:
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db path/to/kabusys.duckdb
```
主なオプション:
- --start / --end: バックテスト期間（YYYY-MM-DD）
- --cash: 初期資金（円）
- --slippage / --commission: スリッページ・手数料率
- --allocation-method: equal | score | risk_based
- --max-positions, --max-utilization, --risk-pct など

実行後にバックテストの評価指標が標準出力に表示されます。

### Python API（例）

- DuckDB 接続を開いて特徴量を作成する:
```python
import duckdb
from datetime import date
from kabusys.strategy.feature_engineering import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 20))
print(f"features upserted: {n}")
conn.close()
```

- シグナル生成:
```python
from kabusys.strategy.signal_generator import generate_signals
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 20))
print(f"signals written: {count}")
conn.close()
```

- ニュース収集ジョブ実行:
```python
from kabusys.data.news_collector import run_news_collection
conn = duckdb.connect("data/kabusys.duckdb")
result = run_news_collection(conn, known_codes={"7203", "6758"})
print(result)  # {source_name: saved_count}
conn.close()
```

- J-Quants データ取得と保存:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
rows = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = save_daily_quotes(conn, rows)
print(f"saved prices: {saved}")
conn.close()
```

> 注意: 上記の一部関数は API トークンや DB スキーマの事前準備を必要とします。J-Quants API を呼ぶ際は `JQUANTS_REFRESH_TOKEN` を設定してください。

---

## 設定と動作上の注意点

- 自動 .env ロード:
  - ロード優先度は OS 環境 > .env.local > .env。
  - テスト時などに自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は `kabusys.config.Settings` で必須となっています。用途に応じて設定してください（バックテストのみ実行する場合は必須でない場合もありますが、モジュールが参照するとエラーになる箇所があります）。

- DuckDB スキーマ:
  - modules（feature, prices_daily, raw_financials, ai_scores, signals, positions, market_regime, stocks, market_calendar, raw_news etc.）のテーブルが必要です。`kabusys.data.schema.init_schema()` を使って初期化してください（スキーマ定義は別ファイルに定義されている想定）。

- レート制御・リトライ:
  - J-Quants クライアントは API レート制限（120 req/min）に対応する RateLimiter を実装し、401 の場合はトークン自動更新、408/429/5xx は指数バックオフ付きでリトライします。

---

## ディレクトリ構成（主要ファイル）

（パッケージルートが `src/` を使う構成として表示）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - jquants_client.py  — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py  — RSS ニュース収集・保存
    - (schema.py 等が存在する想定)
  - research/
    - factor_research.py  — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — IC / 将来リターン / 統計サマリー
  - strategy/
    - feature_engineering.py — features 作成
    - signal_generator.py — シグナル作成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・aggregate cap
    - risk_adjustment.py — セクター上限・レジーム乗数
  - backtest/
    - engine.py — バックテストループ（run_backtest）
    - simulator.py — 擬似約定・ポートフォリオ管理
    - metrics.py — 評価指標計算
    - run.py — CLI エントリ
    - clock.py — （将来用途）模擬時計
  - portfolio/__init__.py, research/__init__.py, strategy/__init__.py, backtest/__init__.py などの export 用モジュール

（実際のリポジトリでは他に data/schema.py、monitoring、execution、UI などのディレクトリやファイルが存在する想定です）

---

## 開発・貢献

- コード品質: ログ出力・入力検証・エラーハンドリングに配慮してあります。新機能追加や修正はユニットテストを追加してください。
- 自動ロードされる .env はテスト実行時に予期せぬ副作用を与えるため、CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することを推奨します。

---

この README は現状の主要モジュール群に基づいた概要と利用手順をまとめたものです。実運用や拡張を行う際は、各モジュール内の docstring（関数コメント）と想定されるスキーマ定義（kabusys.data.schema）を参照してください。疑問点や追加したいサンプルがあれば教えてください。