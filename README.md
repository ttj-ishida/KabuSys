# KabuSys

KabuSys は日本株の自動売買基盤を想定した Python パッケージです。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を備え、研究（research）→ 本番（execution）までのワークフローをサポートします。

バージョン: 0.1.0

---

## 概要

主な設計方針・特徴:
- DuckDB を中心に「Raw → Processed → Feature → Execution」の多層データモデルを採用
- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）をサポート
- ETL は差分更新・バックフィルに対応し、品質チェック機能を備える
- 研究用モジュール（factor 計算、特徴量探索）と運用用モジュール（特徴量正規化、シグナル生成）が分離されている
- 冪等性（ON CONFLICT / upsert、トランザクション）・トレーサビリティ（監査ログ）を重視
- ニュース収集では SSRF 対策・サイズ制限・トラッキング除去など安全策を実装
- 自動環境変数ロード（プロジェクトルートの .env / .env.local）に対応。必要に応じて無効化可

---

## 機能一覧

- データ取得・保存
  - J-Quants からの株価日足、四半期財務、マーケットカレンダー取得（ページネーション・リトライ・レート制御）
  - raw テーブルへの冪等保存（ON CONFLICT）
- ETL / パイプライン
  - 差分ETL（prices / financials / calendar）
  - 日次 ETL 実行エントリポイント（run_daily_etl）
  - 品質チェック呼び出し（quality モジュールと連携）
- スキーマ管理
  - DuckDB スキーマ初期化（init_schema）
- 特徴量 / 戦略
  - ファクター計算（momentum / volatility / value）
  - クロスセクション Z スコア正規化
  - features テーブル構築（build_features）
  - features と ai_scores を統合したシグナル生成（generate_signals）
  - SELL（エグジット）判定ロジック（ストップロス等）
- ニュース収集
  - RSS フィード取得、前処理、raw_news 保存、銘柄抽出と紐付け
  - SSRF/サイズ/Gzip/XML パースの堅牢化
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - 夜間バッチ（calendar_update_job）
- 監査ログ（audit）
  - signal_events / order_requests / executions 等、トレース可能な監査テーブル群

---

## セットアップ手順

※ Python 3.10 以上を推奨します（型ヒントの | 演算子などを使用）。

1. リポジトリをクローン（パッケージ配布済みであれば不要）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   - 他に必要なライブラリがあればプロジェクトの requirements.txt を参照してください。
   - 開発時は `pip install -e .` のようにパッケージをインストールしておくと便利です。

4. 環境変数の設定
   - プロジェクトルートに `.env` と `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - Python から直接呼べます:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（主要な操作例）

以下は簡単な Python スニペット例です。実運用時は適切なログ・エラーハンドリングを追加してください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants からの差分取得・保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可
print(result.to_dict())
```

- 特徴量構築（features テーブルへの保存）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, date(2025, 3, 20))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへの書き込み）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, date(2025, 3, 20))
print(f"signals written: {total}")
```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- マーケットカレンダーの夜間更新
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 注意点 / 運用メモ

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準にします。CI やテスト環境で自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限(120 req/min) を尊重するよう実装されています。大量取得はバックオフやページネーションを考慮してください。
- ニュース収集は外部から取得するため、SSRF や XML 攻撃、巨大レスポンスに対する防御を実装していますが、運用時は信頼できる RSS ソースを設定してください。
- 本パッケージは発注（execution）層への直接的な注文送信を含む構成要素を持ちますが、実際にライブ資金で利用する場合は十分なテスト・リスク管理を行ってください（paper_trading モードでの検証推奨）。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb`。バックアップや排他アクセスに注意してください。

---

## ディレクトリ構成

主要なモジュール・ファイル（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py              — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント & save_* 関数
    - news_collector.py     — RSS ニュース収集・前処理・保存
    - schema.py             — DuckDB スキーマ定義・初期化
    - stats.py              — 汎用統計ユーティリティ（zscore_normalize 等）
    - pipeline.py           — ETL パイプライン（run_daily_etl 他）
    - features.py           — data 側の features export
    - calendar_management.py— マーケットカレンダー管理
    - audit.py              — 監査ログ用 DDL
    - quality.py            — （品質チェック、別ファイル想定）
  - research/
    - __init__.py
    - factor_research.py    — momentum/volatility/value の計算
    - feature_exploration.py— IC/forward returns/summary 等（研究用）
  - strategy/
    - __init__.py
    - feature_engineering.py— features 構築（正規化 / フィルタ等）
    - signal_generator.py   — final_score 計算と signals 生成
  - execution/
    - __init__.py           — 発注関連モジュール（実装分割想定）
  - monitoring/
    - (モニタリング・監視関連モジュール想定)

（上記は本リポジトリで提供されている主なファイルに基づく要約です）

---

## 開発 / 貢献

- コーディング規約・テスト基盤はプロジェクトの CONTRIBUTING.md を参照してください（存在する場合）。
- 単体テスト、統合テストを充実させた上で、paper_trading での十分な検証を行ってから live 環境へ移行してください。
- 機密情報（API トークン等）は .env/.env.local に格納し、誤ってリポジトリへコミットしないよう注意してください。

---

## 参考 / 連絡先

- 各モジュールの詳細・ロジックについてはソースコードの docstring とコメントを参照してください。README は概観と利用手順のための要約です。質問や改善提案があればプルリクエストやイシューでどうぞ。