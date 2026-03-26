# KabuSys

日本株向けの自動売買 / バックテスト / データ収集フレームワークです。  
特徴量計算、シグナル生成、ポートフォリオ構築、バックテストシミュレータ、J-Quants / RSS データ収集などの主要コンポーネントを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 環境変数（設定）
- 使い方（主要コマンド / API）
- ディレクトリ構成（主要ファイルの説明）
- 開発メモ・注意点

---

## プロジェクト概要

KabuSys は以下のフェーズを分離して実装した、研究→本番へつなげやすい設計の自動売買システムです。

- データ収集（J-Quants API、RSS ニュース）
- 研究（ファクター計算・探索）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（ファクター＋AI スコア統合、売買シグナル作成）
- ポートフォリオ構築（候補選定、重み計算、サイジング、セクター制限）
- バックテスト（擬似約定、スナップショット、メトリクス算出）

設計上「DB（DuckDB）上のデータを読み取って処理」するモジュールと、「DBに依存しない純粋関数群」を概ね分離しているため、単体テストや研究用途にも使いやすくなっています。

---

## 主な機能

- J-Quants API クライアント（ページネーション、トークン自動リフレッシュ、レートリミット、リトライ）
- RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID生成、DB保存）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）
- 特徴量作成（Z スコア正規化、ユニバースフィルタ、features テーブルへの UPSERT）
- シグナル生成（final_score 計算、Bear フィルタ、BUY/SELL の判定、signals テーブルへの書込）
- ポートフォリオ構築（候補選定、等配分/スコア加重/リスクベースのサイジング、セクター上限適用）
- バックテストエンジン（擬似約定、スリッページ・手数料モデル、履歴記録、メトリクス算出、CLI）
- 研究用ユーティリティ（Forward Return / IC 計算 / 統計サマリー）

---

## 必要条件

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml
  - （その他の依存は実装状況に応じて追加してください）

パッケージはプロジェクトルートに requirements.txt があればそれで導入してください。無ければ最低限次を入れてください:

pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは: pip install duckdb defusedxml
4. 環境変数を準備
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を用意してください。
   - `.env.example` を参考に必要な値を設定します（ファイルがない場合は下記「環境変数」を参照して手動で設定）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。
5. DuckDB スキーマ初期化
   - 実行に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks, positions, raw_prices, raw_financials, raw_news, news_symbols など）を持つ DuckDB ファイルを準備してください。
   - 本リポジトリ内に schema 初期化スクリプト（kabusys.data.schema.init_schema）がある想定です。init_schema() を使って DB を開いてください。

---

## 環境変数（Settings）

kabusys.config.Settings が参照する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL

必須変数が未設定の場合、Settings のプロパティアクセスで ValueError が発生します。

---

## 使い方

以下は主要な操作の代表例です。

1) バックテスト（CLI）

DuckDB ファイルが用意できていることを前提に、次のコマンドでバックテストを実行できます。

python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --db path/to/kabusys.duckdb

主なオプション:
- --start / --end: バックテスト期間（YYYY-MM-DD）
- --cash: 初期資金（JPY）
- --slippage / --commission: スリッページ・手数料率
- --allocation-method: equal | score | risk_based
- --max-positions: 最大保有銘柄数
- --lot-size: 単元株数（日本株は通常 100）

2) 特徴量作成（プログラム呼び出し）

Python API を使って features を構築できます。例:

from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
conn.close()
print(f"processed {n} symbols")

3) シグナル生成（プログラム呼び出し）

from datetime import date
import duckdb
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
conn.close()
print(f"generated {count} signals")

4) ニュース収集ジョブ（RSS）

from kabusys.data.jquants_client import get_id_token, fetch_market_calendar  # 例
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
conn.close()
print(res)

5) バックテストエンジンをプログラムから呼び出す

from datetime import date
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema

conn = init_schema("path/to/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2022,1,1), end_date=date(2022,12,31))
conn.close()
# result.history, result.trades, result.metrics を参照

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
  - パッケージエクスポート

- config.py
  - .env 読み込み、自動ロードロジック、Settings クラス（環境変数管理）

- data/
  - jquants_client.py
    - J-Quants API クライアント（認証、ページング、保存ユーティリティ）
  - news_collector.py
    - RSS 収集、前処理、raw_news / news_symbols 保存
  - （schema, calendar_management 等のモジュールが想定）

- research/
  - factor_research.py
    - モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py
    - Forward returns、IC 計算、統計サマリー

- strategy/
  - feature_engineering.py
    - features の正規化・UPSERT
  - signal_generator.py
    - final_score 計算、BUY/SELL 判定、signals 書込

- portfolio/
  - portfolio_builder.py
    - 候補選定・重み付け（等配分、スコア加重）
  - position_sizing.py
    - 株数算出（risk_based / equal / score）、aggregate cap、単元丸め
  - risk_adjustment.py
    - セクター上限適用、レジーム乗数

- backtest/
  - engine.py
    - バックテストループ、DB をコピーしてインメモリで実行するユーティリティ
  - simulator.py
    - 擬似約定、ポートフォリオ状態管理、mark_to_market
  - metrics.py
    - CAGR / Sharpe / MaxDD / Win rate / Payoff ratio
  - run.py
    - CLI エントリポイント

- monitoring/, execution/, など（パッケージ公開名に含まれるが詳細は実装に依存）

---

## 開発メモ・注意点

- Python の型ヒントで |（Union リテラル）を多用しているため Python 3.10 以上を想定しています。
- config._find_project_root はパッケージ配置後でも .env をプロジェクトルートから探すため、実行ディレクトリに依存しません。ただしパッケージ配布後は自動ロードがスキップされる場合がある点に注意してください。
- J-Quants API 呼び出しはレート制限・リトライ・トークン更新を内包しているため、ETL バッチ処理で利用してください。バックテストの内部ループから直接 API を叩かないように設計されています（Look-ahead bias 防止）。
- DuckDB のスキーマ（テーブル定義）は本リポジトリにある schema 初期化ロジックを参照してください。バックテストは features / prices_daily / ai_scores / market_regime / market_calendar 等が揃っていることを前提とします。
- news_collector は RSS の XML をパースするため defusedxml を利用しており、SSRF / XML Bomb に配慮した実装になっています。

---

必要に応じて README を拡張します。CI / テスト手順、具体的なスキーマ定義やサンプル .env.example を追加したい場合はその旨を教えてください。