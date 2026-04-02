# Changelog

すべての注目すべき変更点を Keep a Changelog 準拠の形式で日本語で記載します。

タグ付けされたリリース
- 0.1.0 — 2026-04-02

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-02

初回公開リリース。日本株自動売買システム「KabuSys」のコアライブラリを実装しました。主な追加点・設計方針・既知の注意点を以下にまとめます。

### Added
- パッケージ基礎
  - src/kabusys/__init__.py: パッケージの version と公開サブパッケージを定義。
- 設定・環境変数管理
  - src/kabusys/config.py:
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env, .env.local の読み込み順序、OS 環境変数の保護（protected set）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - .env パースの詳細実装（export 形式・クォート内エスケープ・インラインコメント処理）。
    - Settings クラス（J-Quants / kabuステーション / Slack / DB / 監視 / システム設定用プロパティ）。
    - 必須キー未設定時には ValueError を送出する _require ヘルパー。
    - 有効化された設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL）。
- AI（LLM）機能
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事を銘柄別に集約し OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメントを算出し ai_scores テーブルへ保存する処理を実装。
    - バッチ処理（最大20銘柄/回）、トークン肥大対策（記事数・文字数トリム）、リトライ（指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ。
    - calc_news_window(target_date) による JST ベースのニュースウィンドウ計算（前日15:00〜当日08:30 JST -> UTC に変換して DB 比較）。
    - テスト用フック: OpenAI 呼び出し部分を patch 可能に実装（kabusys.ai.news_nlp._call_openai_api をモック可）。
    - API キー未設定時は ValueError を送出。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で算出し market_regime テーブルに書き込む処理を実装。
    - prices_daily / raw_news を参照、OpenAI 呼び出しは独自実装でモジュール結合を低く保つ。
    - フェイルセーフ: API 失敗時は macro_sentiment = 0.0 を採用。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を採用。
    - API 呼び出しリトライ、5xx 判定、JSON パース失敗時の安全なフォールバックを実装。
    - API キー未設定時は ValueError を送出。
- データプラットフォーム（ETL / カレンダー）
  - src/kabusys/data/pipeline.py:
    - ETLResult データクラスを実装（ETL 実行結果、品質チェック結果、エラー一覧、ヘルパーメソッド to_dict）。
    - 差分取得のためのヘルパー（テーブル存在確認、最大日付取得等）。（実装途中やユーティリティを含む）
    - backfill / lookahead / 品質チェック方針をコードで明示。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult の再エクスポート。
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar）ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - calendar_update_job により J-Quants からの差分取得と保存（バックフィル・健全性チェックを含む）。
    - DB 未登録日は曜日ベースのフォールバック（週末は非営業日）で一貫性を保つ。
    - 最大探索日数制限で無限ループを防止。
    - jquants_client を使用して外部 API とのやり取りを想定（依存は分離）。
- リサーチ機能（ファクター / 特徴量探索）
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB SQL を主体とした処理で外部 API へはアクセスしない設計。
    - データ不足時は None を返す等の堅牢性を確保。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient: calc_ic）計算、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず、純 Python / DuckDB で実装。
  - src/kabusys/research/__init__.py:
    - 主要関数の再エクスポートを提供。
- データユーティリティ
  - src/kabusys/data/__init__.py: パッケージ存在のみ（将来的な公開 API の拡張を想定）。
- その他
  - テストしやすさのため、OpenAI 呼び出し箇所の差し替えポイントを明示（_call_openai_api をモック）。

### Changed
- 初公開のため該当なし。

### Fixed
- 初公開のため該当なし。

### Deprecated
- 初公開のため該当なし。

### Removed
- 初公開のため該当なし。

### Security
- 環境変数読み込みはデフォルトで .env を取り込むが、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストや CI でのキー漏洩防止に利用）。
- OpenAI API キーは引数で注入可能（テスト容易性／キー漏洩リスク低減）。

### Notes / 実装上の重要な挙動（ユーザー向け）
- 必須環境変数（Settings が参照する主なキー）
  - JQUANTS_REFRESH_TOKEN（J-Quants 用）
  - KABU_API_PASSWORD（kabuステーション API）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知）
  - OPENAI_API_KEY（news_nlp.score_news / regime_detector.score_regime のデフォルト）
- 自動読み込みするファイル: プロジェクトルート（.git または pyproject.toml 検出）配下の .env → .env.local（.env.local は .env の上書き）
- DuckDB に期待されるテーブル（主要関数で参照されるもの）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など
- OpenAI 呼び出し
  - デフォルトモデル: gpt-4o-mini（JSON mode を利用）
  - news_nlp: バッチサイズ 20、1銘柄あたり最大 10 記事/3000 文字でトリム
  - regime_detector: ETF 1321 の 200 日 MA に基づく指標とマクロセンチメントを合成（MA 重み 0.7、マクロ 0.3）
  - 失敗時は例外をすべて上位に投げるわけではなく（特に LLM の応答／パース失敗はフォールバックして継続する）
- テーブルへの書き込みは冪等性を意識（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK の使用）
- 時刻・日付の扱い
  - ルックアヘッドバイアス防止のため関数内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）
  - ニュースウィンドウは JST を基準に計算し、DB 内の日付は UTC naive datetime で扱う設計想定
- テスト向け仕様
  - OpenAI 呼び出しをモック可能（kabusys.ai.news_nlp._call_openai_api, kabusys.ai.regime_detector._call_openai_api）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により .env 自動読み込みを抑制可能

### Upgrade notes / 互換性
- 初回リリースのため互換性問題はなし。ただし次バージョンで public API の変更（関数シグネチャ、返り値形式、データベーススキーマ等）を行う可能性があります。ETLResult の構造や ai_scores / market_regime のカラム構成を運用に合わせて保持してください。

### Known limitations / 今後の改善候補
- ETL pipeline は high-level の方針と結果オブジェクトを実装済みだが、ジョブスケジューリングや完全な差分ロジックのエンド・ツー・エンド統合テストは必要。
- OpenAI 利用に関するレート制御やコスト管理の追加機能（キューイング、より細かいレート制限の制御など）。
- raw_financials に基づく PBR や配当利回りの計算は未実装（calc_value の拡張候補）。
- DuckDB とのバインドの互換性（executemany の挙動など）に対する追加テスト。

---

このリリースはコードベースから推測して生成しています。実際のリリースノート作成時は、コミットログ・Issue・PR の情報を参照して差分を調整してください。必要であれば、各機能（AI スコアリング、ETL、calendar 等）ごとの例や使用方法、期待される DB スキーマの詳細を追記します。