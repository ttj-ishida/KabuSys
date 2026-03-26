# KabuSys

日本株向けのアルゴリズム売買フレームワーク（研究・データ収集・シグナル生成・バックテストを含む）

概要
- KabuSys は日本株を対象とした自動売買/研究プラットフォームのコードベースです。
- データ収集（J-Quants、RSSニュース）、ファクター計算、特徴量作成、シグナル生成、ポートフォリオ構築、バックテストまでのワークフローを包含します。
- モジュールは出来るだけ純粋関数・メモリ内処理を心がけ、DuckDB を主要なローカルデータストアとして利用します。

主な機能一覧
- 設定管理
  - 環境変数 / .env ファイルの自動読み込み（プロジェクトルートの検出、上書き制御、無効化フラグ有）
  - 必須設定の明示的チェック
- データ取得・ETL
  - J-Quants API クライアント（ページネーション対応、リトライ、トークン自動リフレッシュ、レート制限）
  - RSS ニュース収集（SSRF/リダイレクト対策、トラッキング除去、記事ID生成、DB保存）
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / raw_news / market_calendar など）
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた SQL + Python 実装）
  - 将来リターン計算、IC（情報係数）や統計サマリー
- 特徴量エンジニアリング
  - 研究側で計算した生ファクターを正規化・クリップして features テーブルへ保存（ルックアヘッド防止）
- シグナル生成
  - features + ai_scores を統合して final_score を算出、BUY/SELL シグナルを作成（Bear レジーム抑制、エグジット条件）
- ポートフォリオ構築
  - 候補選定、等配分/スコア加重/リスクベースのサイジング、セクター集中制限、レジーム乗数
- バックテストフレームワーク
  - 擬似約定（スリッページ・手数料モデル）、日次マーク・トゥ・マーケット、トレード記録
  - メトリクス算出（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI 実行可能（python -m kabusys.backtest.run）
- ニュースと銘柄紐付け
  - RSS から記事取得、本文前処理、銘柄コード抽出（4桁コード）と news_symbols 保存

セットアップ手順（開発環境向け）
前提
- Python 3.10 以上（typing の新しい構文（|）を利用）
- DuckDB を利用するため `duckdb` パッケージが必要
- RSS パーサや安全対策のため `defusedxml` が必要

例（仮想環境を作る）
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# 必要パッケージの例
pip install duckdb defusedxml
# パッケージを編集可能インストールする場合（プロジェクトルートに pyproject.toml / setup.cfg がある想定）
pip install -e .
```

環境変数 / .env
- プロジェクトは起動時に自動的にプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env と .env.local を読み込みます（OS環境変数が優先）。
- 自動ロードを無効化するには環境変数をセットします:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主な必須環境変数
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
  - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
  - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- その他設定（任意・デフォルトあり）
  - KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化するフラグ
  - DUCKDB_PATH, SQLITE_PATH — DB ファイルパス（デフォルトを使用可）
- .env.example を参考に .env を作成してください（コード内でも未設定時に .env.example を参考にするよう案内しています）。

使い方（主要な実行例）
1) バックテスト（CLI）
- DB ファイル（DuckDB）に prices_daily, features, ai_scores, market_regime, market_calendar 等が準備されている必要があります。
- 実行例:
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db path/to/kabusys.duckdb \
  --cash 10000000 \
  --allocation-method risk_based
```
- CLI は結果メトリクス（CAGR、Sharpe、Max Drawdown 等）を標準出力に表示します。

2) プログラムからバックテストを呼ぶ
```python
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("path/to/kabusys.duckdb")
result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
# result.history, result.trades, result.metrics を利用
conn.close()
```

3) 特徴量構築 / シグナル生成（DB 接続が必要）
- DuckDB 接続を取得し、日付を指定して呼び出します。
```python
from kabusys.strategy import build_features, generate_signals
# conn は duckdb.DuckDBPyConnection
n_features = build_features(conn, target_date)
n_signals = generate_signals(conn, target_date)
```

4) データ収集（J-Quants）
- jquants_client の fetch/save 関数を組み合わせて ETL を行います（トークンは settings.jquants_refresh_token で取得）。
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=..., date_to=...)
saved = save_daily_quotes(conn, records)
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 銘柄コードセットを渡すと記事と銘柄の紐付けを実施
result_map = run_news_collection(conn, sources=None, known_codes=set_of_codes)
```

主な API ※関数名はコードベース参照
- kabusys.config.settings — 環境設定アクセス
- kabusys.data.jquants_client — fetch_*/save_* 系
- kabusys.data.news_collector — fetch_rss, save_raw_news, run_news_collection
- kabusys.research — calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary
- kabusys.strategy.build_features / generate_signals
- kabusys.portfolio — select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.backtest.run_backtest / CLI entry point

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 読み込み・Settings
  - data/
    - jquants_client.py      — J-Quants API クライアント（取得・保存関数）
    - news_collector.py      — RSS ニュース収集と DB 保存
    - (schema.py 等が別に存在している想定)
  - research/
    - factor_research.py     — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - feature_engineering.py — features の構築（正規化・UPSERT）
    - signal_generator.py    — final_score 計算と signals テーブル挿入
  - portfolio/
    - portfolio_builder.py   — 候補選定と重み計算
    - position_sizing.py     — 株数決定・aggregate cap
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py              — バックテストループと run_backtest
    - simulator.py           — 擬似約定・ポートフォリオ管理
    - metrics.py             — バックテスト評価指標
    - run.py                 — CLI エントリポイント
    - clock.py               — SimulatedClock（将来拡張用）
  - portfolio/ __init__.py、strategy/ __init__.py、research/ __init__.py 等で公開 API を管理

注意事項・運用上のポイント
- ルックアヘッドバイアス防止
  - features / signals 等は target_date 時点のデータのみを用いる設計になっています。バックテストや ETL は「いつそのデータが利用可能になったか（fetched_at）」を意識して運用してください。
- DB スキーマ
  - バックテストや各種処理は特定のテーブル構成を前提とします（prices_daily, raw_prices, raw_financials, features, ai_scores, signals, positions, market_regime, market_calendar, stocks, raw_news, news_symbols 等）。プロジェクトに同梱の schema 初期化関数（kabusys.data.schema.init_schema）を使ってスキーマを用意してください（本リポジトリに schema 実装がある場合）。
- 自動 .env 読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env と .env.local を読み込みます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。
- 依存パッケージ
  - 少なくとも duckdb, defusedxml が必要です。J-Quants やネットワーク処理を行うために標準ライブラリの urllib を使用しますが、運用では HTTP/ネットワークの安定性や認証情報管理にご注意ください。

貢献・拡張案（参考）
- stocks 毎に異なる lot_size をサポートする（現状は共通 lot_size）
- execution 層の実装（kabuステーション API を利用して実際の発注を行うモジュール）
- AI スコアリングの学習パイプライン、自動モデル更新フロー
- 単体テスト・統合テストの強化（ネットワーク依存部はモック化）

お問い合わせ
- このドキュメントはコード内の docstring を元に作成しています。実行時の詳細な挙動や追加オプションは該当モジュールの docstring / ログを参照してください。

以上。README の内容に追記したい点（例: 実際のインストール要件ファイルや schema の初期化方法、CI の手順など）があれば指示してください。