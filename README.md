# KabuSys

日本株向けの自動売買システム用ライブラリ（バックテスト・データパイプライン・特徴量/シグナル生成などのモジュール群）。

本リポジトリは、データ取得（J-Quants）、ニュース収集、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテストシミュレータなど、運用・研究のための主要機能を純粋関数／独立モジュールとして提供します。

---

## 特徴（機能一覧）

- 環境設定管理
  - .env / 環境変数から設定読み込み（自動読み込み／無効化オプションあり）
  - 必須設定は明示的に検証
- データ取得・保存
  - J-Quants API クライアント（ページネーション、リトライ、レート制限、トークン自動更新）
  - 日足（OHLCV）、財務データ、上場銘柄情報、マーケットカレンダーの取得・DuckDB への保存
- ニュース収集
  - RSS フィード収集、正規化、SSRF/サイズ/XML 攻撃対策、記事ID生成、銘柄抽出、DB 保存
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上で計算
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング
  - 研究で得た生ファクターの正規化・フィルタ・features テーブルへの冪等アップサート
- シグナル生成
  - features + ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存
  - Bear レジーム判定やエグジット（ストップロス等）判定を含む
- ポートフォリオ構築
  - 候補選定（スコア順）、等配分／スコア加重、リスクベース配分、セクター制限、レジーム乗数
  - 株数決定（単元丸め、aggregate cap、部分約定対応）
- バックテストフレームワーク
  - インメモリ DuckDB へデータコピーして安全にバックテストを実行
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）、日次スナップショット、トレード記録
  - バックテストメトリクス（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - CLI ランナー（python -m kabusys.backtest.run）
- モジュール化・テストしやすい設計
  - 多くの関数が純粋関数または DB 接続を受け取る形で実装（サイドエフェクトを限定）

---

## 前提（推奨環境）

- Python 3.10+
  - 型注釈で | ユニオンや typing の新構文を利用しています
- 主な依存パッケージ（少なくとも下記をインストールしてください）
  - duckdb
  - defusedxml
- 推奨：仮想環境（venv / pyenv / poetry 等）

インストール例（最小）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# あるいはプロジェクト配布パッケージがあれば pip install -e .
```

requirements.txt / pyproject.toml が提供されている場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # もしあれば
   # または最低限:
   pip install duckdb defusedxml
   ```

3. 環境変数の設定
   - 自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（優先順位: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
   - 必須環境変数（config.Settings 参照）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 省略可（デフォルトあり）
     - KABUS_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG, INFO, ...、デフォルト INFO）
   - 例（.env の例）:
     ```
     JQUANTS_REFRESH_TOKEN=*****
     KABU_API_PASSWORD=*****
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. データベーススキーマ初期化
   - 本プロジェクトは DuckDB を想定（data/schema.py に init_schema 関数が存在します）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ファイル作成・スキーマ初期化
     conn.close()
     ```
   - prices_daily / features / ai_scores / market_regime / market_calendar / stocks 等のテーブルが利用されます。ETL によりデータを投入してください（J-Quants からの取得など）。

---

## 使い方

以下は主要な利用例です。関数群は DB 接続（DuckDBPyConnection）を受け取るため、スクリプトやジョブとして組み込みやすくなっています。

1) バックテスト（CLI）
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb \
  --allocation-method risk_based \
  --lot-size 100
```
出力例: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades が表示されます。

2) バックテスト（プログラムから）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(
    conn=conn,
    start_date=date(2023, 1, 1),
    end_date=date(2023, 12, 31),
    initial_cash=10_000_000,
)
conn.close()

# 結果の参照
print(result.metrics.cagr, result.metrics.sharpe_ratio)
```

3) 特徴量作成
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"{n} 銘柄分の features を保存しました")
conn.close()
```

4) シグナル生成
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"{count} 件のシグナルを書き込みました")
conn.close()
```

5) J-Quants API を使ったデータ取得（例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"{saved} 件を保存しました")
conn.close()
```

6) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # など
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

---

## 自動環境変数読み込みの挙動

- パッケージ読み込み時に自動でプロジェクトルート（.git または pyproject.toml を探索）を探し、.env/.env.local を読み込みます。
- 優先順位:
  - OS 環境変数（最優先）
  - .env.local（存在する場合、既存の OS 環境を上書きしないが .env より優先）
  - .env
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 必須変数が不足している場合、Settings のプロパティアクセスで ValueError が発生します。

---

## ディレクトリ構成（概要）

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py — パッケージメタ（バージョン等）
  - config.py — 環境変数 / 設定管理（Settings）
  - data/
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - news_collector.py — RSS 取得・前処理・DB 保存
    - (schema.py, calendar_management.py, stats.py などが別ファイルとして想定)
  - research/
    - factor_research.py — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - strategy/
    - feature_engineering.py — features テーブル作成（正規化・フィルタ）
    - signal_generator.py — final_score 計算・BUY/SELL 生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・単元丸め・aggregate cap
    - risk_adjustment.py — セクター上限・レジーム乗数
  - backtest/
    - engine.py — バックテストループ（主エンジン）
    - simulator.py — ポートフォリオシミュレータ（約定・MTM）
    - metrics.py — バックテスト評価指標
    - run.py — CLI ラッパー
    - clock.py — 模擬時計（将来拡張用）
  - execution/ — 実際の発注／kabuAPI 統合用モジュール（空の __init__ として存在）
  - monitoring/ — 監視・メトリクス用（未詳細実装）

---

## 開発者向けメモ

- 多くの処理は DuckDB の SQL と Python を組み合わせて実行します。テーブルスキーマは data/schema.py を参照して下さい。
- 単体関数の実装はルックアヘッドバイアス回避のため target_date 時点のデータのみ参照する設計です（バックテストでの再現性確保）。
- 外部接続（API/ネットワーク）部分は相互に独立しており、ユニットテストではモックしやすい設計になっています（例: news_collector._urlopen をモック）。
- ロギングは各モジュールで logger を利用しています。LOG_LEVEL 環境変数で制御可能です。

---

## よくある質問 / トラブルシュート

- Q: .env が読み込まれない
  - A: プロジェクトルートの検出は __file__ を起点に行います。開発中に異なる作業ディレクトリから動かす場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、明示的に環境変数をエクスポートしてください。
- Q: DuckDB のテーブルが不足しているエラー
  - A: data/schema.py の init_schema を使ってスキーマを初期化した後、必要な ETL を実行してテーブルにデータを投入してください（J-Quants からの取得や CSV インポートなど）。
- Q: J-Quants の 401 が出る
  - A: jquants_client は 401 受信時にリフレッシュトークンを使って ID トークンを再取得して1回リトライします。環境変数 JQUANTS_REFRESH_TOKEN を確認してください。

---

必要であれば README に以下の追加項目を追記できます:
- テーブルスキーマ詳細（features, signals, positions, prices_daily など）
- テストの実行方法／CI 設定
- デプロイ・運用手順（paper/live 切替、Slack 通知）
- サンプル .env.example

ご希望があれば追記します。