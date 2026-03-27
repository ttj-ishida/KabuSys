# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本 CHANGELOG は与えられたソースコードから機能・設計意図を推測して作成したもので、実際のコミット履歴ではありません。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージを導入。メインのサブパッケージとして data, research, ai, execution, strategy, monitoring を想定した __all__ を公開。

- 環境設定 / ロード機構（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により、CWD に依存せず .env を探索。
  - .env の行パーサを実装:
    - 空行・コメント行対応、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォートなしの値では inline コメント（#）を適切に無視。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
  - Settings クラスを公開（settings）:
    - J-Quants, kabuステーション, Slack, DB パス等のプロパティを提供（必須項目は未設定時に ValueError を送出）。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証を実装。
    - duckdb/sqlite のデフォルトパスを提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - 時間ウィンドウ：前日15:00 JST ～ 当日08:30 JST（内部は UTC naive を使用）。
    - バッチ・制限:
      - 1 API コールあたり最大 20 銘柄（_BATCH_SIZE）。
      - 1 銘柄あたり最大 10 件の記事、最大 3000 文字でトリム。
    - OpenAI 呼び出しは JSON Mode を利用。レスポンスのバリデーションとスコアの ±1.0 クリップを実装。
    - エラー耐性: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ（最大試行回数設定）。それ以外はスキップして処理継続。
    - DuckDB への書き込みは部分失敗時に既存データを保護するため、対象 code のみ DELETE → INSERT を行う冪等処理。
    - テスト用に _call_openai_api をパッチ差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロニュースはマクロキーワード（日本・米国関連）でフィルタして取得、最大 20 記事までを渡す。
    - OpenAI 呼び出しに対してリトライ・フォールバック（API 失敗時 macro_sentiment=0.0）を実装。
    - レジームスコアの計算・ラベル付け後に market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。
    - ルックアヘッドバイアス回避のため datetime.today() を参照せず、target_date 未満のみのデータを利用。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースでフォールバック（週末は非営業日扱い）。
    - calendar_update_job を実装し J-Quants から差分取得して market_calendar を冪等的に更新。バックフィルと健全性チェックを実装。
    - 探索範囲の上限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - 差分取得→保存（jquants_client の save_* 関数を使用）→品質チェック の流れをサポートする基本構造を実装。
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラー集約、has_errors / has_quality_errors / to_dict を提供）。
    - 最小データ日（_MIN_DATA_DATE）、カレンダー先読み、デフォルトバックフィル日数などの挙動を定義。
    - DuckDB 特有の制約に配慮（executemany に空リストを投げない等）。

  - etl モジュールから ETLResult を再エクスポート。

- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR、平均売買代金、出来高比率）等を DuckDB 上の SQL で算出する関数を提供（calc_momentum, calc_value, calc_volatility）。
    - データ不足時は None を返す仕様。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - pandas 等の外部依存を使わず標準ライブラリ + SQL で実装。
  - kabusys.data.stats の zscore_normalize を再エクスポート。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。ただし全体として以下の堅牢化が行われている:
  - OpenAI API 呼び出しのエラー分類に基づくリトライ実装（RateLimit, APIConnectionError, APITimeoutError, 5xx の再試行）。
  - DB 書き込み中の例外時に ROLLBACK を行い、ROLLBACK 失敗をログ出力することで安全性を高める実装。
  - JSON レスポンスのパース失敗に対するフォールバック（文字列内の最外側の {} を抽出して再パース）を実装。

### Security
- 環境変数による機密情報管理を想定（OpenAI API キー、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）。自動 .env ロードは必要に応じて無効化可能。

### Notes / Migration
- 必須環境変数:
  - OPENAI_API_KEY（AI 機能使用時）、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等は Settings から参照され、未設定時は ValueError を送出します。
- DuckDB のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が前提です。スキーマが揃っていることを確認してください。
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を使用する設計です。レスポンス仕様が変わるとパースに影響します。
- テスト容易性のため、OpenAI 呼び出し箇所（_call_openai_api）を unittest.mock.patch 等で差し替え可能です。
- すべての時刻関連ロジックはルックアヘッドバイアスを避けるために date/target_date ベースで実装されています（datetime.today() の直接参照を回避）。

### Breaking Changes
- 初版リリースのため該当なし。

---

今後のリリースでは、上記機能の安定化、追加のデータコネクタ、戦略および実行モジュールの拡充、監視・アラート機能の追加を予定しています。必要があればリリースノートの粒度をさらに細かく分けて記載します。