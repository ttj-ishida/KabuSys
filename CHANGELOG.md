# Changelog

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-03
最初の公開リリース。

### Added
- パッケージ初期化とバージョン情報
  - pakage: kabusys、バージョン `0.1.0` を追加。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込みを実装。
  - 自動ロードの探索はパッケージファイル位置から行い、.git または pyproject.toml をプロジェクトルート判定に使用（CWD 非依存）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - export 形式やクォート・エスケープ、インラインコメントなどを考慮した .env パーサを実装。
  - Settings クラスでアプリ設定をプロパティとして公開（J-Quants / kabu ステーション / LINE / DB パス / 監視設定 / システム環境等）。
  - 必須環境変数未設定時は明確な例外メッセージを送出する _require 実装。
  - 有効な環境（development, paper_trading, live）やログレベルのバリデーションを実装。

- AI モジュール（kabusys.ai）
  - ニュースNLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を基に記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）の JSON Mode でバッチスコアリング。
    - バッチサイズ上限、1銘柄あたりの記事数・文字数上限、JST 時間ウィンドウ（前日15:00〜当日08:30）計算ロジックを実装。
    - API 呼び出しに対するリトライ（429・ネットワーク断・タイムアウト・5xx を対象）と指数バックオフ、失敗時にスキップして継続するフェイルセーフ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、コード照合、数値検証、±1.0 クリップ）。
    - 成果物は ai_scores テーブルへ冪等的に保存（対象コードのみ DELETE → INSERT）する実装。
    - テスト時に OpenAI 呼び出しを差し替え可能な設計（_call_openai_api を patch 可能）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロニュース抽出用キーワードリストと最大記事数制限、LLM 呼び出しのリトライ/フェイルセーフを実装。
    - レジームスコア合成と閾値によるラベル付け、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - 設計上、ルックアヘッドバイアスを避けるために datetime.today()/date.today() を参照しない等の対策を実施。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB 登録が無い場合は曜日ベースのフォールバック（土日非営業）を行う一貫した挙動。
    - 最大探索日数や健全性チェック、JPX カレンダーの夜間差分取得ジョブ（calendar_update_job）を実装。
    - market_calendar が一部しか登録されていない場合でも整合的に補完できるよう設計。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - 差分更新、jquants_client 経由での安全な保存（idempotent）、品質チェックフレームワーク連携を想定した ETL 設計。
    - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラー等を構造化して返却。
    - backfill による直近再取得（後出し修正吸収）やカレンダー先読み等の運用上の考慮を実装。

  - jquants_client と連携するためのインターフェースを利用する設計（fetch/save 関数呼び出しを想定）。

- 研究用モジュール（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）、Liquidity（20 日平均売買代金、出来高比率）等の定量ファクター計算を実装。
    - DuckDB 上で SQL と Python を組み合わせて計算し、(date, code) ベースの辞書リストを返却。
    - データ不足時の None 扱いやログ出力等の挙動を明示。
  - feature_exploration
    - 将来リターン計算（任意ホライズン）、IC（Spearman のランク相関）計算、rank ユーティリティ、統計サマリー関数を実装。
    - pandas 等の外部依存は使わず標準ライブラリのみで実装。

- 共通ユーティリティ
  - DuckDB と連携する各関数は、部分失敗時に既存データを守るために書込前の DELETE 操作や executemany の空引数回避など、DuckDB の互換性を考慮した実装を採用。
  - OpenAI との統合は gpt-4o-mini を想定、JSON Mode を利用して整形済み JSON を受け取る運用を前提としている。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- API キーなどのシークレットは環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）で管理する設計。
- .env 自動ロードはテスト用途により明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Design decisions（重要な設計上の注意）
- ルックアヘッドバイアス対策: date ベースの処理は必ず外部から target_date を受け取り、内部で datetime.today()/date.today() を参照しない設計。
- フェイルセーフ: OpenAI API 失敗やデータ不足時には例外を投げずに安全なデフォルト（0.0 や None、スキップ）で継続する箇所があるため、本番運用ではログと戻り値を確認すること。
- DuckDB 互換性: executemany に空リストを渡さない等の回避策を実装。
- 冪等性: DB 書き込みは可能な限り冪等（DELETE → INSERT など）にして部分失敗時の既存データ保護を行う。

---

参考:
- 必要な主な環境変数: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings を参照）
- AI モデル: gpt-4o-mini（JSON Mode）
- DB: DuckDB を想定（ai_scores, raw_news, prices_daily, raw_financials, market_calendar 等のテーブルを前提）