# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載します。

## [0.1.0] - 2026-03-28

初回リリース。日本株のデータ基盤・リサーチ・AI スコアリング・環境管理を含むコアライブラリを提供します。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージを __all__ で公開）。
- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順序と override ロジックを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - シンプルだが堅牢な .env ラインパーサ（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 実行環境 (development/paper_trading/live) / ログレベル等をプロパティ経由で取得。
  - 必須環境変数未設定時に明示的な ValueError を送出する _require ヘルパーを実装。
- AI（自然言語処理）
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news + news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を生成。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、記事数・文字数トリム、JSON レスポンスのバリデーション、スコアのクリップを実装。
    - 429 / 接続断 / タイムアウト / 5xx を対象とした指数バックオフのリトライを実装。その他のエラーはスキップして処理継続（フェイルセーフ設計）。
    - DuckDB への書き込み時に部分失敗でも既存スコアを保護する実装（更新対象コードを絞って DELETE → INSERT）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースに対する LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。API 失敗時は macro_sentiment = 0.0 として継続（フェイルセーフ）。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とエラーハンドリング（ROLLBACK）を実装。
- データ基盤 (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - market_calendar を使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新する夜間バッチ処理（バックフィル / 健全性チェック付き）。
  - ETL パイプライン (pipeline.py, etl.py)
    - ETL の成果を表す ETLResult データクラス（取得件数、保存件数、品質問題、エラー等）。
    - 差分取得、バックフィル、品質チェック（kabusys.data.quality）を想定したパイプライン基盤の骨組みを実装。
    - DuckDB 操作時の互換性考慮（executemany における空リスト回避等）を反映。
  - jquants_client 連携（モジュール参照箇所を実装済み：fetch/save を利用する想定の統合点を提供）。
- リサーチ（src/kabusys/research）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Value（PER、ROE）などのファクター計算を実装。
    - DuckDB を用いた SQL ベースの計算（prices_daily, raw_financials を参照）。結果は (date, code) キーの辞書リストとして返す。
  - feature_exploration.py
    - 将来リターン算出（任意ホライズン）calc_forward_returns。
    - IC（Information Coefficient）計算（スピアマン ランク相関）calc_ic。
    - ランク変換ユーティリティ rank、ファクター統計サマリー factor_summary。
  - re-export とユーティリティ連携を __init__ で提供。
- その他
  - DuckDB を主要データストアとして利用する前提で各モジュールが実装されていることを明記。
  - OpenAI Python SDK（OpenAI クライアント）を利用する設計。テスト用に内部の API 呼び出し関数を patch 可能にしている（ユニットテスト容易化を意識）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### 既知の制約・注意点 (Notes)
- OpenAI の呼び出しは外部 API に依存しており、API キーは引数または環境変数 OPENAI_API_KEY で指定する必要があります。未設定の場合は ValueError を送出します。
- news_nlp / regime_detector は API 障害に対してフォールバック（0.0）する設計ですが、これは処理継続を優先するためであり、品質や運用方針によってはモニタリングや通知を併用してください。
- DuckDB のバージョン依存（executemany の空リスト処理など）を考慮した実装が含まれます。利用時の DuckDB バージョン互換性に注意してください。
- .env 自動ロードはプロジェクトルートの検出に依存します。配布後や特定の実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で明示的に無効化できます。
- いくつかの関数は日付演算で datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）です。ETL/スコアリング呼び出し時は明示的に target_date を渡してください。

---

今後の予定（例）
- モニタリング・アラート機能（Slack 通知等）の実装強化
- バックテスト・ストラテジ実行モジュールの追加
- テストカバレッジ拡充と CI ワークフロー整備

行追加・修正の要望があれば、重点的に CHANGELOG を更新します。