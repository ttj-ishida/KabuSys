# CHANGELOG

すべての主な変更をこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初期公開リリース。以下の主要機能・実装が含まれます。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを初期化。バージョンを 0.1.0 として定義。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める（__all__）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - .env ファイルの柔軟なパース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 環境変数保護（既存 OS 環境変数を protected として上書き制御）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 設定アクセス用 Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境切替 / ログレベル 等）。
  - 必須キー未設定時に明示的エラーを送出する _require ユーティリティ。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- AI モジュール: ニュース NLP (kabusys.ai.news_nlp)
  - raw_news / news_symbols を用いて銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
  - 日次対象ウィンドウ計算（JST基準で前日15:00〜当日08:30、DBは UTC 想定）。
  - バッチ処理（最大 20 銘柄 / チャンク）、記事数・文字数トリムによるトークン肥大化対策。
  - JSON Mode を用いた厳格なレスポンス期待・レスポンスバリデーション実装（results リスト、code/score 検証、数値クリップ）。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
  - API失敗やパース失敗時はフェイルセーフでスキップし、例外を上げず処理継続（ログ出力）。
  - DuckDB 互換性考慮（executemany に対する空リストチェックなど）。
  - テスト容易性のため _call_openai_api を patch できる設計。

- AI モジュール: 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - prices_daily / raw_news / market_regime を用いた計算および冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - LLM 呼び出しは独立実装、API エラー時は macro_sentiment=0.0 にフォールバック。
  - リトライ・バックオフ、JSON パースエラー・API エラー処理の実装。
  - ルックアヘッドバイアス防止（target_date 未満のみ使用、date.today() を参照しない）。

- 研究（Research）モジュール (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリューファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - calc_value: raw_financials と結合して PER / ROE を算出（最新財務レコードを使用）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターン取得（LEAD を使用）。
    - calc_ic: スピアマン（ランク）相関による IC 計算（3件未満は None）。
    - rank: 同順位は平均ランクとするランク関数（round による丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median 等の統計量サマリ計算。
  - 研究ユーティリティは DuckDB を直接参照し外部 API や発注機能にはアクセスしない設計。

- データ（Data）モジュール (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブル読み書き、JPX/J-Quants 由来想定）。
    - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - カレンダー未取得時の曜日ベースフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得して冪等保存、バックフィルと健全性チェック実装。
  - ETL / pipeline:
    - ETLResult データクラスを実装（取得数、保存数、品質問題一覧、エラー一覧を保持）。
    - pipeline モジュール設計に基づく差分取得・保存・品質チェックのためのユーティリティを実装（ETLResult をエクスポート）。
    - デフォルトのバックフィル日数・カレンダー先読み等の定義。
    - DuckDB テーブル存在チェック・最大日付取得等のヘルパを提供（DuckDB 互換性を考慮）。

### 変更 (Changed)
- 初期リリースのため変更履歴なし（以降のリリースで差分を記載）。

### 修正 (Fixed)
- 初期リリースのため修正履歴なし。

### 注記 (Notes)
- セキュリティ / 実運用に関する注意
  - OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で供給する必要がある（未設定時は ValueError）。
  - .env 自動ロードはデフォルトで有効。テスト時などには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 設計方針のハイライト
  - ルックアヘッドバイアスを避けるため date.today() を多くの処理で参照しない設計。
  - LLM 呼び出しに対するフェイルセーフ（API失敗時のスコアデフォルトや部分的なスキップ）。
  - DB 書き込みはなるべく冪等（DELETE→INSERT 等）にして部分失敗時のデータ破壊を避ける。
  - DuckDB の実装差異（executemany の空リストなど）を考慮した防御的実装。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充（現時点ではパッケージ __all__ に名前を含むが詳細未提供）。
- 単体テスト・結合テストの追加（OpenAI 呼び出しのモックを用いたテストケース）。
- 性能改善（大規模記事・銘柄数へのスケール対応）。

---
生成はソースコードの実装内容から推測しています。必要であれば、より詳細な変更点（関数ごとの実装要約や既知の制約）を追記します。