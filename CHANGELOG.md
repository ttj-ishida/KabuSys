# CHANGELOG

すべての注目すべき変更はこのドキュメントに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

なお、この CHANGELOG はリポジトリ内の現在のコードベースから機能/設計を推測して作成したものであり、実際のコミット履歴に基づくものではありません。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース

### 追加 (Added)
- パッケージ基盤
  - `kabusys` パッケージの初期公開（__version__ = "0.1.0"）。
  - パッケージ公開対象モジュール: data, strategy, execution, monitoring。

- 設定 / 環境変数管理 (`kabusys.config`)
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - .env/.env.local ファイルの自動読み込み機能を実装（優先順位: OS 環境 > .env.local > .env）。
  - `.env` パーサの強化:
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理に対応。
    - 無効行やキー無し行は無視。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途）。
  - `Settings` クラスを追加:
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティを提供。
    - `env` / `log_level` の値検証（許容値チェック）。
    - `is_live` / `is_paper` / `is_dev` 補助プロパティ。
    - 必須環境変数未設定時に `_require` が ValueError を投げる挙動。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - 原始ニュース（raw_news）を銘柄ごとに集約し、OpenAI（gpt-4o-mini）を用いてセンチメントを算出して `ai_scores` テーブルへ書き込む処理を実装。
    - タイムウィンドウ（JST 前日15:00～当日08:30 → UTC に変換）計算ユーティリティを提供。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事数・文字数のトリム、JSON Mode を用いたレスポンス検証を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーションと ±1.0 のクリッピング。
    - DuckDB の executemany の制約を踏まえ、部分書き換え（DELETE→INSERT）で冪等性を維持。
    - テスト用に OpenAI 呼び出しを差し替え可能（_call_openai_api の patch を想定）。

  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（target_date 未満のデータのみを使用し、データ不足時は中立値 1.0 を採用）。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - 結果を `market_regime` テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時に ROLLBACK）。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。

- Data / ETL / カレンダー (`kabusys.data`)
  - ETL パイプライン (`kabusys.data.pipeline`)
    - ETL 実行結果を表すデータクラス `ETLResult` を追加（取得数・保存数・品質チェック結果・エラー等を保持）。
    - テーブル存在チェック・最大日付取得などの内部ユーティリティを提供。
    - 差分更新、バックフィル、品質チェックの設計方針が反映（実装の骨格）。
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーを扱う夜間バッチ job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → 保存（ON CONFLICT DO UPDATE）を想定。
    - 営業日判定 API を提供:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar の有無にかかわらず一貫したフォールバック（DB がない場合は土日ベース）を実装。
    - 最大探索日数制限やバックフィル／健全性チェックを実装。

- Research（因子・特徴量解析） (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、出来高/売買代金指標）、Value（PER・ROE）の計算関数を実装。
    - DuckDB を用いた SQL + Python 実装。prices_daily / raw_financials のみ参照し外部 API に依存しない。
    - データ不足時の None 処理やログ出力。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算（calc_forward_returns）: 与えられた horizon リストに対してまとめて計算する実装。
    - IC（Information Coefficient）計算（Spearman の ρ）: rank の実装を含む。
    - factor_summary: 各カラムの count/mean/std/min/max/median を返すユーティリティ。
    - pandas 等に依存せず標準ライブラリ+DuckDB で実装。

- 汎用 / 細部設計
  - DuckDB を主要なローカル分析 DB として利用（クエリは DuckDB 特性に配慮して実装）。
  - API 呼び出しの失敗に対する「フェイルセーフで続行」設計（LLM エラーであっても全体処理を停止しない）。
  - ルックアヘッドバイアス防止: 各スコア/判定/ETL は内部で datetime.today()/date.today() を直接参照しないように設計（target_date を明示的に渡す）。

### 修正 (Changed)
- 初版のため目立った後方互換性破壊や移行は無し。  
  （今後、API の変更や DB スキーマ追加時に Breaking 変更を明記予定）

### 修正済みのバグ (Fixed)
- （初版リリースのため過去のバグ修正履歴は無し。実装段階で既知の落とし穴を回避するための防御的コードを多数導入）
  - DuckDB executemany の空リスト制約に対する防御（空リストを渡さないチェックを追加）。
  - OpenAI レスポンスの JSON に前後余計なテキストが混入する場合の復元/パース処理を追加。

### 警告・注記 (Notes)
- 環境変数
  - OpenAI API キーは関数引数で明示的に渡すことも、環境変数 `OPENAI_API_KEY` を利用することも可能。未設定時は ValueError を送出する箇所があるため注意。
  - 自動 .env ロードはデフォルトで有効。CI/テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化可能。
- 必要な DB テーブル（想定）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など。これらのスキーマはコード内部で期待されるカラム名に基づく（例: raw_news.datetime は UTC）。
- OpenAI 呼び出し
  - gpt-4o-mini を前提とした JSON Mode を使用する設計。SDK/API の挙動変化に備え、status_code の扱い等で互換性を考慮した実装になっている。
- フェイルセーフ
  - LLM 呼び出しや外部 API の失敗は基本的に例外を上位に投げず、ログ出力→フォールバック（スコア 0.0 等）で処理継続する設計。ただし DB 書き込み失敗は上位に伝播するため注意。

### 既知の制約 / 今後の改善候補 (Known limitations / Future)
- OpenAI のレスポンス仕様やモデル変更に依存するため、将来の SDK/モデル変更で振る舞いが変わる可能性がある（tests/mocks の整備・抽象化強化が望ましい）。
- ai_score のスキーマや保存ロジックは現在 sentiment_score と ai_score を同値で書き込むフェーズ。将来的な拡張（複数モデル・メタデータ保存）を想定した拡張が必要。
- coverage やユニットテストは各 _call_openai_api の差し替えを想定しているが、実際のテストスイート整備が必要。

---

このリリースはコードベースから推測して作成した CHANGELOG です。実際のコミットログや設計文書と差異がある可能性があるため、必要に応じて追記・修正してください。