# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-31

### Added
- パッケージの初期リリース。kabusys v0.1.0 を公開。
  - パッケージエントリポイント: `src/kabusys/__init__.py` にてバージョン管理と公開モジュールを設定。

- 環境設定管理
  - `kabusys.config`:
    - .env / .env.local を自動ロードする仕組み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - `.env` の行パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
    - OS 環境変数の保護（既存の環境変数を保護する protected set）。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 必須環境変数取得ヘルパ `_require` と、各種設定プロパティを提供（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / ログ・環境判定等）。
    - `KABUSYS_ENV` と `LOG_LEVEL` のバリデーション。

- AI（自然言語処理）機能
  - `kabusys.ai.news_nlp`:
    - ニュース記事を OpenAI（gpt-4o-mini）に投げて銘柄ごとのセンチメント（ai_score）を算出し、`ai_scores` テーブルへ書き込む。
    - スコアリングウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ `calc_news_window` を提供。
    - 銘柄単位で記事を集約、トリム（記事数・文字数上限）してバッチ（最大 20 銘柄）で API 呼び出し。
    - JSON Mode による出力パース・バリデーション、スコアクリップ、エクスポネンシャルバックオフによるリトライ、部分成功時の DB 書き換え戦略（対象 code のみ DELETE → INSERT）。
    - テスト用に OpenAI 呼び出しを差し替え可能（関数をモックしやすい設計）。

  - `kabusys.ai.regime_detector`:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news からデータを取得し、OpenAI（gpt-4o-mini）で記事群のマクロセンチメントを評価。
    - API のフェイルセーフ（失敗時 macro_sentiment=0.0）、リトライ・バックオフ、レスポンスパースの堅牢化を実装。
    - 計算結果を `market_regime` テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。

- リサーチ（ファクター計算・特徴量探索）
  - `kabusys.research.factor_research`:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE）の計算関数を実装。
    - DuckDB の SQL ウィンドウ関数と組み合わせて効率的に集計。
    - データ不足時は None を返す等の安全な挙動。

  - `kabusys.research.feature_exploration`:
    - 将来リターン算出（calc_forward_returns）、IC（Information Coefficient）計算（Spearman ランク相関）、ランク変換ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を提供。
    - 外部依存（pandas 等）を用いず、標準ライブラリ + DuckDB で実装。
    - 数値の有限性チェックや入力検証を含む。

  - `kabusys.research.__init__` で主要ユーティリティを再公開。

- データ基盤関連
  - `kabusys.data.calendar_management`:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 夜間バッチ `calendar_update_job` による J-Quants からの差分取得・保存処理（バックフィル、健全性チェック、エラーハンドリング）。
    - jquants_client への依存はモジュール注入で分離（fetch/save を利用）。

  - `kabusys.data.pipeline` / `kabusys.data.etl`:
    - ETL のための `ETLResult` データクラスを公開（取得件数・保存件数・品質問題・エラー集約・ヘルパーメソッド to_dict を含む）。
    - 差分更新やバックフィル、品質チェックの方針を反映した設計（quality モジュールとの連携を想定）。
    - `etl` からは `ETLResult` を再エクスポート。

- テストしやすい設計上の配慮
  - OpenAI 呼び出し部分や時間参照（datetime.today / date.today を直接参照しない）をテスト可能・ルックアヘッドバイアス回避を重視して設計。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Known issues / Notes
- 現時点のコードベースには pipeline モジュールの末尾で不完全な記述（`return date.fro` のようなタイポ／途中切れ）が見られます。これは ETL パイプライン周りの未完成箇所／コピーペーストミスを示唆しているため、次リリースで修正・補完予定です。
- OpenAI の API 呼び出しは gpt-4o-mini と JSON モードを前提としているため、将来的な SDK 仕様変更やモデル変更に対して互換性確認が必要です。
- DuckDB バインドや executemany の空パラメータに関する注意（コード内に互換性対策の記述あり）があるため、環境の DuckDB バージョンによっては追加対応が必要になる可能性があります。

---

発行: kabusys v0.1.0 — 初期公開リリース（基礎機能: 環境管理、AI スコアリング、マーケットカレンダー、ファクター計算、ETL 結果構造）