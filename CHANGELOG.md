# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-04

初回公開リリース。以下の主要機能・設計方針・実装上の注意点を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（バージョン 0.1.0）。
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0"。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - OS の既存環境変数は protected として上書きされない。
  - .env パーサーの強化:
    - export KEY=val 形式対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォート無しの行でのインラインコメント認識（直前が空白/タブの場合）。
  - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル等）。
  - 設定値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）、必須環境変数未設定時は明示的な例外を返す。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp.score_news)
    - raw_news と news_symbols を用い、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini, JSON mode）へバッチ送信。
    - バッチサイズ 20、1 銘柄あたり最大記事数・文字数の上限を設定（トークン肥大化対策）。
    - 再試行戦略（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、code の正規化、スコア数値チェック）。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ idempotent に書き込み（DELETE → INSERT）。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）、ルックアヘッドバイアス対策。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）。
  - 市場レジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini, JSON mode）、再試行・フォールバック（API 失敗時 macro_sentiment=0.0）。
    - レジームスコアはクリップされ、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 動作設計上、datetime.today()/date.today() を直接参照せず target_date 引数ベースで処理。

- データプラットフォーム & ETL (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを用いた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、is_trading_day 等のユーティリティ。
    - DB 登録値優先、未登録日は曜日（週末）ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants から差分取得して冪等に保存。バックフィルと健全性チェックを実装。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスによる ETL 実行結果の集約（取得件数、保存件数、品質問題、エラー等）。
    - 差分更新、保存（jquants_client による idempotent 保存）、品質チェック（quality モジュール）を想定した実装骨子。
    - ETL の設計方針として「backfill による後出し修正吸収」「品質チェックは収集し呼び出し側が対処」「id_token 注入でテスト可能」を明記。

- リサーチモジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の算出（prices_daily のみ参照）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率の算出。
    - calc_value: EPS に基づく PER、ROE の算出（raw_financials と prices_daily を結合）。
    - すべて DuckDB 上で SQL＋Python により実行、外部 API にはアクセスしない設計。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得するロジック。
    - calc_ic: スピアマン（ランク）相関による IC 計算（結合・欠損削除・最小サンプル数チェック）。
    - rank, factor_summary: ランク変換（同順位は平均ランク）、列の基本統計量（count/mean/std/min/max/median）を算出。
    - pandas 等の外部依存なしで標準ライブラリと DuckDB のみで実装。

- logging / 設計上の堅牢性
  - 各モジュールで詳細なログ出力を実装（info/debug/warning/exception）。
  - DB 書き込み時のトランザクション保護（BEGIN/COMMIT/ROLLBACK）と ROLLBACK 失敗時の警告ロギング。
  - API 呼び出し失敗時のフェイルセーフ（例外を投げずにフォールバックやスキップする箇所を多数実装）により部分失敗時もシステムの継続運用を優先。

### Changed
- 初版につき該当なし。

### Fixed
- 初版につき該当なし（ただし実装には多くの防御的挙動・フォールバックが組み込まれています）。

### Security
- 環境変数管理:
  - OS 環境変数を保護する仕組み（.env の上書きを防ぐ protected set）を導入。
  - OpenAI API キーや各種機密情報は明示的に必須チェックを行い、未設定の場合は ValueError を送出。
  - 自動ロードを外すための KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト時の誤読防止）。

### Notes / Implementation choices
- ルックアヘッドバイアス防止:
  - AI / データ処理関数はすべて target_date を受け取り、date.today() を直接参照しない方針。
- DuckDB 互換性考慮:
  - executemany に空リストを渡すと失敗するバージョン対策（空チェックを挟む等）。
- OpenAI 呼び出し:
  - gpt-4o-mini を前提とした JSON mode での呼び出し、レスポンスの堅牢なパースとクリップ処理を実装。
  - モジュール間でプライベート API 呼び出し関数を共有せず、テストのために差し替え可能な設計（_call_openai_api を patch で差替え可）。

---

既知の制約・今後の改善候補（非網羅）
- 一部機能は外部サービス（J-Quants、OpenAI、kabuステーション）に依存。API の仕様変更やレート制限に注意。
- PBR・配当利回りなどのバリューファクターの拡張は未実装。
- strategy / execution / monitoring パッケージの実装状況に応じて公開 API が変動する可能性あり。

（以上）