# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このプロジェクトはまだ初期バージョンとしてリリースされています。

注意: 以下の変更点は提供されたソースコードの内容から推測してまとめたものです。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初回公開リリース — 日本株自動売買・データ基盤向けユーティリティ群を実装。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - パッケージ外部公開シンボルを __all__ で整理（data, strategy, execution, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - .env 行パーサ (_parse_env_line) を実装:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、コメント処理に対応。
  - ファイル読み込み時の保護キー（protected）と override ロジックを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - Settings クラスを提供し、環境変数をプロパティとして安全に取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須キー検証。
    - KABUSYS_ENV / LOG_LEVEL の検証 (許容値チェック)。
    - データベースパス (duckdb/sqlite) の Path 型返却ユーティリティ。
    - is_live / is_paper / is_dev のブール判定プロパティ。

- AI（自然言語処理） (src/kabusys/ai)
  - ニュースセンチメント分析モジュール (news_nlp.py)
    - OpenAI（gpt-4o-mini）を用いた銘柄別ニューススコアリング。
    - タイムウィンドウ計算 (前日15:00JST〜当日08:30JST) を calc_news_window として提供。
    - 記事の銘柄ごと集約、最大記事数・文字数でトリムする仕組み。
    - バッチ処理（最大 20 銘柄/コール）、レスポンスバリデーション（JSON 抽出・results キー検証・既知コードのみ採用）。
    - 再試行（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフ処理。
    - スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時の既存データ保護）。
    - テスト容易性のため _call_openai_api の差し替えが可能（unittest.mock.patch を想定）。
  - 市場レジーム判定モジュール (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定を実装。
    - マクロニュースは news_nlp の calc_news_window を利用して窓内のタイトルを抽出、OpenAI により macro_sentiment を取得。
    - API エラー・パース失敗時はフェイルセーフで macro_sentiment = 0.0 を採用。
    - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しはモジュール独立で実装（モジュール間結合の抑制）。

- データ基盤 (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - market_calendar テーブルに基づく営業日判定ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB にデータがない場合は曜日ベースでフォールバック（土日を非営業日とする）。
    - calendar_update_job を実装: J-Quants API から差分取得・バックフィルを行い market_calendar を冪等保存。健全性チェック（将来日付上限）を含む。
  - ETL パイプライン (pipeline.py / etl.py)
    - ETLResult データクラスを公開（etl.py で再エクスポート）。
    - 差分取得、保存、品質チェックフローに沿った ETL 用ユーティリティの下地を実装。
    - 最終取得日の算出、テーブル存在チェック等のヘルパ関数を実装。
    - backfill、calendar lookahead 等の設定を定義。

- リサーチ（因子・特徴量） (src/kabusys/research)
  - factor_research.py:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を DuckDB クエリベースで計算する関数を提供:
      - calc_momentum, calc_volatility, calc_value。
    - DuckDB 上で window 関数を用いた実装、データ不足時の None ハンドリング。
  - feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）。
    - IC（Information Coefficient）計算 calc_ic（Spearman のランク相関）。
    - ランク化ユーティリティ rank（同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
  - research パッケージ __init__ で主要 API を公開。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- 環境変数ベースの機密情報（API トークン等）の取り扱いを前提としているため、.env の取り扱いに注意が必要（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- Settings は必須変数が未設定の場合 ValueError を投げるため、デプロイ時に必要な環境変数を確実に設定すること。

### 既知の制約・設計上の注意 (Notes)
- OpenAI API キー (OPENAI_API_KEY) が未設定の場合、news_nlp.score_news / regime_detector.score_regime は ValueError を送出する。
- LLM 呼び出しに依存する処理は、API 失敗時にスコアを 0.0 にフォールバックするなどフェイルセーフを設計しているが、実運用ではレート制限やコスト管理に注意が必要。
- DuckDB のバージョン依存（executemany の空パラメータ等）を考慮した実装上の注意点が多く含まれる。
- 日時関連処理はルックアヘッドバイアスを避けるために datetime.today()/date.today() を直接参照しない方針で実装されています（一部バッチジョブ等で today を参照する箇所あり）。

---

既知のバグ報告や改善リクエストは issue にてお寄せください。