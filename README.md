# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL・データ品質チェック・ニュース NLP（LLM）スコアリング・市場レジーム判定・監査ログ初期化など、研究・運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ収集（J-Quants API）と差分ETL（株価 / 財務 / カレンダー）
  - レートリミット遵守、トークン自動リフレッシュ、ページネーション対応、冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と NLP による銘柄別センチメント算出（OpenAI）
  - バッチ処理、スコアの検証・クリッピング、リトライ/バックオフ
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 監査ログ（signal / order_request / executions）用のスキーマ初期化ユーティリティ
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計・正規化）

設計上の方針として、ルックアヘッドバイアス防止・冪等処理・フェイルセーフ（API失敗時に処理継続）を重視しています。

---

## 機能一覧（モジュール別ハイライト）

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）、必須環境変数取得、設定ラッパー
- kabusys.data
  - jquants_client: J-Quants API 呼び出し・保存（raw_prices / raw_financials / market_calendar）
  - pipeline: 日次 ETL（run_daily_etl）と各 ETL ジョブ
  - quality: データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - news_collector: RSS 収集、前処理、SSRF 対策
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査ログ用テーブル作成・初期化（init_audit_db / init_audit_schema）
  - stats: zscore_normalize 等
- kabusys.ai
  - news_nlp.score_news: ニュースから銘柄別 ai_score を生成して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュース LLM を合成し market_regime に書き込み
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提（推奨環境）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API, OpenAI, RSS ソース）

（実際の requirements.txt がない場合は上のパッケージをインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   例（pip で個別指定）:
   ```
   pip install duckdb openai defusedxml
   ```
   またはパッケージ化されている場合:
   ```
   pip install -e .
   ```

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   最低限設定すべき主な環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
   OPENAI_API_KEY=あなたの_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development           # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   利用可能な設定（主なもの）:
   - JQUANTS_REFRESH_TOKEN (必須 for jquants_client)
   - OPENAI_API_KEY (score_news / score_regime が必要)
   - KABU_API_PASSWORD, KABU_API_BASE_URL
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - DUCKDB_PATH, SQLITE_PATH
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development / paper_trading / live)
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

---

## 使い方（プログラムからの呼び出し例）

以下はプログラム的に利用する際の基本例です。DuckDB 接続は各関数に必要です。

- 基本的な初期化と接続例
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数を使用
print(f"scored {n} codes")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ用 DB 初期化（専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使って監査ログを操作
```

- ファクター計算（研究用途）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# records: list[dict] -> zscore_normalize 等で正規化可能
```

注意点:
- OpenAI 呼び出しは gpt-4o-mini（JSON mode）を利用します。API 料金・レートに注意してください。
- run_daily_etl などは内部で J-Quants API を呼ぶので JQUANTS_REFRESH_TOKEN が必要です。
- API 呼び出し失敗時はフェイルセーフで処理を続ける設計ですが、ログを確認してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル/ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP スコアリング (score_news)
    - regime_detector.py       — 市場レジーム判定 (score_regime)
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント + 保存ロジック
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - quality.py               — データ品質チェック
    - news_collector.py        — RSS 取得・前処理（SSRF 対策など）
    - calendar_management.py   — マーケットカレンダー管理
    - audit.py                 — 監査ログスキーマ初期化（init_audit_db 等）
    - stats.py                 — zscore_normalize 等統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py   — 将来リターン・IC・統計サマリ
  - (その他)
    - strategy, execution, monitoring などのモジュール名はパッケージAPIに列挙されていますが、
      このリポジトリの該当実装が存在しない場合があります（将来的な追加想定）。

---

## 運用上の注意 / 設計上のポイント

- ルックアヘッドバイアス防止:
  - モジュールは内部で datetime.today() / date.today() を安易に参照しないよう設計されています。
  - target_date を明示して処理を行うことでバックテストでのバイアスを低減します。
- 冪等性:
  - DB への保存は ON CONFLICT DO UPDATE / INSERT ... DO UPDATE を使用し、再実行可能な ETL を実現しています。
- フェイルセーフ:
  - API 呼び出しや LLM 結果パース失敗時は例外を投げずデフォルト値で継続するケースが多く、運用での堅牢性を高めています。
- ロギング:
  - 各モジュールは logging を使用しており、LOG_LEVEL で制御できます。
- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml を利用した XML パースなどを実装しています。

---

## トラブルシューティング / よくある質問

- .env が読み込まれない
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。CI 等で無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI のレスポンスが期待どおりの JSON でない
  - モジュールは JSON パース失敗時にログを出してスキップ（0.0 などのフォールバック）します。必要に応じてリトライやプロンプトの調整を検討してください。
- J-Quants の認証エラー（401）
  - jquants_client は 401 を受けるとリフレッシュトークンでトークンを再取得して 1 回リトライします。refresh token が間違っていないか確認してください（環境変数 JQUANTS_REFRESH_TOKEN）。

---

## 貢献 / 開発者向け

- コードスタイル・型付けが比較的整っています。ユニットテストの追加、エンドツーエンドの統合テスト（API モック化）を歓迎します。
- 外部 API の呼び出しは抽象化されているので、テスト時は各モジュールの内部呼び出し（例: kabusys.ai.news_nlp._call_openai_api）をモックして差し替えられる設計です。

---

以上が README の概要です。必要であれば、README に「CLI 使い方」や具体的な .env.example の雛形、サンプル SQL スキーマ（テーブル定義）を追記できます。どの情報を詳しく追記しましょうか？