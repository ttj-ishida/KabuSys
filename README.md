# KabuSys

日本株向けの自動売買システム向けライブラリコレクションです。データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査用スキーマなど、システムを構成する各層のユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下のレイヤーを想定したモジュール群を含みます。

- Data Platform（J-Quants からの株価・財務・カレンダー取得、DuckDB スキーマ・ETL）
- Research（ファクター計算・特徴量探索・統計ユーティリティ）
- Strategy（特徴量の正規化・シグナル生成）
- Execution（発注・約定・ポジション管理用スキーマ・ユーティリティ）
- News（RSS 収集・記事保存・銘柄抽出）
- Audit（監査ログ／トレーサビリティ）

設計上の特徴:
- DuckDB を用いたローカルデータベース（冪等処理を重視）
- J-Quants API や外部 RSS からの取得に対する堅牢な実装（レート制御・リトライ・SSRF 対策など）
- ルックアヘッドバイアス対策（target_date 以前のみ使用する設計）
- 可能な限り外部依存を抑えた実装（ただし DuckDB / defusedxml 等は使用）

---

## 主な機能一覧

- 環境変数管理（.env 自動読み込み、必須値チェック）
- J-Quants API クライアント（認証・ページネーション・レート制御・保存関数）
- DuckDB スキーマ定義と初期化（init_schema）
- ETL パイプライン（差分更新、バックフィル、品質チェックの呼び出し）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ）
- シグナル生成（コンポーネントスコア統合、BUY/SELL 判定、日付単位の冪等書き込み）
- ニュース収集（RSS 取得・前処理・raw_news 保存・銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査テーブル定義（signal → order → execution の追跡用スキーマ）

---

## 前提・依存関係

- Python 3.10 以上（ソース内での型ヒント（|）利用のため）
- 必要な主要パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ：urllib, datetime, logging など多数

インストール例（最小）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージとして配布されていれば:
# pip install -e .
```

（プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

---

## 環境変数

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD ではなくパッケージ位置から .git または pyproject.toml を探索）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数（config.Settings より）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意/デフォルト値あり:

- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途などの SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

注意: 必須変数が未設定の場合、Settings のプロパティ参照で ValueError が投げられます。

---

## セットアップ手順（簡易）

1. リポジトリのクローン／チェックアウト
2. 仮想環境作成と有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
   （配布パッケージがある場合は `pip install -e .` または requirements.txt を使用）
4. 環境変数の準備
   - プロジェクトルートに `.env` を作成（.env.example を参考にしてください）
   - 必須トークン（JQUANTS_REFRESH_TOKEN 等）を設定
5. DuckDB スキーマ初期化（デフォルトの db パスを使う例）
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```
   もしくはコマンドラインから簡易スクリプトを書いて実行してください。

---

## 使い方（主要ユースケース）

以下はライブラリ API を使う最小例です。実運用ではエラーハンドリングやログ、スケジューラ（cron / Airflow 等）での定期実行を組み合わせます。

1) DuckDB の初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # DB ファイルを作成して接続を返す
```

2) 日次 ETL 実行（株価・財務・カレンダーの差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import generate_signals

n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n}")
```

5) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は有効な銘柄コードの集合（例: prices テーブルから取得）
known_codes = {"7203", "6758", ...}

res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

6) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar entries saved: {saved}")
```

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル／ディレクトリ構成（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数管理
    - data/
      - __init__.py
      - jquants_client.py            # J-Quants API クライアント（取得・保存）
      - news_collector.py            # RSS 収集・記事保存・銘柄抽出
      - schema.py                    # DuckDB スキーマ定義と init_schema
      - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
      - stats.py                     # 統計ユーティリティ（zscore_normalize）
      - features.py                  # 再エクスポート（zscore）
      - calendar_management.py       # カレンダー管理（営業日判定等）
      - audit.py                     # 監査ログ用スキーマ定義
      - audit (indexes cut off...)   # 監査用 DDL / インデックス
    - research/
      - __init__.py
      - factor_research.py           # Momentum/Volatility/Value の計算
      - feature_exploration.py       # forward returns / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py       # feature を作成して features テーブルへ
      - signal_generator.py          # final_score を計算し signals を作成
    - execution/
      - __init__.py                  # Execution 層のエッジ（placeholder）
    - monitoring/                    # monitoring は __all__ に含まれる想定（実装は別）
    - その他ファイル...

注: 上記は現在のソースから抽出した主要モジュールです。詳細は src/kabusys 以下を参照してください。

---

## 設計上の注意点 / 運用メモ

- 日付取扱いは厳密に target_date 以前のデータのみを参照することでルックアヘッドバイアスを防止しています。
- ETL や保存は冪等性（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）を重視しています。
- J-Quants API 呼出しは固定間隔スロットリングとリトライを組み合わせています。大量データの連続取得時はレートに注意してください。
- ニュース収集は SSRF 対策・XML パース安全化（defusedxml）・サイズ制限を実装してありますが、外部フィードの種類により前処理をカスタマイズしてください。
- 本ライブラリは戦略ロジックや発注実行を直接行うためのものではなく、基盤・ユーティリティの提供が主目的です。実際の発注ロジックやブローカー接続は別途実装／検証してください。

---

## 貢献・拡張

- 新しいファクターやニュースソースの追加、ETL チェックの強化、監査ログの拡張などを歓迎します。
- Pull Request の際はユニットテスト（可能な箇所）と簡易的な統合テストを追加してください。
- 環境依存の部分（kabu API のエンドポイント、Slack 連携など）は設定ファイル／環境変数から注入する形で実装してください。

---

必要であれば README にコマンドライン実行例、サンプル .env.example、あるいは詳しいアーキテクチャ図（StrategyModel.md / DataPlatform.md 等の参照）を追加します。どの情報を追記するか教えてください。