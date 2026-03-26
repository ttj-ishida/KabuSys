# KabuSys

日本株向けの自動売買・研究プラットフォーム（部分実装）です。  
ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集、J-Quants API クライアントなどのモジュールを含みます。

---

## プロジェクト概要

KabuSys は、以下のレイヤーを持つ日本株アルゴリズムトレーディング基盤を想定した Python パッケージです。

- データ取得／ETL（J-Quants クライアント、RSS ニュース収集）
- 研究（ファクター計算、特徴量探索）
- 戦略（特徴量正規化、シグナル生成）
- ポートフォリオ構築（候補選定、重み付け、サイジング、リスク調整）
- 実行・バックテスト（擬似約定シミュレータ、バックテストエンジン）
- 設定管理（.env 自動ロード、環境変数）

設計方針の一部：
- DuckDB を用いたオンディスク／インメモリ DB を前提にデータ操作を行う
- ルックアヘッドバイアス回避のため「target_date」時点のデータのみを使用
- 冪等性を考慮した DB 書き込み（ON CONFLICT 等）
- 外部 API 呼び出しはラッピングしてレート制御・リトライを実装

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価、財務、上場銘柄、マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事IDの生成）
  - DuckDB への保存ユーティリティ（raw_prices, raw_financials, market_calendar, ...）

- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター要約統計

- 特徴量・戦略（strategy）
  - features テーブルへの Z スコア正規化、クリッピング
  - features + AI スコアを統合した final_score 計算と BUY/SELL シグナル生成（generate_signals）

- ポートフォリオ（portfolio）
  - 候補選定（スコア順）、等金額/スコア重み、リスクベースのサイジング
  - セクター集中制限、レジーム乗数（bull/neutral/bear）

- バックテスト（backtest）
  - ポートフォリオシミュレータ（擬似約定、手数料・スリッページモデル）
  - run_backtest: 日次ループでシミュレーション実行、履歴・トレード・メトリクス出力
  - メトリクス計算（CAGR、Sharpe、Max Drawdown、勝率、Payoff）

- その他
  - 環境変数 / .env 自動ロード（プロジェクトルート検出）
  - CLI エントリポイント（バックテスト実行）
  - ニュース記事から銘柄コード抽出と銘柄紐付け

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（本コードは Python 3.10 の型記法（|）などを使用）
- DuckDB（Python パッケージ）、defusedxml など一部依存ライブラリが必要

基本的なインストール例:

1. リポジトリをクローン（ローカル開発時）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml があれば `pip install -e .` や `pip install -r requirements.txt` を利用してください）

4. 開発インストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動ロードされます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須の環境変数は下記「環境変数一覧」を参照してください。

---

## 環境変数一覧

config.Settings で参照される主な環境変数：

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

.example の内容を参考に `.env` を作成してください（.env.example はプロジェクトに含める想定）。

---

## 使い方

いくつかの典型的な利用例を示します。

1) バックテスト（CLI）
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db path/to/kabusys.duckdb
```
オプションでスリッページ、手数料、allocation-method（equal/score/risk_based）、lot-size 等を指定できます。DB は事前に prices_daily / features / ai_scores / market_regime / market_calendar などが用意されている必要があります。

2) Python API から呼び出す（特徴量作成 / シグナル生成 / バックテスト）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features, generate_signals
from kabusys.backtest import run_backtest

conn = duckdb.connect("data/kabusys.duckdb")
# 特徴量構築
build_features(conn, target_date=date(2024, 1, 10))
# シグナル生成
generate_signals(conn, target_date=date(2024, 1, 10))

# バックテスト実行（既存 DB を用いる）
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics.cagr, result.metrics.sharpe_ratio)
conn.close()
```

3) ニュース収集（RSS）を実行して DB に保存
```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# known_codes を渡すと記事内の4桁銘柄コード抽出→news_symbols 登録まで行う
result = run_news_collection(conn, known_codes={"7203","6758"})
print(result)
conn.close()
```

4) J-Quants データ取得例（高レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=..., date_to=...)
save_daily_quotes(conn, records)
```

注意:
- 多くの機能は DuckDB 上の特定テーブル（prices_daily, raw_prices, features, signals, positions, ai_scores, market_regime, stocks, market_calendar 等）を前提とします。`kabusys.data.schema.init_schema` でスキーマ初期化を行う想定です（init_schema の実装は別ファイルにあります）。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要モジュール（抜粋）です：

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数・.env 自動読み込み
  - data/
    - jquants_client.py                — J-Quants API クライアント（取得・保存）
    - news_collector.py                — RSS ニュース収集・保存
    - (schema.py, calendar_management.py などが別途存在する想定)
  - research/
    - factor_research.py               — モメンタム／ボラティリティ／バリュー等
    - feature_exploration.py           — IC, 将来リターン, 統計サマリー
  - strategy/
    - feature_engineering.py           — features 作成・正規化
    - signal_generator.py              — final_score 計算・signals 挿入
  - portfolio/
    - portfolio_builder.py             — 候補選定・重み計算
    - position_sizing.py               — 株数計算・丸め・aggregate cap
    - risk_adjustment.py               — セクター制限・レジーム乗数
  - backtest/
    - engine.py                        — バックテスト全体制御
    - simulator.py                     — 擬似約定・ポートフォリオ管理
    - metrics.py                       — バックテスト評価指標
    - run.py                           — CLI エントリポイント
    - clock.py                         — バックテスト用模擬時計（将来拡張）
  - execution/                          — 発注・実行層（骨組み）
  - portfolio/                          — パッケージエクスポート（__init__）

（実際のリポジトリには上記以外の補助モジュールや schema 定義が存在する想定です）

---

## 注意点 / 実運用での留意事項

- バックテスト用 DB を準備する際は「ルックアヘッドバイアス」に注意してください。データ取得日時（fetched_at）や prices の date を正しく取り扱うことが重要です。
- J-Quants API のレート制限やエラー取り扱いはクライアントで実装していますが、運用時は追加の監視・ロギングを推奨します。
- news_collector は外部ネットワークを扱うため SSRF 対策やレスポンスサイズ制限など防御処理を含んでいますが、運用環境のセキュリティ要件に応じた追加検討を行ってください。
- 実取引（live）を行う場合は、paper_trading フラグや設定、API 認証情報、SLACK 通知等を必ず確認してください。

---

## 開発・テスト

- 自動環境変数読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化できます（テスト時に便利）。
- 単体テスト・CI 用の設定や requirements.txt / pyproject.toml がある場合はそれに従ってください（本 README はソースコードの参照から生成しています）。

---

必要であれば、README にサンプル .env.example、DB スキーマ初期化手順、より詳細な CLI オプション説明（全オプション例）、および各モジュールの API リファレンスを追記します。どの部分を拡張しますか？