# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
新しい変更は上から順に追加してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-29

初回リリース。以下の主要機能と実装方針を含みます。

### 追加 (Added)
- パッケージ骨格
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブモジュール公開: data, strategy, execution, monitoring（__all__ に登録）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を自動で読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応。
  - 高度な .env パーサ:
    - `export KEY=val` 形式、シングル/ダブルクォート内部でのバックスラッシュエスケープ、行末コメントルールに対応。
    - override と protected キーの概念で OS 環境変数を保護して読み込み可能。
  - 必須設定取得用の _require 関数と検証:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須キーをプロパティとして公開。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装。
  - データベースパス設定（duckdb, sqlite）を Path 型で取得。

- AI 関連 (src/kabusys/ai/*)
  - ニュース NLP スコアリングモジュール (news_nlp.py)
    - raw_news と news_symbols から記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - チャンク処理（最大 20 銘柄/バッチ）、1 銘柄あたり最大記事数・文字数制限、JSON Mode レスポンスの厳密なバリデーションを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフのリトライ処理。
    - レスポンスパースやバリデーション失敗時はフェイルセーフで該当銘柄をスキップ。
    - ai_scores テーブルへ idempotent に DELETE → INSERT（部分失敗時に他銘柄スコアを保護）。
    - calc_news_window で JST の「前日 15:00 ～ 当日 08:30」を UTC に変換するウィンドウ算出。

  - 市場レジーム判定モジュール (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - マクロニュース抽出はキーワードベース、LLM は gpt-4o-mini を利用、最大記事数制限あり。
    - OpenAI 呼び出しはリトライとエラーハンドリングを備え、API 失敗時は macro_sentiment=0.0 のフォールバック。
    - market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）保存。

  - ai パッケージ公開: score_news（news_nlp.score_news）を __all__ に登録。

- データ処理 / ETL / カレンダー (src/kabusys/data/*)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを使った営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合の曜日ベースフォールバック（週末を休日扱い）。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック・冪等保存を実装。
    - 最大探索日数の上限設定で無限ループを防止。

  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを実装（取得数/保存数/品質問題/エラーの記録、has_errors/has_quality_errors 等）。
    - 差分更新・バックフィル・品質チェックを考慮した設計方針を実装。
    - jquants_client（外部クライアント）経由での取得・保存を想定。
    - data.etl モジュールで ETLResult を再エクスポート。

- 研究 / ファクター (src/kabusys/research/*)
  - ファクター計算 (factor_research.py)
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から計算。
    - データ不足時は None を返す設計。
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等へ依存せず、標準ライブラリのみで実装。
  - research パッケージの __init__ で主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- 設計方針の明確化（ドキュメント文字列・コメントで記載）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計。
  - OpenAI API の呼び出し処理はユニットテスト用に差し替え可能（_call_openai_api を patch 可能に実装）。

- DuckDB 互換性考慮
  - executemany に空リストを渡せない DuckDB の挙動に対応して条件分岐で処理を行う（空リスト回避）。
  - 日付変換ユーティリティ（_to_date）で DuckDB からの値を安全に date に変換。

### 修正 / 安全対策 (Fixed / Security)
- フェイルセーフ戦略の導入
  - AI API 呼び出し失敗時に致命例外を投げず、スコア算出において安全なデフォルト（0.0）を使用することでパイプライン継続を担保。
  - OpenAI API エラーのステータスコード取り扱いを堅牢化（status_code がない場合の安全処理）。
- .env 読み込み失敗時の警告（warnings.warn）を追加し、アプリ起動が致命的に失敗しないように配慮。

### 既知の制限 / 備考 (Known)
- OpenAI モデルは現状 gpt-4o-mini を想定しているが、将来的なモデル変更や API 仕様変更に備えて呼び出し箇所の差し替えを容易にしている。
- J-Quants クライアント（jquants_client）や quality モジュールは外部インターフェースとして利用を想定しており、実際の API キーや環境依存設定が必要。
- 一部の機能（strategy / execution / monitoring）の実体はこのリリースでは公開インターフェースのみ（__all__）で、実装は別途追加される想定。

---

参照:
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/