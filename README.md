# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリ。  
J-Quants / kabuステーション / OpenAI を組み合わせ、データ取得（ETL）、品質チェック、ニュース NLP、市場レジーム判定、監査ログなど自動売買システムに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得（J-Quants API 経由）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXマーケットカレンダー（jquants_client）
  - ページネーション・レートリミット・トークン自動リフレッシュ・リトライ実装
- ETL パイプライン（data.pipeline）
  - 差分取得、冪等保存、品質チェック（data.quality）
  - 日次 ETL の統合エントリポイント run_daily_etl
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク（急騰/急落）、日付不整合の検出
  - QualityIssue 型で問題を集約
- ニュース収集（data.news_collector）
  - RSS 取得、安全対策（SSRF 防止、gzip / サイズ上限、XML Bomb 対策）
  - URL 正規化 / トラッキング除去 / 記事ID生成 / raw_news への冪等保存
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア生成（ai_scores テーブルへ書き込み）
  - バッチ処理、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定（ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）を生成
- 研究用ユーティリティ（research）
  - ファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリー、Zスコア正規化
- 監査ログ（data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - 監査用専用 DuckDB 初期化関数 init_audit_db

---

## 要件

- Python 3.10+
- 主要依存（一例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、OpenAI API、ニュース RSS へのアクセス

依存はプロジェクトの pyproject.toml / requirements.txt を参照してください（本コードベースでは依存宣言は含まれていません）。

---

## 環境変数 / 設定

自動で .env（プロジェクトルートで .git または pyproject.toml を基準に探索）を読み込みます。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

必須（Settings から参照される主なキー）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ai モジュールを使う場合必須）

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — データ用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development/paper_trading/live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

簡単な .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動 .env ロードの挙動:
- プロジェクトルートが見つかれば `.env`（読み込み、既存環境変数は優先）→ `.env.local`（存在すれば上書き）を読み込みます。
- テスト時などに自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. Python をインストール（3.10+ 推奨）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject があればそちらを使用）
4. .env を作成して必要なキーを設定（上の .env.example を参照）
5. データベースの置き場ディレクトリを作成（必要な場合）
   - mkdir -p data

---

## 使い方（主要な例）

以下はライブラリ API を直接 Python から使う例です。実運用スクリプトで呼び出して ETL やスコアリングを実行します。

- DuckDB に接続して日次 ETL を実行する例:
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # デフォルトで今日を target_date にして実行
print(result.to_dict())
```

- ニュース NLP（ai.news_nlp.score_news）を呼んで ai_scores に書き込む:
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {written}銘柄")
```
OpenAI API キーは `OPENAI_API_KEY` 環境変数、または score_news の `api_key` 引数で渡せます。

- 市場レジーム判定（ai.regime_detector.score_regime）:
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn に対して監査テーブルが利用可能
```

- J-Quants からデータを直接取得する（テストやデバッグ用）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
```

注意:
- AI 呼び出しや外部 API 呼び出しはネットワークエラーや制限に配慮してリトライやフェイルセーフ設計が施されていますが、APIキーや環境設定は正しく設定してください。
- 外部 API 呼び出しをテストする際は、モック化（unittest.mock.patch）を活用できる設計になっています（コード内にモック対象の内部関数記載あり）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI連携）
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得＋DuckDB保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult エクスポート
    - news_collector.py      — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - quality.py             — データ品質チェック（QualityIssue）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

各モジュールは設計方針のコメントが豊富に記載されており、ユニットテストで差し替えやすいようモジュール境界が明確に分離されています。

---

## テスト・開発上のメモ

- OpenAI 呼び出し部や外部ネットワーク呼び出しはテスト時に mock しやすいよう内部呼び出し関数が分離されています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）から探索します。CI で意図せず .env を読み込みたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany は空配列を受け付けないバージョンの互換性考慮コードが入っています（空チェックを行ってから executemany を呼ぶ）。ローカルでの DuckDB バージョン違いに注意してください。

---

## 参考・注意事項

- Look-ahead バイアス対策: 多くの関数は target_date を明示的に受け取り、内部で date.today()/datetime.today() を直接参照しない設計になっています。バックテストやバッチ実行での使用時には target_date を明示してください。
- ログ出力とエラーハンドリング: ETL はステップごとに例外をキャッチして継続する（Fail-Fast ではない）ため、戻り値や ETLResult の errors / quality_issues を点検してください。
- セキュリティ: news_collector は SSRF 対策や XML の defusedxml 利用、レスポンスサイズ上限などを実装していますが、運用環境のポリシーに合わせた追加対策を検討してください。

---

この README はコードベースの関数・設計コメントに基づいて作成しています。詳細な API 仕様や運用手順はプロジェクト内ドキュメント（DataPlatform.md / StrategyModel.md 等）が存在する想定ですので、そちらも併せて参照してください。