# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
データ取得（J-Quants）→ ETL → 特徴量生成 → シグナル生成 → バックテスト までをカバーするモジュール群を提供します。  
本リポジトリは DuckDB を中心に内部データ層を構成し、バックテスト用のシミュレータやニュース収集、ETL パイプライン等を備えています。

バージョン: 0.1.0

---

## 主な機能

- データ取得・保存
  - J-Quants API クライアント（株価（日足）・財務データ・取引カレンダー）
  - RSS ベースのニュース収集（前処理・記事ID正規化・銘柄抽出）
  - DuckDB への冪等保存（ON CONFLICT / INSERT...DO UPDATE 等を採用）
- ETL / データパイプライン
  - 差分更新・バックフィル対応の株価 ETL
  - 品質チェックフレームワークとの連携（欠損・スパイク検出等）
- 特徴量・リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - クロスセクションの Z スコア正規化（data.stats.zscore_normalize）
  - 将来リターン計算、IC（Information Coefficient）、ファクターの統計サマリ
- 戦略（Signal）
  - features と ai_scores を統合して final_score を算出、BUY / SELL シグナルを生成
  - Bear レジーム抑制・ストップロスなどのポリシーを実装
- バックテスト
  - モデルに基づく日次ループ型バックテスト（擬似約定・スリッページ・手数料モデル）
  - 結果メトリクス（CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio）
  - CLI 実行スクリプトを提供（python -m kabusys.backtest.run）
- ユーティリティ
  - DuckDB スキーマ初期化（init_schema）
  - 設定管理（環境変数 / .env 自動読み込み）

---

## 必要条件（推奨）

- Python 3.9+（型ヒントで | 型合成を使っているため 3.10 以上を推奨）
- duckdb
- defusedxml

※ 実際の運用では network/API 利用に応じた追加パッケージや要件がある場合があります。requirements.txt を用意している場合はそちらを参照してください。

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発時: pip install -e .
```

---

## 環境変数（重要）

settings（kabusys.config.Settings）が参照する主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知対象チャンネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — 有効: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すると .env 自動読み込みを無効化できます（テスト用）

プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD がセットされていないこと）。

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # その他開発依存があれば追加
   ```

4. 環境変数設定（.env をプロジェクトルートに作成）
   - 上記の例を参考に `.env` を用意してください。

5. DuckDB スキーマ初期化
   Python 実行例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   これにより必要なテーブルとインデックスが作成されます。

---

## 使い方（主要ワークフロー例）

以下は主要な処理の実行例です。関数はすべてコードベースの API として利用可能です。

1) データベース初期化（上記参照）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 株価 ETL（差分更新）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl

# conn は init_schema で取得した接続
fetched, saved = run_prices_etl(conn=conn, target_date=date.today())
print("fetched:", fetched, "saved:", saved)
```

3) 財務データ／カレンダーの ETL など（同様に pipeline 内の関数を利用）

4) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は既知の銘柄コードセット（抽出に使う）
results = run_news_collection(conn=conn, known_codes={"7203", "6758"})
print(results)
```

5) 特徴量生成（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn=conn, target_date=date(2024, 1, 10))
print("upserted features:", count)
```

6) シグナル生成（signals テーブルへの書き込み）
```python
from kabusys.strategy import generate_signals
from datetime import date

n = generate_signals(conn=conn, target_date=date(2024, 1, 10), threshold=0.6)
print("generated signals:", n)
```

7) バックテスト（CLI）
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db data/kabusys.duckdb \
  --cash 10000000
```

8) バックテスト（プログラムから）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn=conn, start_date=date(2022,1,1), end_date=date(2022,12,31))
print(result.metrics)
```

---

## よく使う API の概要

- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes — J-Quants から取得・保存
- kabusys.data.pipeline.run_prices_etl — 株価差分 ETL
- kabusys.data.news_collector.run_news_collection — RSS ニュース収集・保存
- kabusys.research.calc_momentum / calc_volatility / calc_value — ファクター計算
- kabusys.strategy.build_features — features テーブル生成
- kabusys.strategy.generate_signals — signals テーブル生成
- kabusys.backtest.run_backtest — バックテスト実行

---

## ディレクトリ構成

（主要ファイル・モジュールの抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント
    - news_collector.py              — RSS ニュース収集
    - schema.py                      — DuckDB スキーマ定義 / init_schema
    - stats.py                       — 統計ユーティリティ（Zスコア等）
    - pipeline.py                    — ETL パイプライン
  - research/
    - __init__.py
    - factor_research.py             — モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py         — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py         — features 作成（正規化・フィルタ）
    - signal_generator.py            — final_score 計算・シグナル生成
  - backtest/
    - __init__.py
    - engine.py                      — バックテスト主ループ
    - simulator.py                   — 擬似約定・ポートフォリオ管理
    - metrics.py                     — バックテスト指標計算
    - clock.py                       — 模擬時計（将来用）
    - run.py                         — CLI エントリポイント
  - execution/                       — 発注・実行関連（将来的拡張）
  - monitoring/                      — 監視・通知（実装置かれる想定）

この README で取り上げた以外にも、品質チェックモジュールや監視用 DB（SQLite）連携等、運用に必要な要素が含まれています。

---

## 開発上の注意点 / 設計ポリシー（抜粋）

- ルックアヘッドバイアス防止: 特徴量・シグナル生成は target_date 時点までの情報のみを利用する設計。
- 冪等性: DB への保存は可能な限り冪等（ON CONFLICT での更新や INSERT...DO NOTHING）で実装。
- エラーハンドリング: ETL/収集はソース単位で独立してエラー処理を行い、部分障害が全体停止にならないようにする。
- Rate limit / retry: J-Quants クライアントは固定間隔のスロットリングと指数バックオフ＋401 自動リフレッシュに対応。

---

## ライセンス / 貢献

（ここにライセンス・貢献方法を記載してください）

---

README に記載のない詳細な使い方や設計ドキュメント（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）がリポジトリ内にある想定です。実運用する場合はそれらの設計資料と合わせて確認してください。疑問点や追加で記載してほしい箇所があれば教えてください。