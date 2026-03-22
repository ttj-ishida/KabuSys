# KabuSys

日本株向けの自動売買 / データ収集・研究フレームワーク (KabuSys)

このリポジトリは、J-Quants 等の外部データソースから市場データ・財務データ・ニュースを収集し、
DuckDB をデータレイクとして保持、特徴量計算 → シグナル生成 → バックテスト → 実注文発行へとつなぐ
モジュール群を提供します。研究（research）機能と本番実行（execution）を分離した設計を特徴とします。

主な設計方針：
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等性（DBへのINSERTはON CONFLICTで制御）
- ネットワーク安全性（RSS の SSRF 対策、API リトライ・レート制御）
- DuckDB ベースで軽量かつ高速なローカルデータプラットフォーム

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足・財務・カレンダー）
  - RSS ニュース収集・前処理・記事保存・銘柄紐付け
  - DuckDB スキーマ定義 & 初期化（init_schema）
  - ETL パイプライン（差分取得、バックフィル、品質チェックのフック）

- 研究 / 特徴量
  - ファクター計算（Momentum / Value / Volatility / Liquidity）
  - クロスセクション Z-スコア正規化ユーティリティ
  - 特徴量構築（build_features → features テーブルへ UPSERT）
  - 特徴量探索（forward returns, IC, summary）

- シグナル生成
  - features と AI スコアを統合し final_score を算出
  - Bear レジーム抑制、BUY/SELL シグナルの生成と signals テーブルへの出力

- バックテスト
  - インメモリ DuckDB へのデータコピーによる安全なバックテスト実行
  - ポートフォリオシミュレータ（スリッページ・手数料モデルを考慮）
  - バックテストメトリクス計算（CAGR, Sharpe, Max DD, Win rate, Payoff 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）

- 実行 / 実装補助（骨子）
  - 発注・約定・ポジション系スキーマ（signals, orders, trades, positions 等）
  - Slack 通知や kabuステーション API 用設定（設定のみ、実API呼び出し層は別実装想定）

---

## 要求環境（Prerequisites）

- Python 3.10 以上（PEP 604 の型記法等を使用）
- 必要なパッケージ（一例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）を使う場合は外部接続が必要

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発インストール（setup.py/pyprojectがある場合）
# pip install -e .
```

requirements.txt がプロジェクトにある場合はそれを利用してください。

---

## セットアップ手順

1. レポジトリをクローンしてソースに移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境の作成・依存ライブラリのインストール（上記参照）

3. DuckDB スキーマの初期化
   - デフォルトファイルパス（例: data/kabusys.duckdb）にスキーマを作成します。
   - Python REPL またはスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動でロードされます（デフォルト）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知（使用する場合）
     - SLACK_CHANNEL_ID — Slack 通知先チャネル
   - 任意（デフォルトあり）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG / INFO / ...（デフォルト: INFO）
     - DUCKDB_PATH — duckdb ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要なコマンド・API）

以下は代表的な利用例です。各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る設計なので、スクリプトやジョブから組み合わせて使います。

1. DuckDB の初期化（再掲）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # ... 使用後
   conn.close()
   ```

2. J-Quants から株価取得 → 保存（ETL の一部）
   - pipeline モジュールの run_prices_etl 等を利用してください（ETL は差分取得ロジックを備えています）。
   - 例（簡易）:
     ```python
     from datetime import date
     from kabusys.data.pipeline import run_prices_etl

     conn = init_schema("data/kabusys.duckdb")
     result = run_prices_etl(conn, target_date=date.today())
     print(result.to_dict())  # ETLResult を確認
     conn.close()
     ```

3. ニュース収集
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄一覧
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)  # {source_name: saved_count}
   conn.close()
   ```

4. 特徴量構築（features テーブル作成）
   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy import build_features

   conn = duckdb.connect("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024, 1, 31))
   print(f"features upserted: {count}")
   conn.close()
   ```

5. シグナル生成
   ```python
   from datetime import date
   import duckdb
   from kabusys.strategy import generate_signals

   conn = duckdb.connect("data/kabusys.duckdb")
   n = generate_signals(conn, target_date=date(2024, 1, 31))
   print(f"signals written: {n}")
   conn.close()
   ```

6. バックテスト（CLI）
   - コマンドラインから実行:
     ```bash
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
     ```
   - 上の CLI は内部で DuckDB から必要なテーブルをインメモリ DB にコピーし、日次ループでシグナル生成→約定→評価を行います。
   - 返り値として履歴・約定履歴・メトリクスが得られ、最終的にサマリを標準出力します。

7. バックテストを Python API から呼ぶ例
   ```python
   from datetime import date
   import duckdb
   from kabusys.backtest.engine import run_backtest

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   print(result.metrics)
   conn.close()
   ```

注意:
- 各関数は target_date 時点のデータのみを参照することでルックアヘッドバイアスを防止しています。
- 実運用で発注を行う場合は、kabuステーション API 周りの実装・認証・安全性対策を別途実装してください（本コードは設定とスキーマを提供）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下にモジュールを配置しています。主要なファイルを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py     — RSS 収集・保存・銘柄抽出
    - schema.py             — DuckDB スキーマ定義・init_schema
    - pipeline.py           — ETL パイプライン（差分取得・品質チェック）
    - stats.py              — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 計算
    - feature_exploration.py— forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py— build_features（features テーブル作成）
    - signal_generator.py   — generate_signals（signals テーブル作成）
  - backtest/
    - __init__.py
    - engine.py             — run_backtest（バックテストエンジン）
    - simulator.py          — PortfolioSimulator（約定・資産評価）
    - metrics.py            — バックテスト指標計算
    - clock.py              — SimulatedClock（将来拡張用）
    - run.py                — CLI エントリポイント
  - execution/              — （発注周りの骨組み、現状はパッケージ）
  - monitoring/             — （監視・アラート関連、必要に応じて実装）

（上記は主要ファイルのみ抜粋。詳細は src/kabusys 以下を参照してください。）

---

## 実運用上の注意・ヒント

- テスト環境では自動的な .env の読み込みを無効化するために環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。
- J-Quants API はレート制限（120 req/min）や 401 リフレッシュ等を考慮したクライアント実装が含まれます。大量取得時は適切にバッチ化してください。
- RSS 取得は外部 URL を開くため SSRF 対策やタイムアウト、受信サイズ制限が組み込まれていますが、運用時には更なる監視を推奨します。
- DuckDB に蓄積されるデータは機密性が高いため、ファイルへのアクセス権限・バックアップ方針を検討してください。
- 本リポジトリは「戦略ロジック」と「実注文ロジック」を分離しており、実注文側（kabuステーションとの接続）を組み合わせる際は、安全性（２重確認、ロールバック、監査ログ）を必ず実装してください。

---

## コントリビューション

バグ修正・改善案・機能追加は Pull Request を歓迎します。PR を作る際は以下を含めてください：
- 再現手順（可能なら最小のコード例）
- 変更の目的と影響範囲
- 既存テストがあればそれを修正・追加

---

README は以上です。必要に応じて「セットアップスクリプト」「開発用 Makefile」「依存管理（pyproject.toml/requirements.txt）」の追加や、運用手順（デプロイ、定期ジョブ設定、バックアップ）に関する追記を行えます。どの部分を拡充したいか教えてください。