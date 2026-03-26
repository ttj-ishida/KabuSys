# KabuSys

KabuSys は日本株向けの自動売買 / 研究フレームワークです。データ収集（J-Quants / RSS）、ファクター計算、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテストまでを一貫して扱えるモジュール群を提供します。

主な設計方針：
- DuckDB を中心としたデータモデル（look-ahead bias に配慮）
- バックテストはメモリ内シミュレータで再現性の高い処理
- API クライアントはレート制限・リトライ・トークン自動更新を備える
- ニュース収集は SSRF / XML 攻撃対策など安全面に配慮

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、上場銘柄、カレンダー）
  - RSS ニュース収集・前処理・記事保存・銘柄紐付け
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - ファクター探索（IC 計算、将来リターン計算、統計サマリー）
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング
  - ユニバースフィルタ、Z スコア正規化、features テーブルへの UPSERT
- シグナル生成
  - 特徴量 + AI スコア統合 → final_score 計算
  - Bear レジーム抑制、BUY / SELL シグナル生成、signals テーブルへの書込
- ポートフォリオ構築
  - 候補選定、等配分 / スコア加重、リスクベースのサイジング、セクター制限
- バックテスト
  - 取引ループ、約定シミュレーション（スリッページ・手数料）、ポートフォリオ履歴、評価指標計算（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio）
  - CLI 実行スクリプト（python -m kabusys.backtest.run）
- 実行レイヤー（execution）やモニタリング用の構成が準備済み（スケールや実口座対応は別途実装）

---

## 必要条件 / 依存関係

- Python 3.10+
- 必須ライブラリ（代表例）
  - duckdb
  - defusedxml
  - （標準ライブラリ外のものがある場合は pyproject.toml / requirements.txt を参照してください）

例（開発環境構築）:
```sh
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# もしパッケージとして管理している場合:
pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロード; テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数（Settings クラス参照）：
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API（kabuステーション）用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL

サンプル `.env`（プロジェクトルート）:
```ini
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（duckdb, defusedxml 等）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB スキーマを初期化（プロジェクトに schema 初期化ユーティリティがある前提）
   - 例: python スクリプトや migrate で tables を作成（`kabusys.data.schema.init_schema()` を参照）
6. データ取得・ETL を実行して prices_daily / raw_financials / stocks / market_calendar 等を投入

（注）本コードベースは schema 初期化や ETL の呼び出し点を参照する実装がありますが、実際のスキーマ定義・マイグレーションは別モジュール（kabusys.data.schema）を参照してください。

---

## 使い方

以下は代表的な利用例です。DuckDB の接続はプロジェクト内の schema ユーティリティを想定しています。

1) バックテスト（CLI）
```sh
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db path/to/kabusys.duckdb
```
オプション:
- --slippage, --commission, --max-position-pct, --allocation-method 等

2) Python からプログラム的にバックテスト呼び出し
```py
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("path/to/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
conn.close()

# 結果
print(result.metrics)
```

3) 特徴量構築（features テーブルへの書き込み）
```py
from datetime import date
import duckdb
from kabusys.strategy.feature_engineering import build_features
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,1,31))
print(f"{n} 銘柄を features に書き込みました")
conn.close()
```

4) シグナル生成
```py
from datetime import date
from kabusys.strategy.signal_generator import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,1,31))
print(f"{count} 件のシグナルを生成しました")
conn.close()
```

5) J-Quants データ取得例
```py
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, recs)
print(f"saved: {saved}")
conn.close()
```

6) RSS ニュース収集実行（run_news_collection）
```py
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # {source_name: 新規挿入数}
conn.close()
```

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイルと概要）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings）
  - data/
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - news_collector.py — RSS 取得・記事抽出・保存、銘柄抽出
    - (schema.py 等: DB スキーマ初期化用モジュールが別途存在)
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - feature_engineering.py — features 作成（正規化・フィルタ）
    - signal_generator.py — final_score 計算・BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算（リスク制御・丸め）
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - backtest/
    - engine.py — バックテストのメインループ（run_backtest）
    - simulator.py — 約定・ポートフォリオ状態の擬似シミュレーション
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント
    - clock.py — 将来用の模擬時計
  - portfolio/__init__.py, strategy/__init__.py, research/__init__.py, backtest/__init__.py 等エクスポート用モジュール
  - execution/ — 実運用・注文実行層（プレースホルダ）
  - monitoring/ — 監視用モジュール（プレースホルダ）

---

## 開発メモ / 注意点

- look-ahead bias に配慮した設計を優先しています。DuckDB のデータ取得は target_date 以前のデータのみを参照するよう実装されています。
- J-Quants API 呼び出しはレート制御とリトライを行います。401 時はトークン自動更新を試みます。
- RSS 収集では SSRF / XML 攻撃対策を実装（ホストのプライベート IP チェック、defusedxml、受信サイズ制限 等）。
- 自動で `.env` を読み込みますが、テスト時に不要な副作用を避けたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- 実運用（live）では手数料・約定・API レート等の現実的なパラメータチューニングが必要です。
- schema 初期化やマイグレーション、ETL ジョブのスケジューリングは別途用意することを想定しています。

---

## 参考 / 今後の拡張

- execution レイヤーの実装（kabu ステーション等への実送信）
- 銘柄別単元サイズ・取引制約への対応（lot_size マップ）
- 分足シミュレーション / リアルタイム監視ダッシュボード
- AI スコアの取得パイプライン統合（ai_scores テーブル連携）

---

README に記載のない内部 API については各モジュールのドキュメント文字列（docstring）を参照してください。README に不足している情報やサンプルを追加してほしい箇所があれば教えてください。