# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL、データ品質チェック、特徴量計算、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）、および証券会社への発注フローに必要な基盤機能群を提供する Python ライブラリです。  
主に以下の用途を想定しています：

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL
- ニュース記事の収集と LLM による銘柄別センチメント算出
- 研究用途のファクター計算（モメンタム / バリュー / ボラティリティなど）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal -> order_request -> execution のトレーサビリティ）
- マーケットレジーム判定（MA と マクロ記事の LLM センチメントを合成）

設計方針としては「ルックアヘッドバイアス防止」「冪等性」「フォールバックの安全性」「API レート制御」「外部ライブラリ依存の最小化」などに配慮しています。

---

## 主な機能一覧

- ETL:
  - J-Quants 経由で株価日足 (OHLCV)、財務データ、上場情報、マーケットカレンダーの差分取得・保存（DuckDB）
  - 差分更新・バックフィル対応、ページネーション、トークン自動リフレッシュ
- データ品質:
  - 欠損データ、スパイク（前日比閾値）、重複、日付整合性チェック
- ニュース収集 & NLP:
  - RSS からのニュース収集（SSRF対策、gzip上限、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（ai_scores）算出（バッチ・リトライ付き）
  - マクロニュースの LLM 評価と ETF 1321 の MA200 乖離を合成して市場レジーム判定
- 研究用ユーティリティ:
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー
- 監査ログ（Audit）:
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - UUID ベースの冪等キー、インデックス定義、UTC タイムスタンプ管理
- 設定管理:
  - .env / .env.local 自動読み込み（プロジェクトルート検出）と環境変数ベースの設定取得
  - 必須変数の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）

---

## セットアップ手順（開発環境向け）

前提:
- Python 3.10+（型アノテーションなどを使用）
- DuckDB、OpenAI SDK 等を使用（以下は代表的依存）

推奨手順（ローカル）:

1. リポジトリをクローンしプロジェクトルートへ
   - プロジェクトは src/ 配下にパッケージがあります

2. Python 仮想環境作成・アクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（requirements.txt が無い場合は代表例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt や pyproject.toml があればそちらを使用してください）

4. 環境変数設定
   - プロジェクトルートに `.env` および開発用に `.env.local` を作成できます。
   - 自動ロード: パッケージ起動時にプロジェクトルートが検出されると `.env` → `.env.local` の順で読み込みます（OS 環境変数より優先されない）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（必須と既定値）:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - OPENAI_API_KEY (OpenAI を使う機能を使う場合必須)
   - DUCKDB_PATH (既定: data/kabusys.duckdb)
   - SQLITE_PATH (既定: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) — 既定: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — 既定: INFO

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   OPENAI_API_KEY=sk-xxxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベースディレクトリ作成
   - DUCKDB のファイルパス parent ディレクトリが無ければ自動作成されるユーティリティもありますが、手動で作成しておくと安心です:
     - mkdir -p data

---

## 簡単な使い方（コード例）

下記は Python REPL やスクリプト内で直接利用する例です。import は src 配下のパッケージを参照するため、プロジェクトルートで実行するか `pip install -e .` でインストールしてください。

- DuckDB 接続を作成して ETL を実行する（例: 今日分の ETL）:
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースの NLP スコアリング（OpenAI API 必須）:
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,3,20), api_key="sk-xxxx")
print("scored", count, "codes")
```

- 市場レジーム判定:
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key="sk-xxxx")
```

- 監査ログスキーマ初期化（別 DB 推奨）:
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests などを記録できます
```

- 研究用ファクター計算:
```
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```

---

## 設定 API の振る舞い

- 設定は `kabusys.config.settings` 経由でアクセスします。必須変数は取得時に検証され、未設定の場合は ValueError が発生します。
- 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` を読みます。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト等の用途）。

---

## ディレクトリ構成

主要ファイル・モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数 / 設定管理（.env 自動読み込み等）
    - ai/
      - __init__.py
      - news_nlp.py                # ニュースの LLM ベースセンチメント算出（score_news）
      - regime_detector.py         # ETF + マクロニュースを合成した市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py          # J-Quants API クライアント（取得／保存／レート制御）
      - pipeline.py                # ETL パイプライン / run_daily_etl 等
      - etl.py                     # ETLResult 再エクスポート
      - calendar_management.py     # マーケットカレンダー管理（is_trading_day 等）
      - news_collector.py          # RSS 収集、前処理、raw_news 保存ロジック
      - quality.py                 # データ品質チェック
      - stats.py                   # 統計ユーティリティ（zscore_normalize 等）
      - audit.py                   # 監査ログ DDL / 初期化ユーティリティ
    - research/
      - __init__.py
      - factor_research.py         # モメンタム/バリュー/ボラティリティ計算
      - feature_exploration.py     # 将来リターン / IC / サマリー関数
    - ai/..., research/...         # その他の補助モジュール
- pyproject.toml (想定)
- .env.example (想定)
- README.md

（上記はコードベースから抜粋した主要ファイルです）

---

## 注意事項 / 実運用上の留意点

- OpenAI の呼び出しには API キーが必要です。課金・レート制約に注意してください。LLM の失敗は多くの箇所でフォールバック（0 スコア等）するよう設計されていますが、運用ポリシーを整備して下さい。
- J-Quants API のレート制限（120 req/min）に対応する RateLimiter を実装していますが、大量取得や並列実行時は追加の制御が必要です。
- DuckDB を用いた保存は ON CONFLICT を利用した冪等設計ですが、DB スキーマやバージョン差異に注意してください（特に executemany の動作など）。
- audit スキーマは削除を行わない前提で設計されています。バックアップ・保守ポリシーを用意してください。
- 研究・検証用途と実運用（ライブ発注）での設定は厳格に分離してください（KABUSYS_ENV 等を使用）。

---

## 開発・貢献

- プロジェクトルートに pyproject.toml / setup.cfg / requirements.txt があることを想定しています。実際のリポジトリに合わせて環境を整えてください。
- テストや CI の推奨:
  - OpenAI / J-Quants など外部 API 呼び出しはテストでモックする（コード内でもモックしやすい設計になっています）。
  - DuckDB を :memory: で使った単体テストが可能です（init_audit_db などは :memory: を受け取れます）。

---

必要であれば README を拡張して下記を追加できます：
- 実行可能な CLI のサンプル（cron 用の起動コマンド例）
- .env.example のフルテンプレート
- よくあるトラブルシュート（OpenAI エラー、J-Quants 401、DuckDB パス権限問題 等）
- API 使用フロー図や ER 図（監査スキーマ）

追加希望があれば用途（開発向け / 運用向け / 研究向け）を教えてください。README をそれに合わせて詳細化します。