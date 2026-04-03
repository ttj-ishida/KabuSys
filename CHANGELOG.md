CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。本プロジェクトは Keep a Changelog の慣例に準拠しています。
※日付はコード解析時点の推定値を使用しています。

Unreleased
----------
（なし）

0.1.0 - 2026-04-03
------------------
初回リリース。以下の主要機能とモジュールを追加しました。

Added
- パッケージ基礎
  - kabusys パッケージを追加。公開 API として data, research, ai, execution, monitoring を想定したモジュール構成を定義。
  - バージョン情報: __version__ = "0.1.0"。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 高度な .env パーサーを実装（コメント処理、export 形式、シングル/ダブルクォート内のエスケープ処理など）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視パラメータ等のプロパティを公開。
    - 必須パラメータ取得時のエラー挙動（_require）。
    - KABUSYS_ENV / LOG_LEVEL の検証（有効値チェック）。
    - デフォルトのパス/閾値を明示（DuckDB/SQLite パス、CPU/Memory/Disk 閾値、PID/KILL ファイルパスなど）。

- データプラットフォーム (kabusys.data)
  - ETL 用の public インターフェースと ETLResult データクラスを実装（kabusys.data.pipeline.ETLResult を再エクスポート）。
  - pipeline モジュール（kabusys.data.pipeline）
    - 差分取得/保存、バックフィル、品質チェックの骨格を提供。
    - ETLResult による実行結果の集約（品質問題の収集、エラー一覧、has_errors/has_quality_errors プロパティ、to_dict）。
    - DuckDB を使用した最終取得日取得やテーブル存在確認ユーティリティを実装。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を基にした営業日判定ロジックを提供。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - データ未取得時は曜日ベース（土日休み）でフォールバック。
    - calendar_update_job を実装し J-Quants API との差分取得 → idempotent 保存（fetch/save を jquants_client 経由）を行う。
    - バックフィル、健全性チェック（過度の将来日付はスキップ）、最大探索日数制限を導入。

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離を計算（prices_daily を参照）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務データを取得）。
    - DuckDB を用いた SQL ベースの実装。外部 API にはアクセスしない設計。
  - feature_exploration
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンの入力検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算するユーティリティ。
    - rank: 同順位は平均ランクで扱うランク計算。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - zscore_normalize は kabusys.data.stats から再公開（research パッケージで利用しやすく）。

- AI / NLP（kabusys.ai）
  - news_nlp
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_score）を生成して ai_scores テーブルへ idempotent に書き込む。
    - タイムウィンドウ: JST の前日 15:00 ～ 当日 08:30（UTC に変換）を対象に記事を収集（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数の上限でトリム、JSON mode による厳密パース。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ、非再試行エラーはスキップ。
    - レスポンスバリデーションとスコアの ±1.0 クリップ。
    - テスト容易性のため _call_openai_api を patch 可能（ユニットテスト向けフック）。
    - API 未設定時は ValueError を送出。
  - regime_detector
    - score_regime: ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事抽出はキーワードベース（複数の日本語/英語キーワード）でタイトルを取得し LLM に投げる。
    - LLM 呼び出しは gpt-4o-mini、JSON レスポンスを期待、失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - OpenAI SDK 呼び出しに対してリトライ/バックオフを実装。テスト用に _call_openai_api を差し替え可能。
    - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ使用、datetime.today() を参照しない）。

- 共通設計方針・運用面
  - DuckDB をデフォルトの分析 DB として使用（SQL ベースの処理、executemany を用いた互換性確保等）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 相当の扱いを想定）。
  - API 呼び出し失敗時は例外で即停止せずフェイルセーフ（部分失敗を許容し、可能な範囲で処理継続）。
  - ロギング、警告メッセージを通じて運用上の問題を可視化。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Security
- OpenAI API キー（OPENAI_API_KEY）等の機密情報は環境変数で管理。Settings クラスで未設定時の明示的エラーを返す設計。

Notes / 補足
- 本リリースはコードベースから推測して作成しています。実運用に当たっては各 API クライアント（J-Quants、kabuステーション、OpenAI）や DB スキーマの実体、依存ライブラリバージョンに応じた追加検証が必要です。
- テスト容易性のため、OpenAI 呼び出し箇所には patch 可能な内部関数を用意しています（ユニットテストでのモック化を想定）。
- ルックアヘッドバイアス回避のため、全ての時刻依存処理は明示的に target_date を受け取る設計になっています。

お問い合わせ・貢献
- バグ報告や改善提案は issue を立ててください。コードコメントや docstring に設計方針を多く含めているため、実装意図の確認に役立ちます。