# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

なお、記載は与えられたコードベースの実装内容から推測して作成しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース。以下の主要機能と実装方針を追加しています。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルート判定は __file__ から上位ディレクトリを走査し `.git` または `pyproject.toml` を基準に行うため、CWD に依存しない設計。
  - .env パーサを実装:
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント除去ロジックを実装。
    - クォートなし値の `#` をコメントとみなす条件を実装。
  - 保護付き上書き（protected set）を考慮した env 上書きロジック。
  - Settings クラスを提供:
    - 必須環境変数取得メソッド（未設定時は ValueError を発生）。
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを実装。
    - `KABUSYS_ENV`（development / paper_trading / live）と `LOG_LEVEL` のバリデーション。
    - ユーティリティ: is_live, is_paper, is_dev。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）でセンチメントをスコア化して ai_scores に書き込む機能を追加。
  - 主な実装内容:
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
    - 1 銘柄あたり最大記事数・最大文字数（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。
    - 1 回の API 呼び出しで最大 20 銘柄（_BATCH_SIZE）をバッチ処理。
    - JSON Mode を期待し厳密 JSON をパース。JSON 解析失敗時は外側の {} を抽出して復元を試みるフォールバックあり。
    - スコアを ±1.0 にクリップして ai_scores テーブルへ冪等書き込み（DELETE → INSERT）。
    - エラー耐性: 429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ、その他はスキップして継続（フェイルセーフ）。
    - テスト容易性のため内部の OpenAI 呼び出し関数を patch 可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を追加。
  - 主な実装内容:
    - ma200_ratio の計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - マクロキーワードで raw_news からタイトルを抽出（最大 20 件）。
    - OpenAI（gpt-4o-mini）でマクロセンチメントを -1.0〜1.0 で評価。API 失敗時は 0.0 でフォールバック。
    - 合成スコア = clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。閾値によりラベル付け（BULL_THRESHOLD 0.2 / BEAR_THRESHOLD 0.2）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。
    - LLM 呼び出しのリトライ・バックオフ・エラー分類を実装。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）を追加。
    - ETLResult dataclass を実装（取得数・保存数・品質問題・エラー概要などを格納）。
    - 差分取得・バックフィル・品質チェック方針を備えた設計（詳細は docstring）。
    - DuckDB に対するヘルパ（テーブル存在チェック、最大日付取得など）。
  - calendar_management（マーケットカレンダー管理）を追加。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が未取得のときは曜日ベース（土日除外）でフォールバックする堅牢な設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新する夜間バッチ処理（バックフィル・健全性チェックを実装）。
    - J-Quants クライアント（jquants_client）を利用（fetch_market_calendar / save_market_calendar を想定）。
  - data.etl で pipeline.ETLResult を公開再エクスポート。

- リサーチ（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等の定量ファクターを DuckDB（prices_daily / raw_financials）から計算する関数を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None）
    - calc_volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率
    - calc_value: PER（EPS が無効な場合は None）, ROE（raw_financials の最新値を使用）
  - feature_exploration: 将来リターン計算・IC（スピアマン ρ）・統計サマリー等のユーティリティを実装:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: factor_records と forward_records を code で結合してスピアマンランク相関を計算（有効レコード <3 の場合は None）。
    - rank: 同順位は平均ランクにするランク化実装（丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の算出。
  - data.stats の zscore_normalize を再エクスポート。

### Fixed
- DB 書き込み時の安全性や部分失敗保護
  - ai_scores / market_regime の書き込みで `DELETE` → `INSERT` の置換パターンを採用し、部分失敗時に既存データを不必要に削除しないように実装。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）を明示的に使い、ROLLBACK の失敗をログ出力して上位に例外を伝播。

- OpenAI API 呼び出しに対するエラー処理の強化
  - RateLimitError / APIConnectionError / APITimeoutError / 5xx に対する指数バックオフリトライを実装。
  - JSON パース失敗時のフォールバック処理やパース例外でサービス全体が止まらないように設計。

### Changed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の未設定時に秘密情報（API キー等）を強制的に要求する実装（Settings の _require により ValueError を投げる）。公開リポジトリ等での .env 管理に注意。

### Known issues / 備考（設計上の注意）
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY に依存。未設定の場合は ValueError を発生するため、運用前に環境変数設定が必須。
- DuckDB の executemany に空リストを渡せない制約（DuckDB 0.10）を考慮したガードを実装している（空パラメータチェック）。
- time / date の扱いはルックアヘッドバイアス防止のため、内部で datetime.today() / date.today() を参照しない実装方針が採られている（target_date を明示的に渡す API）。
- 一部モジュールは外部クライアント（jquants_client, OpenAI）に依存するため、テスト時は patch により外部呼び出しを差し替えることを想定している。
- news_nlp と regime_detector は OpenAI 呼び出し関数を独立実装しており、モジュール間で private 関数を共有しないことで結合度を低くしている。

---

これ以降のリリースでは、各モジュールの API 変更、新しい ETL ジョブ、戦略（strategy）・実行（execution）・監視（monitoring）関連の実装を個別に記録してください。